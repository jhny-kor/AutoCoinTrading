"""
작업 요약
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
) -> dict[str, float | bool]:
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
        }

    lower_reclaim = prev_close <= bb_lower and last_close > bb_lower
    upper_reject = bb_upper is not None and prev_close >= bb_upper and last_close < bb_upper
    mid_headroom_pct = ((bb_mid - last_close) / last_close * 100) if last_close > 0 else 0.0
    gap_pct = max(0.0, mid_headroom_pct)

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
    entry_signal = (
        lower_reclaim
        and gap_pct > 0
        and signal_is_strong
        and rsi_filter_passed
        and macd_filter_passed
    )
    return {
        "bullish": lower_reclaim,
        "bearish": upper_reject,
        "gap_pct": gap_pct,
        "signal_score": signal_score,
        "signal_is_strong": signal_is_strong,
        "entry_signal": entry_signal,
        "trend_follow_entry": False,
        "rsi_filter_passed": rsi_filter_passed,
        "macd_filter_passed": macd_filter_passed,
    }
