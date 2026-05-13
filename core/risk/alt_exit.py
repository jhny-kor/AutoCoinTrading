"""
작업 요약
- 최소 주문 경계에서 알트 부분청산을 전량청산으로 승격하거나 주문을 스킵하는 정책을 공통화했다.
- 알트 매도 사유별 청산 비율과 reason key 결정을 공통화했다.
- 무포지션 기본 지표와 부분익절/부분손절 pending 정책 계산을 공통화했다.
- 익절 구간에서 거래량 급감 시 조기 청산하는 Volume Spike Exit 트리거를 추가
- 알트 포지션의 수익률/순익률/MFE/MAE 계산과 청산 보호 판단을 공통화했다.
- 브레이크이븐 가드와 순익 보호 익절 계산을 한 곳으로 모았다.
- MFE 대비 되돌림 폭 기준을 추가해 수익 구간에서 급한 반납을 더 빠르게 정리할 수 있게 보강했다.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from trade_history_logger import estimate_round_trip_net_pnl


@dataclass(frozen=True)
class AltPartialExitPolicy:
    """알트 부분익절/부분손절 적용 상태를 나타낸다."""

    partial_take_profit_pending: bool
    partial_stop_loss_pending: bool
    effective_partial_take_profit_ratio: float


@dataclass(frozen=True)
class AltSellIntent:
    """알트 매도 주문 직전 사용할 청산 의도를 나타낸다."""

    sell_ratio: float
    exit_reason_key: str
    sell_reason: str


@dataclass(frozen=True)
class AltSellOrderPlan:
    """최소 주문 정책 반영 후 실제 제출할 알트 매도 주문 상태를 나타낸다."""

    amount: float
    sell_ratio: float
    exit_reason_key: str
    sell_reason: str
    order_value_quote: float | None = None
    skip_reason: str | None = None
    log_message: str | None = None

    @property
    def should_order(self) -> bool:
        return self.skip_reason is None


def build_empty_position_runtime_metrics() -> dict[str, float | None]:
    """무포지션 경로에서 참조할 기본 포지션 지표를 반환한다."""
    return {
        "pnl_pct": None,
        "mfe_pct": None,
        "mae_pct": None,
        "current_net_realized_pnl_quote": None,
        "current_net_realized_pnl_pct": None,
    }


def compute_alt_position_metrics(
    *,
    has_position: bool,
    average_entry_price: float | None,
    last_close: float,
    base_free: float,
    fee_rate_pct: float,
    highest_price_since_entry: float | None,
    lowest_price_since_entry: float | None,
) -> dict[str, float | None]:
    if not has_position or average_entry_price is None:
        return {
            "highest_price_since_entry": None,
            "lowest_price_since_entry": None,
            "pnl_pct": None,
            "mfe_pct": None,
            "mae_pct": None,
            "net_pnl_quote": None,
            "net_pnl_pct": None,
        }

    updated_high = max(highest_price_since_entry or last_close, last_close)
    updated_low = min(lowest_price_since_entry or last_close, last_close)
    pnl_pct = (last_close - average_entry_price) / average_entry_price * 100
    mfe_pct = ((updated_high - average_entry_price) / average_entry_price) * 100
    mae_pct = ((updated_low - average_entry_price) / average_entry_price) * 100
    (
        _current_fee_quote_estimate,
        current_net_realized_pnl_quote,
        current_net_realized_pnl_pct,
    ) = estimate_round_trip_net_pnl(
        entry_price=average_entry_price,
        exit_price=last_close,
        amount=base_free,
        fee_rate_pct=fee_rate_pct,
    )
    return {
        "highest_price_since_entry": updated_high,
        "lowest_price_since_entry": updated_low,
        "pnl_pct": pnl_pct,
        "mfe_pct": mfe_pct,
        "mae_pct": mae_pct,
        "net_pnl_quote": current_net_realized_pnl_quote,
        "net_pnl_pct": current_net_realized_pnl_pct,
    }


def resolve_alt_partial_exit_policy(
    *,
    symbol: str,
    partial_take_profit_enabled: bool,
    partial_stop_loss_enabled: bool,
    partial_take_profit_done: Mapping[str, bool],
    partial_stop_loss_done: Mapping[str, bool],
    partial_take_profit_ratio: float,
    partial_take_profit_ratio_multiplier: float,
) -> AltPartialExitPolicy:
    """부분익절/부분손절 pending 상태와 적용 비율을 공통 계산한다."""
    return AltPartialExitPolicy(
        partial_take_profit_pending=(
            partial_take_profit_enabled
            and not partial_take_profit_done.get(symbol, False)
        ),
        partial_stop_loss_pending=(
            partial_stop_loss_enabled
            and not partial_stop_loss_done.get(symbol, False)
        ),
        effective_partial_take_profit_ratio=min(
            1.0,
            partial_take_profit_ratio * partial_take_profit_ratio_multiplier,
        ),
    )


def resolve_alt_sell_intent(
    *,
    sell_split_ratio: float,
    stop_loss_triggered: bool,
    partial_stop_loss_pending: bool,
    partial_stop_loss_ratio: float,
    profit_protect_triggered: bool,
    break_even_guard_triggered: bool,
    volume_spike_exit_triggered: bool,
    sol_probe_time_exit_triggered: bool,
    partial_take_profit_pending: bool,
    effective_partial_take_profit_ratio: float,
) -> AltSellIntent:
    """청산 트리거 우선순위에 따라 매도 비율과 reason 코드를 결정한다."""
    if stop_loss_triggered:
        if partial_stop_loss_pending:
            return AltSellIntent(
                sell_ratio=partial_stop_loss_ratio,
                exit_reason_key="partial_stop_loss",
                sell_reason="부분손절",
            )
        return AltSellIntent(
            sell_ratio=1.0,
            exit_reason_key="stop_loss",
            sell_reason="손절",
        )
    if profit_protect_triggered:
        return AltSellIntent(
            sell_ratio=1.0,
            exit_reason_key="profit_protect_take_profit",
            sell_reason="순익보호익절",
        )
    if break_even_guard_triggered:
        return AltSellIntent(
            sell_ratio=1.0,
            exit_reason_key="break_even_guard_take_profit",
            sell_reason="브레이크이븐보호익절",
        )
    if volume_spike_exit_triggered:
        return AltSellIntent(
            sell_ratio=1.0,
            exit_reason_key="volume_spike_take_profit",
            sell_reason="거래량급감익절",
        )
    if sol_probe_time_exit_triggered:
        return AltSellIntent(
            sell_ratio=1.0,
            exit_reason_key="sol_probe_time_exit",
            sell_reason="SOL Probe 시간청산",
        )
    if partial_take_profit_pending:
        return AltSellIntent(
            sell_ratio=effective_partial_take_profit_ratio,
            exit_reason_key="partial_take_profit",
            sell_reason="부분익절",
        )
    return AltSellIntent(
        sell_ratio=sell_split_ratio,
        exit_reason_key="take_profit",
        sell_reason="익절",
    )


def _promote_partial_exit_reason(
    *,
    exit_reason_key: str,
    sell_reason: str,
) -> tuple[str, str]:
    if exit_reason_key == "partial_take_profit":
        return "take_profit", "익절"
    if exit_reason_key == "partial_stop_loss":
        return "stop_loss", "손절"
    return exit_reason_key, sell_reason


def resolve_alt_sell_order_by_min_amount(
    *,
    symbol: str,
    base: str,
    amount: float,
    full_sell_amount: float,
    sell_ratio: float,
    exit_reason_key: str,
    sell_reason: str,
    min_order_amount: float,
) -> AltSellOrderPlan:
    """수량 기준 최소 주문 정책을 반영한 OKX 알트 매도 주문 계획을 만든다."""
    if (
        amount > 0
        and min_order_amount > 0
        and amount < min_order_amount
        and full_sell_amount >= min_order_amount
    ):
        promoted_exit_reason_key, promoted_sell_reason = _promote_partial_exit_reason(
            exit_reason_key=exit_reason_key,
            sell_reason=sell_reason,
        )
        return AltSellOrderPlan(
            amount=full_sell_amount,
            sell_ratio=1.0,
            exit_reason_key=promoted_exit_reason_key,
            sell_reason=promoted_sell_reason,
            log_message=(
                f"[{symbol}] 부분/분할 매도 수량이 최소 주문 수량보다 작아 전량 청산으로 전환합니다."
            ),
        )

    if amount <= 0:
        return AltSellOrderPlan(
            amount=amount,
            sell_ratio=sell_ratio,
            exit_reason_key=exit_reason_key,
            sell_reason=sell_reason,
            skip_reason="no_sell_amount",
            log_message=f"[{symbol}] 매도할 {base} 수량이 없습니다.",
        )

    if min_order_amount > 0 and amount < min_order_amount:
        return AltSellOrderPlan(
            amount=amount,
            sell_ratio=sell_ratio,
            exit_reason_key=exit_reason_key,
            sell_reason=sell_reason,
            skip_reason="sell_amount_below_min_order_amount",
            log_message=(
                f"[{symbol}] 매도 수량 {amount:.8f} {base} 가 거래소 최소 주문 수량 "
                f"{min_order_amount:.8f} {base} 보다 작아 매도를 생략합니다."
            ),
        )

    return AltSellOrderPlan(
        amount=amount,
        sell_ratio=sell_ratio,
        exit_reason_key=exit_reason_key,
        sell_reason=sell_reason,
    )


def resolve_alt_sell_order_by_min_value(
    *,
    symbol: str,
    base: str,
    quote: str,
    amount: float,
    full_sell_amount: float,
    sell_order_value_quote: float,
    full_sell_order_value_quote: float,
    sell_ratio: float,
    exit_reason_key: str,
    sell_reason: str,
    min_sell_order_value: float,
) -> AltSellOrderPlan:
    """금액 기준 최소 주문 정책을 반영한 업비트 알트 매도 주문 계획을 만든다."""
    if (
        amount > 0
        and sell_order_value_quote <= min_sell_order_value
        and full_sell_order_value_quote > min_sell_order_value
    ):
        promoted_exit_reason_key, promoted_sell_reason = _promote_partial_exit_reason(
            exit_reason_key=exit_reason_key,
            sell_reason=sell_reason,
        )
        return AltSellOrderPlan(
            amount=full_sell_amount,
            sell_ratio=1.0,
            exit_reason_key=promoted_exit_reason_key,
            sell_reason=promoted_sell_reason,
            order_value_quote=full_sell_order_value_quote,
            log_message=(
                f"[{symbol}] 부분/분할 매도 금액이 최소 주문 금액보다 작아 전량 청산으로 전환합니다."
            ),
        )

    if amount <= 0:
        return AltSellOrderPlan(
            amount=amount,
            sell_ratio=sell_ratio,
            exit_reason_key=exit_reason_key,
            sell_reason=sell_reason,
            order_value_quote=sell_order_value_quote,
            skip_reason="no_sell_amount",
            log_message=f"[{symbol}] 매도할 {base} 수량이 없습니다.",
        )

    if sell_order_value_quote <= min_sell_order_value:
        return AltSellOrderPlan(
            amount=amount,
            sell_ratio=sell_ratio,
            exit_reason_key=exit_reason_key,
            sell_reason=sell_reason,
            order_value_quote=sell_order_value_quote,
            skip_reason="sell_value_below_min_order_value",
            log_message=(
                f"[{symbol}] 예상 매도 금액이 {min_sell_order_value} {quote} 이하라 매도 주문을 생략합니다."
            ),
        )

    return AltSellOrderPlan(
        amount=amount,
        sell_ratio=sell_ratio,
        exit_reason_key=exit_reason_key,
        sell_reason=sell_reason,
        order_value_quote=sell_order_value_quote,
    )


def compute_alt_exit_decisions(
    *,
    has_position: bool,
    pnl_pct: float | None,
    mfe_pct: float | None,
    current_net_realized_pnl_pct: float | None,
    take_profit_pct: float,
    stop_loss_pct: float,
    fee_rate_pct: float,
    enable_fee_protect_exit: bool,
    fee_protect_min_net_pnl_pct: float,
    enable_break_even_guard: bool,
    break_even_guard_min_mfe_pct: float,
    break_even_guard_floor_net_pnl_pct: float,
    break_even_guard_max_profit_retrace_pct: float,
    enable_volume_spike_exit: bool,
    volume_spike_exit_min_profit_pct: float,
    volume_spike_exit_max_volume_ratio: float,
    volume_ratio: float | None,
    bearish: bool,
    sell_split_ratio: float,
) -> dict[str, float | bool]:
    fee_round_trip_pct = fee_rate_pct * 2
    effective_min_take_profit_pct = max(
        take_profit_pct,
        fee_round_trip_pct * 1.1,
    )
    take_profit_ready = (
        pnl_pct is not None
        and pnl_pct >= effective_min_take_profit_pct
    )
    stop_loss_triggered = (
        pnl_pct is not None
        and pnl_pct <= -stop_loss_pct
    )
    profit_protect_triggered = (
        has_position
        and enable_fee_protect_exit
        and current_net_realized_pnl_pct is not None
        and current_net_realized_pnl_pct >= fee_protect_min_net_pnl_pct
        and bearish
        and not stop_loss_triggered
    )
    break_even_guard_triggered = (
        has_position
        and enable_break_even_guard
        and break_even_guard_min_mfe_pct > 0
        and mfe_pct is not None
        and mfe_pct >= break_even_guard_min_mfe_pct
        and current_net_realized_pnl_pct is not None
        and current_net_realized_pnl_pct <= break_even_guard_floor_net_pnl_pct
        and (
            break_even_guard_max_profit_retrace_pct <= 0
            or (
                pnl_pct is not None
                and (mfe_pct - pnl_pct) >= break_even_guard_max_profit_retrace_pct
            )
        )
        and bearish
        and not stop_loss_triggered
        and not profit_protect_triggered
    )
    volume_spike_exit_triggered = (
        has_position
        and enable_volume_spike_exit
        and current_net_realized_pnl_pct is not None
        and current_net_realized_pnl_pct >= volume_spike_exit_min_profit_pct
        and volume_ratio is not None
        and volume_ratio <= volume_spike_exit_max_volume_ratio
        and bearish
        and not stop_loss_triggered
        and not profit_protect_triggered
        and not break_even_guard_triggered
    )
    estimated_sell_ratio = (
        1.0
        if (
            stop_loss_triggered
            or profit_protect_triggered
            or break_even_guard_triggered
            or volume_spike_exit_triggered
        )
        else sell_split_ratio
    )
    return {
        "fee_round_trip_pct": fee_round_trip_pct,
        "effective_min_take_profit_pct": effective_min_take_profit_pct,
        "take_profit_ready": take_profit_ready,
        "stop_loss_triggered": stop_loss_triggered,
        "profit_protect_triggered": profit_protect_triggered,
        "break_even_guard_triggered": break_even_guard_triggered,
        "volume_spike_exit_triggered": volume_spike_exit_triggered,
        "profit_retrace_from_mfe_pct": (
            None if (mfe_pct is None or pnl_pct is None) else max(0.0, mfe_pct - pnl_pct)
        ),
        "estimated_sell_ratio": estimated_sell_ratio,
    }
