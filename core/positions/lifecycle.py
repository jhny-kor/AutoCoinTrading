"""
작업 요약
- 알트/BTC 포지션 종료 후 내부 상태 초기화를 공통 함수로 분리했다.
- 포지션 정리 시 남은 상태값 누락을 줄이도록 정리했다.
"""

from __future__ import annotations


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
