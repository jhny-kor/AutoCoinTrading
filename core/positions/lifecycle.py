"""
작업 요약
- 2026-08-05: 신규 알트 진입 시 이전 포지션의 고저가 상태를 현재 체결가로 초기화
- BTC 신규진입/추가매수 후 평균 진입가와 trailing 초기 상태 갱신을 공통 함수로 분리했다.
- 알트 매도 체결 후 남은 수량/진입 카운트/손절 컨텍스트/부분청산 플래그 갱신을 공통 함수로 분리했다.
- 알트 매수 체결 후 평균 진입가/진입 카운트/고저가 상태 갱신을 공통 함수로 분리했다.
- 알트/BTC 포지션 종료 후 내부 상태 초기화를 공통 함수로 분리했다.
- 포지션 정리 시 남은 상태값 누락을 줄이도록 정리했다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AltBuyFillState:
    """알트 매수 체결 후 갱신된 내부 포지션 상태를 나타낸다."""

    bought_amount: float
    entry_price_after: float
    entry_count_after: int
    remaining_base_after_estimate: float


@dataclass(frozen=True)
class AltSellFillState:
    """알트 매도 체결 후 갱신된 내부 포지션 상태를 나타낸다."""

    remaining_base: float
    entry_count_after: int
    holding_seconds: float | None
    should_clear_position: bool


@dataclass(frozen=True)
class BtcEntryFillState:
    """BTC 신규 진입 체결 후 갱신된 내부 포지션 상태를 나타낸다."""

    entry_price_after: float
    entry_opened_at: float
    position_id: str
    highest_price_since_entry: float
    lowest_price_since_entry: float
    trailing_armed: bool
    trailing_armed_at: float | None
    trailing_activation_price: float | None
    last_trade_at: float
    add_on_count_after: int
    remaining_base_after_estimate: float


@dataclass(frozen=True)
class BtcAddOnFillState:
    """BTC 추가매수 체결 후 갱신된 내부 포지션 상태를 나타낸다."""

    added_amount: float
    total_amount: float
    entry_price_after: float
    highest_price_since_entry: float
    lowest_price_since_entry: float
    last_trade_at: float
    add_on_count_after: int


def clear_alt_position_state(
    *,
    symbol: str,
    entry_price: dict,
    entry_count: dict,
    entry_opened_at: dict,
    highest_price_since_entry: dict,
    lowest_price_since_entry: dict,
    partial_take_profit_done: dict,
    partial_stop_loss_done: dict,
    unrecoverable_position_warned: set[str] | None = None,
) -> None:
    entry_price.pop(symbol, None)
    entry_count.pop(symbol, None)
    entry_opened_at.pop(symbol, None)
    highest_price_since_entry.pop(symbol, None)
    lowest_price_since_entry.pop(symbol, None)
    partial_take_profit_done.pop(symbol, None)
    partial_stop_loss_done.pop(symbol, None)
    if unrecoverable_position_warned is not None:
        unrecoverable_position_warned.discard(symbol)


def apply_alt_buy_fill_state(
    *,
    symbol: str,
    bought_amount: float,
    last_close: float,
    has_position: bool,
    avg_entry_price: float | None,
    base_free: float,
    current_entry_count: int,
    now_ts: float,
    entry_price: dict,
    entry_count: dict,
    entry_opened_at: dict,
    highest_price_since_entry: dict,
    lowest_price_since_entry: dict,
) -> AltBuyFillState:
    """알트 매수 체결 후 공통 내부 상태를 갱신한다."""
    if has_position and avg_entry_price and base_free > 0:
        total_cost = (avg_entry_price * base_free) + (last_close * bought_amount)
        total_size = base_free + bought_amount
        entry_price_after = total_cost / total_size if total_size > 0 else last_close
    else:
        entry_price_after = last_close

    entry_price[symbol] = entry_price_after
    entry_count_after = current_entry_count + 1
    entry_count[symbol] = entry_count_after
    if not has_position:
        entry_opened_at[symbol] = now_ts
        highest_price_since_entry[symbol] = last_close
        lowest_price_since_entry[symbol] = last_close
    else:
        highest_price_since_entry[symbol] = max(
            highest_price_since_entry.get(symbol, last_close),
            last_close,
        )
        lowest_price_since_entry[symbol] = min(
            lowest_price_since_entry.get(symbol, last_close),
            last_close,
        )
    return AltBuyFillState(
        bought_amount=bought_amount,
        entry_price_after=entry_price_after,
        entry_count_after=entry_count_after,
        remaining_base_after_estimate=base_free + bought_amount,
    )


def apply_alt_sell_fill_state(
    *,
    symbol: str,
    sold_amount: float,
    base_free: float,
    current_entry_count: int,
    exit_reason_key: str,
    full_clear_threshold: float,
    now_ts: float,
    entry_count: dict,
    entry_opened_at: dict,
    last_trade_at: dict,
    last_stop_loss_at: dict,
    last_stop_loss_context: dict,
    current_entry_risk_context: dict,
    partial_take_profit_done: dict,
    partial_take_profit_last_at: dict,
    partial_stop_loss_done: dict,
) -> AltSellFillState:
    """알트 매도 체결 후 공통 내부 상태를 갱신한다."""
    last_trade_at[symbol] = now_ts
    if exit_reason_key in {"stop_loss", "partial_stop_loss"}:
        last_stop_loss_at[symbol] = now_ts
        last_stop_loss_context[symbol] = dict(current_entry_risk_context)

    remaining_base = max(base_free - sold_amount, 0.0)
    should_clear_position = remaining_base <= full_clear_threshold
    entry_count_after = (
        0 if should_clear_position else max(current_entry_count - 1, 0)
    )
    entry_count[symbol] = entry_count_after

    if exit_reason_key == "partial_take_profit" and not should_clear_position:
        partial_take_profit_done[symbol] = True
        partial_take_profit_last_at[symbol] = now_ts
    if exit_reason_key == "partial_stop_loss" and not should_clear_position:
        partial_stop_loss_done[symbol] = True

    opened_at = entry_opened_at.get(symbol)
    holding_seconds = None if opened_at is None else max(0.0, now_ts - opened_at)
    return AltSellFillState(
        remaining_base=remaining_base,
        entry_count_after=entry_count_after,
        holding_seconds=holding_seconds,
        should_clear_position=should_clear_position,
    )


def apply_btc_entry_fill_state(
    *,
    symbol: str,
    bought_amount: float,
    last_close: float,
    now_ts: float,
) -> BtcEntryFillState:
    """BTC 신규 진입 체결 후 공통 내부 상태를 계산한다."""
    return BtcEntryFillState(
        entry_price_after=last_close,
        entry_opened_at=now_ts,
        position_id=f"{symbol}:{int(now_ts)}",
        highest_price_since_entry=last_close,
        lowest_price_since_entry=last_close,
        trailing_armed=False,
        trailing_armed_at=None,
        trailing_activation_price=None,
        last_trade_at=now_ts,
        add_on_count_after=0,
        remaining_base_after_estimate=bought_amount,
    )


def apply_btc_add_on_fill_state(
    *,
    previous_amount: float,
    added_amount: float,
    previous_entry_price: float | None,
    last_close: float,
    current_add_on_count: int,
    highest_price_since_entry: float | None,
    lowest_price_since_entry: float | None,
    now_ts: float,
) -> BtcAddOnFillState:
    """BTC 추가매수 체결 후 평균 진입가와 고저가 상태를 계산한다."""
    total_amount = previous_amount + added_amount
    entry_price_before = previous_entry_price or last_close
    if total_amount > 0:
        entry_price_after = (
            (entry_price_before * previous_amount) + (last_close * added_amount)
        ) / total_amount
    else:
        entry_price_after = last_close

    return BtcAddOnFillState(
        added_amount=added_amount,
        total_amount=total_amount,
        entry_price_after=entry_price_after,
        highest_price_since_entry=max(highest_price_since_entry or last_close, last_close),
        lowest_price_since_entry=min(lowest_price_since_entry or last_close, last_close),
        last_trade_at=now_ts,
        add_on_count_after=current_add_on_count + 1,
    )


def clear_btc_position_state() -> dict[str, object]:
    return {
        "entry_price": None,
        "entry_opened_at": None,
        "position_id": None,
        "highest_price_since_entry": None,
        "lowest_price_since_entry": None,
        "trailing_armed": False,
        "trailing_armed_at": None,
        "trailing_activation_price": None,
        "partial_take_profit_done": False,
        "add_on_count": 0,
    }
