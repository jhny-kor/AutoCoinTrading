"""
수정 요약
- 업비트 주문, 캔들, 잔고, 호가 REST fallback 호출을 공통 모듈에서 관리하도록 분리했다.
- 각 REST 호출에 Upbit 공식 Rate Limit 그룹을 명시해 그룹별 대기만 적용되도록 했다.
"""

from __future__ import annotations

import time
from typing import Any, Tuple

import ccxt

from core.execution.upbit_markets import (
    ensure_upbit_market_cached,
    get_upbit_runtime_cache,
)
from core.execution.upbit_rate_limits import call_upbit_with_retry
from core.market_data.upbit_provider import UpbitMarketDataProvider


def create_market_buy_order_upbit(
    exchange: ccxt.upbit,
    symbol: str,
    cost_to_spend: float,
):
    ensure_upbit_market_cached(exchange, symbol)
    return call_upbit_with_retry(
        exchange,
        exchange.create_market_buy_order,
        symbol,
        cost_to_spend,
        rate_limit_group="order",
        params={"createMarketBuyOrderRequiresPrice": False},
    )


def create_market_sell_order_upbit(
    exchange: ccxt.upbit,
    symbol: str,
    amount: float,
):
    ensure_upbit_market_cached(exchange, symbol)
    return call_upbit_with_retry(
        exchange,
        exchange.create_market_sell_order,
        symbol,
        amount,
        rate_limit_group="order",
    )


def fetch_ohlcv_upbit(
    exchange: ccxt.upbit, symbol: str, timeframe: str = "1m", limit: int = 200
):
    ensure_upbit_market_cached(exchange, symbol)
    return call_upbit_with_retry(
        exchange,
        exchange.fetch_ohlcv,
        symbol,
        rate_limit_group="candle",
        timeframe=timeframe,
        limit=limit,
    )


def fetch_ohlcv_upbit_with_provider(
    exchange: ccxt.upbit,
    *,
    symbol: str,
    timeframe: str,
    limit: int,
    market_data_provider: UpbitMarketDataProvider | None = None,
) -> list[list[float]]:
    if market_data_provider is not None:
        rows = market_data_provider.get_recent_ohlcv(symbol, timeframe, limit)
        if rows:
            return rows
    return fetch_ohlcv_upbit(exchange, symbol, timeframe=timeframe, limit=limit)


def get_spot_balances_upbit(exchange: ccxt.upbit, base: str, quote: str) -> Tuple[float, float]:
    cache = get_upbit_runtime_cache(exchange)
    ttl_sec = float(exchange.options.get("upbit_balance_cache_ttl_sec", 0.0) or 0.0)
    now_ts = time.time()
    cached_balance = cache.get("balance")
    balance = None
    if (
        ttl_sec > 0
        and isinstance(cached_balance, dict)
        and (now_ts - float(cached_balance.get("ts", 0.0))) <= ttl_sec
    ):
        balance = cached_balance.get("payload")
    if balance is None:
        balance = call_upbit_with_retry(
            exchange,
            exchange.fetch_balance,
            rate_limit_group="default",
        )
        cache["balance"] = {"ts": now_ts, "payload": balance}
    base_free = balance.get(base, {}).get("free", 0.0)
    quote_free = balance.get(quote, {}).get("free", 0.0)
    return float(base_free), float(quote_free)


def get_spot_balances_upbit_with_provider(
    exchange: ccxt.upbit,
    *,
    base: str,
    quote: str,
    market_data_provider: UpbitMarketDataProvider | None = None,
) -> Tuple[float, float]:
    if market_data_provider is not None:
        balances = market_data_provider.get_private_balances(base, quote)
        if balances is not None:
            return balances
    return get_spot_balances_upbit(exchange, base, quote)


def enrich_upbit_order_with_private_event(
    raw_order: Any,
    *,
    symbol: str,
    market_data_provider: UpbitMarketDataProvider | None = None,
    max_age_sec: float = 10.0,
) -> Any:
    if market_data_provider is None or not isinstance(raw_order, dict):
        return raw_order
    order_id = str(raw_order.get("id", "") or raw_order.get("orderId", "") or "")
    if not order_id:
        info = raw_order.get("info")
        if isinstance(info, dict):
            order_id = str(info.get("uuid", "") or "")
    if not order_id:
        return raw_order
    event = market_data_provider.find_recent_myorder_event(
        order_id=order_id,
        market=market_data_provider.get_market_code(symbol),
        max_age_sec=max_age_sec,
    )
    if event is None:
        return raw_order
    enriched = dict(raw_order)
    enriched["private_ws_event"] = event
    return enriched


def fetch_best_bid_upbit(exchange: ccxt.upbit, symbol: str) -> float | None:
    ensure_upbit_market_cached(exchange, symbol)
    cache = get_upbit_runtime_cache(exchange).setdefault("orderbook", {})
    ttl_sec = float(exchange.options.get("upbit_orderbook_cache_ttl_sec", 0.0) or 0.0)
    now_ts = time.time()
    cached_orderbook = cache.get(symbol)
    order_book = None
    if (
        ttl_sec > 0
        and isinstance(cached_orderbook, dict)
        and (now_ts - float(cached_orderbook.get("ts", 0.0))) <= ttl_sec
    ):
        order_book = cached_orderbook.get("payload")
    try:
        if order_book is None:
            order_book = call_upbit_with_retry(
                exchange,
                exchange.fetch_order_book,
                symbol,
                rate_limit_group="orderbook",
                limit=1,
            )
            cache[symbol] = {"ts": now_ts, "payload": order_book}
    except Exception:
        return None
    bids = order_book.get("bids") or []
    if not bids:
        return None
    try:
        return float(bids[0][0])
    except (TypeError, ValueError, IndexError):
        return None
