"""포트폴리오 배분 잔고 조회 재시도 테스트."""

import unittest

from settings.portfolio_allocator import _fetch_okx_balance_map


class FlakyOkxExchange:
    """첫 balance 호출만 timeout 으로 실패하는 OKX 테스트 더블."""

    id = "okx"

    def __init__(self):
        self.options = {
            "okx_request_retry_count": 1,
            "okx_request_retry_delay_sec": 0.0,
        }
        self.calls = 0

    def privateGetAccountBalance(self, params):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("RequestTimeout('okx GET https://www.okx.com/api/v5/account/balance')")
        return {
            "data": [
                {
                    "details": [
                        {"ccy": "BTC", "availBal": "0.01"},
                        {"ccy": "USDT", "availBal": "10.5"},
                    ]
                }
            ]
        }


class PortfolioAllocatorRetryTests(unittest.TestCase):
    def test_okx_balance_timeout_is_retried(self):
        exchange = FlakyOkxExchange()

        balances = _fetch_okx_balance_map(exchange, ["BTC", "USDT"])

        self.assertEqual(2, exchange.calls)
        self.assertEqual(0.01, balances["BTC"])
        self.assertEqual(10.5, balances["USDT"])


if __name__ == "__main__":
    unittest.main()
