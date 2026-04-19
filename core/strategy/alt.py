"""
작업 요약
- regime별 동적 가중치를 적용하는 알트 신호 점수 계산으로 EMA slope / Bollinger Squeeze 비중을 장 상태에 맞게 조정
- 2026-04-09: 손절 후 재진입은 최소 시간과 신호/거래량/HTF 복구를 함께 보는 패턴 기반 gate helper 를 추가
- 2026-04-06: Bollinger Squeeze + 거래량 확장 돌파 기반 병렬 진입 모드 구성
- 알트 신호 계산과 평균단가 대비 추가매수 허용 여부를 공통 함수로 분리했다.
- 골든/데드크로스와 trend-follow 진입 계산을 한 곳으로 모았다.
- RSI, MACD, 기울기, 거래량을 반영한 신호 스코어 계산을 추가해 횡보장 오탐을 줄이도록 보강했다.
"""

from __future__ import annotations

from core.strategy.indicators import calc_weighted_signal_score


def _clamp_score(raw: float) -> float:
    """신호 스코어를 0~100 범위로 제한한다."""
    return max(0.0, min(100.0, raw))


def _get_alt_signal_weights(symbol_regime: str | None, entry_mode: str) -> dict[str, float]:
    """레짐별 알트 신호 점수 가중치를 반환한다."""
    if entry_mode == "squeeze":
        return {
            "squeeze": 0.5,
            "volume": 0.2,
            "trend": 0.1,
            "slope": 0.1,
            "macd": 0.05,
            "rsi": 0.05,
        }

    if symbol_regime in {"TRENDING", "TRENDING_EARLY", "TRENDING_MATURE"}:
        return {
            "slope": 0.4,
            "trend": 0.2,
            "gap": 0.15,
            "volume": 0.1,
            "macd": 0.1,
            "rsi": 0.05,
        }
    if symbol_regime == "BREAKOUT_ATTEMPT":
        return {
            "gap": 0.25,
            "volume": 0.2,
            "trend": 0.15,
            "slope": 0.15,
            "squeeze": 0.15,
            "macd": 0.05,
            "rsi": 0.05,
        }
    if symbol_regime in {"CHOPPY", "CHOPPY_LOW_VOL", "CHOPPY_HIGH_VOL"}:
        return {
            "squeeze": 0.5,
            "rsi": 0.15,
            "macd": 0.15,
            "gap": 0.1,
            "volume": 0.05,
            "slope": 0.05,
        }
    return {
        "gap": 0.2,
        "volume": 0.15,
        "rsi": 0.15,
        "macd": 0.15,
        "slope": 0.15,
        "trend": 0.1,
        "squeeze": 0.1,
    }


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
    symbol_regime: str | None = None,
    entry_mode: str = "ma",
    bb_width_pct: float | None = None,
    squeeze_max_bandwidth_pct: float = 3.0,
    bb_upper: float | None = None,
    squeeze_min_volume_ratio: float = 2.5,
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
    trend_follow_entry = False
    if entry_mode == "ma":
        trend_follow_entry = (
            enable_trend_follow_entry
            and last_close > last_ma
            and (not require_prev_above_ma or prev_close > prev_ma)
            and (not require_price_rising or last_close > prev_close)
            and (not require_ma_slope_positive or ma_slope_positive)
        )
    gap_component = 0.0
    if min_gap_pct > 0:
        gap_component = min(1.0, gap_pct / min_gap_pct) * 100.0
    elif gap_pct > 0:
        gap_component = 100.0

    volume_component = 0.0
    if volume_ratio is not None and min_volume_ratio > 0:
        volume_component = min(1.0, volume_ratio / min_volume_ratio) * 100.0
    elif volume_ratio is not None and volume_ratio > 0:
        volume_component = 100.0

    rsi_component = 0.0
    if rsi_filter_passed and rsi_value is not None:
        band_center = (rsi_entry_min + rsi_entry_max) / 2
        half_band = max((rsi_entry_max - rsi_entry_min) / 2, 1e-9)
        normalized_distance = min(1.0, abs(rsi_value - band_center) / half_band)
        rsi_component = (1.0 - normalized_distance) * 100.0

    macd_component = 0.0
    if macd_filter_passed and macd_histogram is not None and last_close > 0:
        macd_hist_pct = abs(macd_histogram) / last_close * 100
        macd_component = min(1.0, macd_hist_pct / 0.12) * 100.0

    slope_component = 0.0
    if ma_slope_positive:
        slope_component += 50.0
    if price_slope_positive:
        slope_component += 50.0

    trend_component = 0.0
    if bullish:
        trend_component = 100.0
    elif trend_follow_entry:
        trend_component = 70.0

    squeeze_component = 0.0
    if bb_width_pct is not None and squeeze_max_bandwidth_pct > 0:
        if bb_width_pct <= squeeze_max_bandwidth_pct:
            squeeze_component = 100.0
        else:
            squeeze_component = max(
                0.0,
                100.0 - ((bb_width_pct - squeeze_max_bandwidth_pct) / squeeze_max_bandwidth_pct) * 100.0,
            )

    entry_signal = False
    signal_score = 0.0

    if entry_mode == "squeeze":
        is_squeezed = bb_width_pct is not None and bb_width_pct <= squeeze_max_bandwidth_pct
        volume_exploded = volume_ratio is not None and volume_ratio >= squeeze_min_volume_ratio
        breakout = bb_upper is not None and last_close > bb_upper

        entry_signal = (
            is_squeezed
            and volume_exploded
            and breakout
            and rsi_filter_passed
            and macd_filter_passed
        )
        signal_score = calc_weighted_signal_score(
            {
                "squeeze": squeeze_component,
                "volume": volume_component,
                "trend": 100.0 if breakout else 0.0,
                "slope": slope_component,
                "macd": macd_component,
                "rsi": rsi_component,
            },
            _get_alt_signal_weights(symbol_regime, entry_mode),
        )
    else:
        signal_score = calc_weighted_signal_score(
            {
                "gap": gap_component,
                "volume": volume_component,
                "rsi": rsi_component,
                "macd": macd_component,
                "slope": slope_component,
                "trend": trend_component,
                "squeeze": squeeze_component,
            },
            _get_alt_signal_weights(symbol_regime, entry_mode),
        )
        entry_signal = (bullish or trend_follow_entry) and rsi_filter_passed and macd_filter_passed

    signal_is_strong = signal_score >= signal_score_min
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


def compute_alt_stop_loss_reentry_gate(
    *,
    enabled: bool,
    elapsed_since_stop_loss_sec: float,
    min_cooldown_sec: int,
    entry_signal: bool,
    bullish: bool,
    signal_score: float,
    min_signal_score: float,
    volume_ratio: float | None,
    min_volume_ratio: float,
    min_volume_ratio_multiplier: float,
    htf_bullish: bool,
    require_htf_bullish: bool,
    require_fresh_cross: bool,
) -> dict[str, float | bool]:
    """손절 후 알트 재진입 허용 여부를 패턴 기준으로 계산한다."""
    effective_min_volume_ratio = max(0.0, min_volume_ratio * max(min_volume_ratio_multiplier, 0.0))
    cooldown_passed = elapsed_since_stop_loss_sec >= max(0, min_cooldown_sec)
    signal_score_passed = signal_score >= min_signal_score
    volume_passed = (
        volume_ratio is not None and volume_ratio >= effective_min_volume_ratio
    )
    htf_passed = (not require_htf_bullish) or htf_bullish
    fresh_cross_passed = (not require_fresh_cross) or bullish
    pattern_ready = (
        enabled
        and cooldown_passed
        and entry_signal
        and signal_score_passed
        and volume_passed
        and htf_passed
        and fresh_cross_passed
    )
    return {
        "enabled": enabled,
        "cooldown_passed": cooldown_passed,
        "signal_score_passed": signal_score_passed,
        "volume_passed": volume_passed,
        "htf_passed": htf_passed,
        "fresh_cross_passed": fresh_cross_passed,
        "pattern_ready": pattern_ready,
        "required_min_volume_ratio": effective_min_volume_ratio,
    }
