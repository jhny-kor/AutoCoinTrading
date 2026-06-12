"""
수정 요약
- 업비트 공식 Rate Limit 그룹별 최소 호출 간격을 적용하는 lightweight limiter 를 추가했다.
- Quotation 과 주문 생성 그룹을 분리해 현재가 조회 직후 주문 생성에는 불필요한 전역 대기를 넣지 않도록 했다.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Final

import ccxt


UPBIT_MIN_INTERVAL_SEC: Final[dict[str, float]] = {
    "market": 0.1,
    "candle": 0.1,
    "trade": 0.1,
    "ticker": 0.1,
    "orderbook": 0.1,
    "default": 1.0 / 30.0,
    "order": 0.125,
    "order-test": 0.125,
    "order-cancel-all": 2.0,
}


@dataclass(slots=True)
class UpbitGroupRateLimiter:
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    _last_request_at: dict[str, float] = field(default_factory=dict)

    def throttle(self, group: str) -> None:
        min_interval_sec = UPBIT_MIN_INTERVAL_SEC.get(
            group,
            UPBIT_MIN_INTERVAL_SEC["default"],
        )
        now_ts = self.clock()
        last_request_at = self._last_request_at.get(group)
        if last_request_at is not None:
            wait_sec = min_interval_sec - (now_ts - last_request_at)
            if wait_sec > 0:
                self.sleep(wait_sec)
                now_ts = self.clock()
        self._last_request_at[group] = now_ts


def get_upbit_rate_limiter(options: dict) -> UpbitGroupRateLimiter:
    limiter = options.get("upbit_rate_limiter")
    if isinstance(limiter, UpbitGroupRateLimiter):
        return limiter

    clock = options.get("upbit_rate_limit_clock")
    sleep = options.get("upbit_rate_limit_sleep")
    limiter = UpbitGroupRateLimiter(
        clock=clock if callable(clock) else time.monotonic,
        sleep=sleep if callable(sleep) else time.sleep,
    )
    options["upbit_rate_limiter"] = limiter
    return limiter


def throttle_upbit_rest_call(exchange, group: str) -> None:
    options = getattr(exchange, "options", None)
    if not isinstance(options, dict):
        return
    if options.get("upbit_group_rate_limit_enabled", True) is False:
        return
    get_upbit_rate_limiter(options).throttle(group)


def is_upbit_retryable_error(exc: Exception) -> bool:
    lowered = str(exc).lower()
    return (
        isinstance(
            exc,
            (
                ccxt.RateLimitExceeded,
                ccxt.RequestTimeout,
                ccxt.NetworkError,
                ccxt.ExchangeNotAvailable,
                ccxt.DDoSProtection,
            ),
        )
        or "too_many_requests" in lowered
        or "429" in lowered
        or "timeout" in lowered
        or "timed out" in lowered
        or "temporarily unavailable" in lowered
    )


def call_upbit_with_retry(
    exchange,
    func,
    *args,
    rate_limit_group: str = "default",
    **kwargs,
):
    retry_count = int(exchange.options.get("upbit_request_retry_count", 3) or 3)
    retry_delay_sec = float(exchange.options.get("upbit_request_retry_delay_sec", 1.2) or 1.2)
    last_error: Exception | None = None
    for attempt in range(retry_count + 1):
        try:
            throttle_upbit_rest_call(exchange, rate_limit_group)
            return func(*args, **kwargs)
        except Exception as exc:
            last_error = exc
            if not is_upbit_retryable_error(exc) or attempt >= retry_count:
                raise
            time.sleep(retry_delay_sec * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise RuntimeError("업비트 재시도 호출이 비정상 종료되었습니다.")
