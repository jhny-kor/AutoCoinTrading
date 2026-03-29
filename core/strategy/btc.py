from __future__ import annotations


def compute_btc_entry_state(
    *,
    bullish: bool,
    last_fast: float,
    last_slow: float,
    last_close: float,
    min_ema_spread_pct: float,
    enable_trend_follow_entry: bool,
    require_price_above_fast: bool,
) -> dict[str, float | bool]:
    ema_aligned = last_fast > last_slow
    price_above_fast = last_close >= last_fast
    ema_spread_pct = abs(last_fast - last_slow) / last_slow * 100 if last_slow else 0.0
    trend_follow_entry = (
        enable_trend_follow_entry
        and ema_aligned
        and ema_spread_pct >= min_ema_spread_pct
        and (not require_price_above_fast or price_above_fast)
    )
    entry_signal = bullish or trend_follow_entry
    return {
        "ema_aligned": ema_aligned,
        "price_above_fast": price_above_fast,
        "ema_spread_pct": ema_spread_pct,
        "trend_follow_entry": trend_follow_entry,
        "entry_signal": entry_signal,
    }


def compute_btc_exit_flags(
    *,
    has_position: bool,
    stop_price: float | None,
    take_profit_price: float | None,
    last_close: float,
    highest_price_since_entry: float | None,
    trailing_drawdown_pct: float,
    trailing_armed: bool,
    enable_fee_protect_exit: bool,
    fee_protect_min_net_pnl_pct: float,
    pnl_pct: float | None,
    bearish: bool,
    confirm_bullish: bool,
) -> dict[str, float | bool | None]:
    drawdown_from_high_pct = None
    if highest_price_since_entry and highest_price_since_entry > 0:
        drawdown_from_high_pct = (
            (highest_price_since_entry - last_close) / highest_price_since_entry * 100
        )
    stop_triggered = has_position and stop_price is not None and last_close <= stop_price
    take_profit_triggered = (
        has_position and take_profit_price is not None and last_close >= take_profit_price
    )
    trailing_stop_triggered = (
        has_position
        and trailing_armed
        and drawdown_from_high_pct is not None
        and drawdown_from_high_pct >= trailing_drawdown_pct
    )
    profit_protect_triggered = (
        has_position
        and enable_fee_protect_exit
        and pnl_pct is not None
        and pnl_pct >= fee_protect_min_net_pnl_pct
        and bearish
        and not trailing_stop_triggered
    )
    trend_exit_triggered = (
        has_position
        and bearish
        and not trailing_armed
        and not stop_triggered
        and not profit_protect_triggered
        and not confirm_bullish
    )
    return {
        "drawdown_from_high_pct": drawdown_from_high_pct,
        "stop_triggered": stop_triggered,
        "take_profit_triggered": take_profit_triggered,
        "trailing_stop_triggered": trailing_stop_triggered,
        "profit_protect_triggered": profit_protect_triggered,
        "trend_exit_triggered": trend_exit_triggered,
    }

