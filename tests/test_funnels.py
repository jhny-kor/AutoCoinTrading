"""알트/BTC 퍼널 step 생성기 구조에 대한 개발 테스트."""

import unittest

from core.strategy.funnels import (
    build_alt_entry_steps,
    build_alt_exit_steps,
    build_btc_add_on_steps,
    build_btc_entry_steps,
    build_btc_exit_steps,
)


class FunnelBuilderTests(unittest.TestCase):
    def test_alt_entry_steps_shape_and_reasons(self):
        steps = build_alt_entry_steps(
            entry_signal=True,
            bullish=True,
            trend_follow_entry=False,
            signal_is_strong=True,
            signal_score=75.0,
            min_signal_score=55.0,
            gap_pct=0.5,
            min_gap_pct=0.2,
            max_gap_pct=0.8,
            gap_within_upper_bound=True,
            rsi_filter_passed=True,
            macd_filter_passed=True,
            htf_bullish=True,
            volume_filter_passed=True,
            volume_ratio=1.4,
            effective_min_volume_ratio=1.0,
            max_volume_ratio=2.5,
            volume_within_upper_bound=True,
            volatility_filter_passed=True,
            avg_abs_change_pct=0.8,
            min_volatility_pct=0.1,
            max_volatility_pct=5.0,
            in_cooldown=False,
            seconds_since_last_trade=999.0,
            can_average_down=True,
            last_close=101.0,
            avg_entry_price=100.0,
            current_entry_count=0,
            max_entry_count=3,
            daily_loss_limit_reached=False,
            daily_realized_pnl_quote=0.0,
            max_daily_loss_quote=5.0,
            order_value_quote=50.0,
            min_buy_order_value=1.0,
            funding_rate_filter_passed=True,
            funding_rate=None,
            max_funding_rate=None,
        )
        self.assertEqual(16, len(steps))
        self.assertEqual("trend", steps[0].stage)
        self.assertEqual("order_value", steps[-1].stage)

    def test_alt_exit_steps_trigger_reason(self):
        steps = build_alt_exit_steps(
            has_position=True,
            stop_loss_triggered=False,
            profit_protect_triggered=True,
            break_even_guard_triggered=False,
            volume_spike_exit_triggered=False,
            bearish=True,
            in_cooldown=False,
            seconds_since_last_trade=30.0,
            signal_is_strong=False,
            gap_pct=0.05,
            min_gap_pct=0.2,
            htf_bearish=True,
            take_profit_ready=False,
            pnl_pct=0.4,
            current_net_realized_pnl_pct=0.25,
            mfe_pct=1.1,
            min_take_profit_pct=0.6,
            fee_protect_min_net_pnl_pct=0.2,
            break_even_guard_min_mfe_pct=1.0,
            break_even_guard_floor_net_pnl_pct=0.0,
        )
        self.assertEqual("position", steps[0].stage)
        self.assertEqual("take_profit", steps[-1].stage)
        self.assertTrue(steps[1].passed)

    def test_btc_entry_steps_include_order_amount(self):
        steps = build_btc_entry_steps(
            entry_signal=True,
            bullish=True,
            trend_follow_entry=False,
            ema_aligned=True,
            price_above_fast=True,
            ema_slope_positive=True,
            ema_spread_pct=0.15,
            effective_min_ema_spread_pct=0.1,
            signal_score=70.0,
            min_signal_score=55.0,
            rsi_filter_passed=True,
            bb_width_filter_passed=True,
            bb_width_pct=0.8,
            min_bb_width_pct=0.2,
            max_bb_width_pct=5.0,
            has_position=False,
            in_cooldown=False,
            cooldown_remaining=0.0,
            base_cooldown_remaining=0.0,
            stop_loss_cooldown_remaining=0.0,
            profit_exit_cooldown_remaining=0.0,
            low_energy_guard_active=False,
            low_energy_avg_volume_ratio=1.0,
            low_energy_avg_abs_change_pct=0.1,
            low_energy_ready_count=1,
            symbol_regime_blocks_entry=False,
            symbol_regime="TREND",
            symbol_regime_requires_fresh_cross=False,
            volume_filter_passed=True,
            volume_ratio=1.5,
            effective_min_volume_ratio=1.0,
            atr_filter_passed=True,
            atr_pct=0.2,
            effective_min_atr_pct=0.1,
            max_atr_pct=2.5,
            confirm_bullish=True,
            daily_loss_limit_reached=False,
            daily_realized_pnl_quote=0.0,
            max_daily_loss_quote=5.0,
            remaining_budget_quote=100.0,
            current_cost_basis_quote=0.0,
            target_budget_quote=100.0,
            order_value=50.0,
            min_buy_order_value=5.0,
            estimated_entry_amount=0.001,
            min_order_amount=0.0001,
        )
        self.assertEqual("order_amount", steps[-1].stage)
        self.assertEqual("bb_width", steps[2].stage)

    def test_btc_add_on_steps_include_budget(self):
        steps = build_btc_add_on_steps(
            has_position=True,
            add_on_profit_ready=True,
            pnl_pct=0.8,
            min_pnl_pct=0.35,
            add_on_limit_available=True,
            add_on_count=0,
            max_add_ons=1,
            trailing_armed=False,
            entry_signal=True,
            bullish=False,
            trend_follow_entry=True,
            in_cooldown=False,
            cooldown_remaining=0.0,
            profit_exit_cooldown_remaining=0.0,
            volume_filter_passed=True,
            volume_ratio=1.3,
            effective_min_volume_ratio=1.0,
            atr_filter_passed=True,
            atr_pct=0.2,
            min_atr_pct=0.1,
            max_atr_pct=2.5,
            confirm_bullish=True,
            daily_loss_limit_reached=False,
            daily_realized_pnl_quote=0.0,
            max_daily_loss_quote=5.0,
            remaining_budget_quote=50.0,
            current_cost_basis_quote=25.0,
            target_budget_quote=100.0,
            add_on_order_value=25.0,
            min_buy_order_value=5.0,
            estimated_add_on_amount=0.0005,
            min_order_amount=0.0001,
        )
        stages = [step.stage for step in steps]
        self.assertIn("add_on_portfolio_budget", stages)
        self.assertEqual("add_on_order_amount", stages[-1])

    def test_btc_exit_steps_structure(self):
        steps = build_btc_exit_steps(
            has_position=True,
            stop_triggered=False,
            partial_take_profit_triggered=True,
            profit_protect_triggered=False,
            trailing_stop_triggered=False,
            donchian_failure_triggered=False,
            trend_exit_triggered=False,
            estimated_exit_amount=0.001,
            min_order_amount=0.0001,
            sell_order_value_quote=100.0,
            min_sell_order_value=5.0,
        )
        self.assertEqual(["position", "exit_trigger", "amount", "order_value"], [s.stage for s in steps])


if __name__ == "__main__":
    unittest.main()
