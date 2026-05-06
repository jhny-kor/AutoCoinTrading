"""매수 검토 위원회 평가 로직 테스트."""

import unittest

from core.strategy.entry_committee import (
    EntryCommitteeSettings,
    evaluate_entry_committee,
)


def build_settings(mode: str = "shadow") -> EntryCommitteeSettings:
    return EntryCommitteeSettings(
        enabled=True,
        mode=mode,
        min_approve_votes=3,
        require_risk_approval=True,
        require_execution_approval=True,
        min_signal_score=50.0,
        min_orderbook_pressure_score=45.0,
        min_fill_ratio=0.70,
        high_atr_percentile=95.0,
        upper_range_position_pct=80.0,
    )


class EntryCommitteeTests(unittest.TestCase):
    def test_approves_when_strategy_risk_execution_portfolio_and_regime_clear(self):
        result = evaluate_entry_committee(
            {
                "entry_signal": True,
                "signal_score": 72.0,
                "effective_signal_score_min": 62.0,
                "signal_is_strong": True,
                "orderbook_pressure_score": 58.0,
                "fill_quality_avg_fill_ratio": 0.95,
                "fill_quality_sample_count": 5,
                "portfolio_remaining_budget_quote": 100.0,
                "effective_position_ratio": 0.25,
                "order_value": 25.0,
                "regime_strategy_key": "trend_follow",
            },
            build_settings(),
        )

        self.assertTrue(result.approved)
        self.assertFalse(result.active_blocks_entry)
        self.assertGreaterEqual(result.approve_votes, 3)

    def test_shadow_mode_records_reject_without_blocking_entry(self):
        result = evaluate_entry_committee(
            {
                "entry_signal": True,
                "signal_score": 80.0,
                "signal_is_strong": True,
                "daily_loss_limit_reached": True,
                "portfolio_remaining_budget_quote": 100.0,
                "effective_position_ratio": 0.25,
                "order_value": 25.0,
            },
            build_settings(mode="shadow"),
        )

        self.assertFalse(result.approved)
        self.assertTrue(result.hard_veto)
        self.assertFalse(result.active_blocks_entry)
        self.assertEqual("entry_committee_hard_veto", result.reason)

    def test_active_mode_blocks_on_risk_hard_veto(self):
        result = evaluate_entry_committee(
            {
                "entry_signal": True,
                "signal_score": 80.0,
                "signal_is_strong": True,
                "overheated_entry_blocked": True,
                "portfolio_remaining_budget_quote": 100.0,
                "effective_position_ratio": 0.25,
                "order_value": 25.0,
            },
            build_settings(mode="active"),
        )

        self.assertFalse(result.approved)
        self.assertTrue(result.hard_veto)
        self.assertTrue(result.active_blocks_entry)


if __name__ == "__main__":
    unittest.main()
