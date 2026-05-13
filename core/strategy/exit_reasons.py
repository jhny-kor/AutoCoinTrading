"""
작업 요약
- 알트/BTC 청산 퍼널 ready reason 우선순위 결정을 공통 helper 로 분리했다.
"""

from __future__ import annotations


def resolve_alt_exit_ready_reason(
    *,
    stop_loss_triggered: bool,
    profit_protect_triggered: bool,
    break_even_guard_triggered: bool,
    volume_spike_exit_triggered: bool,
    sol_probe_time_exit_triggered: bool,
) -> str:
    """알트 청산 퍼널 통과 시 대표 reason 코드를 우선순위대로 반환한다."""
    if stop_loss_triggered:
        return "stop_loss_triggered"
    if profit_protect_triggered:
        return "profit_protect_triggered"
    if break_even_guard_triggered:
        return "break_even_guard_triggered"
    if volume_spike_exit_triggered:
        return "volume_spike_exit_triggered"
    if sol_probe_time_exit_triggered:
        return "sol_probe_time_exit_triggered"
    return "take_profit_conditions_met"


def resolve_btc_exit_ready_reason(
    *,
    stop_loss_triggered: bool,
    partial_take_profit_triggered: bool,
    profit_protect_triggered: bool,
    trailing_stop_triggered: bool,
    donchian_failure_triggered: bool,
    trend_exit_triggered: bool,
) -> str:
    """BTC 청산 퍼널 통과 시 대표 reason 코드를 우선순위대로 반환한다."""
    if stop_loss_triggered:
        return "stop_loss_triggered"
    if partial_take_profit_triggered:
        return "partial_take_profit_triggered"
    if profit_protect_triggered:
        return "profit_protect_triggered"
    if trailing_stop_triggered:
        return "trailing_stop_triggered"
    if donchian_failure_triggered:
        return "donchian_failure_triggered"
    if trend_exit_triggered:
        return "trend_exit_triggered"
    return "trend_exit_triggered"
