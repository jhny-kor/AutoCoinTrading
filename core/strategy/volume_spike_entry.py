"""
작업 요약
- 거래량 상한 초과 신호를 손절방지 조건이 맞을 때만 소액/추가확인 후보로 낮추는 판단 helper 를 추가했다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VolumeSpikeEntryDowngrade:
    """거래량 급등 진입 차단을 소액 후보로 낮출 수 있는지 나타낸다."""

    allowed: bool
    reason: str
    position_scale: float
    extra_confirmation_loops: int


def evaluate_volume_spike_entry_downgrade(
    *,
    enabled: bool,
    symbol: str,
    eligible_symbols: tuple[str, ...],
    volume_ratio: float | None,
    max_volume_ratio: float,
    hard_max_volume_ratio: float,
    signal_score: float,
    min_signal_score: float,
    htf_bullish: bool,
    require_htf_bullish: bool,
    orderbook_pressure_score: float | None,
    min_orderbook_pressure_score: float,
    atr_percentile: float | None,
    max_atr_percentile: float,
    position_scale: float,
    extra_confirmation_loops: int,
) -> VolumeSpikeEntryDowngrade:
    """손절 리스크가 낮은 거래량 급등만 소액 진입 후보로 허용한다."""
    bounded_scale = max(0.0, min(position_scale, 1.0))
    bounded_extra_loops = max(0, extra_confirmation_loops)
    blocked = VolumeSpikeEntryDowngrade(
        allowed=False,
        reason="not_applicable",
        position_scale=1.0,
        extra_confirmation_loops=0,
    )

    if not enabled:
        return blocked
    if symbol not in eligible_symbols:
        return VolumeSpikeEntryDowngrade(False, "symbol_not_enabled", 1.0, 0)
    if volume_ratio is None:
        return VolumeSpikeEntryDowngrade(False, "volume_missing", 1.0, 0)
    if volume_ratio <= max_volume_ratio:
        return VolumeSpikeEntryDowngrade(False, "within_normal_volume_cap", 1.0, 0)
    if volume_ratio >= hard_max_volume_ratio:
        return VolumeSpikeEntryDowngrade(False, "volume_extreme", 1.0, 0)
    if signal_score < min_signal_score:
        return VolumeSpikeEntryDowngrade(False, "signal_score_low", 1.0, 0)
    if require_htf_bullish and not htf_bullish:
        return VolumeSpikeEntryDowngrade(False, "higher_timeframe_not_bullish", 1.0, 0)
    if orderbook_pressure_score is None:
        return VolumeSpikeEntryDowngrade(False, "orderbook_pressure_missing", 1.0, 0)
    if orderbook_pressure_score < min_orderbook_pressure_score:
        return VolumeSpikeEntryDowngrade(False, "orderbook_pressure_low", 1.0, 0)
    if atr_percentile is None:
        return VolumeSpikeEntryDowngrade(False, "atr_percentile_missing", 1.0, 0)
    if atr_percentile > max_atr_percentile:
        return VolumeSpikeEntryDowngrade(False, "atr_percentile_high", 1.0, 0)

    return VolumeSpikeEntryDowngrade(
        allowed=True,
        reason="small_size_extra_confirmation",
        position_scale=bounded_scale,
        extra_confirmation_loops=bounded_extra_loops,
    )
