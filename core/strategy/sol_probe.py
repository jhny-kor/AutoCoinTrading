"""
작업 요약
- SOL 제한형 probe 진입과 최대 보유 시간 청산 판단을 공통 helper 로 분리했다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SolProbeDecision:
    """SOL 제한형 probe 진입 허용 여부와 적용 배율을 나타낸다."""

    allowed: bool
    reason: str
    position_scale: float


def _bounded_scale(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def evaluate_sol_probe_entry(
    *,
    enabled: bool,
    symbol: str,
    eligible_symbols: tuple[str, ...],
    signal_score: float,
    min_signal_score: float,
    has_position: bool,
    current_entry_count: int,
    position_scale: float,
) -> SolProbeDecision:
    """SOL 전용 소액 probe 진입을 허용할지 판단한다."""
    bounded_scale = _bounded_scale(position_scale)
    if not enabled:
        return SolProbeDecision(False, "sol_probe_disabled", bounded_scale)
    if symbol not in eligible_symbols:
        return SolProbeDecision(False, "sol_probe_symbol_not_enabled", bounded_scale)
    if has_position:
        return SolProbeDecision(False, "sol_probe_position_exists", bounded_scale)
    if current_entry_count > 0:
        return SolProbeDecision(False, "sol_probe_entry_count_exists", bounded_scale)
    if signal_score < min_signal_score:
        return SolProbeDecision(False, "sol_probe_signal_score_low", bounded_scale)
    if bounded_scale <= 0:
        return SolProbeDecision(False, "sol_probe_position_scale_zero", bounded_scale)
    return SolProbeDecision(True, "sol_probe_allowed", bounded_scale)


def scale_probe_order_value(order_value_quote: float, decision: SolProbeDecision) -> float:
    """probe 허용 시 주문 금액을 제한 배율로 축소한다."""
    if not decision.allowed:
        return order_value_quote
    return order_value_quote * decision.position_scale


def is_sol_probe_time_exit_triggered(
    *,
    enabled: bool,
    symbol: str,
    eligible_symbols: tuple[str, ...],
    has_position: bool,
    opened_at: float | None,
    now_ts: float,
    max_hold_minutes: int,
) -> bool:
    """SOL probe 포지션이 최대 보유 시간을 넘겼는지 반환한다."""
    if not enabled or symbol not in eligible_symbols or not has_position:
        return False
    if opened_at is None or max_hold_minutes <= 0:
        return False
    return (now_ts - opened_at) >= max_hold_minutes * 60
