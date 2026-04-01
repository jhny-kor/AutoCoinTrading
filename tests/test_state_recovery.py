"""trade_history 기반 상태 복구와 당일 순손익 재계산에 대한 개발 테스트."""

import unittest
from datetime import date
from unittest.mock import patch

from settings.state_recovery import (
    load_program_daily_realized_pnl_quote,
    restore_program_position_states,
)


class StateRecoveryTests(unittest.TestCase):
    def test_restore_position_after_partial_take_profit(self):
        records = [
            {
                "program_name": "ma_crossover_bot",
                "symbol": "ETH/USDT",
                "side": "buy",
                "amount": 2.0,
                "order_value_quote": 200.0,
                "recorded_at_local": "2026-03-29T09:00:00+09:00",
            },
            {
                "program_name": "ma_crossover_bot",
                "symbol": "ETH/USDT",
                "side": "sell",
                "reason": "partial_take_profit",
                "amount": 1.0,
                "order_value_quote": 110.0,
                "recorded_at_local": "2026-03-29T09:10:00+09:00",
            },
        ]
        with patch("settings.state_recovery.read_trade_history", return_value=records):
            recovered = restore_program_position_states("ma_crossover_bot", ["ETH/USDT"])
        state = recovered["ETH/USDT"]
        self.assertAlmostEqual(state.remaining_amount, 1.0)
        self.assertAlmostEqual(state.average_entry_price, 100.0)
        self.assertTrue(state.partial_take_profit_done)

    def test_daily_pnl_uses_net_when_available(self):
        records = [
            {
                "program_name": "okx_btc_ema_trend_bot",
                "symbol": "BTC/USDT",
                "side": "sell",
                "net_realized_pnl_quote": 1.25,
                "recorded_at_local": "2026-03-29T10:00:00+09:00",
            },
            {
                "program_name": "okx_btc_ema_trend_bot",
                "symbol": "BTC/USDT",
                "side": "sell",
                "realized_pnl_quote": -0.5,
                "recorded_at_local": "2026-03-29T11:00:00+09:00",
            },
        ]
        with patch("settings.state_recovery.read_trade_history", return_value=records):
            total = load_program_daily_realized_pnl_quote(
                "okx_btc_ema_trend_bot",
                target_date=date(2026, 3, 29),
            )
        self.assertAlmostEqual(total, 0.75)


if __name__ == "__main__":
    unittest.main()
