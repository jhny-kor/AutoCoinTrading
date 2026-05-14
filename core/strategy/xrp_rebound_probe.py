"""
작업 요약
- XRP/KRW 전용 고점수 반등 probe 판정을 공통 helper 로 분리했다.
- mean_reversion 하단 reclaim 미확인은 전역 해제가 아니라 XRP 전용 보수 조건에서만 소액 후보로 낮춘다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class XrpReboundProbeDecision:
    """XRP/KRW 고점수 반등 probe 허용 여부와 적용 비중을 나타낸다."""

    allowed: bool
    reason: str
    position_scale: float
    extra_confirmation_loops: int


@dataclass(frozen=True)
class XrpReboundProbeState:
    """XRP 반등 probe 적용 뒤 봇이 사용할 진입 상태를 나타낸다."""

    decision: XrpReboundProbeDecision
    entry_signal: bool
    signal_is_strong: bool
    bullish: bool
    mean_reversion_lower_near_probe_allowed: bool
    mean_reversion_lower_near_extra_confirmation_loops: int
    lower_near_suppressed: bool


def _bounded_scale(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def evaluate_xrp_rebound_probe(
    *,
    enabled: bool,
    symbol: str,
    eligible_symbols: tuple[str, ...],
    signal_score: float,
    min_signal_score: float,
    htf_bearish: bool,
    rsi_filter_passed: bool,
    macd_filter_passed: bool,
    lower_reclaim_confirmed: bool,
    falling_knife_blocked: bool,
    position_scale: float,
    extra_confirmation_loops: int,
) -> XrpReboundProbeDecision:
    """XRP/KRW 하단 reclaim 미확인 신호를 소액 반등 후보로 낮출지 판단한다."""
    bounded_scale = _bounded_scale(position_scale)
    if symbol not in eligible_symbols:
        return XrpReboundProbeDecision(
            False,
            "xrp_rebound_probe_symbol_not_enabled",
            bounded_scale,
            0,
        )
    if not enabled:
        return XrpReboundProbeDecision(
            False,
            "xrp_rebound_probe_disabled",
            bounded_scale,
            0,
        )
    if lower_reclaim_confirmed:
        return XrpReboundProbeDecision(
            False,
            "xrp_rebound_probe_lower_reclaim_confirmed",
            bounded_scale,
            0,
        )
    if signal_score < min_signal_score:
        return XrpReboundProbeDecision(
            False,
            "xrp_rebound_probe_signal_score_low",
            bounded_scale,
            0,
        )
    if htf_bearish:
        return XrpReboundProbeDecision(
            False,
            "xrp_rebound_probe_htf_bearish",
            bounded_scale,
            0,
        )
    if not rsi_filter_passed:
        return XrpReboundProbeDecision(
            False,
            "xrp_rebound_probe_rsi_blocked",
            bounded_scale,
            0,
        )
    if not macd_filter_passed:
        return XrpReboundProbeDecision(
            False,
            "xrp_rebound_probe_macd_blocked",
            bounded_scale,
            0,
        )
    if falling_knife_blocked:
        return XrpReboundProbeDecision(
            False,
            "xrp_rebound_probe_falling_knife",
            bounded_scale,
            0,
        )
    if bounded_scale <= 0:
        return XrpReboundProbeDecision(
            False,
            "xrp_rebound_probe_position_scale_zero",
            bounded_scale,
            0,
        )
    return XrpReboundProbeDecision(
        True,
        "xrp_rebound_probe_allowed",
        bounded_scale,
        max(0, int(extra_confirmation_loops)),
    )


def resolve_xrp_rebound_probe_state(
    *,
    enabled: bool,
    symbol: str,
    eligible_symbols: tuple[str, ...],
    strategy_key: str,
    signal_score: float,
    min_signal_score: float,
    htf_bearish: bool,
    rsi_filter_passed: bool,
    macd_filter_passed: bool,
    lower_reclaim_confirmed: bool,
    falling_knife_blocked: bool,
    position_scale: float,
    extra_confirmation_loops: int,
    entry_signal: bool,
    signal_is_strong: bool,
    bullish: bool,
    mean_reversion_lower_near_probe_allowed: bool,
    mean_reversion_lower_near_extra_confirmation_loops: int,
) -> XrpReboundProbeState:
    """XRP 전용 probe 판정과 lower-near 전역 예외 억제를 한 번에 처리한다."""
    decision = evaluate_xrp_rebound_probe(
        enabled=enabled,
        symbol=symbol,
        eligible_symbols=eligible_symbols,
        signal_score=signal_score,
        min_signal_score=min_signal_score,
        htf_bearish=htf_bearish,
        rsi_filter_passed=rsi_filter_passed,
        macd_filter_passed=macd_filter_passed,
        lower_reclaim_confirmed=lower_reclaim_confirmed,
        falling_knife_blocked=falling_knife_blocked,
        position_scale=position_scale,
        extra_confirmation_loops=extra_confirmation_loops,
    )
    normalized_strategy = str(strategy_key or "").strip().lower()
    probe_strategy_scope = (
        symbol in eligible_symbols
        and normalized_strategy in {"mean_reversion", "low_energy_probe"}
    )
    if symbol in eligible_symbols and not probe_strategy_scope:
        decision = XrpReboundProbeDecision(
            False,
            "xrp_rebound_probe_strategy_not_applicable",
            decision.position_scale,
            0,
        )
    probe_scope = probe_strategy_scope and not lower_reclaim_confirmed
    resolved_entry_signal = bool(entry_signal)
    resolved_signal_is_strong = bool(signal_is_strong)
    resolved_bullish = bool(bullish)
    resolved_lower_near_allowed = bool(mean_reversion_lower_near_probe_allowed)
    resolved_lower_near_extra_loops = int(
        mean_reversion_lower_near_extra_confirmation_loops
    )
    lower_near_suppressed = False

    if probe_scope and resolved_lower_near_allowed:
        resolved_lower_near_allowed = False
        resolved_lower_near_extra_loops = 0
        resolved_entry_signal = False
        resolved_bullish = False
        lower_near_suppressed = True

    if probe_scope and decision.allowed:
        resolved_entry_signal = True
        resolved_signal_is_strong = True
        resolved_bullish = True

    return XrpReboundProbeState(
        decision=decision,
        entry_signal=resolved_entry_signal,
        signal_is_strong=resolved_signal_is_strong,
        bullish=resolved_bullish,
        mean_reversion_lower_near_probe_allowed=resolved_lower_near_allowed,
        mean_reversion_lower_near_extra_confirmation_loops=resolved_lower_near_extra_loops,
        lower_near_suppressed=lower_near_suppressed,
    )
