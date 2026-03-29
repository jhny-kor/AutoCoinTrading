from __future__ import annotations


def compute_alt_signal_state(
    *,
    prev_close: float,
    prev_ma: float,
    last_close: float,
    last_ma: float,
    min_gap_pct: float,
    enable_trend_follow_entry: bool,
    require_prev_above_ma: bool,
    require_price_rising: bool,
) -> dict[str, float | bool]:
    gap_pct = abs(last_close - last_ma) / last_ma * 100 if last_ma else 0.0
    bullish = prev_close < prev_ma and last_close > last_ma
    bearish = prev_close > prev_ma and last_close < last_ma
    signal_is_strong = gap_pct >= min_gap_pct
    trend_follow_entry = (
        enable_trend_follow_entry
        and last_close > last_ma
        and (not require_prev_above_ma or prev_close > prev_ma)
        and (not require_price_rising or last_close > prev_close)
    )
    entry_signal = bullish or trend_follow_entry
    return {
        "bullish": bullish,
        "bearish": bearish,
        "gap_pct": gap_pct,
        "signal_is_strong": signal_is_strong,
        "trend_follow_entry": trend_follow_entry,
        "entry_signal": entry_signal,
    }


def compute_can_average_down(
    *,
    has_position: bool,
    average_entry_price: float | None,
    last_close: float,
    averaging_down_gap_pct: float,
) -> bool:
    return (
        not has_position
        or average_entry_price is None
        or last_close <= average_entry_price * (1 - averaging_down_gap_pct / 100)
    )

