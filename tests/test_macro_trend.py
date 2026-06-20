"""매크로 추세 게이트 단위 테스트."""

import unittest

from core.strategy.macro_trend import compute_macro_trend_gate


class MacroTrendGateTests(unittest.TestCase):
    def test_disabled_passes(self):
        passed, ema = compute_macro_trend_gate([1, 2, 3], period=2, enabled=False)
        self.assertTrue(passed)
        self.assertIsNone(ema)

    def test_insufficient_data_passes_failopen(self):
        passed, ema = compute_macro_trend_gate([1, 2], period=10, enabled=True)
        self.assertTrue(passed)
        self.assertIsNone(ema)

    def test_above_macro_ema_passes(self):
        closes = [10.0] * 40 + [12.0]  # last close clearly above the EMA
        passed, ema = compute_macro_trend_gate(closes, period=40, enabled=True)
        self.assertTrue(passed)
        self.assertIsNotNone(ema)
        self.assertGreater(closes[-1], ema)

    def test_below_macro_ema_blocks(self):
        closes = [10.0] * 40 + [8.0]  # last close clearly below the EMA
        passed, ema = compute_macro_trend_gate(closes, period=40, enabled=True)
        self.assertFalse(passed)
        self.assertLess(closes[-1], ema)

    def test_zero_period_passes(self):
        passed, ema = compute_macro_trend_gate([1, 2, 3], period=0, enabled=True)
        self.assertTrue(passed)
        self.assertIsNone(ema)


if __name__ == "__main__":
    unittest.main()
