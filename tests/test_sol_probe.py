"""SOL 제한형 probe helper 회귀 테스트."""

import unittest

from core.strategy.sol_probe import (
    evaluate_sol_probe_entry,
    is_sol_probe_time_exit_triggered,
    scale_probe_order_value,
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
        self.assertEqual(2500.0, scale_probe_order_value(10000.0, decision))

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
