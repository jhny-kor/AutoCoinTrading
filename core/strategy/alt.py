"""
작업 요약
- 알트 신호 계산과 평균단가 대비 추가매수 허용 여부를 공통 함수로 분리했다.
- 골든/데드크로스와 trend-follow 진입 계산을 한 곳으로 모았다.
- RSI, MACD, 기울기, 거래량을 반영한 신호 스코어 계산을 추가해 횡보장 오탐을 줄이도록 보강했다.
"""

from __future__ import annotations


def _clamp_score(raw: float) -> float:
    """신호 스코어를 0~100 범위로 제한한다."""
    return max(0.0, min(100.0, raw))


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
    require_ma_slope_positive: bool,
    volume_ratio: float | None,
    min_volume_ratio: float,
    rsi_value: float | None,
    enable_rsi_filter: bool,
    rsi_entry_min: float,
    rsi_entry_max: float,
    macd_histogram: float | None,
    enable_macd_filter: bool,
    ma_slope_pct: float | None,
    price_slope_pct: float | None,
    signal_score_min: float,
) -> dict[str, float | bool]:
    gap_pct = abs(last_close - last_ma) / last_ma * 100 if last_ma else 0.0
    bullish = prev_close < prev_ma and last_close > last_ma
    bearish = prev_close > prev_ma and last_close < last_ma
    rsi_filter_passed = (
        not enable_rsi_filter
        or (
            rsi_value is not None
            and rsi_entry_min <= rsi_value <= rsi_entry_max
        )
    )
    macd_filter_passed = (
        not enable_macd_filter
        or (macd_histogram is not None and macd_histogram > 0)
    )
    ma_slope_positive = ma_slope_pct is not None and ma_slope_pct > 0
    price_slope_positive = price_slope_pct is not None and price_slope_pct > 0
    trend_follow_entry = (
        enable_trend_follow_entry
        and last_close > last_ma
        and (not require_prev_above_ma or prev_close > prev_ma)
        and (not require_price_rising or last_close > prev_close)
        and (not require_ma_slope_positive or ma_slope_positive)
    )
    gap_component = 0.0
    if min_gap_pct > 0:
        gap_component = min(1.0, gap_pct / min_gap_pct) * 35.0
    elif gap_pct > 0:
        gap_component = 35.0

    volume_component = 0.0
    if volume_ratio is not None and min_volume_ratio > 0:
        volume_component = min(1.0, volume_ratio / min_volume_ratio) * 20.0
    elif volume_ratio is not None and volume_ratio > 0:
        volume_component = 20.0

    rsi_component = 0.0
    if rsi_filter_passed and rsi_value is not None:
        band_center = (rsi_entry_min + rsi_entry_max) / 2
        half_band = max((rsi_entry_max - rsi_entry_min) / 2, 1e-9)
        normalized_distance = min(1.0, abs(rsi_value - band_center) / half_band)
        rsi_component = (1.0 - normalized_distance) * 15.0

    macd_component = 0.0
    if macd_filter_passed and macd_histogram is not None and last_close > 0:
        macd_hist_pct = abs(macd_histogram) / last_close * 100
        macd_component = min(1.0, macd_hist_pct / 0.12) * 15.0

    slope_component = 0.0
    if ma_slope_positive:
        slope_component += 7.5
    if price_slope_positive:
        slope_component += 7.5

    trend_component = 0.0
    if bullish:
        trend_component = 15.0
    elif trend_follow_entry:
        trend_component = 10.0

    signal_score = _clamp_score(
        gap_component
        + volume_component
        + rsi_component
        + macd_component
        + slope_component
        + trend_component
    )
    signal_is_strong = signal_score >= signal_score_min
    entry_signal = (bullish or trend_follow_entry) and rsi_filter_passed and macd_filter_passed
    return {
        "bullish": bullish,
        "bearish": bearish,
        "gap_pct": gap_pct,
        "rsi_filter_passed": rsi_filter_passed,
        "macd_filter_passed": macd_filter_passed,
        "ma_slope_positive": ma_slope_positive,
        "price_slope_positive": price_slope_positive,
        "signal_is_strong": signal_is_strong,
        "signal_score": signal_score,
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
