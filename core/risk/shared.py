from __future__ import annotations


def is_daily_loss_limit_reached(
    *,
    daily_realized_pnl_quote: float,
    max_daily_loss_quote: float,
) -> bool:
    return daily_realized_pnl_quote <= -max_daily_loss_quote


def is_dynamic_bonus_eligible(
    *,
    has_position: bool,
    base_signal: bool,
    strong_signal: bool,
    require_strong_signal: bool,
    volume_ratio: float | None,
    volume_threshold: float,
    trend_ok: bool,
    require_trend_ok: bool,
    enable_dynamic_overweight: bool = True,
) -> bool:
    return (
        enable_dynamic_overweight
        and not has_position
        and base_signal
        and (not require_strong_signal or strong_signal)
        and volume_ratio is not None
        and volume_ratio >= volume_threshold
        and (not require_trend_ok or trend_ok)
    )
