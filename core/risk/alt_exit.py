"""
작업 요약
- 알트 매도 사유별 청산 비율과 reason key 결정을 공통화했다.
- 무포지션 기본 지표와 부분익절/부분손절 pending 정책 계산을 공통화했다.
- 익절 구간에서 거래량 급감 시 조기 청산하는 Volume Spike Exit 트리거를 추가
- 알트 포지션의 수익률/순익률/MFE/MAE 계산과 청산 보호 판단을 공통화했다.
- 브레이크이븐 가드와 순익 보호 익절 계산을 한 곳으로 모았다.
- MFE 대비 되돌림 폭 기준을 추가해 수익 구간에서 급한 반납을 더 빠르게 정리할 수 있게 보강했다.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from trade_history_logger import estimate_round_trip_net_pnl


@dataclass(frozen=True)
class AltPartialExitPolicy:
    """알트 부분익절/부분손절 적용 상태를 나타낸다."""

    partial_take_profit_pending: bool
    partial_stop_loss_pending: bool
    effective_partial_take_profit_ratio: float


@dataclass(frozen=True)
class AltSellIntent:
    """알트 매도 주문 직전 사용할 청산 의도를 나타낸다."""

    sell_ratio: float
    exit_reason_key: str
    sell_reason: str


def build_empty_position_runtime_metrics() -> dict[str, float | None]:
    """무포지션 경로에서 참조할 기본 포지션 지표를 반환한다."""
    return {
        "pnl_pct": None,
        "mfe_pct": None,
        "mae_pct": None,
        "current_net_realized_pnl_quote": None,
        "current_net_realized_pnl_pct": None,
    }


def compute_alt_position_metrics(
    *,
    has_position: bool,
    average_entry_price: float | None,
    last_close: float,
    base_free: float,
    fee_rate_pct: float,
    highest_price_since_entry: float | None,
    lowest_price_since_entry: float | None,
) -> dict[str, float | None]:
    if not has_position or average_entry_price is None:
        return {
            "highest_price_since_entry": None,
            "lowest_price_since_entry": None,
            "pnl_pct": None,
            "mfe_pct": None,
            "mae_pct": None,
            "net_pnl_quote": None,
            "net_pnl_pct": None,
        }

    updated_high = max(highest_price_since_entry or last_close, last_close)
    updated_low = min(lowest_price_since_entry or last_close, last_close)
    pnl_pct = (last_close - average_entry_price) / average_entry_price * 100
    mfe_pct = ((updated_high - average_entry_price) / average_entry_price) * 100
    mae_pct = ((updated_low - average_entry_price) / average_entry_price) * 100
    (
        _current_fee_quote_estimate,
        current_net_realized_pnl_quote,
        current_net_realized_pnl_pct,
    ) = estimate_round_trip_net_pnl(
        entry_price=average_entry_price,
        exit_price=last_close,
        amount=base_free,
        fee_rate_pct=fee_rate_pct,
    )
    return {
        "highest_price_since_entry": updated_high,
        "lowest_price_since_entry": updated_low,
        "pnl_pct": pnl_pct,
        "mfe_pct": mfe_pct,
        "mae_pct": mae_pct,
        "net_pnl_quote": current_net_realized_pnl_quote,
        "net_pnl_pct": current_net_realized_pnl_pct,
    }


def resolve_alt_partial_exit_policy(
    *,
    symbol: str,
    partial_take_profit_enabled: bool,
    partial_stop_loss_enabled: bool,
    partial_take_profit_done: Mapping[str, bool],
    partial_stop_loss_done: Mapping[str, bool],
    partial_take_profit_ratio: float,
    partial_take_profit_ratio_multiplier: float,
) -> AltPartialExitPolicy:
    """부분익절/부분손절 pending 상태와 적용 비율을 공통 계산한다."""
    return AltPartialExitPolicy(
        partial_take_profit_pending=(
            partial_take_profit_enabled
            and not partial_take_profit_done.get(symbol, False)
        ),
        partial_stop_loss_pending=(
            partial_stop_loss_enabled
            and not partial_stop_loss_done.get(symbol, False)
        ),
        effective_partial_take_profit_ratio=min(
            1.0,
            partial_take_profit_ratio * partial_take_profit_ratio_multiplier,
        ),
    )


def resolve_alt_sell_intent(
    *,
    sell_split_ratio: float,
    stop_loss_triggered: bool,
    partial_stop_loss_pending: bool,
    partial_stop_loss_ratio: float,
    profit_protect_triggered: bool,
    break_even_guard_triggered: bool,
    volume_spike_exit_triggered: bool,
    sol_probe_time_exit_triggered: bool,
    partial_take_profit_pending: bool,
    effective_partial_take_profit_ratio: float,
) -> AltSellIntent:
    """청산 트리거 우선순위에 따라 매도 비율과 reason 코드를 결정한다."""
    if stop_loss_triggered:
        if partial_stop_loss_pending:
            return AltSellIntent(
                sell_ratio=partial_stop_loss_ratio,
                exit_reason_key="partial_stop_loss",
                sell_reason="부분손절",
            )
        return AltSellIntent(
            sell_ratio=1.0,
            exit_reason_key="stop_loss",
            sell_reason="손절",
        )
    if profit_protect_triggered:
        return AltSellIntent(
            sell_ratio=1.0,
            exit_reason_key="profit_protect_take_profit",
            sell_reason="순익보호익절",
        )
    if break_even_guard_triggered:
        return AltSellIntent(
            sell_ratio=1.0,
            exit_reason_key="break_even_guard_take_profit",
            sell_reason="브레이크이븐보호익절",
        )
    if volume_spike_exit_triggered:
        return AltSellIntent(
            sell_ratio=1.0,
            exit_reason_key="volume_spike_take_profit",
            sell_reason="거래량급감익절",
        )
    if sol_probe_time_exit_triggered:
        return AltSellIntent(
            sell_ratio=1.0,
            exit_reason_key="sol_probe_time_exit",
            sell_reason="SOL Probe 시간청산",
        )
    if partial_take_profit_pending:
        return AltSellIntent(
            sell_ratio=effective_partial_take_profit_ratio,
            exit_reason_key="partial_take_profit",
            sell_reason="부분익절",
        )
    return AltSellIntent(
        sell_ratio=sell_split_ratio,
        exit_reason_key="take_profit",
        sell_reason="익절",
    )


def compute_alt_exit_decisions(
    *,
    has_position: bool,
    pnl_pct: float | None,
    mfe_pct: float | None,
    current_net_realized_pnl_pct: float | None,
    take_profit_pct: float,
    stop_loss_pct: float,
    fee_rate_pct: float,
    enable_fee_protect_exit: bool,
    fee_protect_min_net_pnl_pct: float,
    enable_break_even_guard: bool,
    break_even_guard_min_mfe_pct: float,
    break_even_guard_floor_net_pnl_pct: float,
    break_even_guard_max_profit_retrace_pct: float,
    enable_volume_spike_exit: bool,
    volume_spike_exit_min_profit_pct: float,
    volume_spike_exit_max_volume_ratio: float,
    volume_ratio: float | None,
    bearish: bool,
    sell_split_ratio: float,
) -> dict[str, float | bool]:
    fee_round_trip_pct = fee_rate_pct * 2
    effective_min_take_profit_pct = max(
        take_profit_pct,
        fee_round_trip_pct * 1.1,
    )
    take_profit_ready = (
        pnl_pct is not None
        and pnl_pct >= effective_min_take_profit_pct
    )
    stop_loss_triggered = (
        pnl_pct is not None
        and pnl_pct <= -stop_loss_pct
    )
    profit_protect_triggered = (
        has_position
        and enable_fee_protect_exit
        and current_net_realized_pnl_pct is not None
        and current_net_realized_pnl_pct >= fee_protect_min_net_pnl_pct
        and bearish
        and not stop_loss_triggered
    )
    break_even_guard_triggered = (
        has_position
        and enable_break_even_guard
        and break_even_guard_min_mfe_pct > 0
        and mfe_pct is not None
        and mfe_pct >= break_even_guard_min_mfe_pct
        and current_net_realized_pnl_pct is not None
        and current_net_realized_pnl_pct <= break_even_guard_floor_net_pnl_pct
        and (
            break_even_guard_max_profit_retrace_pct <= 0
            or (
                pnl_pct is not None
                and (mfe_pct - pnl_pct) >= break_even_guard_max_profit_retrace_pct
            )
        )
        and bearish
        and not stop_loss_triggered
        and not profit_protect_triggered
    )
    volume_spike_exit_triggered = (
        has_position
        and enable_volume_spike_exit
        and current_net_realized_pnl_pct is not None
        and current_net_realized_pnl_pct >= volume_spike_exit_min_profit_pct
        and volume_ratio is not None
        and volume_ratio <= volume_spike_exit_max_volume_ratio
        and bearish
        and not stop_loss_triggered
        and not profit_protect_triggered
        and not break_even_guard_triggered
    )
    estimated_sell_ratio = (
        1.0
        if (
            stop_loss_triggered
            or profit_protect_triggered
            or break_even_guard_triggered
            or volume_spike_exit_triggered
        )
        else sell_split_ratio
    )
    return {
        "fee_round_trip_pct": fee_round_trip_pct,
        "effective_min_take_profit_pct": effective_min_take_profit_pct,
        "take_profit_ready": take_profit_ready,
        "stop_loss_triggered": stop_loss_triggered,
        "profit_protect_triggered": profit_protect_triggered,
        "break_even_guard_triggered": break_even_guard_triggered,
        "volume_spike_exit_triggered": volume_spike_exit_triggered,
        "profit_retrace_from_mfe_pct": (
            None if (mfe_pct is None or pnl_pct is None) else max(0.0, mfe_pct - pnl_pct)
        ),
        "estimated_sell_ratio": estimated_sell_ratio,
    }
