"""
작업 요약
- LOW_ENERGY 완전 차단을 고품질 소액/추가확인 후보로 보정할 수 있는 공통 판정 helper 를 추가했다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LowEnergyProbeDecision:
    """저에너지 장에서 제한적 신규 진입을 허용할지에 대한 판정 결과."""

    allowed: bool
    reason: str
    position_scale: float
    extra_confirmation_loops: int


def evaluate_low_energy_probe(
    *,
    enabled: bool,
    low_energy_guard_active: bool,
    signal_score: float,
    min_signal_score: float,
    htf_bullish: bool,
    require_htf_bullish: bool,
    volume_ratio: float | None,
    min_volume_ratio: float,
    orderbook_pressure_score: float | None = None,
    min_orderbook_pressure_score: float = 0.0,
    atr_percentile: float | None = None,
    max_atr_percentile: float | None = None,
    falling_knife_blocked: bool = False,
    position_scale: float = 0.25,
    extra_confirmation_loops: int = 2,
) -> LowEnergyProbeDecision:
    """LOW_ENERGY 신규 진입을 소액 후보로 낮출 수 있는지 보수적으로 확인한다."""
    if not low_energy_guard_active:
        return LowEnergyProbeDecision(
            allowed=False,
            reason="low_energy_inactive",
            position_scale=position_scale,
            extra_confirmation_loops=0,
        )
    if not enabled:
        return LowEnergyProbeDecision(
            allowed=False,
            reason="low_energy_probe_disabled",
            position_scale=position_scale,
            extra_confirmation_loops=0,
        )
    if signal_score < min_signal_score:
        return LowEnergyProbeDecision(
            allowed=False,
            reason="low_energy_probe_signal_low",
            position_scale=position_scale,
            extra_confirmation_loops=0,
        )
    if require_htf_bullish and not htf_bullish:
        return LowEnergyProbeDecision(
            allowed=False,
            reason="low_energy_probe_htf_not_bullish",
            position_scale=position_scale,
            extra_confirmation_loops=0,
        )
    if volume_ratio is None:
        return LowEnergyProbeDecision(
            allowed=False,
            reason="low_energy_probe_volume_missing",
            position_scale=position_scale,
            extra_confirmation_loops=0,
        )
    if volume_ratio < min_volume_ratio:
        return LowEnergyProbeDecision(
            allowed=False,
            reason="low_energy_probe_volume_low",
            position_scale=position_scale,
            extra_confirmation_loops=0,
        )
    if min_orderbook_pressure_score > 0:
        if orderbook_pressure_score is None:
            return LowEnergyProbeDecision(
                allowed=False,
                reason="low_energy_probe_orderbook_missing",
                position_scale=position_scale,
                extra_confirmation_loops=0,
            )
        if orderbook_pressure_score < min_orderbook_pressure_score:
            return LowEnergyProbeDecision(
                allowed=False,
                reason="low_energy_probe_orderbook_weak",
                position_scale=position_scale,
                extra_confirmation_loops=0,
            )
    if max_atr_percentile is not None and atr_percentile is not None:
        if atr_percentile > max_atr_percentile:
            return LowEnergyProbeDecision(
                allowed=False,
                reason="low_energy_probe_atr_too_high",
                position_scale=position_scale,
                extra_confirmation_loops=0,
            )
    if falling_knife_blocked:
        return LowEnergyProbeDecision(
            allowed=False,
            reason="low_energy_probe_falling_knife",
            position_scale=position_scale,
            extra_confirmation_loops=0,
        )

    return LowEnergyProbeDecision(
        allowed=True,
        reason="low_energy_probe_allowed",
        position_scale=position_scale,
        extra_confirmation_loops=extra_confirmation_loops,
    )
