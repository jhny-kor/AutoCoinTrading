"""
작업 요약
- OKX 설정 로드, 조회 재시도, 잔고 조회, 시장가 주문 유틸을 공통 모듈로 분리했다.
- 알트/BTC 봇이 같은 OKX 실행 경로를 재사용하도록 정리했다.
"""

from __future__ import annotations

import os
import time
from typing import Tuple

import ccxt
from dotenv import load_dotenv


def load_okx_config() -> dict:
    load_dotenv()

    api_key = os.getenv("OKX_API_KEY")
    api_secret = os.getenv("OKX_API_SECRET")
    api_passphrase = os.getenv("OKX_API_PASSPHRASE")

    if not api_key or not api_secret or not api_passphrase:
        raise RuntimeError(
            "OKX_API_KEY / OKX_API_SECRET / OKX_API_PASSPHRASE 가 .env 에 설정되어 있지 않습니다."
        )

    sandbox = os.getenv("OKX_SANDBOX", "true").lower() == "true"
    risk_per_trade = float(os.getenv("OKX_TRADE_RISK_PER_TRADE", "0.05"))
    fee_rate_pct = float(os.getenv("OKX_FEE_RATE_PCT", "1.0"))
    max_daily_loss_quote = float(os.getenv("OKX_MAX_DAILY_LOSS_QUOTE", "5.0"))
    request_retry_count = int(os.getenv("OKX_REQUEST_RETRY_COUNT", "2"))
    request_retry_delay_sec = float(os.getenv("OKX_REQUEST_RETRY_DELAY_SEC", "1.0"))
    timeout_ms = int(os.getenv("OKX_REQUEST_TIMEOUT_MS", "15000"))

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
