"""런타임 상태 bootstrap helper 테스트."""

import unittest

from core.runtime.bootstrap import build_alt_runtime_state, build_btc_runtime_state
from settings.state_recovery import RecoveredPositionState


class RuntimeBootstrapTests(unittest.TestCase):
    def test_build_alt_runtime_state_filters_empty_values(self):
        recovered = {
            "ETH/USDT": RecoveredPositionState(
                symbol="ETH/USDT",
                remaining_amount=1.0,
                cost_basis_quote=2000.0,
                average_entry_price=2000.0,
                cycle_buy_count=2,
                opened_at_ts=100.0,
                highest_price_since_entry=2100.0,
                lowest_price_since_entry=1950.0,
                trailing_armed=False,
                trailing_armed_at_ts=None,
                trailing_activation_price=None,
                partial_take_profit_done=True,
                partial_stop_loss_done=False,
                last_trade_at_ts=110.0,
                last_partial_take_profit_at_ts=108.0,
                last_stop_loss_at_ts=0.0,
                last_profit_exit_at_ts=0.0,
            ),
            "XRP/USDT": RecoveredPositionState(
                symbol="XRP/USDT",
                remaining_amount=0.0,
                cost_basis_quote=0.0,
                average_entry_price=None,
                cycle_buy_count=0,
                opened_at_ts=None,
                highest_price_since_entry=None,
                lowest_price_since_entry=None,
                trailing_armed=False,
                trailing_armed_at_ts=None,
                trailing_activation_price=None,
                partial_take_profit_done=False,
                partial_stop_loss_done=False,
                last_trade_at_ts=0.0,
                last_partial_take_profit_at_ts=0.0,
                last_stop_loss_at_ts=0.0,
                last_profit_exit_at_ts=0.0,
            ),
        }

        runtime_state = build_alt_runtime_state(recovered)

        self.assertEqual(runtime_state.entry_price, {"ETH/USDT": 2000.0})
        self.assertEqual(runtime_state.entry_opened_at, {"ETH/USDT": 100.0})
        self.assertEqual(runtime_state.partial_take_profit_done, {"ETH/USDT": True})
        self.assertEqual(runtime_state.entry_count, {"ETH/USDT": 2})
        self.assertEqual(runtime_state.last_trade_at, {"ETH/USDT": 110.0})

    def test_build_btc_runtime_state_handles_missing_recovery(self):
        runtime_state = build_btc_runtime_state("BTC/USDT", None)

        self.assertIsNone(runtime_state.entry_price)
        self.assertIsNone(runtime_state.position_id)
        self.assertFalse(runtime_state.trailing_armed)
        self.assertEqual(runtime_state.add_on_count, 0)
        self.assertEqual(runtime_state.last_trade_at, 0.0)


if __name__ == "__main__":
    unittest.main()

