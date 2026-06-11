"""
작업 요약
- 알트 봇 루프의 진입/청산 퍼널 실행 단계를 공통 helper 로 분리했다.
- 알트 순익 trailing exit ready reason 을 청산 퍼널에 전달한다.
"""

from __future__ import annotations

from typing import Any

from core.strategy.exit_reasons import resolve_alt_exit_ready_reason


def run_alt_entry_funnel(
    *,
    structured_logger: Any,
    symbol: str,
    entry_steps: list[Any],
    metrics: dict[str, Any],
) -> bool:
    """알트 진입 퍼널을 표준 ready stage/reason 으로 실행한다."""
    ready, _ = structured_logger.run_funnel(
        symbol=symbol,
        side="entry",
        steps=entry_steps,
        metrics=metrics,
        ready_stage="buy_ready",
        ready_reason="entry_conditions_met",
    )
    return bool(ready)


def run_alt_exit_funnel(
    *,
    structured_logger: Any,
    symbol: str,
    exit_steps: list[Any],
    metrics: dict[str, Any],
    stop_loss_triggered: bool,
    profit_protect_triggered: bool,
    break_even_guard_triggered: bool,
    volume_spike_exit_triggered: bool,
    sol_probe_time_exit_triggered: bool,
    alt_profit_trailing_exit_triggered: bool = False,
) -> bool:
    """알트 청산 퍼널을 표준 ready stage와 우선순위 reason 으로 실행한다."""
    ready, _ = structured_logger.run_funnel(
        symbol=symbol,
        side="exit",
        steps=exit_steps,
        metrics=metrics,
        ready_stage="sell_ready",
        ready_reason=resolve_alt_exit_ready_reason(
            stop_loss_triggered=stop_loss_triggered,
            profit_protect_triggered=profit_protect_triggered,
            break_even_guard_triggered=break_even_guard_triggered,
            volume_spike_exit_triggered=volume_spike_exit_triggered,
            sol_probe_time_exit_triggered=sol_probe_time_exit_triggered,
            alt_profit_trailing_exit_triggered=alt_profit_trailing_exit_triggered,
        ),
    )
    return bool(ready)
