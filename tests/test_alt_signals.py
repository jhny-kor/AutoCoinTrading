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
        )
        self.assertTrue(state["bullish"])
        self.assertTrue(state["entry_signal"])
        self.assertTrue(state["signal_is_strong"])

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
        )
        self.assertFalse(state["bullish"])
        self.assertTrue(state["trend_follow_entry"])
        self.assertTrue(state["entry_signal"])

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
