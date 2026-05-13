"""
작업 요약
- 알트 청산 보호/부분청산 계산과 최소 주문 fallback 정책을 검증한다.
"""

import unittest

from core.risk.alt_exit import (
    build_empty_position_runtime_metrics,
    compute_alt_exit_decisions,
    compute_alt_position_metrics,
    resolve_alt_partial_exit_policy,
    resolve_alt_sell_order_by_min_amount,
    resolve_alt_sell_order_by_min_value,
    resolve_alt_sell_intent,
)


class AltExitRuleTests(unittest.TestCase):
    def test_build_empty_position_runtime_metrics_returns_all_expected_keys(self):
        metrics = build_empty_position_runtime_metrics()
        self.assertEqual(
            set(metrics.keys()),
            {
                "pnl_pct",
                "mfe_pct",
                "mae_pct",
                "current_net_realized_pnl_quote",
                "current_net_realized_pnl_pct",
            },
        )
        self.assertTrue(all(value is None for value in metrics.values()))

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

    def test_partial_exit_policy_tracks_pending_flags_and_ratio(self):
        policy = resolve_alt_partial_exit_policy(
            symbol="ETH/KRW",
            partial_take_profit_enabled=True,
            partial_stop_loss_enabled=True,
            partial_take_profit_done={"ETH/KRW": False},
            partial_stop_loss_done={"ETH/KRW": True},
            partial_take_profit_ratio=0.4,
            partial_take_profit_ratio_multiplier=1.5,
        )

        self.assertTrue(policy.partial_take_profit_pending)
        self.assertFalse(policy.partial_stop_loss_pending)
        self.assertAlmostEqual(0.6, policy.effective_partial_take_profit_ratio)

    def test_partial_exit_policy_caps_take_profit_ratio(self):
        policy = resolve_alt_partial_exit_policy(
            symbol="XRP/KRW",
            partial_take_profit_enabled=True,
            partial_stop_loss_enabled=False,
            partial_take_profit_done={},
            partial_stop_loss_done={},
            partial_take_profit_ratio=0.8,
            partial_take_profit_ratio_multiplier=2.0,
        )

        self.assertTrue(policy.partial_take_profit_pending)
        self.assertFalse(policy.partial_stop_loss_pending)
        self.assertAlmostEqual(1.0, policy.effective_partial_take_profit_ratio)

    def test_sell_intent_prioritizes_stop_loss_over_other_exits(self):
        intent = resolve_alt_sell_intent(
            sell_split_ratio=0.4,
            stop_loss_triggered=True,
            partial_stop_loss_pending=False,
            partial_stop_loss_ratio=0.5,
            profit_protect_triggered=True,
            break_even_guard_triggered=True,
            volume_spike_exit_triggered=True,
            sol_probe_time_exit_triggered=True,
            partial_take_profit_pending=True,
            effective_partial_take_profit_ratio=0.6,
        )

        self.assertEqual(1.0, intent.sell_ratio)
        self.assertEqual("stop_loss", intent.exit_reason_key)
        self.assertEqual("손절", intent.sell_reason)

    def test_sell_intent_uses_partial_stop_loss_when_pending(self):
        intent = resolve_alt_sell_intent(
            sell_split_ratio=0.4,
            stop_loss_triggered=True,
            partial_stop_loss_pending=True,
            partial_stop_loss_ratio=0.35,
            profit_protect_triggered=False,
            break_even_guard_triggered=False,
            volume_spike_exit_triggered=False,
            sol_probe_time_exit_triggered=False,
            partial_take_profit_pending=False,
            effective_partial_take_profit_ratio=0.6,
        )

        self.assertAlmostEqual(0.35, intent.sell_ratio)
        self.assertEqual("partial_stop_loss", intent.exit_reason_key)
        self.assertEqual("부분손절", intent.sell_reason)

    def test_sell_intent_uses_partial_take_profit_or_default_split(self):
        partial_intent = resolve_alt_sell_intent(
            sell_split_ratio=0.4,
            stop_loss_triggered=False,
            partial_stop_loss_pending=False,
            partial_stop_loss_ratio=0.35,
            profit_protect_triggered=False,
            break_even_guard_triggered=False,
            volume_spike_exit_triggered=False,
            sol_probe_time_exit_triggered=False,
            partial_take_profit_pending=True,
            effective_partial_take_profit_ratio=0.6,
        )
        default_intent = resolve_alt_sell_intent(
            sell_split_ratio=0.4,
            stop_loss_triggered=False,
            partial_stop_loss_pending=False,
            partial_stop_loss_ratio=0.35,
            profit_protect_triggered=False,
            break_even_guard_triggered=False,
            volume_spike_exit_triggered=False,
            sol_probe_time_exit_triggered=False,
            partial_take_profit_pending=False,
            effective_partial_take_profit_ratio=0.6,
        )

        self.assertAlmostEqual(0.6, partial_intent.sell_ratio)
        self.assertEqual("partial_take_profit", partial_intent.exit_reason_key)
        self.assertAlmostEqual(0.4, default_intent.sell_ratio)
        self.assertEqual("take_profit", default_intent.exit_reason_key)

    def test_min_amount_policy_promotes_partial_exit_to_full_okx_sell(self):
        plan = resolve_alt_sell_order_by_min_amount(
            symbol="SOL/USDT",
            base="SOL",
            amount=0.01,
            full_sell_amount=0.1,
            sell_ratio=0.5,
            exit_reason_key="partial_take_profit",
            sell_reason="부분익절",
            min_order_amount=0.05,
        )

        self.assertTrue(plan.should_order)
        self.assertEqual(0.1, plan.amount)
        self.assertEqual(1.0, plan.sell_ratio)
        self.assertEqual("take_profit", plan.exit_reason_key)
        self.assertEqual("익절", plan.sell_reason)
        self.assertIn("전량 청산으로 전환", plan.log_message)

    def test_min_amount_policy_skips_dust_okx_sell(self):
        plan = resolve_alt_sell_order_by_min_amount(
            symbol="SOL/USDT",
            base="SOL",
            amount=0.01,
            full_sell_amount=0.02,
            sell_ratio=0.5,
            exit_reason_key="take_profit",
            sell_reason="익절",
            min_order_amount=0.05,
        )

        self.assertFalse(plan.should_order)
        self.assertEqual("sell_amount_below_min_order_amount", plan.skip_reason)
        self.assertIn("매도를 생략", plan.log_message)

    def test_min_value_policy_promotes_partial_exit_to_full_upbit_sell(self):
        plan = resolve_alt_sell_order_by_min_value(
            symbol="SOL/KRW",
            base="SOL",
            quote="KRW",
            amount=0.01,
            full_sell_amount=0.1,
            sell_order_value_quote=3000.0,
            full_sell_order_value_quote=30000.0,
            sell_ratio=0.5,
            exit_reason_key="partial_stop_loss",
            sell_reason="부분손절",
            min_sell_order_value=5000.0,
        )

        self.assertTrue(plan.should_order)
        self.assertEqual(0.1, plan.amount)
        self.assertEqual(30000.0, plan.order_value_quote)
        self.assertEqual("stop_loss", plan.exit_reason_key)
        self.assertEqual("손절", plan.sell_reason)

    def test_min_value_policy_skips_small_upbit_sell(self):
        plan = resolve_alt_sell_order_by_min_value(
            symbol="SOL/KRW",
            base="SOL",
            quote="KRW",
            amount=0.01,
            full_sell_amount=0.02,
            sell_order_value_quote=3000.0,
            full_sell_order_value_quote=4000.0,
            sell_ratio=0.5,
            exit_reason_key="take_profit",
            sell_reason="익절",
            min_sell_order_value=5000.0,
        )

        self.assertFalse(plan.should_order)
        self.assertEqual("sell_value_below_min_order_value", plan.skip_reason)
        self.assertIn("예상 매도 금액", plan.log_message)


if __name__ == "__main__":
    unittest.main()
