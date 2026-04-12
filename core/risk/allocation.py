"""
수정 요약
- 2026-04-12: volume percentile, ATR percentile, HTF slope, 호가 압력 점수를 결합해 약한 단일 지표 의존도를 줄이도록 allocation score 를 확장
- 2026-04-10: allocation reason_top 을 최고 점수 축이 아니라 최저 점수 축 기준으로 바꿔 실제 약점 설명에 가깝게 조정
- 2026-04-09: signal/market/execution/diversification 기반 score_scale 계산 helper 를 추가
- 레짐별 포지션 스케일을 적용하되 최소 0, 최대 1.2 범위로 제한하는 공통 helper 를 추가했다.
- 알트/BTC 신규 진입과 추가매수의 포트폴리오 배분 호출을 공통 래퍼로 분리했다.
- 배분 계산 호출 방식이 봇마다 갈라지지 않도록 정리했다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AllocationScoreResult:
    allocation_score: float
    signal_score_component: float
    market_score_component: float
    execution_score_component: float
    diversification_score_component: float
    score_scale: float
    reason_top: str


def _clamp_score(value: float, *, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def _bucket_scale(*, score: float, settings) -> float:
    if score >= settings.score_bucket_very_strong:
        return min(settings.score_scale_max, 1.10)
    if score >= settings.score_bucket_strong:
        return min(settings.score_scale_max, 1.00)
    if score >= settings.score_bucket_neutral:
        return min(settings.score_scale_max, 0.90)
    if score >= settings.score_bucket_weak:
        return max(settings.score_scale_min, 0.75)
    return settings.score_scale_min


def compute_allocation_score(
    *,
    settings,
    signal_score: float,
    volume_ratio: float | None,
    required_volume_ratio: float | None,
    volume_ratio_percentile: float | None = None,
    trend_ok: bool,
    htf_slope_pct: float | None = None,
    low_energy_guard_active: bool,
    symbol_regime: str | None,
    atr_pct: float | None = None,
    atr_percentile: float | None = None,
    orderbook_pressure_score: float | None = None,
    fill_quality_avg_fill_ratio: float | None,
    fill_quality_entry_blocked: bool,
    correlation_with_btc: float | None,
    max_correlation_with_btc: float,
) -> AllocationScoreResult:
    """진입 품질을 하나의 allocation score 로 환산한다."""
    if not settings.enable_score_based_scaling:
        return AllocationScoreResult(
            allocation_score=100.0,
            signal_score_component=100.0,
            market_score_component=100.0,
            execution_score_component=100.0,
            diversification_score_component=100.0,
            score_scale=1.0,
            reason_top="score_scaling_disabled",
        )

    signal_component = _clamp_score(signal_score)

    market_component = 60.0
    if low_energy_guard_active:
        market_component = 0.0
    elif not trend_ok:
        market_component = 25.0
    elif symbol_regime in {"TRENDING", "TRENDING_EARLY", "TRENDING_MATURE", "BREAKOUT_ATTEMPT"}:
        market_component = 85.0
    elif symbol_regime in {"CHOPPY", "CHOPPY_LOW_VOL", "CHOPPY_HIGH_VOL"}:
        market_component = 45.0
    elif symbol_regime in {"OVERHEATED", "EXHAUSTION_RISK"}:
        market_component = 30.0

    if volume_ratio is not None and required_volume_ratio not in (None, 0):
        market_component = _clamp_score(
            market_component + min(20.0, (volume_ratio / required_volume_ratio) * 10.0)
        )
    if volume_ratio_percentile is not None:
        if volume_ratio_percentile < 35:
            market_component = _clamp_score(market_component - 10.0)
        elif 55 <= volume_ratio_percentile <= 85:
            market_component = _clamp_score(market_component + 6.0)
        elif volume_ratio_percentile > 95:
            market_component = _clamp_score(market_component - 6.0)

    if atr_percentile is not None:
        if atr_percentile < 30:
            market_component = _clamp_score(market_component - 8.0)
        elif 50 <= atr_percentile <= 85:
            market_component = _clamp_score(market_component + 5.0)
        elif atr_percentile > 95:
            market_component = _clamp_score(market_component - 4.0)

    if htf_slope_pct is not None:
        market_component = _clamp_score(
            market_component + max(-8.0, min(8.0, float(htf_slope_pct) * 200.0))
        )

    if atr_pct is not None and atr_pct < 0.08:
        market_component = _clamp_score(market_component - 10.0)

    execution_component = 65.0
    if fill_quality_entry_blocked:
        execution_component = 20.0
    elif fill_quality_avg_fill_ratio is not None:
        execution_component = _clamp_score(fill_quality_avg_fill_ratio * 100.0)
    if orderbook_pressure_score is not None:
        execution_component = _clamp_score(
            execution_component * 0.7 + float(orderbook_pressure_score) * 0.3
        )

    diversification_component = 65.0
    if correlation_with_btc is not None and max_correlation_with_btc > 0:
        if correlation_with_btc >= max_correlation_with_btc:
            diversification_component = 20.0
        else:
            headroom = max(1e-9, max_correlation_with_btc)
            diversification_component = _clamp_score(
                100.0 - (correlation_with_btc / headroom) * 50.0
            )

    allocation_score = _clamp_score(
        signal_component * settings.signal_weight
        + market_component * settings.market_weight
        + execution_component * settings.execution_weight
        + diversification_component * settings.diversification_weight
    )
    score_scale = _bucket_scale(score=allocation_score, settings=settings)

    component_map = {
        "signal": signal_component,
        "market": market_component,
        "execution": execution_component,
        "diversification": diversification_component,
    }
    reason_top = min(component_map.items(), key=lambda item: item[1])[0]

    return AllocationScoreResult(
        allocation_score=allocation_score,
        signal_score_component=signal_component,
        market_score_component=market_component,
        execution_score_component=execution_component,
        diversification_score_component=diversification_component,
        score_scale=score_scale,
        reason_top=reason_top,
    )


def apply_regime_position_scale(
    *,
    base_position_ratio: float,
    regime_scale: float,
    min_ratio: float = 0.0,
    max_ratio: float = 1.2,
) -> float:
    """기본 포지션 비중에 레짐 스케일을 적용하고 안전 범위로 제한한다."""
    scaled = base_position_ratio * regime_scale
    return max(min_ratio, min(max_ratio, scaled))


def build_alt_allocation(
    *,
    portfolio_allocator,
    exchange,
    symbol: str,
    quote_free: float,
    position_ratio: float,
    buy_split_ratio: float,
    dynamic_bonus_eligible: bool,
):
    requested_order_value = quote_free * position_ratio * buy_split_ratio
    allocation_decision = portfolio_allocator.build_buy_decision(
        exchange=exchange,
        symbol=symbol,
        requested_order_value_quote=requested_order_value,
        dynamic_bonus_eligible=dynamic_bonus_eligible,
    )
    return requested_order_value, allocation_decision


def build_btc_allocations(
    *,
    portfolio_allocator,
    exchange,
    symbol: str,
    quote_free: float,
    risk_per_trade: float,
    position_ratio: float,
    pyramid_position_ratio: float,
    score_scale: float,
    dynamic_bonus_eligible: bool,
):
    requested_order_value = quote_free * risk_per_trade * position_ratio
    requested_add_on_order_value = quote_free * risk_per_trade * pyramid_position_ratio * score_scale
    allocation_decision = portfolio_allocator.build_buy_decision(
        exchange=exchange,
        symbol=symbol,
        requested_order_value_quote=requested_order_value,
        dynamic_bonus_eligible=dynamic_bonus_eligible,
    )
    add_on_allocation_decision = portfolio_allocator.build_buy_decision(
        exchange=exchange,
        symbol=symbol,
        requested_order_value_quote=requested_add_on_order_value,
        dynamic_bonus_eligible=dynamic_bonus_eligible,
    )
    return requested_order_value, requested_add_on_order_value, allocation_decision, add_on_allocation_decision
