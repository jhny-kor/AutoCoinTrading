"""
수정 요약
- 2026-06-12: 알트 순익 trailing arm 상태도 런타임 복구 상태에 포함했다.
- 2026-04-09: 알트도 손절 전용 재진입 시각을 런타임 상태에 복구해 패턴 기반 재진입에 재사용하도록 확장
"""

from __future__ import annotations

from dataclasses import dataclass

from settings.state_recovery import RecoveredPositionState


@dataclass(frozen=True)
class AltRuntimeState:
    entry_price: dict[str, float]
    entry_opened_at: dict[str, float]
    highest_price_since_entry: dict[str, float]
    lowest_price_since_entry: dict[str, float]
    partial_take_profit_done: dict[str, bool]
    partial_stop_loss_done: dict[str, bool]
    trailing_armed: dict[str, bool]
    partial_take_profit_last_at: dict[str, float]
    entry_count: dict[str, int]
    last_trade_at: dict[str, float]
    last_stop_loss_at: dict[str, float]


@dataclass(frozen=True)
class BtcRuntimeState:
    entry_price: float | None
    entry_opened_at: float | None
    position_id: str | None
    highest_price_since_entry: float | None
    lowest_price_since_entry: float | None
    trailing_armed: bool
    trailing_armed_at: float | None
    trailing_activation_price: float | None
    partial_take_profit_done: bool
    add_on_count: int
    last_trade_at: float
    last_stop_loss_at: float
    last_profit_exit_at: float


def build_alt_runtime_state(
    recovered_states: dict[str, RecoveredPositionState],
) -> AltRuntimeState:
    return AltRuntimeState(
        entry_price={
            symbol: state.average_entry_price
            for symbol, state in recovered_states.items()
            if state.average_entry_price is not None
        },
        entry_opened_at={
            symbol: state.opened_at_ts
            for symbol, state in recovered_states.items()
            if state.opened_at_ts is not None
        },
        highest_price_since_entry={
            symbol: state.highest_price_since_entry
            for symbol, state in recovered_states.items()
            if state.highest_price_since_entry is not None
        },
        lowest_price_since_entry={
            symbol: state.lowest_price_since_entry
            for symbol, state in recovered_states.items()
            if state.lowest_price_since_entry is not None
        },
        partial_take_profit_done={
            symbol: state.partial_take_profit_done
            for symbol, state in recovered_states.items()
            if state.partial_take_profit_done
        },
        partial_stop_loss_done={
            symbol: state.partial_stop_loss_done
            for symbol, state in recovered_states.items()
            if state.partial_stop_loss_done
        },
        trailing_armed={
            symbol: state.trailing_armed
            for symbol, state in recovered_states.items()
            if state.trailing_armed
        },
        partial_take_profit_last_at={
            symbol: state.last_partial_take_profit_at_ts
            for symbol, state in recovered_states.items()
            if state.last_partial_take_profit_at_ts > 0
        },
        entry_count={
            symbol: state.cycle_buy_count
            for symbol, state in recovered_states.items()
            if state.cycle_buy_count > 0
        },
        last_trade_at={
            symbol: state.last_trade_at_ts
            for symbol, state in recovered_states.items()
            if state.last_trade_at_ts > 0
        },
        last_stop_loss_at={
            symbol: state.last_stop_loss_at_ts
            for symbol, state in recovered_states.items()
            if state.last_stop_loss_at_ts > 0
        },
    )


def build_btc_runtime_state(
    symbol: str,
    recovered_state: RecoveredPositionState | None,
) -> BtcRuntimeState:
    return BtcRuntimeState(
        entry_price=recovered_state.average_entry_price if recovered_state else None,
        entry_opened_at=recovered_state.opened_at_ts if recovered_state else None,
        position_id=(
            f"{symbol}:{int(recovered_state.opened_at_ts)}"
            if recovered_state and recovered_state.opened_at_ts is not None
            else None
        ),
        highest_price_since_entry=(
            recovered_state.highest_price_since_entry if recovered_state else None
        ),
        lowest_price_since_entry=(
            recovered_state.lowest_price_since_entry if recovered_state else None
        ),
        trailing_armed=recovered_state.trailing_armed if recovered_state else False,
        trailing_armed_at=(
            recovered_state.trailing_armed_at_ts if recovered_state else None
        ),
        trailing_activation_price=(
            recovered_state.trailing_activation_price if recovered_state else None
        ),
        partial_take_profit_done=(
            recovered_state.partial_take_profit_done if recovered_state else False
        ),
        add_on_count=max(0, recovered_state.cycle_buy_count - 1) if recovered_state else 0,
        last_trade_at=recovered_state.last_trade_at_ts if recovered_state else 0.0,
        last_stop_loss_at=recovered_state.last_stop_loss_at_ts if recovered_state else 0.0,
        last_profit_exit_at=(
            recovered_state.last_profit_exit_at_ts if recovered_state else 0.0
        ),
    )
