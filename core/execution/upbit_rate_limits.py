"""
수정 요약
- 업비트 REST 제한을 Oracle 호스트 전체에서 공유하도록 파일락 기반 limiter 를 추가했다.
- 업비트 공식 Rate Limit 그룹별 최소 호출 간격을 적용하는 lightweight limiter 를 추가했다.
- Quotation 과 주문 생성 그룹을 분리해 현재가 조회 직후 주문 생성에는 불필요한 전역 대기를 넣지 않도록 했다.
"""

from __future__ import annotations

import fcntl
import os
from pathlib import Path
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


def _safe_rate_limit_group_name(group: str) -> str:
    sanitized = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in group)
    return sanitized or "default"


def _parse_last_request_at(raw_value: str) -> float | None:
    try:
        return float(raw_value.strip())
    except ValueError:
        return None


@dataclass(slots=True)
class UpbitGroupRateLimiter:
    """프로세스 내부에서 업비트 REST 호출 간격을 그룹별로 제한한다."""

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


@dataclass(slots=True)
class UpbitSharedGroupRateLimiter:
    """파일락으로 여러 봇 프로세스의 업비트 REST 호출 간격을 함께 제한한다."""

    state_dir: Path
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep

    def throttle(self, group: str) -> None:
        min_interval_sec = UPBIT_MIN_INTERVAL_SEC.get(
            group,
            UPBIT_MIN_INTERVAL_SEC["default"],
        )
        self.state_dir.mkdir(parents=True, exist_ok=True)
        state_path = self.state_dir / f"{_safe_rate_limit_group_name(group)}.lock"
        with state_path.open("a+", encoding="utf-8") as state_file:
            fcntl.flock(state_file.fileno(), fcntl.LOCK_EX)
            try:
                state_file.seek(0)
                last_request_at = _parse_last_request_at(state_file.read())
                now_ts = self.clock()
                if (
                    last_request_at is not None
                    and last_request_at <= now_ts + min_interval_sec
                ):
                    wait_sec = min_interval_sec - (now_ts - last_request_at)
                    if wait_sec > 0:
                        self.sleep(wait_sec)
                        now_ts = self.clock()
                state_file.seek(0)
                state_file.truncate()
                state_file.write(f"{now_ts:.9f}\n")
                state_file.flush()
                os.fsync(state_file.fileno())
            finally:
                fcntl.flock(state_file.fileno(), fcntl.LOCK_UN)


def get_upbit_rate_limiter(
    options: dict,
) -> UpbitGroupRateLimiter | UpbitSharedGroupRateLimiter:
    limiter = options.get("upbit_rate_limiter")
    if isinstance(limiter, (UpbitGroupRateLimiter, UpbitSharedGroupRateLimiter)):
        return limiter

    clock = options.get("upbit_rate_limit_clock")
    sleep = options.get("upbit_rate_limit_sleep")
    limiter_clock = clock if callable(clock) else time.monotonic
    limiter_sleep = sleep if callable(sleep) else time.sleep
    if options.get("upbit_rate_limit_shared_enabled", True) is False:
        limiter = UpbitGroupRateLimiter(clock=limiter_clock, sleep=limiter_sleep)
    else:
        raw_state_dir = str(
            options.get("upbit_rate_limit_shared_state_dir")
            or os.getenv("UPBIT_RATE_LIMIT_SHARED_STATE_DIR")
            or "logs/runtime/upbit_rate_limits"
        )
        limiter = UpbitSharedGroupRateLimiter(
            state_dir=Path(raw_state_dir),
            clock=limiter_clock,
            sleep=limiter_sleep,
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
