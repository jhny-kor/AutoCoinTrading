"""
수정 요약
- 레짐별 포지션 스케일을 적용하되 최소 0, 최대 1.2 범위로 제한하는 공통 helper 를 추가했다.
- 알트/BTC 신규 진입과 추가매수의 포트폴리오 배분 호출을 공통 래퍼로 분리했다.
- 배분 계산 호출 방식이 봇마다 갈라지지 않도록 정리했다.
"""

from __future__ import annotations


def apply_regime_position_scale(
    *,
    base_position_ratio: float,
    regime_scale: float,
    min_ratio: float = 0.0,
    max_ratio: float = 1.2,
) -> float:
    """기본 포지션 비중에 레짐 스케일을 적용하고 안전 범위로 제한한다."""
    scaled = base_position_ratio * regime_scale
    return max(min_ratio, min(max_ratio, scaled))


def build_alt_allocation(
    *,
    portfolio_allocator,
    exchange,
    symbol: str,
    quote_free: float,
    position_ratio: float,
    buy_split_ratio: float,
    dynamic_bonus_eligible: bool,
):
    requested_order_value = quote_free * position_ratio * buy_split_ratio
    allocation_decision = portfolio_allocator.build_buy_decision(
        exchange=exchange,
        symbol=symbol,
        requested_order_value_quote=requested_order_value,
        dynamic_bonus_eligible=dynamic_bonus_eligible,
    )
    return requested_order_value, allocation_decision


def build_btc_allocations(
    *,
    portfolio_allocator,
    exchange,
    symbol: str,
    quote_free: float,
    risk_per_trade: float,
    position_ratio: float,
    pyramid_position_ratio: float,
    dynamic_bonus_eligible: bool,
):
    requested_order_value = quote_free * risk_per_trade * position_ratio
    requested_add_on_order_value = quote_free * risk_per_trade * pyramid_position_ratio
    allocation_decision = portfolio_allocator.build_buy_decision(
        exchange=exchange,
        symbol=symbol,
        requested_order_value_quote=requested_order_value,
        dynamic_bonus_eligible=dynamic_bonus_eligible,
    )
    add_on_allocation_decision = portfolio_allocator.build_buy_decision(
        exchange=exchange,
        symbol=symbol,
        requested_order_value_quote=requested_add_on_order_value,
        dynamic_bonus_eligible=dynamic_bonus_eligible,
    )
    return requested_order_value, requested_add_on_order_value, allocation_decision, add_on_allocation_decision
