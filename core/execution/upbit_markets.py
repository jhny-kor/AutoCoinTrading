"""
수정 요약
- 업비트 심볼 metadata, 런타임 캐시, 주문 버퍼, 수량 정밀도 helper 를 실행 공통층에서 분리했다.
"""

from __future__ import annotations

import ccxt


def ensure_upbit_market_cached(exchange: ccxt.upbit, symbol: str) -> None:
    if not symbol or "/" not in symbol:
        return

    markets = exchange.markets if isinstance(exchange.markets, dict) else {}
    if symbol in markets:
        return

    base, quote = symbol.split("/", 1)
    market_id = f"{quote}-{base}"
    market = {
        "id": market_id,
        "symbol": symbol,
        "base": base,
        "quote": quote,
        "baseId": base,
        "quoteId": quote,
        "active": True,
        "type": "spot",
        "spot": True,
        "margin": False,
        "swap": False,
        "future": False,
        "option": False,
        "precision": {
            "amount": 0.00000001,
            "price": 0.00000001,
        },
        "limits": {
            "amount": {"min": 0.00000001, "max": None},
            "price": {"min": None, "max": None},
            "cost": {"min": None, "max": None},
        },
        "info": {"market": market_id},
    }

    markets[symbol] = market
    exchange.markets = markets

    markets_by_id = exchange.markets_by_id if isinstance(exchange.markets_by_id, dict) else {}
    markets_by_id.setdefault(market_id, []).append(market)
    exchange.markets_by_id = markets_by_id

    symbols = list(exchange.symbols) if isinstance(exchange.symbols, list) else []
    if symbol not in symbols:
        symbols.append(symbol)
        symbols.sort()
    exchange.symbols = symbols


def get_upbit_runtime_cache(exchange: ccxt.upbit) -> dict:
    return exchange.options.setdefault("upbit_runtime_cache", {})


def invalidate_upbit_balance_cache(exchange: ccxt.upbit) -> None:
    get_upbit_runtime_cache(exchange).pop("balance", None)


def invalidate_upbit_orderbook_cache(
    exchange: ccxt.upbit,
    symbol: str | None = None,
) -> None:
    cache = get_upbit_runtime_cache(exchange).get("orderbook", {})
    if symbol is None:
        cache.clear()
        return
    cache.pop(symbol, None)


def should_refresh_best_bid_upbit(
    *,
    base_free: float,
    last_close: float,
    min_order_value: float,
    refresh_buffer_pct: float,
) -> bool:
    if base_free <= 0 or last_close <= 0 or min_order_value <= 0:
        return False
    approx_position_value = base_free * last_close
    refresh_threshold = min_order_value * (1 + max(refresh_buffer_pct, 0.0))
    return approx_position_value <= refresh_threshold


def apply_upbit_buy_order_buffer(
    *,
    requested_order_value_quote: float,
    quote_free: float,
    fee_rate_pct: float,
    buffer_pct: float,
    buffer_krw: float,
) -> float:
    if requested_order_value_quote <= 0 or quote_free <= 0:
        return 0.0
    fee_multiplier = 1 + max(fee_rate_pct, 0.0) / 100.0
    max_order_value_by_balance = quote_free / fee_multiplier
    buffer_value = max(buffer_krw, quote_free * max(buffer_pct, 0.0))
    safe_order_value = min(requested_order_value_quote, max_order_value_by_balance - buffer_value)
    return max(0.0, float(f"{safe_order_value:.8f}"))


def safe_amount_to_precision_upbit(exchange: ccxt.upbit, symbol: str, amount: float) -> float:
    try:
        ensure_upbit_market_cached(exchange, symbol)
        return float(exchange.amount_to_precision(symbol, amount))
    except Exception:
        return float(f"{amount:.8f}")
