"""알트 신호 계산과 평균단가 추가매수 조건에 대한 개발 테스트."""

import unittest

from core.strategy.alt import compute_alt_signal_state, compute_can_average_down


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
