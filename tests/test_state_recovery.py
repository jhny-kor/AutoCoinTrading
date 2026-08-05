"""
수정 요약
- 명시적 최종 청산은 반올림 잔량을 제거하고 부분청산은 유지하는 회귀 테스트를 추가한다.
- trade_history 기반 상태 복구와 당일 순손익 재계산을 검증한다.
"""

import unittest
from datetime import date
from unittest.mock import patch

from settings.state_recovery import (
    load_program_daily_realized_pnl_quote,
    restore_program_position_states,
)


class StateRecoveryTests(unittest.TestCase):
    def test_explicit_final_exit_clears_rounding_residual(self):
        records = [
            {
                "program_name": "ma_crossover_bot",
                "symbol": "ETH/USDT",
                "side": "buy",
                "amount": 1.0,
                "order_value_quote": 2000.0,
                "recorded_at_local": "2026-03-29T09:00:00+09:00",
            },
            {
                "program_name": "ma_crossover_bot",
                "symbol": "ETH/USDT",
                "side": "sell",
                "reason": "stop_loss",
                "is_final_exit": True,
                "amount": 0.99,
                "order_value_quote": 1960.0,
                "recorded_at_local": "2026-03-29T09:10:00+09:00",
            },
        ]
        with patch("settings.state_recovery.read_trade_history", return_value=records):
            recovered = restore_program_position_states("ma_crossover_bot", ["ETH/USDT"])
        state = recovered["ETH/USDT"]
        self.assertEqual(0.0, state.remaining_amount)
        self.assertIsNone(state.average_entry_price)
        self.assertEqual(0, state.cycle_buy_count)

    def test_partial_exit_does_not_clear_on_zero_metadata_without_final_flag(self):
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
                "reason": "partial_stop_loss",
                "entry_count_after": 0,
                "remaining_base_after_estimate": 0,
                "amount": 1.0,
                "order_value_quote": 90.0,
                "recorded_at_local": "2026-03-29T09:10:00+09:00",
            },
        ]
        with patch("settings.state_recovery.read_trade_history", return_value=records):
            recovered = restore_program_position_states("ma_crossover_bot", ["ETH/USDT"])
        state = recovered["ETH/USDT"]
        self.assertAlmostEqual(1.0, state.remaining_amount)
        self.assertTrue(state.partial_stop_loss_done)

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
