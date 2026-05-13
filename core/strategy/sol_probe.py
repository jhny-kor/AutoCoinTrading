"""
작업 요약
- SOL 제한형 probe 진입/청산 판정과 진입 상태 보정을 공통 helper 로 분리했다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SolProbeDecision:
    """SOL 제한형 probe 진입 허용 여부와 적용 배율을 나타낸다."""

    allowed: bool
    reason: str
    position_scale: float


@dataclass(frozen=True)
class SolProbeEntryState:
    """SOL probe 적용 뒤 봇이 사용할 진입 상태를 나타낸다."""

    decision: SolProbeDecision
    entry_signal: bool
    signal_is_strong: bool
    max_entry_count: int
    low_energy_guard_active: bool
    symbol_regime_blocks_entry: bool


@dataclass(frozen=True)
class SolProbeExitState:
    """SOL probe 적용 뒤 봇이 사용할 청산 기준을 나타낸다."""

    active: bool
    take_profit_pct: float
    stop_loss_pct: float
    effective_take_profit_pct: float
    time_exit_triggered: bool


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


def resolve_sol_probe_entry_state(
    *,
    enabled: bool,
    symbol: str,
    eligible_symbols: tuple[str, ...],
    signal_score: float,
    min_signal_score: float,
    has_position: bool,
    current_entry_count: int,
    position_scale: float,
    entry_signal: bool,
    signal_is_strong: bool,
    max_entry_count: int,
    low_energy_guard_active: bool,
    low_energy_probe_allowed: bool,
    symbol_regime_blocks_entry: bool,
    mean_reversion_lower_near_probe_allowed: bool,
) -> SolProbeEntryState:
    """SOL probe 진입 판정과 그에 따른 공통 상태 보정을 한 번에 처리한다."""
    decision = evaluate_sol_probe_entry(
        enabled=enabled,
        symbol=symbol,
        eligible_symbols=eligible_symbols,
        signal_score=signal_score,
        min_signal_score=min_signal_score,
        has_position=has_position,
        current_entry_count=current_entry_count,
        position_scale=position_scale,
    )
    sol_probe_symbol_enabled = enabled and symbol in eligible_symbols
    probe_allowed = decision.allowed
    resolved_max_entry_count = 1 if sol_probe_symbol_enabled else int(max_entry_count)
    if low_energy_probe_allowed:
        resolved_max_entry_count = max(1, resolved_max_entry_count)
    return SolProbeEntryState(
        decision=decision,
        entry_signal=bool(entry_signal) or probe_allowed,
        signal_is_strong=bool(signal_is_strong) or probe_allowed,
        max_entry_count=resolved_max_entry_count,
        low_energy_guard_active=(
            bool(low_energy_guard_active)
            and not low_energy_probe_allowed
            and not probe_allowed
        ),
        symbol_regime_blocks_entry=(
            bool(symbol_regime_blocks_entry)
            and not low_energy_probe_allowed
            and not mean_reversion_lower_near_probe_allowed
            and not probe_allowed
        ),
    )


def format_sol_probe_entry_log(
    *, symbol: str, signal_score: float, position_scale: float
) -> str:
    """SOL probe 진입 후보 전환 로그 문구를 거래소 봇 간 동일하게 유지한다."""
    return (
        f"[{symbol}] SOL 제한형 probe 후보로 전환합니다. "
        f"signal={signal_score:.1f}, position_scale={position_scale:.2f}x"
    )


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


def resolve_sol_probe_exit_state(
    *,
    enabled: bool,
    symbol: str,
    eligible_symbols: tuple[str, ...],
    has_position: bool,
    opened_at: float | None,
    now_ts: float,
    max_hold_minutes: int,
    base_take_profit_pct: float,
    base_stop_loss_pct: float,
    stop_loss_multiplier: float,
    take_profit_bonus_pct: float,
    fee_round_trip_pct: float,
    sol_probe_take_profit_pct: float,
    sol_probe_stop_loss_pct: float,
) -> SolProbeExitState:
    """SOL probe 대상 여부에 따라 청산 기준과 시간 청산 여부를 공통 계산한다."""
    active = enabled and symbol in eligible_symbols
    take_profit_pct = (
        sol_probe_take_profit_pct if active else base_take_profit_pct
    )
    stop_loss_pct = (
        sol_probe_stop_loss_pct
        if active
        else base_stop_loss_pct * stop_loss_multiplier
    )
    effective_take_profit_pct = max(
        take_profit_pct if active else take_profit_pct + take_profit_bonus_pct,
        fee_round_trip_pct * 1.1,
    )
    return SolProbeExitState(
        active=active,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        effective_take_profit_pct=effective_take_profit_pct,
        time_exit_triggered=is_sol_probe_time_exit_triggered(
            enabled=enabled,
            symbol=symbol,
            eligible_symbols=eligible_symbols,
            has_position=has_position,
            opened_at=opened_at,
            now_ts=now_ts,
            max_hold_minutes=max_hold_minutes,
        ),
    )
