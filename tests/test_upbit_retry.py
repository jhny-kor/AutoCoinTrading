"""업비트 재시도 가능 예외 분류 테스트."""

import unittest

import ccxt

from core.execution.upbit import ensure_upbit_market_cached, is_upbit_retryable_error


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


if __name__ == "__main__":
    unittest.main()
