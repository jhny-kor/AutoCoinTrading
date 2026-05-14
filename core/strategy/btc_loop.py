"""
작업 요약
- BTC 봇 루프의 진입/추가매수/청산 퍼널 실행 단계를 공통 helper 로 분리했다.
"""

from __future__ import annotations

from typing import Any

from core.strategy.exit_reasons import resolve_btc_exit_ready_reason


def run_btc_entry_funnel(
    *,
    structured_logger: Any,
    symbol: str,
    entry_steps: list[Any],
    metrics: dict[str, Any],
) -> bool:
    """BTC 신규 진입 퍼널을 표준 ready stage/reason 으로 실행한다."""
    ready, _ = structured_logger.run_funnel(
        symbol=symbol,
        side="entry",
        steps=entry_steps,
        metrics=metrics,
        ready_stage="buy_ready",
        ready_reason="entry_conditions_met",
    )
    return bool(ready)


def run_btc_add_on_funnel(
    *,
    structured_logger: Any,
    symbol: str,
    add_on_steps: list[Any],
    metrics: dict[str, Any],
) -> bool:
    """BTC 추가매수 퍼널을 표준 add-on ready stage/reason 으로 실행한다."""
    ready, _ = structured_logger.run_funnel(
        symbol=symbol,
        side="entry",
        steps=add_on_steps,
        metrics=metrics,
        ready_stage="add_on_ready",
        ready_reason="add_on_conditions_met",
        ready_extra={"entry_type": "add_on_winner"},
    )
    return bool(ready)


def run_btc_exit_funnel(
    *,
    structured_logger: Any,
    symbol: str,
    exit_steps: list[Any],
    metrics: dict[str, Any],
    stop_loss_triggered: bool,
    partial_take_profit_triggered: bool,
    profit_protect_triggered: bool,
    trailing_stop_triggered: bool,
    donchian_failure_triggered: bool,
    trend_exit_triggered: bool,
) -> bool:
    """BTC 청산 퍼널을 표준 ready stage와 우선순위 reason 으로 실행한다."""
    ready, _ = structured_logger.run_funnel(
        symbol=symbol,
        side="exit",
        steps=exit_steps,
        metrics=metrics,
        ready_stage="sell_ready",
        ready_reason=resolve_btc_exit_ready_reason(
            stop_loss_triggered=stop_loss_triggered,
            partial_take_profit_triggered=partial_take_profit_triggered,
            profit_protect_triggered=profit_protect_triggered,
            trailing_stop_triggered=trailing_stop_triggered,
            donchian_failure_triggered=donchian_failure_triggered,
            trend_exit_triggered=trend_exit_triggered,
        ),
    )
    return bool(ready)
