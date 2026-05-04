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

    def test_hot_atr_or_upper_range_blocks_mean_reversion(self):
        hot_atr = compute_bollinger_mean_reversion_state(
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
            atr_percentile=90.0,
            max_atr_percentile=80.0,
            range_position_pct=20.0,
            max_range_position_pct=35.0,
        )
        upper_range = compute_bollinger_mean_reversion_state(
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
            atr_percentile=60.0,
            max_atr_percentile=80.0,
            range_position_pct=55.0,
            max_range_position_pct=35.0,
        )

        self.assertFalse(hot_atr["atr_context_passed"])
        self.assertFalse(hot_atr["entry_signal"])
        self.assertFalse(upper_range["range_context_passed"])
        self.assertFalse(upper_range["entry_signal"])

    def test_negative_slope_high_volume_atr_near_low_blocks_mean_reversion(self):
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
            atr_percentile=65.0,
            max_atr_percentile=80.0,
            range_position_pct=20.0,
            max_range_position_pct=35.0,
            ma_slope_pct=-0.03,
            price_slope_pct=-0.11,
            volume_ratio=2.2,
            distance_from_recent_low_pct=0.05,
            high_volume_ratio=2.0,
            mid_atr_percentile=60.0,
            min_distance_from_low_pct=0.10,
        )

        self.assertTrue(state["falling_knife_blocked"])
        self.assertFalse(state["entry_signal"])

    def test_negative_slope_guard_waits_for_low_reclaim_distance(self):
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
            atr_percentile=65.0,
            max_atr_percentile=80.0,
            range_position_pct=20.0,
            max_range_position_pct=35.0,
            ma_slope_pct=-0.03,
            price_slope_pct=-0.11,
            volume_ratio=2.2,
            distance_from_recent_low_pct=0.20,
            high_volume_ratio=2.0,
            mid_atr_percentile=60.0,
            min_distance_from_low_pct=0.10,
        )

        self.assertFalse(state["falling_knife_blocked"])
        self.assertTrue(state["entry_signal"])
