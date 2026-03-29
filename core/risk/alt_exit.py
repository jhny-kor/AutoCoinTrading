"""
작업 요약
- 알트 포지션의 수익률/순익률/MFE/MAE 계산과 청산 보호 판단을 공통화했다.
- 브레이크이븐 가드와 순익 보호 익절 계산을 한 곳으로 모았다.
"""

from __future__ import annotations

from trade_history_logger import estimate_round_trip_net_pnl


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
        and bearish
        and not stop_loss_triggered
        and not profit_protect_triggered
    )
    estimated_sell_ratio = (
        1.0
        if (stop_loss_triggered or profit_protect_triggered or break_even_guard_triggered)
        else sell_split_ratio
    )
    return {
        "fee_round_trip_pct": fee_round_trip_pct,
        "effective_min_take_profit_pct": effective_min_take_profit_pct,
        "take_profit_ready": take_profit_ready,
        "stop_loss_triggered": stop_loss_triggered,
        "profit_protect_triggered": profit_protect_triggered,
        "break_even_guard_triggered": break_even_guard_triggered,
        "estimated_sell_ratio": estimated_sell_ratio,
    }
