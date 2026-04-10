"""레짐 기반 전략 라우터에 대한 개발 테스트."""

import unittest

from core.strategy.regime_router import route_alt_strategy, route_btc_strategy


class RegimeRouterTests(unittest.TestCase):
    def test_btc_router_returns_skip_for_low_energy(self):
        route = route_btc_strategy("LOW_ENERGY")
        self.assertEqual("skip", route.strategy_key)
        self.assertTrue(route.policy.pause_new_entry)

    def test_btc_router_returns_breakout_for_breakout_attempt(self):
        route = route_btc_strategy("BREAKOUT_ATTEMPT")
        self.assertEqual("breakout", route.strategy_key)
        self.assertTrue(route.policy.require_fresh_cross)

    def test_btc_router_returns_breakout_for_trending_early(self):
        route = route_btc_strategy("TRENDING_EARLY")
        self.assertEqual("breakout", route.strategy_key)
        self.assertFalse(route.policy.allow_trend_follow_entry)

    def test_alt_router_shares_same_route_keys(self):
        self.assertEqual("skip", route_alt_strategy("CHOPPY_LOW_VOL").strategy_key)
        self.assertEqual("breakout", route_alt_strategy("CHOPPY_HIGH_VOL").strategy_key)
        self.assertEqual("trend_follow", route_alt_strategy("TRENDING_MATURE").strategy_key)


if __name__ == "__main__":
    unittest.main()
