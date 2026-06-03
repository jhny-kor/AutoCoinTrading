"""알트/BTC 퍼널 step 생성기 구조에 대한 개발 테스트."""

import unittest
from types import SimpleNamespace

from core.strategy.funnels import (
    build_alt_entry_guard_steps,
    build_alt_entry_steps,
    build_alt_exit_steps,
    build_btc_add_on_steps,
    build_btc_entry_steps,
    build_btc_exit_steps,
)


class FunnelBuilderTests(unittest.TestCase):
    def test_alt_entry_guard_steps_common_shape(self):
        strategy = SimpleNamespace(
            allows_sol_probe=lambda symbol: symbol == "SOL/KRW",
            enable_sol_probe=True,
            sol_probe_symbols=("SOL/KRW", "SOL/USDT"),
            sol_probe_min_signal_score=70.0,
            low_energy_probe_min_signal_score=70.0,
            low_energy_probe_min_volume_ratio=1.0,
            low_energy_probe_min_orderbook_pressure_score=0.2,
            low_energy_probe_max_atr_percentile=0.8,
            max_correlation_with_btc=0.75,
            btc_correlation_volatility_risky_regimes=("LOW_ENERGY",),
            btc_correlation_volatility_min_corr=0.7,
            btc_correlation_volatility_min_atr_percentile=0.7,
            volume_atr_execution_guard_volume_ratio=2.0,
            volume_atr_execution_guard_atr_percentile=0.8,
            volume_atr_execution_min_fill_ratio=0.8,
            volume_atr_execution_min_orderbook_pressure_score=0.2,
            stop_loss_context_reentry_cooldown_sec=600,
            stop_loss_context_min_similarity_count=2,
            fill_quality_min_fill_ratio=0.8,
        )

        steps = build_alt_entry_guard_steps(
            strategy=strategy,
            symbol="SOL/KRW",
            sol_probe_entry_allowed=True,
            sol_probe_entry_decision=SimpleNamespace(
                reason="sol_probe_allowed",
                position_scale=0.25,
            ),
            has_position=False,
            current_entry_count=0,
            signal_score=72.0,
            htf_bearish_entry_blocked=False,
            htf_bearish=False,
            effective_low_energy_guard_active=False,
            low_energy_guard_active=True,
            low_energy_probe_decision=SimpleNamespace(
                allowed=False,
                reason="low_energy_probe_signal_score_low",
            ),
            low_energy_snapshot=SimpleNamespace(
                avg_volume_ratio=0.5,
                avg_abs_change_pct=0.1,
                ready_count=0,
            ),
            volume_ratio=1.1,
            orderbook_pressure_score=0.3,
            atr_percentile=0.5,
            effective_symbol_regime_blocks_entry=False,
            symbol_regime="LOW_ENERGY",
            symbol_regime_requires_strong_signal=True,
            signal_is_strong=False,
            entry_probe_score_override_allowed=True,
            effective_signal_score_min=70.0,
            correlation_entry_blocked=False,
            correlation_with_btc=0.4,
            btc_reference_above_ma=True,
            btc_correlation_volatility_blocked=False,
            btc_reference_regime="TRENDING",
            volume_atr_execution_blocked=False,
            low_energy_top_chase_entry_blocked=False,
            low_energy_top_chase_actual={"btc_reference_regime": "TRENDING"},
            low_energy_top_chase_required={"risky_btc_regimes": ("LOW_ENERGY",)},
            fill_quality_snapshot=SimpleNamespace(avg_fill_ratio=0.95, sample_count=3),
            stop_loss_context_reentry_blocked=False,
            seconds_since_last_stop_loss=999.0,
            last_stop_loss_ts=1.0,
            current_entry_risk_context={"atr": "mid"},
            last_stop_loss_context={"SOL/KRW": {"atr": "low"}},
            fill_quality_entry_blocked=False,
            entry_timing_snapshot=SimpleNamespace(
                ready=True,
                phase="READY",
                confirmation_count=3,
                required_confirmations=3,
            ),
        )

        self.assertEqual(
            [
                "sol_probe",
                "htf_bearish_entry_guard",
                "market_regime",
                "symbol_regime",
                "regime_signal_strength",
                "correlation_guard",
                "btc_regime_correlation_volatility_guard",
                "volume_atr_execution_guard",
                "low_energy_top_chase_guard",
                "stop_loss_context_reentry_guard",
                "fill_quality_guard",
                "entry_timing",
            ],
            [step.stage for step in steps],
        )
        self.assertTrue(all(step.passed for step in steps))
        self.assertEqual("sol_probe_allowed", steps[0].reason)
        self.assertTrue(steps[4].actual["probe_score_override_allowed"])

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
            volume_cap_downgrade_allowed=False,
            volume_cap_downgrade_reason="within_normal_volume_cap",
            volume_cap_hard_max_ratio=30.0,
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
        self.assertEqual(23, len(steps))
        self.assertEqual("raw_entry_signal", steps[0].stage)
        self.assertEqual("order_value", steps[-1].stage)

    def test_alt_entry_steps_split_mean_reversion_reason(self):
        steps = build_alt_entry_steps(
            entry_signal=False,
            bullish=False,
            trend_follow_entry=False,
            signal_is_strong=True,
            signal_score=80.0,
            min_signal_score=55.0,
            gap_pct=0.3,
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
            volume_cap_downgrade_allowed=False,
            volume_cap_downgrade_reason="within_normal_volume_cap",
            volume_cap_hard_max_ratio=30.0,
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
            entry_strategy_key="mean_reversion",
        )
        self.assertEqual("mean_reversion_lower_reclaim_missing", steps[0].reason)

    def test_alt_entry_steps_accept_probe_signal(self):
        steps = build_alt_entry_steps(
            entry_signal=True,
            bullish=False,
            trend_follow_entry=False,
            signal_is_strong=True,
            signal_score=72.0,
            min_signal_score=70.0,
            gap_pct=0.1,
            min_gap_pct=0.2,
            max_gap_pct=0.8,
            gap_within_upper_bound=True,
            rsi_filter_passed=True,
            macd_filter_passed=True,
            htf_bullish=True,
            volume_filter_passed=True,
            volume_ratio=1.0,
            effective_min_volume_ratio=0.9,
            max_volume_ratio=2.5,
            volume_within_upper_bound=True,
            volume_cap_downgrade_allowed=False,
            volume_cap_downgrade_reason="within_normal_volume_cap",
            volume_cap_hard_max_ratio=30.0,
            volatility_filter_passed=True,
            avg_abs_change_pct=0.2,
            min_volatility_pct=0.03,
            max_volatility_pct=5.0,
            in_cooldown=False,
            seconds_since_last_trade=999.0,
            can_average_down=True,
            last_close=101.0,
            avg_entry_price=None,
            current_entry_count=0,
            max_entry_count=1,
            daily_loss_limit_reached=False,
            daily_realized_pnl_quote=0.0,
            max_daily_loss_quote=5000.0,
            order_value_quote=10000.0,
            min_buy_order_value=5000.0,
            entry_probe_signal=True,
            entry_probe_reason="sol_probe_allowed",
        )

        self.assertTrue(steps[0].passed)
        self.assertTrue(steps[11].passed)
        self.assertTrue(steps[0].actual["entry_probe_signal"])

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

    def test_alt_exit_steps_accept_sol_probe_time_exit(self):
        steps = build_alt_exit_steps(
            has_position=True,
            stop_loss_triggered=False,
            profit_protect_triggered=False,
            break_even_guard_triggered=False,
            volume_spike_exit_triggered=False,
            bearish=False,
            in_cooldown=True,
            seconds_since_last_trade=30.0,
            signal_is_strong=False,
            gap_pct=0.01,
            min_gap_pct=0.2,
            htf_bearish=False,
            take_profit_ready=False,
            pnl_pct=0.1,
            current_net_realized_pnl_pct=0.0,
            mfe_pct=0.2,
            min_take_profit_pct=0.8,
            fee_protect_min_net_pnl_pct=0.2,
            break_even_guard_min_mfe_pct=1.0,
            break_even_guard_floor_net_pnl_pct=0.0,
            sol_probe_time_exit_triggered=True,
        )

        self.assertTrue(steps[1].passed)
        self.assertTrue(steps[2].passed)
        self.assertTrue(steps[-1].passed)

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
