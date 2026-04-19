"""BTC 청산 플래그 계산 테스트."""

import unittest

from core.strategy.btc import compute_btc_exit_flags


class BtcExitFlagTests(unittest.TestCase):
    def test_atr_trailing_exit_triggers_after_activation(self):
        flags = compute_btc_exit_flags(
            has_position=True,
            stop_price=95.0,
            take_profit_price=105.0,
            last_close=106.5,
            highest_price_since_entry=110.0,
            trailing_drawdown_pct=5.0,
            trailing_armed=True,
            enable_fee_protect_exit=True,
            fee_protect_min_net_pnl_pct=0.2,
            enable_atr_trailing_exit=True,
            trailing_atr_multiple=1.0,
            atr_value=3.0,
            pnl_pct=0.5,
            bearish=False,
            confirm_bullish=True,
            entry_mode="ema",
            donchian_exit_lower=100.0,
            last_low=107.0,
            enable_donchian_failure_exit=True,
        )
        self.assertTrue(flags["atr_trailing_stop_triggered"])
        self.assertTrue(flags["trailing_stop_triggered"])

    def test_donchian_failure_exit_triggers(self):
        flags = compute_btc_exit_flags(
            has_position=True,
            stop_price=95.0,
            take_profit_price=105.0,
            last_close=101.0,
            highest_price_since_entry=104.0,
            trailing_drawdown_pct=10.0,
            trailing_armed=False,
            enable_fee_protect_exit=True,
            fee_protect_min_net_pnl_pct=0.2,
            enable_atr_trailing_exit=True,
            trailing_atr_multiple=1.0,
            atr_value=2.0,
            pnl_pct=0.1,
            bearish=False,
            confirm_bullish=True,
            entry_mode="ema",
            donchian_exit_lower=102.0,
            last_low=101.5,
            enable_donchian_failure_exit=True,
        )
        self.assertTrue(flags["donchian_failure_triggered"])
