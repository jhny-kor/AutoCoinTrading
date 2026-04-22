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
            rsi_min=25.0,
            rsi_max=58.0,
            macd_histogram=-0.01,
            prev_macd_histogram=-0.02,
            allow_negative_macd=True,
            require_macd_recovering=True,
            macd_recovery_epsilon=0.0,
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
            rsi_min=40.0,
            rsi_max=58.0,
            macd_histogram=-0.01,
            prev_macd_histogram=-0.02,
            allow_negative_macd=True,
            require_macd_recovering=True,
            macd_recovery_epsilon=0.0,
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
            rsi_min=25.0,
            rsi_max=58.0,
            macd_histogram=-0.01,
            prev_macd_histogram=-0.02,
            allow_negative_macd=True,
            require_macd_recovering=True,
            macd_recovery_epsilon=0.0,
        )
        self.assertFalse(state["signal_is_strong"])
        self.assertFalse(state["entry_signal"])

    def test_worsening_macd_blocks_mean_reversion(self):
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
            rsi_min=25.0,
            rsi_max=58.0,
            macd_histogram=-0.03,
            prev_macd_histogram=-0.02,
            allow_negative_macd=True,
            require_macd_recovering=True,
            macd_recovery_epsilon=0.0,
        )
        self.assertFalse(state["macd_filter_passed"])
        self.assertFalse(state["entry_signal"])
