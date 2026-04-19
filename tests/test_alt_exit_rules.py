"""알트 청산 보호 계산에 대한 개발 테스트."""

import unittest

from core.risk.alt_exit import compute_alt_exit_decisions, compute_alt_position_metrics


class AltExitRuleTests(unittest.TestCase):
    def test_position_metrics_calculates_mfe_mae_and_pnl(self):
        metrics = compute_alt_position_metrics(
            has_position=True,
            average_entry_price=100.0,
            last_close=105.0,
            base_free=1.0,
            fee_rate_pct=0.05,
            highest_price_since_entry=104.0,
            lowest_price_since_entry=99.0,
        )
        self.assertAlmostEqual(metrics["highest_price_since_entry"], 105.0)
        self.assertAlmostEqual(metrics["lowest_price_since_entry"], 99.0)
        self.assertAlmostEqual(metrics["pnl_pct"], 5.0)
        self.assertGreater(metrics["mfe_pct"], 0)
        self.assertLess(metrics["mae_pct"], 0)
        self.assertIsNotNone(metrics["net_pnl_pct"])

    def test_profit_protect_and_break_even_flags(self):
        decisions = compute_alt_exit_decisions(
            has_position=True,
            pnl_pct=1.5,
            mfe_pct=2.0,
            current_net_realized_pnl_pct=0.4,
            take_profit_pct=1.0,
            stop_loss_pct=1.5,
            fee_rate_pct=0.05,
            enable_fee_protect_exit=True,
            fee_protect_min_net_pnl_pct=0.2,
            enable_break_even_guard=True,
            break_even_guard_min_mfe_pct=1.0,
            break_even_guard_floor_net_pnl_pct=0.0,
            break_even_guard_max_profit_retrace_pct=0.5,
            enable_volume_spike_exit=True,
            volume_spike_exit_min_profit_pct=0.2,
            volume_spike_exit_max_volume_ratio=0.8,
            volume_ratio=1.2,
            bearish=True,
            sell_split_ratio=0.5,
        )
        self.assertTrue(decisions["take_profit_ready"])
        self.assertTrue(decisions["profit_protect_triggered"])
        self.assertFalse(decisions["break_even_guard_triggered"])
        self.assertEqual(decisions["estimated_sell_ratio"], 1.0)

    def test_break_even_guard_can_trigger_without_profit_protect(self):
        decisions = compute_alt_exit_decisions(
            has_position=True,
            pnl_pct=0.3,
            mfe_pct=1.5,
            current_net_realized_pnl_pct=-0.01,
            take_profit_pct=1.0,
            stop_loss_pct=1.5,
            fee_rate_pct=0.05,
            enable_fee_protect_exit=True,
            fee_protect_min_net_pnl_pct=0.2,
            enable_break_even_guard=True,
            break_even_guard_min_mfe_pct=1.0,
            break_even_guard_floor_net_pnl_pct=0.0,
            break_even_guard_max_profit_retrace_pct=0.5,
            enable_volume_spike_exit=True,
            volume_spike_exit_min_profit_pct=0.2,
            volume_spike_exit_max_volume_ratio=0.8,
            volume_ratio=1.2,
            bearish=True,
            sell_split_ratio=0.5,
        )
        self.assertFalse(decisions["profit_protect_triggered"])
        self.assertTrue(decisions["break_even_guard_triggered"])
        self.assertEqual(decisions["estimated_sell_ratio"], 1.0)

    def test_break_even_guard_waits_until_profit_retrace_is_large_enough(self):
        decisions = compute_alt_exit_decisions(
            has_position=True,
            pnl_pct=1.2,
            mfe_pct=1.5,
            current_net_realized_pnl_pct=-0.02,
            take_profit_pct=1.0,
            stop_loss_pct=1.5,
            fee_rate_pct=0.05,
            enable_fee_protect_exit=True,
            fee_protect_min_net_pnl_pct=0.2,
            enable_break_even_guard=True,
            break_even_guard_min_mfe_pct=1.0,
            break_even_guard_floor_net_pnl_pct=0.0,
            break_even_guard_max_profit_retrace_pct=0.5,
            enable_volume_spike_exit=True,
            volume_spike_exit_min_profit_pct=0.2,
            volume_spike_exit_max_volume_ratio=0.8,
            volume_ratio=1.2,
            bearish=True,
            sell_split_ratio=0.5,
        )
        self.assertFalse(decisions["break_even_guard_triggered"])

    def test_volume_spike_exit_triggers_when_profit_and_volume_collapse(self):
        decisions = compute_alt_exit_decisions(
            has_position=True,
            pnl_pct=0.6,
            mfe_pct=1.0,
            current_net_realized_pnl_pct=0.3,
            take_profit_pct=1.0,
            stop_loss_pct=1.5,
            fee_rate_pct=0.05,
            enable_fee_protect_exit=True,
            fee_protect_min_net_pnl_pct=0.5,
            enable_break_even_guard=True,
            break_even_guard_min_mfe_pct=1.0,
            break_even_guard_floor_net_pnl_pct=0.0,
            break_even_guard_max_profit_retrace_pct=0.5,
            enable_volume_spike_exit=True,
            volume_spike_exit_min_profit_pct=0.2,
            volume_spike_exit_max_volume_ratio=0.8,
            volume_ratio=0.5,
            bearish=True,
            sell_split_ratio=0.5,
        )
        self.assertTrue(decisions["volume_spike_exit_triggered"])
        self.assertEqual(decisions["estimated_sell_ratio"], 1.0)


if __name__ == "__main__":
    unittest.main()
