"""
수정 요약
- 목표 비중과 남아 있는 누적 투입 원가를 기준으로 신규 매수 허용 금액을 계산하는 포트폴리오 배분 모듈을 추가
- 거래량과 추세 품질이 강한 코인만 목표 비중을 보수적으로 +5% 확대하는 동적 오버웨이트를 지원하도록 추가
- 거래소별 잔고 조회와 체결 이력 기반 원가 추적을 함께 처리해 BTC/ETH/XRP 목표 비중을 공통 규칙으로 맞추도록 구성
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from strategy_settings import parse_bool, parse_symbol_float_map


@dataclass(frozen=True)
class PortfolioAllocationSettings:
    """포트폴리오 배분 설정."""

    target_allocations: dict[str, float]
    enable_dynamic_overweight: bool
    dynamic_max_bonus_pct: float
    dynamic_volume_ratio_threshold: float
    dynamic_require_trend_ok: bool
    dynamic_require_strong_signal: bool


@dataclass(frozen=True)
class AllocationDecision:
    """특정 코인 신규 매수 허용 금액 계산 결과."""

    base_asset: str
    base_target_pct: float
    effective_target_pct: float
    dynamic_bonus_pct: float
    current_cost_basis_quote: float
    total_portfolio_quote: float
    target_budget_quote: float
    remaining_budget_quote: float
    approved_order_value_quote: float
    quote_free: float
    dynamic_bonus_applied: bool
    reason: str


def load_portfolio_allocation_settings() -> PortfolioAllocationSettings:
    """환경 변수에서 포트폴리오 배분 설정을 읽는다."""
    load_dotenv()
    return PortfolioAllocationSettings(
        target_allocations=parse_symbol_float_map(
            os.getenv("PORTFOLIO_TARGET_ALLOCATIONS", "BTC:0.60,ETH:0.30,XRP:0.10")
        ),
        enable_dynamic_overweight=parse_bool(
            os.getenv("PORTFOLIO_ENABLE_DYNAMIC_OVERWEIGHT", "true"),
            default=True,
        ),
        dynamic_max_bonus_pct=float(
            os.getenv("PORTFOLIO_DYNAMIC_MAX_BONUS_PCT", "0.05")
        ),
        dynamic_volume_ratio_threshold=float(
            os.getenv("PORTFOLIO_DYNAMIC_VOLUME_RATIO_THRESHOLD", "2.00")
        ),
        dynamic_require_trend_ok=parse_bool(
            os.getenv("PORTFOLIO_DYNAMIC_REQUIRE_TREND_OK", "true"),
            default=True,
        ),
        dynamic_require_strong_signal=parse_bool(
            os.getenv("PORTFOLIO_DYNAMIC_REQUIRE_STRONG_SIGNAL", "true"),
            default=True,
        ),
    )


def _safe_float(value: Any) -> float | None:
    """숫자 후보를 float 로 안전하게 바꾼다."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_targets(targets: dict[str, float]) -> dict[str, float]:
    """양수 비중만 합이 1이 되도록 정규화한다."""
    filtered = {asset: weight for asset, weight in targets.items() if weight > 0}
    total = sum(filtered.values())
    if total <= 0:
        return {}
    return {asset: weight / total for asset, weight in filtered.items()}


def _apply_dynamic_bonus(
    targets: dict[str, float],
    focus_asset: str,
    bonus_pct: float,
) -> dict[str, float]:
    """특정 코인 비중을 bonus 만큼 늘리고 나머지는 비례 축소한다."""
    if focus_asset not in targets or bonus_pct <= 0:
        return dict(targets)

    current_weight = targets[focus_asset]
    others_total = 1.0 - current_weight
    if others_total <= 0:
        return dict(targets)

    applied_bonus = min(bonus_pct, others_total)
    scale = (others_total - applied_bonus) / others_total

    adjusted: dict[str, float] = {}
    for asset, weight in targets.items():
        if asset == focus_asset:
            adjusted[asset] = weight + applied_bonus
        else:
            adjusted[asset] = weight * scale
    return adjusted


def _fetch_okx_balance_map(exchange, assets: list[str]) -> dict[str, float]:
    """OKX 계정 원시 API 로 여러 자산 잔고를 읽는다."""
    res = exchange.privateGetAccountBalance({})
    data = res.get("data", []) if isinstance(res, dict) else res
    if not data:
        return {asset: 0.0 for asset in assets}

    wanted = set(assets)
    balances = {asset: 0.0 for asset in assets}
    for item in data[0].get("details", []):
        asset = str(item.get("ccy", "")).strip()
        if asset not in wanted:
            continue
        balances[asset] = float(item.get("availBal", 0.0))
    return balances


def _fetch_upbit_balance_map(exchange, assets: list[str]) -> dict[str, float]:
    """업비트 잔고를 여러 자산 기준으로 읽는다."""
    balance = exchange.fetch_balance()
    balances = {asset: 0.0 for asset in assets}
    for asset in assets:
        balances[asset] = float(balance.get(asset, {}).get("free", 0.0))
    return balances


class PortfolioAllocator:
    """체결 이력 기준 누적 원가와 목표 비중으로 신규 매수 한도를 계산한다."""

    def __init__(
        self,
        *,
        exchange_name: str,
        quote_currency: str,
        tracked_symbols: list[str],
        refresh_interval_sec: int = 5,
    ) -> None:
        self.exchange_name = exchange_name.upper()
        self.quote_currency = quote_currency
        self.refresh_interval_sec = refresh_interval_sec
        self.settings = load_portfolio_allocation_settings()
        tracked_assets = {
            symbol.split("/", 1)[0]
            for symbol in tracked_symbols
            if "/" in symbol
        }
        self.target_assets = sorted(
            tracked_assets.intersection(self.settings.target_allocations.keys())
        )
        self._last_refresh_at = 0.0
        self._last_seen_signature: tuple[tuple[str, float], ...] = ()
        self._cost_basis_by_asset: dict[str, float] = {asset: 0.0 for asset in self.target_assets}

    def _compute_signature(self) -> tuple[tuple[str, float], ...]:
        """trade_history 파일들의 수정 시각 시그니처를 만든다."""
        signature: list[tuple[str, float]] = []
        for path in sorted(Path("trade_logs").rglob("trade_history.jsonl")):
            try:
                signature.append((str(path), path.stat().st_mtime))
            except FileNotFoundError:
                continue
        return tuple(signature)

    def _refresh_cost_basis_if_needed(self) -> None:
        """체결 이력 기준 누적 원가 캐시를 필요할 때만 갱신한다."""
        now = time.time()
        signature = self._compute_signature()
        if (
            signature == self._last_seen_signature
            and (now - self._last_refresh_at) < self.refresh_interval_sec
        ):
            return

        position_amount_by_asset = {asset: 0.0 for asset in self.target_assets}
        cost_basis_by_asset = {asset: 0.0 for asset in self.target_assets}

        for path, _ in signature:
            text = Path(path).read_text(encoding="utf-8")
            for line in text.splitlines():
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(record.get("exchange", "")).upper() != self.exchange_name:
                    continue
                base_asset = str(record.get("base_currency", "")).strip()
                if base_asset not in cost_basis_by_asset:
                    continue

                amount = _safe_float(record.get("amount")) or 0.0
                order_value_quote = _safe_float(record.get("order_value_quote")) or 0.0
                side = str(record.get("side", "")).lower()

                if side == "buy":
                    position_amount_by_asset[base_asset] += amount
                    cost_basis_by_asset[base_asset] += order_value_quote
                elif side == "sell":
                    current_amount = position_amount_by_asset[base_asset]
                    current_cost = cost_basis_by_asset[base_asset]
                    if current_amount <= 0 or current_cost <= 0:
                        position_amount_by_asset[base_asset] = max(0.0, current_amount - amount)
                        cost_basis_by_asset[base_asset] = 0.0
                        continue
                    sold_ratio = min(1.0, amount / current_amount) if current_amount > 0 else 1.0
                    cost_reduction = current_cost * sold_ratio
                    position_amount_by_asset[base_asset] = max(0.0, current_amount - amount)
                    cost_basis_by_asset[base_asset] = max(0.0, current_cost - cost_reduction)
                    if position_amount_by_asset[base_asset] <= 1e-12:
                        position_amount_by_asset[base_asset] = 0.0
                        cost_basis_by_asset[base_asset] = 0.0

        self._cost_basis_by_asset = cost_basis_by_asset
        self._last_seen_signature = signature
        self._last_refresh_at = now

    def _fetch_balance_map(self, exchange) -> dict[str, float]:
        """대상 자산과 현금 잔고를 읽는다."""
        assets = [*self.target_assets, self.quote_currency]
        if self.exchange_name == "OKX":
            return _fetch_okx_balance_map(exchange, assets)
        return _fetch_upbit_balance_map(exchange, assets)

    def build_buy_decision(
        self,
        *,
        exchange,
        symbol: str,
        requested_order_value_quote: float,
        dynamic_bonus_eligible: bool,
    ) -> AllocationDecision:
        """심볼별 신규 매수 허용 금액을 계산한다."""
        self._refresh_cost_basis_if_needed()

        base_asset = symbol.split("/", 1)[0]
        base_targets = _normalize_targets(
            {
                asset: self.settings.target_allocations.get(asset, 0.0)
                for asset in self.target_assets
            }
        )
        if base_asset not in base_targets:
            return AllocationDecision(
                base_asset=base_asset,
                base_target_pct=0.0,
                effective_target_pct=0.0,
                dynamic_bonus_pct=0.0,
                current_cost_basis_quote=0.0,
                total_portfolio_quote=0.0,
                target_budget_quote=0.0,
                remaining_budget_quote=0.0,
                approved_order_value_quote=0.0,
                quote_free=0.0,
                dynamic_bonus_applied=False,
                reason="asset_not_in_target_allocations",
            )

        balances = self._fetch_balance_map(exchange)
        quote_free = max(0.0, balances.get(self.quote_currency, 0.0))

        active_cost_basis: dict[str, float] = {}
        for asset in self.target_assets:
            asset_balance = balances.get(asset, 0.0)
            tracked_cost = self._cost_basis_by_asset.get(asset, 0.0)
            active_cost_basis[asset] = tracked_cost if asset_balance > 0 else 0.0

        total_portfolio_quote = quote_free + sum(active_cost_basis.values())
        base_target_pct = base_targets.get(base_asset, 0.0)

        dynamic_bonus_pct = 0.0
        if self.settings.enable_dynamic_overweight and dynamic_bonus_eligible:
            dynamic_bonus_pct = self.settings.dynamic_max_bonus_pct
        effective_targets = _apply_dynamic_bonus(base_targets, base_asset, dynamic_bonus_pct)
        effective_target_pct = effective_targets.get(base_asset, 0.0)
        current_cost_basis_quote = active_cost_basis.get(base_asset, 0.0)
        target_budget_quote = total_portfolio_quote * effective_target_pct
        remaining_budget_quote = max(0.0, target_budget_quote - current_cost_basis_quote)
        approved_order_value_quote = min(
            max(0.0, requested_order_value_quote),
            quote_free,
            remaining_budget_quote,
        )

        reason = "ok"
        if total_portfolio_quote <= 0:
            reason = "portfolio_empty"
        elif remaining_budget_quote <= 0:
            reason = "target_budget_exhausted"
        elif approved_order_value_quote <= 0:
            reason = "quote_free_unavailable"

        return AllocationDecision(
            base_asset=base_asset,
            base_target_pct=base_target_pct,
            effective_target_pct=effective_target_pct,
            dynamic_bonus_pct=dynamic_bonus_pct,
            current_cost_basis_quote=current_cost_basis_quote,
            total_portfolio_quote=total_portfolio_quote,
            target_budget_quote=target_budget_quote,
            remaining_budget_quote=remaining_budget_quote,
            approved_order_value_quote=approved_order_value_quote,
            quote_free=quote_free,
            dynamic_bonus_applied=dynamic_bonus_pct > 0,
            reason=reason,
        )
