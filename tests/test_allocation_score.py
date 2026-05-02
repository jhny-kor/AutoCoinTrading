"""score 기반 동적 자본 배분 helper 테스트."""

import unittest
from types import SimpleNamespace

from core.risk.allocation import compute_allocation_score


class AllocationScoreTests(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            enable_score_based_scaling=True,
            score_scale_min=0.60,
            score_scale_max=1.10,
            signal_weight=0.40,
            market_weight=0.30,
            execution_weight=0.20,
            diversification_weight=0.10,
            score_bucket_very_strong=85.0,
            score_bucket_strong=75.0,
            score_bucket_neutral=65.0,
            score_bucket_weak=55.0,
        )

    def test_strong_signal_gets_higher_scale(self):
        result = compute_allocation_score(
            settings=self.settings,
            signal_score=88.0,
            volume_ratio=2.0,
            required_volume_ratio=1.0,
            trend_ok=True,
            low_energy_guard_active=False,
            symbol_regime="TRENDING",
            fill_quality_avg_fill_ratio=1.0,
            fill_quality_entry_blocked=False,
            correlation_with_btc=0.2,
            max_correlation_with_btc=0.7,
        )
        self.assertGreaterEqual(result.score_scale, 1.0)
        self.assertGreater(result.allocation_score, 75.0)

    def test_low_energy_and_bad_execution_reduce_scale(self):
        result = compute_allocation_score(
            settings=self.settings,
            signal_score=62.0,
            volume_ratio=0.8,
            required_volume_ratio=1.0,
            trend_ok=False,
            low_energy_guard_active=True,
            symbol_regime="LOW_ENERGY",
            fill_quality_avg_fill_ratio=0.4,
            fill_quality_entry_blocked=True,
            correlation_with_btc=0.8,
            max_correlation_with_btc=0.7,
        )
        self.assertEqual(result.score_scale, 0.60)
        self.assertLess(result.allocation_score, 55.0)
        self.assertEqual(result.reason_top, "market")

    def test_high_volume_high_atr_and_weak_orderbook_reduce_score(self):
        result = compute_allocation_score(
            settings=self.settings,
            signal_score=90.0,
            volume_ratio=3.0,
            required_volume_ratio=1.0,
            volume_ratio_percentile=98.0,
            trend_ok=True,
            low_energy_guard_active=False,
            symbol_regime="TRENDING",
            atr_percentile=85.0,
            orderbook_pressure_score=40.0,
            fill_quality_avg_fill_ratio=1.0,
            fill_quality_entry_blocked=False,
            correlation_with_btc=0.2,
            max_correlation_with_btc=0.7,
        )

        self.assertLess(result.market_score_component, 80.0)
        self.assertLess(result.execution_score_component, 90.0)
        self.assertLess(result.allocation_score, 85.0)

    def test_correlation_alone_is_not_max_penalty(self):
        result = compute_allocation_score(
            settings=self.settings,
            signal_score=80.0,
            volume_ratio=1.2,
            required_volume_ratio=1.0,
            trend_ok=True,
            low_energy_guard_active=False,
            symbol_regime="TRENDING",
            fill_quality_avg_fill_ratio=1.0,
            fill_quality_entry_blocked=False,
            correlation_with_btc=0.75,
            max_correlation_with_btc=0.7,
        )

        self.assertEqual(result.diversification_score_component, 50.0)
        self.assertGreater(result.allocation_score, 70.0)


if __name__ == "__main__":
    unittest.main()
