"""
작업 요약
- OKX 현물 심볼을 대응 SWAP funding rate 로 조회하고, 짧은 TTL 캐시로 재사용하는 helper 를 추가
- `config/runtime.toml` + env override 레이어를 중앙 환경 로더로 읽도록 정리
- typed config access helper 를 사용해 OKX 설정 로딩의 문자열 파싱을 일관되게 정리
- OKX 설정 로드, 조회 재시도, 잔고 조회, 시장가 주문 유틸을 공통 모듈로 분리했다.
- 알트/BTC 봇이 같은 OKX 실행 경로를 재사용하도록 정리했다.
"""

from __future__ import annotations

import os
import time
from typing import Tuple

import ccxt
from settings.config_access import env_bool, env_float, env_int, env_str
from settings.env import load_project_env


def _get_runtime_cache(exchange: ccxt.okx) -> dict:
    """클라이언트별 OKX 런타임 캐시 저장소를 반환한다."""
    return exchange.options.setdefault("okx_runtime_cache", {})


def load_okx_config() -> dict:
    load_project_env()

    api_key = env_str("OKX_API_KEY", required=True)
    api_secret = env_str("OKX_API_SECRET", required=True)
    api_passphrase = env_str("OKX_API_PASSPHRASE", required=True)

    if not api_key or not api_secret or not api_passphrase:
        raise RuntimeError(
            "OKX_API_KEY / OKX_API_SECRET / OKX_API_PASSPHRASE 가 secrets 레이어에 설정되어 있지 않습니다."
        )

    sandbox = env_bool("OKX_SANDBOX", True)
    risk_per_trade = env_float("OKX_TRADE_RISK_PER_TRADE", 0.05)
    fee_rate_pct = env_float("OKX_FEE_RATE_PCT", 1.0)
    max_daily_loss_quote = env_float("OKX_MAX_DAILY_LOSS_QUOTE", 5.0)
    request_retry_count = env_int("OKX_REQUEST_RETRY_COUNT", 2)
    request_retry_delay_sec = env_float("OKX_REQUEST_RETRY_DELAY_SEC", 1.0)
    timeout_ms = env_int("OKX_REQUEST_TIMEOUT_MS", 15000)

    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "api_passphrase": api_passphrase,
        "sandbox": sandbox,
        "risk_per_trade": risk_per_trade,
        "fee_rate_pct": fee_rate_pct,
        "max_daily_loss_quote": max_daily_loss_quote,
        "request_retry_count": request_retry_count,
        "request_retry_delay_sec": request_retry_delay_sec,
        "timeout_ms": timeout_ms,
    }


def create_okx_client(config: dict) -> ccxt.okx:
    exchange = ccxt.okx(
        {
            "apiKey": config["api_key"],
            "secret": config["api_secret"],
            "password": config["api_passphrase"],
            "enableRateLimit": True,
            "timeout": config["timeout_ms"],
            "options": {
                "defaultType": "spot",
                "fetchMarkets": ["spot"],
                "okx_request_retry_count": config["request_retry_count"],
                "okx_request_retry_delay_sec": config["request_retry_delay_sec"],
            },
        }
    )
    if config["sandbox"]:
        exchange.set_sandbox_mode(True)
    return exchange


def is_okx_retryable_error(exc: Exception) -> bool:
    lowered = str(exc).lower()
    return (
        isinstance(exc, ccxt.RequestTimeout)
        or isinstance(exc, ccxt.NetworkError)
        or "timeout" in lowered
        or "networkerror" in lowered
        or "connection reset" in lowered
    )


def call_okx_with_retry(exchange: ccxt.okx, func, *args, **kwargs):
    retry_count = int(exchange.options.get("okx_request_retry_count", 2) or 2)
    retry_delay_sec = float(exchange.options.get("okx_request_retry_delay_sec", 1.0) or 1.0)
    last_error: Exception | None = None
    for attempt in range(retry_count + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_error = exc
            if not is_okx_retryable_error(exc) or attempt >= retry_count:
                raise
            time.sleep(retry_delay_sec * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise RuntimeError("OKX 재시도 호출이 비정상 종료되었습니다.")


def fetch_ohlcv_okx(
    exchange: ccxt.okx, symbol: str, timeframe: str = "1m", limit: int = 200
):
    inst_id = symbol.replace("/", "-")
    timeframe_map = {
        "1m": "1m",
        "3m": "3m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1H",
        "4h": "4H",
        "1d": "1D",
    }
    bar = timeframe_map.get(timeframe, "1m")
    res = call_okx_with_retry(
        exchange,
        exchange.publicGetMarketCandles,
        {
            "instId": inst_id,
            "bar": bar,
            "limit": limit,
        },
    )
    data = res.get("data", []) if isinstance(res, dict) else res
    ohlcv = []
    for item in data:
        ohlcv.append(
            [int(item[0]), float(item[1]), float(item[2]), float(item[3]), float(item[4]), float(item[5])]
        )
    ohlcv.sort(key=lambda x: x[0])
    return ohlcv


def spot_symbol_to_okx_swap_inst_id(symbol: str) -> str | None:
    """OKX 현물 심볼을 대응 perpetual swap instId 로 변환한다."""
    if "/" not in symbol:
        return None
    base, quote = symbol.split("/", 1)
    base = base.strip().upper()
    quote = quote.strip().upper()
    if not base or not quote:
        return None
    return f"{base}-{quote}-SWAP"


def fetch_funding_rate_okx(
    exchange: ccxt.okx,
    symbol: str,
    *,
    cache_ttl_sec: float = 300.0,
) -> float | None:
    """OKX 현물 대응 SWAP funding rate 를 조회한다."""
    inst_id = spot_symbol_to_okx_swap_inst_id(symbol)
    if inst_id is None:
        return None

    cache = _get_runtime_cache(exchange).setdefault("funding_rate", {})
    now_ts = time.time()
    cached = cache.get(inst_id)
    if (
        isinstance(cached, dict)
        and (now_ts - float(cached.get("ts", 0.0))) <= max(cache_ttl_sec, 0.0)
    ):
        return cached.get("value")

    response = call_okx_with_retry(
        exchange,
        exchange.publicGetPublicFundingRate,
        {"instId": inst_id},
    )
    data = response.get("data", []) if isinstance(response, dict) else response
    first = data[0] if data else {}
    value = None
    try:
        if isinstance(first, dict) and first.get("fundingRate") not in (None, ""):
            value = float(first.get("fundingRate"))
    except (TypeError, ValueError):
        value = None
    cache[inst_id] = {"ts": now_ts, "value": value}
    return value


def get_spot_balances_okx(exchange: ccxt.okx, base: str, quote: str) -> Tuple[float, float]:
    res = call_okx_with_retry(exchange, exchange.privateGetAccountBalance, {})
    data = res.get("data", []) if isinstance(res, dict) else res
    if not data:
        return 0.0, 0.0
    details = data[0].get("details", [])
    base_free = 0.0
    quote_free = 0.0
    for d in details:
        ccy = d.get("ccy")
        avail = float(d.get("availBal", 0.0))
        if ccy == base:
            base_free = avail
        elif ccy == quote:
            quote_free = avail
    return float(base_free), float(quote_free)


def safe_amount_to_precision_okx(exchange: ccxt.okx, symbol: str, amount: float) -> float:
    try:
        return float(exchange.amount_to_precision(symbol, amount))
    except Exception:
        return float(f"{amount:.9f}")


def place_market_order_okx(
    exchange: ccxt.okx, symbol: str, side: str, size: float, tgt_ccy: str | None = None
):
    inst_id = symbol.replace("/", "-")
    side = side.lower()
    if side not in ("buy", "sell"):
        raise ValueError("side 는 'buy' 또는 'sell' 이어야 합니다.")

    payload = {
        "instId": inst_id,
        "tdMode": "cash",
        "side": side,
        "ordType": "market",
        "sz": str(size),
    }
    if tgt_ccy is not None:
        payload["tgtCcy"] = tgt_ccy
    return exchange.privatePostTradeOrder(payload)
