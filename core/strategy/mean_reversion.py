"""
작업 요약
- Bollinger 하단 reclaim 을 완전 해제하지 않고 하단 근접 신호를 소액/추가확인 probe 후보로만 허용
- 음수 slope + 고거래량 + 중고 ATR + 저점 근접 조합에서는 mean_reversion 진입을 차단하도록 보강
- ATR percentile 과 최근 range 위치를 함께 확인해 횡보장 반등 진입이 고변동/상단 추격으로 바뀌지 않도록 보강
- mean_reversion 전용 RSI 범위와 MACD 회복 조건을 적용해 추세형 hard filter 를 보수적으로 완화
- 횡보/혼조 구간에서 Bollinger 하단 복귀 기반 mean reversion 진입 신호를 계산하는 모듈을 추가
"""

from __future__ import annotations

from core.strategy.indicators import calc_weighted_signal_score


def compute_bollinger_mean_reversion_state(
    *,
    prev_close: float,
    last_close: float,
    bb_lower: float | None,
    bb_mid: float | None,
    bb_upper: float | None,
    bb_width_pct: float | None,
    squeeze_max_bandwidth_pct: float,
    rsi_value: float | None,
    signal_score_min: float,
    rsi_min: float,
    rsi_max: float,
    macd_histogram: float | None,
    prev_macd_histogram: float | None,
    allow_negative_macd: bool,
    require_macd_recovering: bool,
    macd_recovery_epsilon: float,
    atr_percentile: float | None = None,
    max_atr_percentile: float = 80.0,
    range_position_pct: float | None = None,
    max_range_position_pct: float = 35.0,
    ma_slope_pct: float | None = None,
    price_slope_pct: float | None = None,
    volume_ratio: float | None = None,
    distance_from_recent_low_pct: float | None = None,
    block_negative_slope_high_volume_atr: bool = True,
    negative_slope_threshold_pct: float = 0.0,
    high_volume_ratio: float = 2.0,
    mid_atr_percentile: float = 60.0,
    min_distance_from_low_pct: float = 0.10,
    allow_lower_near_probe: bool = False,
    lower_near_max_distance_pct: float = 0.12,
    lower_near_min_headroom_pct: float = 0.12,
    lower_near_position_scale: float = 0.25,
    lower_near_extra_confirmation_loops: int = 2,
) -> dict[str, float | bool | str]:
    """볼린저 하단 복귀와 중단 회귀 여지를 기반으로 mean reversion 신호를 계산한다."""
    if bb_lower is None or bb_mid is None:
        return {
            "bullish": False,
            "bearish": False,
            "gap_pct": 0.0,
            "signal_score": 0.0,
            "signal_is_strong": False,
            "entry_signal": False,
            "trend_follow_entry": False,
            "rsi_filter_passed": False,
            "macd_filter_passed": False,
            "atr_context_passed": False,
            "range_context_passed": False,
            "falling_knife_blocked": False,
            "negative_slope_context": False,
            "high_volume_context": False,
            "mid_atr_context": False,
            "low_reclaim_unconfirmed": False,
            "lower_reclaim_confirmed": False,
            "lower_near_probe_allowed": False,
            "lower_near_probe_reason": "bollinger_band_missing",
            "bb_lower_distance_pct": 0.0,
            "lower_near_position_scale": lower_near_position_scale,
            "lower_near_extra_confirmation_loops": 0,
        }

    lower_reclaim = prev_close <= bb_lower and last_close > bb_lower
    upper_reject = bb_upper is not None and prev_close >= bb_upper and last_close < bb_upper
    mid_headroom_pct = ((bb_mid - last_close) / last_close * 100) if last_close > 0 else 0.0
    gap_pct = max(0.0, mid_headroom_pct)
    bb_lower_distance_pct = ((last_close - bb_lower) / last_close * 100) if last_close > 0 else 0.0

    squeeze_component = 0.0
    if bb_width_pct is not None and squeeze_max_bandwidth_pct > 0:
        squeeze_component = max(
            0.0,
            min(100.0, 100.0 - (bb_width_pct / squeeze_max_bandwidth_pct) * 100.0),
        )

    reclaim_component = 100.0 if lower_reclaim else 0.0
    rsi_component = 0.0
    if rsi_value is not None:
        if rsi_value <= 35:
            rsi_component = 100.0
        elif rsi_value <= 45:
            rsi_component = 70.0
        elif rsi_value <= 55:
            rsi_component = 40.0

    headroom_component = min(100.0, gap_pct / 0.25 * 100.0) if gap_pct > 0 else 0.0

    rsi_filter_passed = rsi_value is not None and rsi_min <= rsi_value <= rsi_max
    macd_recovering = (
        macd_histogram is not None
        and prev_macd_histogram is not None
        and macd_histogram >= (prev_macd_histogram + macd_recovery_epsilon)
    )
    macd_direction_ok = (
        macd_histogram is not None
        and (allow_negative_macd or macd_histogram >= 0)
    )
    macd_filter_passed = (
        macd_direction_ok
        and ((not require_macd_recovering) or macd_recovering)
    )
    atr_context_passed = (
        atr_percentile is None
        or atr_percentile <= max_atr_percentile
    )
    range_context_passed = (
        range_position_pct is None
        or range_position_pct <= max_range_position_pct
    )
    negative_slope_context = (
        ma_slope_pct is not None
        and price_slope_pct is not None
        and ma_slope_pct < negative_slope_threshold_pct
        and price_slope_pct < negative_slope_threshold_pct
    )
    high_volume_context = (
        volume_ratio is not None
        and volume_ratio >= high_volume_ratio
    )
    mid_atr_context = (
        atr_percentile is not None
        and atr_percentile >= mid_atr_percentile
    )
    low_reclaim_unconfirmed = (
        distance_from_recent_low_pct is not None
        and distance_from_recent_low_pct <= min_distance_from_low_pct
    )
    falling_knife_blocked = (
        block_negative_slope_high_volume_atr
        and negative_slope_context
        and high_volume_context
        and mid_atr_context
        and low_reclaim_unconfirmed
    )

    signal_score = calc_weighted_signal_score(
        {
            "squeeze": squeeze_component,
            "reclaim": reclaim_component,
            "rsi": rsi_component,
            "headroom": headroom_component,
        },
        {
            "squeeze": 0.5,
            "reclaim": 0.25,
            "rsi": 0.15,
            "headroom": 0.10,
        },
    )
    signal_is_strong = signal_score >= signal_score_min
    lower_near_price_context = (
        not lower_reclaim
        and 0.0 <= bb_lower_distance_pct <= lower_near_max_distance_pct
    )
    lower_near_headroom_passed = gap_pct >= lower_near_min_headroom_pct
    lower_near_probe_allowed = (
        allow_lower_near_probe
        and lower_near_price_context
        and lower_near_headroom_passed
        and signal_is_strong
        and rsi_filter_passed
        and macd_filter_passed
        and atr_context_passed
        and range_context_passed
        and not falling_knife_blocked
    )
    lower_near_probe_reason = "lower_near_probe_allowed"
    if not allow_lower_near_probe:
        lower_near_probe_reason = "lower_near_probe_disabled"
    elif lower_reclaim:
        lower_near_probe_reason = "lower_reclaim_confirmed"
    elif not lower_near_price_context:
        lower_near_probe_reason = "lower_near_distance_too_far"
    elif not lower_near_headroom_passed:
        lower_near_probe_reason = "lower_near_headroom_low"
    elif not signal_is_strong:
        lower_near_probe_reason = "lower_near_signal_low"
    elif not rsi_filter_passed:
        lower_near_probe_reason = "lower_near_rsi_blocked"
    elif not macd_filter_passed:
        lower_near_probe_reason = "lower_near_macd_blocked"
    elif not atr_context_passed:
        lower_near_probe_reason = "lower_near_atr_blocked"
    elif not range_context_passed:
        lower_near_probe_reason = "lower_near_range_blocked"
    elif falling_knife_blocked:
        lower_near_probe_reason = "lower_near_falling_knife"

    entry_signal = (
        (lower_reclaim or lower_near_probe_allowed)
        and gap_pct > 0
        and signal_is_strong
        and rsi_filter_passed
        and macd_filter_passed
        and atr_context_passed
        and range_context_passed
        and not falling_knife_blocked
    )
    return {
        "bullish": lower_reclaim or lower_near_probe_allowed,
        "bearish": upper_reject,
        "gap_pct": gap_pct,
        "signal_score": signal_score,
        "signal_is_strong": signal_is_strong,
        "entry_signal": entry_signal,
        "trend_follow_entry": False,
        "rsi_filter_passed": rsi_filter_passed,
        "macd_filter_passed": macd_filter_passed,
        "atr_context_passed": atr_context_passed,
        "range_context_passed": range_context_passed,
        "falling_knife_blocked": falling_knife_blocked,
        "negative_slope_context": negative_slope_context,
        "high_volume_context": high_volume_context,
        "mid_atr_context": mid_atr_context,
        "low_reclaim_unconfirmed": low_reclaim_unconfirmed,
        "lower_reclaim_confirmed": lower_reclaim,
        "lower_near_probe_allowed": lower_near_probe_allowed,
        "lower_near_probe_reason": lower_near_probe_reason,
        "bb_lower_distance_pct": bb_lower_distance_pct,
        "lower_near_position_scale": lower_near_position_scale,
        "lower_near_extra_confirmation_loops": lower_near_extra_confirmation_loops
        if lower_near_probe_allowed
        else 0,
    }
