"""
작업 요약
- 알트 매수/매도 체결 후 포지션 lifecycle 공통 helper 동작을 검증한다.
"""

import unittest

from core.positions.lifecycle import apply_alt_buy_fill_state, apply_alt_sell_fill_state


class PositionLifecycleTests(unittest.TestCase):
    def test_apply_alt_buy_fill_state_initializes_new_position(self):
        entry_price = {}
        entry_count = {}
        entry_opened_at = {}
        highest_price_since_entry = {}
        lowest_price_since_entry = {}

        state = apply_alt_buy_fill_state(
            symbol="ETH/KRW",
            bought_amount=2.0,
            last_close=100.0,
            has_position=False,
            avg_entry_price=None,
            base_free=0.0,
            current_entry_count=0,
            now_ts=1234.0,
            entry_price=entry_price,
            entry_count=entry_count,
            entry_opened_at=entry_opened_at,
            highest_price_since_entry=highest_price_since_entry,
            lowest_price_since_entry=lowest_price_since_entry,
        )

        self.assertEqual(2.0, state.bought_amount)
        self.assertEqual(100.0, state.entry_price_after)
        self.assertEqual(1, state.entry_count_after)
        self.assertEqual(2.0, state.remaining_base_after_estimate)
        self.assertEqual({"ETH/KRW": 100.0}, entry_price)
        self.assertEqual({"ETH/KRW": 1}, entry_count)
        self.assertEqual({"ETH/KRW": 1234.0}, entry_opened_at)
        self.assertEqual({"ETH/KRW": 100.0}, highest_price_since_entry)
        self.assertEqual({"ETH/KRW": 100.0}, lowest_price_since_entry)

    def test_apply_alt_buy_fill_state_averages_existing_position(self):
        entry_price = {"ETH/KRW": 90.0}
        entry_count = {"ETH/KRW": 1}
        entry_opened_at = {"ETH/KRW": 1000.0}
        highest_price_since_entry = {"ETH/KRW": 110.0}
        lowest_price_since_entry = {"ETH/KRW": 80.0}

        state = apply_alt_buy_fill_state(
            symbol="ETH/KRW",
            bought_amount=1.0,
            last_close=120.0,
            has_position=True,
            avg_entry_price=90.0,
            base_free=2.0,
            current_entry_count=1,
            now_ts=1234.0,
            entry_price=entry_price,
            entry_count=entry_count,
            entry_opened_at=entry_opened_at,
            highest_price_since_entry=highest_price_since_entry,
            lowest_price_since_entry=lowest_price_since_entry,
        )

        self.assertAlmostEqual(100.0, state.entry_price_after)
        self.assertEqual(2, state.entry_count_after)
        self.assertEqual(3.0, state.remaining_base_after_estimate)
        self.assertEqual({"ETH/KRW": 100.0}, entry_price)
        self.assertEqual({"ETH/KRW": 2}, entry_count)
        self.assertEqual({"ETH/KRW": 1000.0}, entry_opened_at)
        self.assertEqual({"ETH/KRW": 120.0}, highest_price_since_entry)
        self.assertEqual({"ETH/KRW": 80.0}, lowest_price_since_entry)

    def test_apply_alt_sell_fill_state_tracks_partial_take_profit(self):
        entry_count = {"ETH/KRW": 2}
        entry_opened_at = {"ETH/KRW": 1000.0}
        last_trade_at = {}
        last_stop_loss_at = {}
        last_stop_loss_context = {}
        partial_take_profit_done = {}
        partial_take_profit_last_at = {}
        partial_stop_loss_done = {}

        state = apply_alt_sell_fill_state(
            symbol="ETH/KRW",
            sold_amount=0.4,
            base_free=1.0,
            current_entry_count=2,
            exit_reason_key="partial_take_profit",
            full_clear_threshold=0.0001,
            now_ts=1300.0,
            entry_count=entry_count,
            entry_opened_at=entry_opened_at,
            last_trade_at=last_trade_at,
            last_stop_loss_at=last_stop_loss_at,
            last_stop_loss_context=last_stop_loss_context,
            current_entry_risk_context={"atr": "mid"},
            partial_take_profit_done=partial_take_profit_done,
            partial_take_profit_last_at=partial_take_profit_last_at,
            partial_stop_loss_done=partial_stop_loss_done,
        )

        self.assertAlmostEqual(0.6, state.remaining_base)
        self.assertEqual(1, state.entry_count_after)
        self.assertEqual(300.0, state.holding_seconds)
        self.assertFalse(state.should_clear_position)
        self.assertEqual({"ETH/KRW": 1}, entry_count)
        self.assertEqual({"ETH/KRW": 1300.0}, last_trade_at)
        self.assertEqual({"ETH/KRW": True}, partial_take_profit_done)
        self.assertEqual({"ETH/KRW": 1300.0}, partial_take_profit_last_at)
        self.assertEqual({}, partial_stop_loss_done)
        self.assertEqual({}, last_stop_loss_at)
        self.assertEqual({}, last_stop_loss_context)

    def test_apply_alt_sell_fill_state_tracks_full_stop_loss(self):
        entry_count = {"ETH/KRW": 1}
        entry_opened_at = {"ETH/KRW": 1000.0}
        last_trade_at = {}
        last_stop_loss_at = {}
        last_stop_loss_context = {}
        partial_take_profit_done = {}
        partial_take_profit_last_at = {}
        partial_stop_loss_done = {}

        state = apply_alt_sell_fill_state(
            symbol="ETH/KRW",
            sold_amount=1.0,
            base_free=1.0,
            current_entry_count=1,
            exit_reason_key="stop_loss",
            full_clear_threshold=0.0001,
            now_ts=1400.0,
            entry_count=entry_count,
            entry_opened_at=entry_opened_at,
            last_trade_at=last_trade_at,
            last_stop_loss_at=last_stop_loss_at,
            last_stop_loss_context=last_stop_loss_context,
            current_entry_risk_context={"volume": "high"},
            partial_take_profit_done=partial_take_profit_done,
            partial_take_profit_last_at=partial_take_profit_last_at,
            partial_stop_loss_done=partial_stop_loss_done,
        )

        self.assertEqual(0.0, state.remaining_base)
        self.assertEqual(0, state.entry_count_after)
        self.assertEqual(400.0, state.holding_seconds)
        self.assertTrue(state.should_clear_position)
        self.assertEqual({"ETH/KRW": 0}, entry_count)
        self.assertEqual({"ETH/KRW": 1400.0}, last_trade_at)
        self.assertEqual({"ETH/KRW": 1400.0}, last_stop_loss_at)
        self.assertEqual({"ETH/KRW": {"volume": "high"}}, last_stop_loss_context)
        self.assertEqual({}, partial_take_profit_done)
        self.assertEqual({}, partial_stop_loss_done)


if __name__ == "__main__":
    unittest.main()
