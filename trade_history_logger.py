"""
체결 결과 구조화 로거

- 체결 시 왕복 수수료 추정치를 이용한 순손익 계산 helper 를 함께 제공해 로그 기록 기준을 통일
- strategy_version 을 최상위 필드로 남겨 버전별 성과 비교가 가능하도록 확장
- 진입 후 최고가/최저가, MFE/MAE, 트레일링 활성화 소요 시간 같은 거래 품질 필드도 함께 저장하도록 확장
- 매수, 익절 매도, 손절 매도 체결 결과를 JSONL 형식으로 저장한다.
- 거래소/심볼/수량/금액/손익/원본 주문 응답까지 함께 남겨 나중에 분석하기 쉽게 만든다.
- 결과는 trade_logs/trade_history.jsonl 파일에 누적된다.
- 기존 단일 파일과 함께 structured_logs/live/<program>/trade.jsonl 에도 분리 저장한다.
- 포지션 ID, 트레일링 상태, 예상 수수료 같은 분석용 필드도 함께 저장할 수 있도록 확장한다.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def to_json_safe(value: Any) -> Any:
    """JSON 으로 안전하게 직렬화할 수 있는 형태로 바꾼다."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_json_safe(item) for item in value]
    return str(value)


def estimate_round_trip_net_pnl(
    *,
    entry_price: float | None,
    exit_price: float | None,
    amount: float | None,
    fee_rate_pct: float | None,
    realized_pnl_quote: float | None = None,
) -> tuple[float | None, float | None, float | None]:
    """왕복 수수료를 추정해 순손익 금액과 비율을 계산한다."""
    if (
        entry_price in (None, 0)
        or exit_price in (None, 0)
        or amount in (None, 0)
        or fee_rate_pct in (None, "")
    ):
        return None, None, None

    try:
        entry_price_float = float(entry_price)
        exit_price_float = float(exit_price)
        amount_float = float(amount)
        fee_rate_pct_float = float(fee_rate_pct)
    except (TypeError, ValueError):
        return None, None, None

    if entry_price_float <= 0 or exit_price_float <= 0 or amount_float <= 0:
        return None, None, None

    gross_quote = (
        float(realized_pnl_quote)
        if realized_pnl_quote not in (None, "")
        else (exit_price_float - entry_price_float) * amount_float
    )
    fee_rate = fee_rate_pct_float / 100.0
    fee_quote_estimate = (
        entry_price_float * amount_float * fee_rate
        + exit_price_float * amount_float * fee_rate
    )
    net_realized_pnl_quote = gross_quote - fee_quote_estimate
    entry_notional = entry_price_float * amount_float
    net_realized_pnl_pct = (
        (net_realized_pnl_quote / entry_notional) * 100 if entry_notional > 0 else None
    )
    return fee_quote_estimate, net_realized_pnl_quote, net_realized_pnl_pct


class TradeHistoryLogger:
    """체결 결과를 JSONL 파일로 누적 저장하는 로거."""

    def __init__(self, path: str = "trade_logs/trade_history.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.structured_root = Path("structured_logs") / "live"

    def log_fill(
        self,
        *,
        exchange_name: str,
        program_name: str,
        symbol: str,
        side: str,
        reason: str,
        base_currency: str,
        quote_currency: str,
        amount: float | None = None,
        order_value_quote: float | None = None,
        reference_price: float | None = None,
        estimated_entry_price: float | None = None,
        realized_pnl_pct: float | None = None,
        realized_pnl_quote: float | None = None,
        daily_realized_pnl_quote_after: float | None = None,
        entry_count_after: int | None = None,
        base_free_before: float | None = None,
        quote_free_before: float | None = None,
        remaining_base_after_estimate: float | None = None,
        timeframe: str | None = None,
        ma_period: int | None = None,
        strategy_version: str | None = None,
        position_id: str | None = None,
        leg_index: int | None = None,
        is_final_exit: bool | None = None,
        holding_seconds: float | None = None,
        fee_rate_pct: float | None = None,
        fee_quote_estimate: float | None = None,
        net_realized_pnl_quote: float | None = None,
        net_realized_pnl_pct: float | None = None,
        highest_price_since_entry: float | None = None,
        lowest_price_since_entry: float | None = None,
        mfe_pct: float | None = None,
        mae_pct: float | None = None,
        drawdown_from_high_pct: float | None = None,
        trailing_armed: bool | None = None,
        trailing_armed_at: str | None = None,
        trailing_activation_price: float | None = None,
        trailing_armed_seconds: float | None = None,
        activation_to_exit_seconds: float | None = None,
        raw_order: Any = None,
        extra: dict[str, Any] | None = None,
    ):
        """체결 결과 1건을 JSONL 형식으로 기록한다."""
        record = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "recorded_at_local": datetime.now().astimezone().isoformat(),
            "exchange": exchange_name,
            "program_name": program_name,
            "symbol": symbol,
            "side": side,
            "reason": reason,
            "base_currency": base_currency,
            "quote_currency": quote_currency,
            "amount": amount,
            "order_value_quote": order_value_quote,
            "reference_price": reference_price,
            "estimated_entry_price": estimated_entry_price,
            "realized_pnl_pct": realized_pnl_pct,
            "realized_pnl_quote": realized_pnl_quote,
            "daily_realized_pnl_quote_after": daily_realized_pnl_quote_after,
            "entry_count_after": entry_count_after,
            "base_free_before": base_free_before,
            "quote_free_before": quote_free_before,
            "remaining_base_after_estimate": remaining_base_after_estimate,
            "timeframe": timeframe,
            "ma_period": ma_period,
            "strategy_version": strategy_version,
            "position_id": position_id,
            "leg_index": leg_index,
            "is_final_exit": is_final_exit,
            "holding_seconds": holding_seconds,
            "fee_rate_pct": fee_rate_pct,
            "fee_quote_estimate": fee_quote_estimate,
            "net_realized_pnl_quote": net_realized_pnl_quote,
            "net_realized_pnl_pct": net_realized_pnl_pct,
            "highest_price_since_entry": highest_price_since_entry,
            "lowest_price_since_entry": lowest_price_since_entry,
            "mfe_pct": mfe_pct,
            "mae_pct": mae_pct,
            "drawdown_from_high_pct": drawdown_from_high_pct,
            "trailing_armed": trailing_armed,
            "trailing_armed_at": trailing_armed_at,
            "trailing_activation_price": trailing_activation_price,
            "trailing_armed_seconds": trailing_armed_seconds,
            "activation_to_exit_seconds": activation_to_exit_seconds,
            "raw_order": to_json_safe(raw_order),
            "extra": to_json_safe(extra or {}),
        }

        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        structured_path = self.structured_root / program_name / "trade.jsonl"
        structured_path.parent.mkdir(parents=True, exist_ok=True)
        with structured_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
