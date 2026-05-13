"""
작업 요약
- OKX/업비트 시장가 주문 제출 후 공통으로 필요한 타이밍 기록과 후처리를 어댑터로 분리했다.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from core.execution.okx import place_market_order_okx
from core.execution.upbit import (
    create_market_buy_order_upbit,
    create_market_sell_order_upbit,
    enrich_upbit_order_with_private_event,
    invalidate_upbit_balance_cache,
    invalidate_upbit_orderbook_cache,
)


@dataclass(frozen=True)
class OrderSubmissionResult:
    """주문 제출 결과와 주문 API 응답 시간 정보를 함께 담는다."""

    order: Any
    request_started_at: float
    response_received_at: float


Clock = Callable[[], float]


def submit_okx_market_buy(
    *,
    exchange: Any,
    symbol: str,
    order_value_quote: float,
    clock: Clock = time.time,
    place_order: Callable[..., Any] = place_market_order_okx,
) -> OrderSubmissionResult:
    """OKX 시장가 매수를 quote 금액 기준으로 제출한다."""
    request_started_at = clock()
    order = place_order(
        exchange,
        symbol,
        "buy",
        order_value_quote,
        tgt_ccy="quote_ccy",
    )
    return OrderSubmissionResult(
        order=order,
        request_started_at=request_started_at,
        response_received_at=clock(),
    )


def submit_okx_market_sell(
    *,
    exchange: Any,
    symbol: str,
    amount: float,
    clock: Clock = time.time,
    place_order: Callable[..., Any] = place_market_order_okx,
) -> OrderSubmissionResult:
    """OKX 시장가 매도를 base 수량 기준으로 제출한다."""
    request_started_at = clock()
    order = place_order(
        exchange,
        symbol,
        "sell",
        amount,
        tgt_ccy="base_ccy",
    )
    return OrderSubmissionResult(
        order=order,
        request_started_at=request_started_at,
        response_received_at=clock(),
    )


def submit_upbit_market_buy(
    *,
    exchange: Any,
    symbol: str,
    order_value_quote: float,
    market_data_provider: Any = None,
    clock: Clock = time.time,
    place_order: Callable[..., Any] = create_market_buy_order_upbit,
    enrich_order: Callable[..., Any] = enrich_upbit_order_with_private_event,
    invalidate_balance_cache: Callable[..., Any] = invalidate_upbit_balance_cache,
    invalidate_orderbook_cache: Callable[..., Any] = invalidate_upbit_orderbook_cache,
) -> OrderSubmissionResult:
    """업비트 시장가 매수 후 private 이벤트 보강과 잔고/호가 캐시 무효화를 수행한다."""
    request_started_at = clock()
    order = place_order(exchange, symbol, order_value_quote)
    response_received_at = clock()
    order = enrich_order(
        order,
        symbol=symbol,
        market_data_provider=market_data_provider,
    )
    invalidate_balance_cache(exchange)
    invalidate_orderbook_cache(exchange, symbol)
    return OrderSubmissionResult(
        order=order,
        request_started_at=request_started_at,
        response_received_at=response_received_at,
    )


def submit_upbit_market_sell(
    *,
    exchange: Any,
    symbol: str,
    amount: float,
    market_data_provider: Any = None,
    clock: Clock = time.time,
    place_order: Callable[..., Any] = create_market_sell_order_upbit,
    enrich_order: Callable[..., Any] = enrich_upbit_order_with_private_event,
    invalidate_balance_cache: Callable[..., Any] = invalidate_upbit_balance_cache,
    invalidate_orderbook_cache: Callable[..., Any] = invalidate_upbit_orderbook_cache,
) -> OrderSubmissionResult:
    """업비트 시장가 매도 후 private 이벤트 보강과 잔고/호가 캐시 무효화를 수행한다."""
    request_started_at = clock()
    order = place_order(exchange, symbol, amount)
    response_received_at = clock()
    order = enrich_order(
        order,
        symbol=symbol,
        market_data_provider=market_data_provider,
    )
    invalidate_balance_cache(exchange)
    invalidate_orderbook_cache(exchange, symbol)
    return OrderSubmissionResult(
        order=order,
        request_started_at=request_started_at,
        response_received_at=response_received_at,
    )
