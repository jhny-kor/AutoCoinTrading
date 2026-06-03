"""
수정 요약
- 2026-06-03: BTC LOW_ENERGY 저ATR 구간의 알트 고점 추격 진입 차단 helper 를 추가했다.
- 2026-05-22: BTC/KRW 고ATR+최근 고점 근접 조건을 거래량과 무관한 추격 진입 차단 기준으로 추가했다.
- 2026-05-19: BTC/KRW 고점권+고ATR+거래량 폭증 추격 진입을 RSI 없이 차단하는 helper 를 추가했다.
- 2026-05-02: BTC 위험 레짐+고상관+알트 고ATR, 거래량+ATR+체결/호가 약세, 손절 후 유사 조건 재진입 가드를 추가했다.
- 거래량, ATR, RSI, 최근 가격 위치를 결합해 단독 지표의 오탐을 줄이는 진입 보조 필터를 추가했다.
"""

from __future__ import annotations


def safe_optional_float(value) -> float | None:
    """로그/설정에서 읽은 숫자 후보를 안전하게 float 로 바꾼다."""
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def calc_recent_range_context(
    ohlcv: list[list[float]],
    *,
    last_close: float,
    lookback: int = 20,
) -> dict[str, float | None]:
    """최근 range 안에서 현재가 위치와 고점/저점까지의 거리를 계산한다."""
    if last_close <= 0 or not ohlcv:
        return {
            "recent_high": None,
            "recent_low": None,
            "range_position_pct": None,
            "distance_from_recent_high_pct": None,
            "distance_from_recent_low_pct": None,
        }

    recent = ohlcv[-max(1, lookback):]
    highs = [float(row[2]) for row in recent if len(row) > 3]
    lows = [float(row[3]) for row in recent if len(row) > 3]
    if not highs or not lows:
        return {
            "recent_high": None,
            "recent_low": None,
            "range_position_pct": None,
            "distance_from_recent_high_pct": None,
            "distance_from_recent_low_pct": None,
        }

    recent_high = max(highs)
    recent_low = min(lows)
    recent_range = recent_high - recent_low
    range_position_pct = None
    if recent_range > 0:
        range_position_pct = (last_close - recent_low) / recent_range * 100.0
        range_position_pct = max(0.0, min(100.0, range_position_pct))

    return {
        "recent_high": recent_high,
        "recent_low": recent_low,
        "range_position_pct": range_position_pct,
        "distance_from_recent_high_pct": max(0.0, (recent_high - last_close) / last_close * 100.0),
        "distance_from_recent_low_pct": max(0.0, (last_close - recent_low) / last_close * 100.0),
    }


def is_overheated_entry_risk(
    *,
    volume_ratio: float | None,
    atr_percentile: float | None,
    rsi_value: float | None,
    volume_ratio_threshold: float,
    atr_percentile_threshold: float,
    rsi_threshold: float,
) -> bool:
    """고거래량, 고ATR, RSI 과열이 동시에 나타나는 추격 진입 리스크를 판정한다."""
    return (
        volume_ratio is not None
        and atr_percentile is not None
        and rsi_value is not None
        and volume_ratio >= volume_ratio_threshold
        and atr_percentile >= atr_percentile_threshold
        and rsi_value >= rsi_threshold
    )


def is_symbol_top_chase_entry_risk(
    *,
    enabled: bool,
    symbol: str,
    target_symbol: str,
    volume_ratio: float | None,
    atr_percentile: float | None,
    range_position_pct: float | None,
    volume_ratio_threshold: float,
    atr_percentile_threshold: float,
    range_position_threshold: float,
    distance_from_recent_high_pct: float | None = None,
    near_high_atr_percentile_threshold: float | None = None,
    distance_from_high_threshold_pct: float | None = None,
) -> bool:
    """특정 심볼의 range 최상단/고ATR 고점 근접 진입을 추격 진입으로 본다."""
    if not enabled or symbol != target_symbol or atr_percentile is None:
        return False

    volume_range_risk = (
        volume_ratio is not None
        and range_position_pct is not None
        and volume_ratio >= volume_ratio_threshold
        and atr_percentile >= atr_percentile_threshold
        and range_position_pct >= range_position_threshold
    )
    near_high_atr_risk = (
        distance_from_recent_high_pct is not None
        and near_high_atr_percentile_threshold is not None
        and distance_from_high_threshold_pct is not None
        and atr_percentile >= near_high_atr_percentile_threshold
        and distance_from_recent_high_pct <= distance_from_high_threshold_pct
    )
    return volume_range_risk or near_high_atr_risk


def requires_overheat_confirmation(
    *,
    signal_is_strong: bool,
    range_position_pct: float | None,
    distance_from_recent_high_pct: float | None,
    range_position_threshold: float,
    distance_from_high_threshold_pct: float,
) -> bool:
    """강한 신호라도 최근 range 상단 추격이면 추가 confirmation 을 요구한다."""
    if not signal_is_strong:
        return False
    range_top_risk = (
        range_position_pct is not None
        and range_position_pct >= range_position_threshold
    )
    near_high_risk = (
        distance_from_recent_high_pct is not None
        and distance_from_recent_high_pct <= distance_from_high_threshold_pct
    )
    return range_top_risk or near_high_risk


def is_low_energy_top_chase_entry_risk(
    *,
    enabled: bool,
    btc_regime: str | None,
    btc_atr_pct: float | None,
    range_position_pct: float | None,
    distance_from_recent_high_pct: float | None,
    risky_btc_regimes: tuple[str, ...],
    max_btc_atr_pct: float,
    range_position_threshold: float,
    distance_from_high_threshold_pct: float,
) -> bool:
    """BTC 저에너지+저ATR 구간에서 알트가 최근 고점권이면 추격 진입으로 본다."""
    if not enabled or btc_atr_pct is None:
        return False

    normalized_regime = str(btc_regime or "UNKNOWN").strip().upper()
    risky_regimes = {str(item).strip().upper() for item in risky_btc_regimes}
    if normalized_regime not in risky_regimes or btc_atr_pct > max_btc_atr_pct:
        return False

    range_top_risk = (
        range_position_pct is not None
        and range_position_pct >= range_position_threshold
    )
    near_high_risk = (
        distance_from_recent_high_pct is not None
        and distance_from_recent_high_pct <= distance_from_high_threshold_pct
    )
    return range_top_risk or near_high_risk


def is_btc_regime_correlation_volatility_risk(
    *,
    btc_regime: str | None,
    correlation_with_btc: float | None,
    alt_atr_percentile: float | None,
    risky_btc_regimes: tuple[str, ...],
    min_correlation: float,
    min_alt_atr_percentile: float,
) -> bool:
    """BTC 위험 레짐에서 알트가 BTC와 강하게 묶이고 자체 변동성도 높으면 진입 리스크로 본다."""
    normalized_regime = str(btc_regime or "UNKNOWN").strip().upper()
    risky_regimes = {str(item).strip().upper() for item in risky_btc_regimes}
    return (
        normalized_regime in risky_regimes
        and correlation_with_btc is not None
        and alt_atr_percentile is not None
        and correlation_with_btc >= min_correlation
        and alt_atr_percentile >= min_alt_atr_percentile
    )


def is_volume_atr_execution_weak_risk(
    *,
    volume_ratio: float | None,
    atr_percentile: float | None,
    fill_quality_avg_fill_ratio: float | None,
    fill_quality_sample_count: int,
    orderbook_pressure_score: float | None,
    volume_ratio_threshold: float,
    atr_percentile_threshold: float,
    min_fill_ratio: float,
    min_fill_sample_count: int,
    min_orderbook_pressure_score: float,
) -> bool:
    """거래량과 ATR이 같이 뜨는데 체결 품질/매수 우위가 약하면 변동성 폭발로 보고 차단한다."""
    volume_atr_hot = (
        volume_ratio is not None
        and atr_percentile is not None
        and volume_ratio >= volume_ratio_threshold
        and atr_percentile >= atr_percentile_threshold
    )
    if not volume_atr_hot:
        return False

    weak_fill = (
        fill_quality_avg_fill_ratio is not None
        and fill_quality_sample_count >= max(1, min_fill_sample_count)
        and fill_quality_avg_fill_ratio < min_fill_ratio
    )
    weak_orderbook = (
        orderbook_pressure_score is not None
        and orderbook_pressure_score < min_orderbook_pressure_score
    )
    return weak_fill or weak_orderbook


def is_stop_loss_context_reentry_risk(
    *,
    elapsed_since_stop_loss_sec: float,
    cooldown_sec: int,
    current_context: dict[str, object],
    previous_context: dict[str, object] | None,
    min_similarity_count: int,
) -> bool:
    """손절 직후 이전 손절과 유사한 시장 조건이면 재진입을 막는다."""
    if previous_context is None:
        return False
    if elapsed_since_stop_loss_sec > cooldown_sec:
        return False

    comparable_keys = (
        "strategy_key",
        "symbol_regime",
        "btc_reference_regime",
        "high_atr",
        "high_volume",
        "range_top_risk",
        "high_btc_correlation",
    )
    similarity_count = sum(
        1
        for key in comparable_keys
        if current_context.get(key) == previous_context.get(key)
    )
    return similarity_count >= max(1, min_similarity_count)
