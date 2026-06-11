"""
작업 요약
- 알트 순익 trailing exit 의 arm/청산 판단을 라이브 봇과 백테스트가 공유하도록 분리했다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AltProfitTrailingDecision:
    trailing_armed: bool
    trailing_armed_just_now: bool
    trailing_exit_triggered: bool
    profit_retrace_from_mfe_pct: float | None
    trigger_reason: str | None


def resolve_alt_profit_trailing_exit(
    *,
    has_position: bool,
    enabled: bool,
    trailing_armed: bool,
    pnl_pct: float | None,
    mfe_pct: float | None,
    current_net_realized_pnl_pct: float | None,
    arm_net_pnl_pct: float,
    drawdown_pct: float,
    floor_net_pnl_pct: float,
    bearish: bool,
    stop_loss_triggered: bool,
) -> AltProfitTrailingDecision:
    profit_retrace_from_mfe_pct = (
        None if (mfe_pct is None or pnl_pct is None) else max(0.0, mfe_pct - pnl_pct)
    )
    if (
        not has_position
        or not enabled
        or stop_loss_triggered
        or current_net_realized_pnl_pct is None
    ):
        return AltProfitTrailingDecision(
            trailing_armed=False,
            trailing_armed_just_now=False,
            trailing_exit_triggered=False,
            profit_retrace_from_mfe_pct=profit_retrace_from_mfe_pct,
            trigger_reason=None,
        )

    trailing_armed_just_now = (
        not trailing_armed
        and bearish
        and current_net_realized_pnl_pct >= arm_net_pnl_pct
    )
    next_trailing_armed = trailing_armed or trailing_armed_just_now
    drawdown_exit = (
        next_trailing_armed
        and drawdown_pct > 0
        and profit_retrace_from_mfe_pct is not None
        and profit_retrace_from_mfe_pct >= drawdown_pct
    )
    floor_exit = next_trailing_armed and current_net_realized_pnl_pct < floor_net_pnl_pct
    trigger_reason = None
    if drawdown_exit:
        trigger_reason = "drawdown"
    elif floor_exit:
        trigger_reason = "net_floor"
    return AltProfitTrailingDecision(
        trailing_armed=next_trailing_armed,
        trailing_armed_just_now=trailing_armed_just_now,
        trailing_exit_triggered=drawdown_exit or floor_exit,
        profit_retrace_from_mfe_pct=profit_retrace_from_mfe_pct,
        trigger_reason=trigger_reason,
    )
