"""
수정 요약
- 업비트 myAsset latest 를 잔고 조회 우선 경로로 읽고 myOrder 최근 이벤트를 주문 응답 보강에 쓸 helper 를 추가했다.
- 업비트 5분/15분 OHLCV 도 웹소켓 1분 캔들 리샘플 우선, stale 시 REST fallback 으로 읽게 확장했다.
- 업비트 1분봉 OHLCV 를 웹소켓 1분 캔들 우선, stale 시 REST fallback 으로 읽는 helper 를 추가해 phase 3 전환을 시작했다.
- 업비트 웹소켓 latest 스냅샷을 읽는 market data provider 설정과 생성 helper 를 추가해 best bid 를 웹소켓 우선으로 읽을 준비를 맞췄다.
- 업비트 잔고/호가 조회를 짧은 TTL 캐시로 재사용하고 최소 주문 경계 근처에서만 호가를 재조회하도록 지연 완화 경로를 추가했다.
- 업비트 시장가 매도도 공통 재시도 경로와 캐시 무효화 helper 를 쓰도록 확장했다.
- 업비트 설정 로드, 429 재시도, 주문 버퍼, 잔고/호가 조회, 시장가 주문 유틸을 공통 모듈로 분리했다.
- 알트/BTC 봇이 같은 업비트 실행 경로를 재사용하도록 정리했다.
"""

from __future__ import annotations

import os
import time
from typing import Tuple

import ccxt
from dotenv import load_dotenv

from core.market_data.upbit_provider import UpbitMarketDataProvider


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
    request_timeout_ms = int(os.getenv("UPBIT_REQUEST_TIMEOUT_MS", "10000"))
    balance_cache_ttl_sec = float(os.getenv("UPBIT_BALANCE_CACHE_TTL_SEC", "1.0"))
    orderbook_cache_ttl_sec = float(os.getenv("UPBIT_ORDERBOOK_CACHE_TTL_SEC", "0.8"))
    best_bid_refresh_buffer_pct = float(
        os.getenv("UPBIT_BEST_BID_REFRESH_BUFFER_PCT", "0.30")
    )
    ws_provider_enabled = parse_bool(os.getenv("UPBIT_WS_PROVIDER_ENABLED", "true"))
    ws_provider_root_dir = os.getenv("UPBIT_WS_PROVIDER_ROOT_DIR", "logs/runtime/upbit_ws").strip()
    ws_provider_cache_ttl_sec = float(os.getenv("UPBIT_WS_PROVIDER_CACHE_TTL_SEC", "0.25"))
    ws_provider_stale_sec = float(os.getenv("UPBIT_WS_PROVIDER_STALE_SEC", "5.0"))

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
        "request_timeout_ms": request_timeout_ms,
        "balance_cache_ttl_sec": balance_cache_ttl_sec,
        "orderbook_cache_ttl_sec": orderbook_cache_ttl_sec,
        "best_bid_refresh_buffer_pct": best_bid_refresh_buffer_pct,
        "ws_provider_enabled": ws_provider_enabled,
        "ws_provider_root_dir": ws_provider_root_dir,
        "ws_provider_cache_ttl_sec": ws_provider_cache_ttl_sec,
        "ws_provider_stale_sec": ws_provider_stale_sec,
    }


def create_upbit_client(config: dict) -> ccxt.upbit:
    return ccxt.upbit(
        {
            "apiKey": config["api_key"],
            "secret": config["api_secret"],
            "enableRateLimit": True,
            "timeout": config["request_timeout_ms"],
            "options": {
                "adjustForTimeDifference": True,
                "upbit_request_retry_count": config["request_retry_count"],
                "upbit_request_retry_delay_sec": config["request_retry_delay_sec"],
                "upbit_balance_cache_ttl_sec": config["balance_cache_ttl_sec"],
                "upbit_orderbook_cache_ttl_sec": config["orderbook_cache_ttl_sec"],
                "upbit_best_bid_refresh_buffer_pct": config["best_bid_refresh_buffer_pct"],
            },
        }
    )


def parse_bool(raw: str | None, default: bool = False) -> bool:
    """문자열 불리언 값을 파싱한다."""
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def create_upbit_market_data_provider(config: dict) -> UpbitMarketDataProvider | None:
    """업비트 웹소켓 latest 스냅샷 provider 를 생성한다."""
    if not config.get("ws_provider_enabled", True):
        return None
    return UpbitMarketDataProvider(
        root_dir=str(config.get("ws_provider_root_dir", "logs/runtime/upbit_ws")),
        cache_ttl_sec=float(config.get("ws_provider_cache_ttl_sec", 0.25) or 0.25),
        stale_sec=float(config.get("ws_provider_stale_sec", 5.0) or 5.0),
    )


def _get_runtime_cache(exchange: ccxt.upbit) -> dict:
    """클라이언트별 업비트 런타임 캐시 저장소를 반환한다."""
    return exchange.options.setdefault("upbit_runtime_cache", {})


def invalidate_upbit_balance_cache(exchange: ccxt.upbit) -> None:
    """업비트 잔고 캐시를 비운다."""
    _get_runtime_cache(exchange).pop("balance", None)


def invalidate_upbit_orderbook_cache(
    exchange: ccxt.upbit,
    symbol: str | None = None,
) -> None:
    """업비트 호가 캐시를 비운다."""
    cache = _get_runtime_cache(exchange).get("orderbook", {})
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
    """최소 주문 금액 경계 근처일 때만 최신 호가를 다시 조회할지 판단한다."""
    if base_free <= 0 or last_close <= 0 or min_order_value <= 0:
        return False
    approx_position_value = base_free * last_close
    refresh_threshold = min_order_value * (1 + max(refresh_buffer_pct, 0.0))
    return approx_position_value <= refresh_threshold


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


def create_market_sell_order_upbit(
    exchange: ccxt.upbit,
    symbol: str,
    amount: float,
):
    """업비트 시장가 매도를 공통 재시도 경로로 감싼다."""
    return call_upbit_with_retry(
        exchange,
        exchange.create_market_sell_order,
        symbol,
        amount,
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


def fetch_ohlcv_upbit_with_provider(
    exchange: ccxt.upbit,
    *,
    symbol: str,
    timeframe: str,
    limit: int,
    market_data_provider: UpbitMarketDataProvider | None = None,
) -> list[list[float]]:
    """업비트 OHLCV 를 provider 우선으로 읽고 필요 시 REST fallback 한다."""
    if market_data_provider is not None:
        rows = market_data_provider.get_recent_ohlcv(symbol, timeframe, limit)
        if rows:
            return rows
    return fetch_ohlcv_upbit(exchange, symbol, timeframe=timeframe, limit=limit)


def get_spot_balances_upbit(exchange: ccxt.upbit, base: str, quote: str) -> Tuple[float, float]:
    cache = _get_runtime_cache(exchange)
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
        balance = call_upbit_with_retry(exchange, exchange.fetch_balance)
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
    """업비트 잔고를 provider 우선으로 읽고 필요 시 REST fallback 한다."""
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
    """주문 응답에 최근 myOrder private 이벤트를 보강해 반환한다."""
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


def safe_amount_to_precision_upbit(exchange: ccxt.upbit, symbol: str, amount: float) -> float:
    try:
        return float(exchange.amount_to_precision(symbol, amount))
    except Exception:
        return float(f"{amount:.8f}")


def fetch_best_bid_upbit(exchange: ccxt.upbit, symbol: str) -> float | None:
    cache = _get_runtime_cache(exchange).setdefault("orderbook", {})
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
