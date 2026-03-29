from __future__ import annotations


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
