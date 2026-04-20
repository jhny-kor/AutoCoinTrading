"""Mean reversion 전략 helper 테스트."""

import unittest

from core.strategy.mean_reversion import compute_bollinger_mean_reversion_state


class MeanReversionTests(unittest.TestCase):
    def test_lower_band_reclaim_sets_entry_signal(self):
        state = compute_bollinger_mean_reversion_state(
            prev_close=98.0,
            last_close=100.5,
            bb_lower=99.0,
            bb_mid=103.0,
            bb_upper=107.0,
            bb_width_pct=2.0,
            squeeze_max_bandwidth_pct=3.0,
            rsi_value=34.0,
            signal_score_min=55.0,
            rsi_filter_passed=True,
            macd_filter_passed=True,
        )
        self.assertTrue(state["bullish"])
        self.assertTrue(state["entry_signal"])
        self.assertGreater(state["signal_score"], 0.0)

    def test_filter_failure_blocks_entry_even_when_band_reclaims(self):
        state = compute_bollinger_mean_reversion_state(
            prev_close=98.0,
            last_close=100.5,
            bb_lower=99.0,
            bb_mid=103.0,
            bb_upper=107.0,
            bb_width_pct=2.0,
            squeeze_max_bandwidth_pct=3.0,
            rsi_value=34.0,
            signal_score_min=55.0,
            rsi_filter_passed=False,
            macd_filter_passed=True,
        )
        self.assertFalse(state["rsi_filter_passed"])
        self.assertFalse(state["entry_signal"])

    def test_signal_score_min_contract_blocks_weak_reversion(self):
        state = compute_bollinger_mean_reversion_state(
            prev_close=98.0,
            last_close=100.5,
            bb_lower=99.0,
            bb_mid=103.0,
            bb_upper=107.0,
            bb_width_pct=2.0,
            squeeze_max_bandwidth_pct=3.0,
            rsi_value=34.0,
            signal_score_min=99.0,
            rsi_filter_passed=True,
            macd_filter_passed=True,
        )
        self.assertFalse(state["signal_is_strong"])
        self.assertFalse(state["entry_signal"])
