"""알트 신호 계산, 평균단가 추가매수, 손절 후 패턴 재진입 gate 테스트."""

import unittest

from core.strategy.alt import (
    compute_alt_signal_state,
    compute_can_average_down,
    compute_alt_stop_loss_reentry_gate,
)


class AltSignalTests(unittest.TestCase):
    def test_bullish_crossover_sets_entry_signal(self):
        state = compute_alt_signal_state(
            prev_close=99.0,
            prev_ma=100.0,
            last_close=101.0,
            last_ma=100.0,
            min_gap_pct=0.5,
            enable_trend_follow_entry=True,
            require_prev_above_ma=True,
            require_price_rising=True,
            require_ma_slope_positive=True,
            volume_ratio=1.8,
            min_volume_ratio=1.2,
            rsi_value=55.0,
            enable_rsi_filter=True,
            rsi_entry_min=40.0,
            rsi_entry_max=70.0,
            macd_histogram=0.2,
            enable_macd_filter=True,
            ma_slope_pct=0.4,
            price_slope_pct=0.8,
            signal_score_min=55.0,
        )
        self.assertTrue(state["bullish"])
        self.assertTrue(state["entry_signal"])
        self.assertTrue(state["signal_is_strong"])
        self.assertGreaterEqual(state["signal_score"], 55.0)

    def test_trend_follow_entry_works_without_fresh_cross(self):
        state = compute_alt_signal_state(
            prev_close=101.0,
            prev_ma=100.0,
            last_close=102.0,
            last_ma=100.5,
            min_gap_pct=1.0,
            enable_trend_follow_entry=True,
            require_prev_above_ma=True,
            require_price_rising=True,
            require_ma_slope_positive=True,
            volume_ratio=1.5,
            min_volume_ratio=1.2,
            rsi_value=58.0,
            enable_rsi_filter=True,
            rsi_entry_min=40.0,
            rsi_entry_max=70.0,
            macd_histogram=0.1,
            enable_macd_filter=True,
            ma_slope_pct=0.2,
            price_slope_pct=0.5,
            signal_score_min=40.0,
        )
        self.assertFalse(state["bullish"])
        self.assertTrue(state["trend_follow_entry"])
        self.assertTrue(state["entry_signal"])

    def test_rsi_filter_blocks_entry_when_out_of_band(self):
        state = compute_alt_signal_state(
            prev_close=99.0,
            prev_ma=100.0,
            last_close=101.0,
            last_ma=100.0,
            min_gap_pct=0.5,
            enable_trend_follow_entry=True,
            require_prev_above_ma=True,
            require_price_rising=True,
            require_ma_slope_positive=True,
            volume_ratio=2.0,
            min_volume_ratio=1.0,
            rsi_value=78.0,
            enable_rsi_filter=True,
            rsi_entry_min=40.0,
            rsi_entry_max=70.0,
            macd_histogram=0.2,
            enable_macd_filter=True,
            ma_slope_pct=0.6,
            price_slope_pct=0.9,
            signal_score_min=40.0,
        )
        self.assertFalse(state["rsi_filter_passed"])
        self.assertFalse(state["entry_signal"])

    def test_average_down_gate_blocks_when_price_not_low_enough(self):
        self.assertFalse(
            compute_can_average_down(
                has_position=True,
                average_entry_price=100.0,
                last_close=99.0,
                averaging_down_gap_pct=2.0,
            )
        )

    def test_stop_loss_pattern_reentry_requires_recovery_conditions(self):
        blocked = compute_alt_stop_loss_reentry_gate(
            enabled=True,
            elapsed_since_stop_loss_sec=120,
            min_cooldown_sec=180,
            entry_signal=True,
            bullish=False,
            signal_score=65.0,
            min_signal_score=70.0,
            volume_ratio=1.0,
            min_volume_ratio=1.0,
            min_volume_ratio_multiplier=1.2,
            htf_bullish=False,
            require_htf_bullish=True,
            require_fresh_cross=True,
        )
        self.assertFalse(blocked["pattern_ready"])

        ready = compute_alt_stop_loss_reentry_gate(
            enabled=True,
            elapsed_since_stop_loss_sec=240,
            min_cooldown_sec=180,
            entry_signal=True,
            bullish=True,
            signal_score=75.0,
            min_signal_score=70.0,
            volume_ratio=1.4,
            min_volume_ratio=1.0,
            min_volume_ratio_multiplier=1.2,
            htf_bullish=True,
            require_htf_bullish=True,
            require_fresh_cross=True,
        )
        self.assertTrue(ready["pattern_ready"])
        self.assertTrue(
            compute_can_average_down(
                has_position=True,
                average_entry_price=100.0,
                last_close=98.0,
                averaging_down_gap_pct=2.0,
            )
        )


if __name__ == "__main__":
    unittest.main()
