"""루프 fetch 최적화(잔고 일괄조회 + HTF TTL 캐시) 개발 테스트."""

import unittest
from types import SimpleNamespace

import core.execution.okx as okx_mod
from core.execution.okx import get_all_spot_balances_okx
from core.runtime.fetch_cache import get_fresh_cached, store_cached


class GetAllSpotBalancesOkxTests(unittest.TestCase):
    def setUp(self):
        # call_okx_with_retry(exchange, fn, params) 를 fn(params) 직접 호출로 대체
        self._orig = okx_mod.call_okx_with_retry
        okx_mod.call_okx_with_retry = lambda exchange, fn, params: fn(params)

    def tearDown(self):
        okx_mod.call_okx_with_retry = self._orig

    def _exchange(self, payload):
        return SimpleNamespace(privateGetAccountBalance=lambda params: payload)

    def test_parses_all_currencies_once(self):
        payload = {"data": [{"details": [
            {"ccy": "USDT", "availBal": "70.5"},
            {"ccy": "ETH", "availBal": "0.0"},
            {"ccy": "SOL", "availBal": "1.25"},
        ]}]}
        balances = get_all_spot_balances_okx(self._exchange(payload))
        self.assertEqual(balances["USDT"], 70.5)
        self.assertEqual(balances["SOL"], 1.25)
        self.assertEqual(balances.get("ETH"), 0.0)
        # 맵에 없는 통화는 호출측에서 .get(x, 0.0) 로 0 처리
        self.assertIsNone(balances.get("XRP"))

    def test_empty_data_returns_empty_map(self):
        self.assertEqual(get_all_spot_balances_okx(self._exchange({"data": []})), {})

    def test_malformed_availbal_defaults_zero(self):
        payload = {"data": [{"details": [{"ccy": "USDT", "availBal": None}]}]}
        self.assertEqual(get_all_spot_balances_okx(self._exchange(payload))["USDT"], 0.0)


class FetchCacheTests(unittest.TestCase):
    def test_returns_value_within_ttl(self):
        cache = {}
        store_cached(cache, ("ETH/USDT", "5m"), 1000.0, ["candle"])
        self.assertEqual(get_fresh_cached(cache, ("ETH/USDT", "5m"), 1015.0, 20.0), ["candle"])

    def test_expires_after_ttl(self):
        cache = {}
        store_cached(cache, "k", 1000.0, "v")
        self.assertIsNone(get_fresh_cached(cache, "k", 1025.0, 20.0))

    def test_ttl_zero_disables_cache(self):
        cache = {}
        store_cached(cache, "k", 1000.0, "v")
        self.assertIsNone(get_fresh_cached(cache, "k", 1000.0, 0.0))

    def test_missing_key_returns_none(self):
        self.assertIsNone(get_fresh_cached({}, "absent", 1.0, 20.0))


if __name__ == "__main__":
    unittest.main()
