"""미등록 심볼 후보 Sharpe 랭킹 테스트."""

import unittest

from tools.discover_untracked_symbols import calc_sharpe_score_from_ohlcv


class DiscoverSymbolsTests(unittest.TestCase):
    def test_calc_sharpe_score_from_ohlcv_returns_positive_for_uptrend(self):
        ohlcv = [
            [0, 100.0, 101.0, 99.0, 100.0, 1.0],
            [1, 100.0, 103.0, 99.5, 102.0, 1.0],
            [2, 102.0, 106.0, 101.0, 105.0, 1.0],
            [3, 105.0, 109.0, 104.0, 108.0, 1.0],
        ]
        score = calc_sharpe_score_from_ohlcv(ohlcv)
        self.assertIsNotNone(score)
        self.assertGreater(score, 0.0)
