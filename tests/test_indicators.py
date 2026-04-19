"""공통 보조지표 helper 에 대한 개발 테스트."""

import unittest

from core.strategy.indicators import calc_noise_ratio, calc_weighted_signal_score


class IndicatorTests(unittest.TestCase):
    def test_noise_ratio_averages_recent_completed_candles(self):
        ohlcv = [
            [0, 100.0, 110.0, 90.0, 108.0, 1.0],
            [1, 108.0, 112.0, 104.0, 110.0, 1.0],
            [2, 110.0, 118.0, 109.0, 111.0, 1.0],
            [3, 111.0, 119.0, 110.0, 118.0, 1.0],
        ]
        noise_ratio = calc_noise_ratio(ohlcv, 3)
        self.assertIsNotNone(noise_ratio)
        self.assertGreater(noise_ratio, 0.0)
        self.assertLess(noise_ratio, 1.0)

    def test_weighted_signal_score_normalizes_weights(self):
        score = calc_weighted_signal_score(
            {"slope": 80.0, "trend": 40.0},
            {"slope": 4.0, "trend": 1.0},
        )
        self.assertAlmostEqual(score, 72.0)


if __name__ == "__main__":
    unittest.main()
