"""단독 지표를 결합해 추격 진입 리스크를 줄이는 helper 테스트."""

import unittest

from core.strategy.combined_filters import (
    calc_recent_range_context,
    is_btc_regime_correlation_volatility_risk,
    is_overheated_entry_risk,
    is_stop_loss_context_reentry_risk,
    is_volume_atr_execution_weak_risk,
    requires_overheat_confirmation,
)


class CombinedFilterTests(unittest.TestCase):
    def test_overheated_entry_requires_volume_atr_and_rsi_together(self):
        self.assertTrue(
            is_overheated_entry_risk(
                volume_ratio=2.5,
                atr_percentile=90.0,
                rsi_value=72.0,
                volume_ratio_threshold=2.0,
                atr_percentile_threshold=85.0,
                rsi_threshold=68.0,
            )
        )
        self.assertFalse(
            is_overheated_entry_risk(
                volume_ratio=2.5,
                atr_percentile=90.0,
                rsi_value=55.0,
                volume_ratio_threshold=2.0,
                atr_percentile_threshold=85.0,
                rsi_threshold=68.0,
            )
        )

    def test_recent_range_context_and_extra_confirmation(self):
        ohlcv = [
            [1, 100.0, 102.0, 99.0, 100.0, 10.0],
            [2, 100.0, 104.0, 98.0, 103.5, 12.0],
        ]
        context = calc_recent_range_context(ohlcv, last_close=103.5, lookback=2)

        self.assertGreaterEqual(context["range_position_pct"], 90.0)
        self.assertLessEqual(context["distance_from_recent_high_pct"], 0.5)
        self.assertTrue(
            requires_overheat_confirmation(
                signal_is_strong=True,
                range_position_pct=context["range_position_pct"],
                distance_from_recent_high_pct=context["distance_from_recent_high_pct"],
                range_position_threshold=70.0,
                distance_from_high_threshold_pct=0.20,
            )
        )

    def test_btc_regime_correlation_volatility_guard_requires_all_parts(self):
        self.assertTrue(
            is_btc_regime_correlation_volatility_risk(
                btc_regime="OVERHEATED",
                correlation_with_btc=0.82,
                alt_atr_percentile=76.0,
                risky_btc_regimes=("LOW_ENERGY", "OVERHEATED"),
                min_correlation=0.75,
                min_alt_atr_percentile=70.0,
            )
        )
        self.assertFalse(
            is_btc_regime_correlation_volatility_risk(
                btc_regime="TRENDING_EARLY",
                correlation_with_btc=0.82,
                alt_atr_percentile=76.0,
                risky_btc_regimes=("LOW_ENERGY", "OVERHEATED"),
                min_correlation=0.75,
                min_alt_atr_percentile=70.0,
            )
        )

    def test_volume_atr_execution_guard_uses_fill_or_orderbook_weakness(self):
        self.assertTrue(
            is_volume_atr_execution_weak_risk(
                volume_ratio=2.4,
                atr_percentile=88.0,
                fill_quality_avg_fill_ratio=0.92,
                fill_quality_sample_count=1,
                orderbook_pressure_score=None,
                volume_ratio_threshold=2.0,
                atr_percentile_threshold=80.0,
                min_fill_ratio=0.98,
                min_fill_sample_count=1,
                min_orderbook_pressure_score=45.0,
            )
        )
        self.assertTrue(
            is_volume_atr_execution_weak_risk(
                volume_ratio=2.4,
                atr_percentile=88.0,
                fill_quality_avg_fill_ratio=None,
                fill_quality_sample_count=0,
                orderbook_pressure_score=40.0,
                volume_ratio_threshold=2.0,
                atr_percentile_threshold=80.0,
                min_fill_ratio=0.98,
                min_fill_sample_count=1,
                min_orderbook_pressure_score=45.0,
            )
        )
        self.assertFalse(
            is_volume_atr_execution_weak_risk(
                volume_ratio=2.4,
                atr_percentile=88.0,
                fill_quality_avg_fill_ratio=1.0,
                fill_quality_sample_count=1,
                orderbook_pressure_score=55.0,
                volume_ratio_threshold=2.0,
                atr_percentile_threshold=80.0,
                min_fill_ratio=0.98,
                min_fill_sample_count=1,
                min_orderbook_pressure_score=45.0,
            )
        )

    def test_stop_loss_context_reentry_guard_matches_recent_similar_context(self):
        previous = {
            "strategy_key": "breakout",
            "symbol_regime": "CHOPPY_HIGH_VOL",
            "btc_reference_regime": "OVERHEATED",
            "high_atr": True,
        }
        current = {
            "strategy_key": "breakout",
            "symbol_regime": "CHOPPY_HIGH_VOL",
            "btc_reference_regime": "OVERHEATED",
            "high_atr": False,
        }

        self.assertTrue(
            is_stop_loss_context_reentry_risk(
                elapsed_since_stop_loss_sec=600,
                cooldown_sec=3600,
                current_context=current,
                previous_context=previous,
                min_similarity_count=3,
            )
        )
        self.assertFalse(
            is_stop_loss_context_reentry_risk(
                elapsed_since_stop_loss_sec=4000,
                cooldown_sec=3600,
                current_context=current,
                previous_context=previous,
                min_similarity_count=3,
            )
        )


if __name__ == "__main__":
    unittest.main()
