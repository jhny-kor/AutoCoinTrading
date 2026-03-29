from __future__ import annotations

from trade_history_logger import estimate_round_trip_net_pnl


def build_btc_exit_prices(
    *,
    entry_price: float,
    atr_value: float,
    recent_swing_low: float,
    recent_swing_high: float,
    min_take_profit_pct: float,
    settings,
) -> tuple[float, float]:
    if settings.stop_mode == "swing":
        stop_price = recent_swing_low
    else:
        stop_price = entry_price - (atr_value * settings.stop_atr_multiple)

    if settings.take_profit_mode == "swing":
        take_profit_price = recent_swing_high
        if take_profit_price <= entry_price:
            take_profit_price = entry_price + (
                atr_value * settings.take_profit_atr_multiple
            )
    else:
        take_profit_price = entry_price + (
            atr_value * settings.take_profit_atr_multiple
        )

    fee_floor_take_profit_price = entry_price * (1 + (min_take_profit_pct / 100))
    take_profit_price = max(take_profit_price, fee_floor_take_profit_price)
    return stop_price, take_profit_price


def evaluate_btc_open_position(
    *,
    has_position: bool,
    entry_price: float | None,
    last_close: float,
    base_free: float,
    fee_rate_pct: float,
    atr_value: float,
    recent_swing_low: float,
    recent_swing_high: float,
    highest_price_since_entry: float | None,
    lowest_price_since_entry: float | None,
    trailing_armed: bool,
    trailing_armed_at: float | None,
    trailing_activation_price: float | None,
    partial_take_profit_done: bool,
    confirm_bullish: bool,
    ema_aligned: bool,
    ema_spread_pct: float,
    settings,
) -> dict[str, object]:
    if not has_position or entry_price is None:
        return {
            "stop_price": None,
            "take_profit_price": None,
            "pnl_pct": None,
            "current_fee_quote_estimate": None,
            "current_net_realized_pnl_quote": None,
            "current_net_realized_pnl_pct": None,
            "partial_take_profit_triggered": False,
            "bull_pullback_hold_active": False,
            "drawdown_from_high_pct": None,
            "mfe_pct": None,
            "mae_pct": None,
            "highest_price_since_entry": None if not has_position else highest_price_since_entry,
            "lowest_price_since_entry": None if not has_position else lowest_price_since_entry,
            "trailing_armed": False if not has_position else trailing_armed,
            "trailing_armed_at": None if not has_position else trailing_armed_at,
            "trailing_activation_price": None if not has_position else trailing_activation_price,
            "partial_take_profit_done": False if not has_position else partial_take_profit_done,
            "add_on_count_reset": not has_position,
            "trailing_armed_just_now": False,
        }

    updated_high = max(highest_price_since_entry or last_close, last_close)
    updated_low = min(lowest_price_since_entry or last_close, last_close)
    stop_price, take_profit_price = build_btc_exit_prices(
        entry_price=entry_price,
        atr_value=atr_value,
        recent_swing_low=recent_swing_low,
        recent_swing_high=recent_swing_high,
        min_take_profit_pct=(fee_rate_pct * 2 * 1.1),
        settings=settings,
    )
    pnl_pct = (last_close - entry_price) / entry_price * 100
    (
        current_fee_quote_estimate,
        current_net_realized_pnl_quote,
        current_net_realized_pnl_pct,
    ) = estimate_round_trip_net_pnl(
        entry_price=entry_price,
        exit_price=last_close,
        amount=base_free,
        fee_rate_pct=fee_rate_pct,
    )
    partial_take_profit_triggered = (
        has_position
        and settings.enable_partial_take_profit
        and not partial_take_profit_done
        and take_profit_price is not None
        and last_close >= take_profit_price
    )
    trailing_armed_just_now = False
    if (
        not partial_take_profit_triggered
        and (not trailing_armed)
        and take_profit_price is not None
        and last_close >= take_profit_price
    ):
        trailing_armed = True
        trailing_armed_at = trailing_armed_at or 0.0
        trailing_activation_price = last_close
        trailing_armed_just_now = True
    drawdown_from_high_pct = (
        ((updated_high - last_close) / updated_high) * 100
        if updated_high
        else None
    )
    mfe_pct = (
        ((updated_high - entry_price) / entry_price) * 100
        if entry_price
        else None
    )
    mae_pct = (
        ((updated_low - entry_price) / entry_price) * 100
        if entry_price
        else None
    )
    bull_pullback_hold_active = (
        settings.enable_bull_pullback_hold
        and confirm_bullish
        and ema_aligned
        and pnl_pct > 0
        and drawdown_from_high_pct is not None
        and drawdown_from_high_pct <= settings.bull_pullback_tolerance_pct
        and ema_spread_pct >= settings.bull_pullback_min_spread_pct
    )
    return {
        "stop_price": stop_price,
        "take_profit_price": take_profit_price,
        "pnl_pct": pnl_pct,
        "current_fee_quote_estimate": current_fee_quote_estimate,
        "current_net_realized_pnl_quote": current_net_realized_pnl_quote,
        "current_net_realized_pnl_pct": current_net_realized_pnl_pct,
        "partial_take_profit_triggered": partial_take_profit_triggered,
        "bull_pullback_hold_active": bull_pullback_hold_active,
        "drawdown_from_high_pct": drawdown_from_high_pct,
        "mfe_pct": mfe_pct,
        "mae_pct": mae_pct,
        "highest_price_since_entry": updated_high,
        "lowest_price_since_entry": updated_low,
        "trailing_armed": trailing_armed,
        "trailing_armed_at": trailing_armed_at,
        "trailing_activation_price": trailing_activation_price,
        "partial_take_profit_done": partial_take_profit_done,
        "add_on_count_reset": False,
        "trailing_armed_just_now": trailing_armed_just_now,
    }
