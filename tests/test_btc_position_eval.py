"""BTC 보유 포지션 평가와 익절가 계산에 대한 개발 테스트."""

import unittest
from types import SimpleNamespace

from core.strategy.btc_position import build_btc_exit_prices, evaluate_btc_open_position


class BtcPositionEvalTests(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            stop_mode="atr",
            take_profit_mode="atr",
            stop_atr_multiple=1.5,
            take_profit_atr_multiple=1.0,
            enable_partial_take_profit=True,
            enable_bull_pullback_hold=True,
            bull_pullback_tolerance_pct=0.5,
            bull_pullback_min_spread_pct=0.1,
        )

    def test_fee_floor_applies_to_take_profit(self):
        stop_price, take_profit_price = build_btc_exit_prices(
            entry_price=100.0,
            atr_value=1.0,
            recent_swing_low=98.0,
            recent_swing_high=100.2,
            min_take_profit_pct=1.5,
            settings=self.settings,
        )
        self.assertAlmostEqual(stop_price, 98.5)
        self.assertAlmostEqual(take_profit_price, 101.5, places=6)

    def test_evaluate_position_arms_trailing_when_take_profit_reached(self):
        state = evaluate_btc_open_position(
            has_position=True,
            entry_price=100.0,
            last_close=102.0,
            base_free=1.0,
            fee_rate_pct=0.05,
            atr_value=1.0,
            recent_swing_low=99.0,
            recent_swing_high=101.0,
            highest_price_since_entry=101.0,
            lowest_price_since_entry=99.0,
            trailing_armed=False,
            trailing_armed_at=None,
            trailing_activation_price=None,
            partial_take_profit_done=False,
            confirm_bullish=True,
            ema_aligned=True,
            ema_spread_pct=0.2,
            settings=self.settings,
        )
        self.assertTrue(state["partial_take_profit_triggered"])
        self.assertFalse(state["trailing_armed"])
        self.assertFalse(state["trailing_armed_just_now"])
        self.assertGreater(state["pnl_pct"], 0)
        self.assertGreater(state["mfe_pct"], 0)

    def test_no_position_returns_reset_shape(self):
        state = evaluate_btc_open_position(
            has_position=False,
            entry_price=None,
            last_close=100.0,
            base_free=0.0,
            fee_rate_pct=0.05,
            atr_value=1.0,
            recent_swing_low=99.0,
            recent_swing_high=101.0,
            highest_price_since_entry=None,
            lowest_price_since_entry=None,
            trailing_armed=False,
            trailing_armed_at=None,
            trailing_activation_price=None,
            partial_take_profit_done=False,
            confirm_bullish=False,
            ema_aligned=False,
            ema_spread_pct=0.0,
            settings=self.settings,
        )
        self.assertIsNone(state["pnl_pct"])
        self.assertFalse(state["trailing_armed"])
        self.assertTrue(state["add_on_count_reset"])


if __name__ == "__main__":
    unittest.main()
