"""
작업 요약
- 업비트 설정 로드, 429 재시도, 주문 버퍼, 잔고/호가 조회, 시장가 주문 유틸을 공통 모듈로 분리했다.
- 알트/BTC 봇이 같은 업비트 실행 경로를 재사용하도록 정리했다.
"""

from __future__ import annotations

import os
import time
from typing import Tuple

import ccxt
from dotenv import load_dotenv


def load_upbit_config() -> dict:
    load_dotenv()

    api_key = os.getenv("UPBIT_API_KEY")
    api_secret = os.getenv("UPBIT_API_SECRET")

    if not api_key or not api_secret:
        raise RuntimeError(
            "UPBIT_API_KEY / UPBIT_API_SECRET 가 .env 에 설정되어 있지 않습니다."
        )

    risk_per_trade = float(os.getenv("UPBIT_TRADE_RISK_PER_TRADE", "0.05"))
    fee_rate_pct = float(os.getenv("UPBIT_FEE_RATE_PCT", "0.05"))
    max_daily_loss_quote = float(os.getenv("UPBIT_MAX_DAILY_LOSS_QUOTE", "5000"))
    request_retry_count = int(os.getenv("UPBIT_REQUEST_RETRY_COUNT", "3"))
    request_retry_delay_sec = float(os.getenv("UPBIT_REQUEST_RETRY_DELAY_SEC", "1.2"))
    krw_order_buffer_pct = float(os.getenv("UPBIT_KRW_ORDER_BUFFER_PCT", "0.002"))
    krw_order_buffer_krw = float(os.getenv("UPBIT_KRW_ORDER_BUFFER_KRW", "1000"))

    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "risk_per_trade": risk_per_trade,
        "fee_rate_pct": fee_rate_pct,
        "max_daily_loss_quote": max_daily_loss_quote,
        "request_retry_count": request_retry_count,
        "request_retry_delay_sec": request_retry_delay_sec,
        "krw_order_buffer_pct": krw_order_buffer_pct,
        "krw_order_buffer_krw": krw_order_buffer_krw,
    }


def create_upbit_client(config: dict) -> ccxt.upbit:
    return ccxt.upbit(
        {
            "apiKey": config["api_key"],
            "secret": config["api_secret"],
            "enableRateLimit": True,
            "options": {
                "adjustForTimeDifference": True,
            },
        }
    )


def is_upbit_rate_limit_error(exc: Exception) -> bool:
    lowered = str(exc).lower()
    return isinstance(exc, ccxt.RateLimitExceeded) or "too_many_requests" in lowered or "429" in lowered


def call_upbit_with_retry(exchange: ccxt.upbit, func, *args, **kwargs):
    retry_count = int(exchange.options.get("upbit_request_retry_count", 3) or 3)
    retry_delay_sec = float(exchange.options.get("upbit_request_retry_delay_sec", 1.2) or 1.2)
    last_error: Exception | None = None
    for attempt in range(retry_count + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_error = exc
            if not is_upbit_rate_limit_error(exc) or attempt >= retry_count:
                raise
            time.sleep(retry_delay_sec * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise RuntimeError("업비트 재시도 호출이 비정상 종료되었습니다.")


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


def create_market_buy_order_upbit(
    exchange: ccxt.upbit,
    symbol: str,
    cost_to_spend: float,
):
    return call_upbit_with_retry(
        exchange,
        exchange.create_market_buy_order,
        symbol,
        cost_to_spend,
        params={"createMarketBuyOrderRequiresPrice": False},
    )


def fetch_ohlcv_upbit(
    exchange: ccxt.upbit, symbol: str, timeframe: str = "1m", limit: int = 200
):
    return call_upbit_with_retry(
        exchange,
        exchange.fetch_ohlcv,
        symbol,
        timeframe=timeframe,
        limit=limit,
    )


def get_spot_balances_upbit(exchange: ccxt.upbit, base: str, quote: str) -> Tuple[float, float]:
    balance = call_upbit_with_retry(exchange, exchange.fetch_balance)
    base_free = balance.get(base, {}).get("free", 0.0)
    quote_free = balance.get(quote, {}).get("free", 0.0)
    return float(base_free), float(quote_free)


def safe_amount_to_precision_upbit(exchange: ccxt.upbit, symbol: str, amount: float) -> float:
    try:
        return float(exchange.amount_to_precision(symbol, amount))
    except Exception:
        return float(f"{amount:.8f}")


def fetch_best_bid_upbit(exchange: ccxt.upbit, symbol: str) -> float | None:
    try:
        order_book = call_upbit_with_retry(exchange, exchange.fetch_order_book, symbol, limit=1)
    except Exception:
        return None
    bids = order_book.get("bids") or []
    if not bids:
        return None
    try:
        return float(bids[0][0])
    except (TypeError, ValueError, IndexError):
        return None
