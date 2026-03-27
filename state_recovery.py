"""
수정 요약
- trade_history.jsonl 기반으로 프로그램별 포지션 상태를 복구하는 공통 모듈을 추가
- 평균 진입가, 남은 수량, 분할 진입 카운트, 부분 익절/부분 손절 플래그, 최근 거래 시각을 함께 복구하도록 확장
- 프로그램별 당일 실현 손익을 trade_history 기준으로 다시 계산하는 helper 를 추가

실행 상태 복구 유틸

- 재시작 후 현재 보유 포지션의 평균 진입가를 현재가로 임시 대체하지 않도록 돕는다.
- 일일 손실 제한을 메모리 변수 대신 체결 이력 기준으로 복구할 수 있게 한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from analyze_strategy_logs import read_trade_history


POSITION_EPSILON = 1e-12
PROFIT_EXIT_REASONS = {
    "take_profit",
    "partial_take_profit",
    "profit_protect_take_profit",
    "break_even_guard_exit",
    "trailing_take_profit",
    "trend_exit",
}
STOP_EXIT_REASONS = {
    "stop_loss",
    "partial_stop_loss",
}


@dataclass(frozen=True)
class RecoveredPositionState:
    """프로그램 재시작 시 복구한 심볼별 상태."""

    symbol: str
    remaining_amount: float
    cost_basis_quote: float
    average_entry_price: float | None
    cycle_buy_count: int
    opened_at_ts: float | None
    highest_price_since_entry: float | None
    lowest_price_since_entry: float | None
    trailing_armed: bool
    trailing_armed_at_ts: float | None
    trailing_activation_price: float | None
    partial_take_profit_done: bool
    partial_stop_loss_done: bool
    last_trade_at_ts: float
    last_partial_take_profit_at_ts: float
    last_stop_loss_at_ts: float
    last_profit_exit_at_ts: float


def _to_float(value: Any) -> float | None:
    """숫자 후보를 float 로 안전하게 바꾼다."""
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _recorded_timestamp(record: dict[str, Any]) -> float | None:
    """체결 레코드에서 timestamp 초 값을 추출한다."""
    for key in ("recorded_at_local", "recorded_at"):
        raw = record.get(key)
        if not raw:
            continue
        try:
            return datetime.fromisoformat(str(raw)).timestamp()
        except ValueError:
            continue
    return None


def _recorded_date(record: dict[str, Any]) -> date | None:
    """체결 레코드에서 로컬 날짜를 추출한다."""
    for key in ("recorded_at_local", "recorded_at"):
        raw = record.get(key)
        if not raw:
            continue
        try:
            return datetime.fromisoformat(str(raw)).date()
        except ValueError:
            continue
    return None


def _parse_iso_timestamp(raw: Any) -> float | None:
    """ISO 시각 문자열을 timestamp 초 값으로 바꾼다."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw)).timestamp()
    except ValueError:
        return None


def restore_program_position_states(
    program_name: str,
    symbols: list[str] | None = None,
) -> dict[str, RecoveredPositionState]:
    """체결 이력을 읽어 프로그램의 현재 포지션 상태를 복구한다."""
    target_symbols = set(symbols or [])
    states: dict[str, dict[str, Any]] = {}

    records = [
        record
        for record in read_trade_history()
        if str(record.get("program_name", "")) == program_name
    ]
    records.sort(
        key=lambda record: (
            _recorded_timestamp(record) or 0.0,
            0 if str(record.get("side", "")).lower() == "buy" else 1,
        )
    )

    for record in records:
        symbol = str(record.get("symbol", ""))
        if not symbol:
            continue
        if target_symbols and symbol not in target_symbols:
            continue

        state = states.setdefault(
            symbol,
            {
                "remaining_amount": 0.0,
                "cost_basis_quote": 0.0,
                "cycle_buy_count": 0,
                "opened_at_ts": None,
                "open_legs": [],
                "highest_price_since_entry": None,
                "lowest_price_since_entry": None,
                "trailing_armed": False,
                "trailing_armed_at_ts": None,
                "trailing_activation_price": None,
                "partial_take_profit_done": False,
                "partial_stop_loss_done": False,
                "last_trade_at_ts": 0.0,
                "last_partial_take_profit_at_ts": 0.0,
                "last_stop_loss_at_ts": 0.0,
                "last_profit_exit_at_ts": 0.0,
            },
        )
        recorded_ts = _recorded_timestamp(record) or 0.0
        side = str(record.get("side", "")).lower()
        reason = str(record.get("reason", ""))
        amount = _to_float(record.get("amount")) or 0.0
        order_value_quote = _to_float(record.get("order_value_quote"))
        if order_value_quote is None:
            reference_price = _to_float(record.get("reference_price")) or 0.0
            order_value_quote = amount * reference_price

        if side == "buy" and amount > 0:
            if state["remaining_amount"] <= POSITION_EPSILON:
                state["cycle_buy_count"] = 0
                state["opened_at_ts"] = recorded_ts or None
                state["partial_take_profit_done"] = False
                state["partial_stop_loss_done"] = False
                state["open_legs"] = []
                state["highest_price_since_entry"] = None
                state["lowest_price_since_entry"] = None
                state["trailing_armed"] = False
                state["trailing_armed_at_ts"] = None
                state["trailing_activation_price"] = None
            state["remaining_amount"] += amount
            state["cost_basis_quote"] += max(0.0, order_value_quote or 0.0)
            state["open_legs"].append(
                {
                    "amount": amount,
                    "cost_basis_quote": max(0.0, order_value_quote or 0.0),
                    "opened_at_ts": recorded_ts or None,
                }
            )
            state["cycle_buy_count"] = len(state["open_legs"])
            if state["open_legs"]:
                state["opened_at_ts"] = state["open_legs"][0]["opened_at_ts"]
            state["last_trade_at_ts"] = max(state["last_trade_at_ts"], recorded_ts)
            highest_price_since_entry = _to_float(record.get("highest_price_since_entry"))
            lowest_price_since_entry = _to_float(record.get("lowest_price_since_entry"))
            if highest_price_since_entry is not None:
                state["highest_price_since_entry"] = highest_price_since_entry
            if lowest_price_since_entry is not None:
                state["lowest_price_since_entry"] = lowest_price_since_entry
            if record.get("trailing_armed") is not None:
                state["trailing_armed"] = bool(record.get("trailing_armed"))
            trailing_armed_at_ts = _parse_iso_timestamp(record.get("trailing_armed_at"))
            if trailing_armed_at_ts is not None:
                state["trailing_armed_at_ts"] = trailing_armed_at_ts
            trailing_activation_price = _to_float(record.get("trailing_activation_price"))
            if trailing_activation_price is not None:
                state["trailing_activation_price"] = trailing_activation_price
            continue

        if side != "sell" or amount <= 0:
            continue

        remaining_before = float(state["remaining_amount"])
        cost_before = float(state["cost_basis_quote"])
        if remaining_before <= POSITION_EPSILON:
            continue

        sold_amount = min(amount, remaining_before)
        sold_ratio = sold_amount / remaining_before if remaining_before > 0 else 1.0
        cost_reduction = cost_before * sold_ratio
        state["remaining_amount"] = max(0.0, remaining_before - sold_amount)
        state["cost_basis_quote"] = max(0.0, cost_before - cost_reduction)
        state["last_trade_at_ts"] = max(state["last_trade_at_ts"], recorded_ts)
        remaining_to_consume = sold_amount
        open_legs: list[dict[str, Any]] = list(state["open_legs"])
        while remaining_to_consume > POSITION_EPSILON and open_legs:
            leg = open_legs[0]
            leg_amount = float(leg.get("amount", 0.0) or 0.0)
            if leg_amount <= POSITION_EPSILON:
                open_legs.pop(0)
                continue
            consume_amount = min(remaining_to_consume, leg_amount)
            leg["amount"] = max(0.0, leg_amount - consume_amount)
            remaining_to_consume -= consume_amount
            if leg["amount"] <= POSITION_EPSILON:
                open_legs.pop(0)
        state["open_legs"] = open_legs
        state["cycle_buy_count"] = len(open_legs)
        state["opened_at_ts"] = open_legs[0]["opened_at_ts"] if open_legs else None

        if reason == "partial_take_profit" and state["remaining_amount"] > POSITION_EPSILON:
            state["partial_take_profit_done"] = True
            state["last_partial_take_profit_at_ts"] = max(
                state["last_partial_take_profit_at_ts"],
                recorded_ts,
            )
        if reason == "partial_stop_loss" and state["remaining_amount"] > POSITION_EPSILON:
            state["partial_stop_loss_done"] = True
        highest_price_since_entry = _to_float(record.get("highest_price_since_entry"))
        lowest_price_since_entry = _to_float(record.get("lowest_price_since_entry"))
        if highest_price_since_entry is not None:
            state["highest_price_since_entry"] = highest_price_since_entry
        if lowest_price_since_entry is not None:
            state["lowest_price_since_entry"] = lowest_price_since_entry
        if record.get("trailing_armed") is not None:
            state["trailing_armed"] = bool(record.get("trailing_armed"))
        trailing_armed_at_ts = _parse_iso_timestamp(record.get("trailing_armed_at"))
        if trailing_armed_at_ts is not None:
            state["trailing_armed_at_ts"] = trailing_armed_at_ts
        trailing_activation_price = _to_float(record.get("trailing_activation_price"))
        if trailing_activation_price is not None:
            state["trailing_activation_price"] = trailing_activation_price
        if reason in STOP_EXIT_REASONS:
            state["last_stop_loss_at_ts"] = max(state["last_stop_loss_at_ts"], recorded_ts)
        if reason in PROFIT_EXIT_REASONS:
            state["last_profit_exit_at_ts"] = max(
                state["last_profit_exit_at_ts"],
                recorded_ts,
            )

        if state["remaining_amount"] <= POSITION_EPSILON:
            state["remaining_amount"] = 0.0
            state["cost_basis_quote"] = 0.0
            state["cycle_buy_count"] = 0
            state["opened_at_ts"] = None
            state["open_legs"] = []
            state["highest_price_since_entry"] = None
            state["lowest_price_since_entry"] = None
            state["trailing_armed"] = False
            state["trailing_armed_at_ts"] = None
            state["trailing_activation_price"] = None
            state["partial_take_profit_done"] = False
            state["partial_stop_loss_done"] = False

    recovered: dict[str, RecoveredPositionState] = {}
    for symbol, payload in states.items():
        remaining_amount = float(payload["remaining_amount"])
        cost_basis_quote = float(payload["cost_basis_quote"])
        average_entry_price = (
            cost_basis_quote / remaining_amount
            if remaining_amount > POSITION_EPSILON and cost_basis_quote > 0
            else None
        )
        highest_price_since_entry = payload["highest_price_since_entry"]
        lowest_price_since_entry = payload["lowest_price_since_entry"]
        if highest_price_since_entry is None and average_entry_price is not None:
            highest_price_since_entry = average_entry_price
        if lowest_price_since_entry is None and average_entry_price is not None:
            lowest_price_since_entry = average_entry_price
        recovered[symbol] = RecoveredPositionState(
            symbol=symbol,
            remaining_amount=remaining_amount,
            cost_basis_quote=cost_basis_quote,
            average_entry_price=average_entry_price,
            cycle_buy_count=int(payload["cycle_buy_count"]),
            opened_at_ts=payload["opened_at_ts"],
            highest_price_since_entry=highest_price_since_entry,
            lowest_price_since_entry=lowest_price_since_entry,
            trailing_armed=bool(payload["trailing_armed"]),
            trailing_armed_at_ts=payload["trailing_armed_at_ts"],
            trailing_activation_price=payload["trailing_activation_price"],
            partial_take_profit_done=bool(payload["partial_take_profit_done"]),
            partial_stop_loss_done=bool(payload["partial_stop_loss_done"]),
            last_trade_at_ts=float(payload["last_trade_at_ts"]),
            last_partial_take_profit_at_ts=float(payload["last_partial_take_profit_at_ts"]),
            last_stop_loss_at_ts=float(payload["last_stop_loss_at_ts"]),
            last_profit_exit_at_ts=float(payload["last_profit_exit_at_ts"]),
        )
    return recovered


def load_program_daily_realized_pnl_quote(
    program_name: str,
    target_date: date | None = None,
) -> float:
    """프로그램의 당일 실현 손익을 trade_history 기준으로 다시 계산한다."""
    today = target_date or datetime.now().date()
    total = 0.0
    for record in read_trade_history():
        if str(record.get("program_name", "")) != program_name:
            continue
        if str(record.get("side", "")).lower() != "sell":
            continue
        recorded_date = _recorded_date(record)
        if recorded_date != today:
            continue
        pnl_value = _to_float(record.get("net_realized_pnl_quote"))
        if pnl_value is None:
            pnl_value = _to_float(record.get("realized_pnl_quote"))
        total += pnl_value or 0.0
    return total
