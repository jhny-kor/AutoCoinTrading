"""
작업 요약
- 2026-04-06: Donchian Channel + ATR 돌파 기반 병렬 진입 모드 추가
- BTC EMA 돌파와 추세 조건을 공통 함수로 분리하고, 불필요한 중복 평가를 제거했다.
- EMA 정렬, spread, 손절/트레일링/순익 보호 판단을 한 곳으로 모았다.
- RSI, 볼린저 밴드 폭, EMA 기울기를 진입 필터에 반영해 추세 확인 강도를 높였다.
"""

from __future__ import annotations


def _clamp_score(raw: float) -> float:
    """신호 스코어를 0~100 범위로 제한한다."""
    return max(0.0, min(100.0, raw))


def compute_btc_entry_state(
    *,
    bullish: bool,
    last_fast: float,
    last_slow: float,
    last_close: float,
    min_ema_spread_pct: float,
    enable_trend_follow_entry: bool,
    require_price_above_fast: bool,
    require_ema_slope_positive: bool,
    fast_ema_slope_pct: float | None,
    slow_ema_slope_pct: float | None,
    rsi_value: float | None,
    enable_rsi_filter: bool,
    rsi_entry_min: float,
    rsi_entry_max: float,
    bb_width_pct: float | None,
    enable_bb_width_filter: bool,
    min_bb_width_pct: float,
    max_bb_width_pct: float,
    signal_score_min: float,
    entry_mode: str = "ema",
    donchian_entry_upper: float | None = None,
    donchian_confirm_breakout_close: bool = True,
    last_high: float = 0.0,
) -> dict[str, float | bool]:
    ema_aligned = last_fast > last_slow
    price_above_fast = last_close >= last_fast
    ema_spread_pct = abs(last_fast - last_slow) / last_slow * 100 if last_slow else 0.0
    ema_slope_positive = (
        fast_ema_slope_pct is not None
        and slow_ema_slope_pct is not None
        and fast_ema_slope_pct > 0
        and slow_ema_slope_pct > 0
    )
    rsi_filter_passed = (
        not enable_rsi_filter
        or (
            rsi_value is not None
            and rsi_entry_min <= rsi_value <= rsi_entry_max
        )
    )
    bb_width_filter_passed = (
        not enable_bb_width_filter
        or (
            bb_width_pct is not None
            and min_bb_width_pct <= bb_width_pct <= max_bb_width_pct
        )
    )
    donchian_breakout = False
    if entry_mode == "donchian" and donchian_entry_upper is not None:
        if donchian_confirm_breakout_close:
            donchian_breakout = last_close > donchian_entry_upper
        else:
            donchian_breakout = last_high > donchian_entry_upper

    trend_follow_entry = False
    if entry_mode == "ema":
        trend_follow_entry = (
            enable_trend_follow_entry
            and ema_aligned
            and ema_spread_pct >= min_ema_spread_pct
            and (not require_price_above_fast or price_above_fast)
            and (not require_ema_slope_positive or ema_slope_positive)
        )
    elif entry_mode == "donchian":
        trend_follow_entry = donchian_breakout

    spread_component = 0.0
    if min_ema_spread_pct > 0:
        spread_component = min(1.0, ema_spread_pct / min_ema_spread_pct) * 35.0
    elif ema_spread_pct > 0:
        spread_component = 35.0

    rsi_component = 0.0
    if rsi_filter_passed and rsi_value is not None:
        band_center = (rsi_entry_min + rsi_entry_max) / 2
        half_band = max((rsi_entry_max - rsi_entry_min) / 2, 1e-9)
        normalized_distance = min(1.0, abs(rsi_value - band_center) / half_band)
        rsi_component = (1.0 - normalized_distance) * 20.0

    bb_component = 0.0
    if bb_width_filter_passed and bb_width_pct is not None and min_bb_width_pct > 0:
        bb_component = min(1.0, bb_width_pct / min_bb_width_pct) * 20.0
    elif bb_width_filter_passed and bb_width_pct is not None:
        bb_component = 20.0

    slope_component = 15.0 if ema_slope_positive else 0.0
    trend_component = 10.0 if price_above_fast else 0.0
    cross_component = 15.0 if bullish else 0.0

    entry_signal = False
    signal_score = 0.0
    
    if entry_mode == "donchian":
        entry_signal = (
            donchian_breakout
            and rsi_filter_passed
            and bb_width_filter_passed
        )
        signal_score = 100.0 if entry_signal else 0.0
    else:
        entry_signal = (
            (bullish or trend_follow_entry)
            and rsi_filter_passed
            and bb_width_filter_passed
        )
        signal_score = _clamp_score(
            spread_component
            + rsi_component
            + bb_component
            + slope_component
            + trend_component
            + cross_component
        )
        
    signal_is_strong = signal_score >= signal_score_min
    
    return {
        "ema_aligned": ema_aligned,
        "price_above_fast": price_above_fast,
        "ema_spread_pct": ema_spread_pct,
        "ema_slope_positive": ema_slope_positive,
        "rsi_filter_passed": rsi_filter_passed,
        "bb_width_filter_passed": bb_width_filter_passed,
        "signal_score": signal_score,
        "signal_is_strong": signal_is_strong,
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
    entry_mode: str = "ema",
    donchian_exit_lower: float | None = None,
    last_low: float = 0.0,
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
    
    trend_exit_triggered = False
    donchian_exit_triggered = False
    
    if entry_mode == "donchian":
        donchian_exit_triggered = (
            donchian_exit_lower is not None 
            and last_low < donchian_exit_lower
        )
        trend_exit_triggered = (
            has_position
            and donchian_exit_triggered
            and not trailing_armed
            and not stop_triggered
            and not profit_protect_triggered
        )
    else:
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
