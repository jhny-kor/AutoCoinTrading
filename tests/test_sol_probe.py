"""SOL 제한형 probe helper 회귀 테스트."""

import unittest

from core.strategy.sol_probe import (
    evaluate_sol_probe_entry,
    resolve_sol_probe_entry_state,
    resolve_sol_probe_exit_state,
    is_sol_probe_time_exit_triggered,
)


class SolProbeTests(unittest.TestCase):
    def test_allows_only_sol_with_score_and_no_position(self):
        decision = evaluate_sol_probe_entry(
            enabled=True,
            symbol="SOL/KRW",
            eligible_symbols=("SOL/USDT", "SOL/KRW"),
            signal_score=72.0,
            min_signal_score=70.0,
            has_position=False,
            current_entry_count=0,
            position_scale=0.25,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual("sol_probe_allowed", decision.reason)
        self.assertEqual(0.25, decision.position_scale)

    def test_entry_state_promotes_sol_probe_and_bypasses_entry_blocks(self):
        state = resolve_sol_probe_entry_state(
            enabled=True,
            symbol="SOL/KRW",
            eligible_symbols=("SOL/USDT", "SOL/KRW"),
            signal_score=72.0,
            min_signal_score=70.0,
            has_position=False,
            current_entry_count=0,
            position_scale=0.25,
            entry_signal=False,
            signal_is_strong=False,
            max_entry_count=3,
            low_energy_guard_active=True,
            low_energy_probe_allowed=False,
            symbol_regime_blocks_entry=True,
            mean_reversion_lower_near_probe_allowed=False,
        )

        self.assertTrue(state.decision.allowed)
        self.assertTrue(state.entry_signal)
        self.assertTrue(state.signal_is_strong)
        self.assertEqual(1, state.max_entry_count)
        self.assertFalse(state.low_energy_guard_active)
        self.assertFalse(state.symbol_regime_blocks_entry)

    def test_entry_state_keeps_non_sol_blocks_unchanged(self):
        state = resolve_sol_probe_entry_state(
            enabled=True,
            symbol="ETH/KRW",
            eligible_symbols=("SOL/USDT", "SOL/KRW"),
            signal_score=90.0,
            min_signal_score=70.0,
            has_position=False,
            current_entry_count=0,
            position_scale=0.25,
            entry_signal=False,
            signal_is_strong=False,
            max_entry_count=3,
            low_energy_guard_active=True,
            low_energy_probe_allowed=False,
            symbol_regime_blocks_entry=True,
            mean_reversion_lower_near_probe_allowed=False,
        )

        self.assertFalse(state.decision.allowed)
        self.assertFalse(state.entry_signal)
        self.assertFalse(state.signal_is_strong)
        self.assertEqual(3, state.max_entry_count)
        self.assertTrue(state.low_energy_guard_active)
        self.assertTrue(state.symbol_regime_blocks_entry)

    def test_entry_state_keeps_low_energy_probe_min_entry_count(self):
        state = resolve_sol_probe_entry_state(
            enabled=True,
            symbol="ETH/KRW",
            eligible_symbols=("SOL/USDT", "SOL/KRW"),
            signal_score=90.0,
            min_signal_score=70.0,
            has_position=False,
            current_entry_count=0,
            position_scale=0.25,
            entry_signal=False,
            signal_is_strong=False,
            max_entry_count=0,
            low_energy_guard_active=True,
            low_energy_probe_allowed=True,
            symbol_regime_blocks_entry=True,
            mean_reversion_lower_near_probe_allowed=False,
        )

        self.assertEqual(1, state.max_entry_count)
        self.assertFalse(state.low_energy_guard_active)
        self.assertFalse(state.symbol_regime_blocks_entry)

    def test_blocks_existing_symbol_position(self):
        decision = evaluate_sol_probe_entry(
            enabled=True,
            symbol="SOL/USDT",
            eligible_symbols=("SOL/USDT", "SOL/KRW"),
            signal_score=90.0,
            min_signal_score=70.0,
            has_position=True,
            current_entry_count=1,
            position_scale=0.25,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual("sol_probe_position_exists", decision.reason)

    def test_time_exit_uses_configured_minutes(self):
        self.assertTrue(
            is_sol_probe_time_exit_triggered(
                enabled=True,
                symbol="SOL/KRW",
                eligible_symbols=("SOL/USDT", "SOL/KRW"),
                has_position=True,
                opened_at=1000.0,
                now_ts=1000.0 + 180 * 60,
                max_hold_minutes=180,
            )
        )

    def test_exit_state_uses_probe_thresholds_for_sol(self):
        state = resolve_sol_probe_exit_state(
            enabled=True,
            symbol="SOL/KRW",
            eligible_symbols=("SOL/USDT", "SOL/KRW"),
            has_position=True,
            opened_at=1000.0,
            now_ts=1000.0 + 181 * 60,
            max_hold_minutes=180,
            base_take_profit_pct=1.5,
            base_stop_loss_pct=1.0,
            stop_loss_multiplier=1.2,
            take_profit_bonus_pct=0.3,
            fee_round_trip_pct=0.1,
            sol_probe_take_profit_pct=0.8,
            sol_probe_stop_loss_pct=0.5,
        )

        self.assertTrue(state.active)
        self.assertAlmostEqual(0.8, state.take_profit_pct)
        self.assertAlmostEqual(0.5, state.stop_loss_pct)
        self.assertAlmostEqual(0.8, state.effective_take_profit_pct)
        self.assertTrue(state.time_exit_triggered)

    def test_exit_state_keeps_regular_thresholds_for_non_sol(self):
        state = resolve_sol_probe_exit_state(
            enabled=True,
            symbol="ETH/KRW",
            eligible_symbols=("SOL/USDT", "SOL/KRW"),
            has_position=True,
            opened_at=1000.0,
            now_ts=1000.0 + 181 * 60,
            max_hold_minutes=180,
            base_take_profit_pct=1.5,
            base_stop_loss_pct=1.0,
            stop_loss_multiplier=1.2,
            take_profit_bonus_pct=0.3,
            fee_round_trip_pct=0.1,
            sol_probe_take_profit_pct=0.8,
            sol_probe_stop_loss_pct=0.5,
        )

        self.assertFalse(state.active)
        self.assertAlmostEqual(1.5, state.take_profit_pct)
        self.assertAlmostEqual(1.2, state.stop_loss_pct)
        self.assertAlmostEqual(1.8, state.effective_take_profit_pct)
        self.assertFalse(state.time_exit_triggered)
        self.assertFalse(
            is_sol_probe_time_exit_triggered(
                enabled=True,
                symbol="ETH/KRW",
                eligible_symbols=("SOL/USDT", "SOL/KRW"),
                has_position=True,
                opened_at=1000.0,
                now_ts=1000.0 + 180 * 60,
                max_hold_minutes=180,
            )
        )


if __name__ == "__main__":
    unittest.main()
