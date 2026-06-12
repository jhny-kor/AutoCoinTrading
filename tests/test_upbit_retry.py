"""업비트 재시도 가능 예외와 그룹별 요청 제한 테스트."""

import unittest

import ccxt

from core.execution.upbit import (
    call_upbit_with_retry,
    ensure_upbit_market_cached,
    is_upbit_retryable_error,
)


class UpbitRetryTests(unittest.TestCase):
    def test_request_timeout_is_retryable(self):
        self.assertTrue(is_upbit_retryable_error(ccxt.RequestTimeout("timeout")))

    def test_rate_limit_is_retryable(self):
        self.assertTrue(is_upbit_retryable_error(ccxt.RateLimitExceeded("429")))

    def test_non_retryable_value_error_is_false(self):
        self.assertFalse(is_upbit_retryable_error(ValueError("bad input")))

    def test_ensure_upbit_market_cached_populates_symbol_without_network(self):
        exchange = ccxt.upbit({})
        ensure_upbit_market_cached(exchange, "BTC/KRW")
        self.assertIn("BTC/KRW", exchange.markets)
        self.assertIn("KRW-BTC", exchange.markets_by_id)
        self.assertIn("BTC/KRW", exchange.symbols)

    def test_orderbook_lookup_does_not_delay_next_order_group(self):
        calls = []
        sleeps = []

        class FakeExchange:
            def __init__(self) -> None:
                self.options = {
                    "upbit_request_retry_count": 0,
                    "upbit_rate_limit_sleep": sleeps.append,
                    "upbit_rate_limit_clock": lambda: 100.0,
                }

        def fake_orderbook() -> dict[str, str]:
            calls.append("orderbook")
            return {"ok": "orderbook"}

        def fake_order() -> dict[str, str]:
            calls.append("order")
            return {"ok": "order"}

        exchange = FakeExchange()

        call_upbit_with_retry(exchange, fake_orderbook, rate_limit_group="orderbook")
        call_upbit_with_retry(exchange, fake_order, rate_limit_group="order")

        self.assertEqual(["orderbook", "order"], calls)
        self.assertEqual([], sleeps)

    def test_same_order_group_waits_for_upbit_order_limit(self):
        sleeps = []
        now = [100.0]

        class FakeExchange:
            def __init__(self) -> None:
                self.options = {
                    "upbit_request_retry_count": 0,
                    "upbit_rate_limit_sleep": self.sleep,
                    "upbit_rate_limit_clock": lambda: now[0],
                }

            def sleep(self, seconds: float) -> None:
                sleeps.append(seconds)
                now[0] += seconds

        def fake_order() -> dict[str, str]:
            return {"ok": "order"}

        exchange = FakeExchange()

        call_upbit_with_retry(exchange, fake_order, rate_limit_group="order")
        call_upbit_with_retry(exchange, fake_order, rate_limit_group="order")

        self.assertEqual(1, len(sleeps))
        self.assertAlmostEqual(0.125, sleeps[0])


if __name__ == "__main__":
    unittest.main()
