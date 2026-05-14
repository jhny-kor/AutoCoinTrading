"""
작업 요약
- BTC 공통 지표 helper 가 기존 실거래 봇의 계산 계약을 유지하는지 검증한다.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from core.strategy.btc_indicators import (
    build_exit_prices,
    calc_atr,
    calc_volume_ratio,
    detect_ema_crossover,
    get_recent_swing_high,
    get_recent_swing_low,
)


class BtcIndicatorTests(unittest.TestCase):
    def test_detect_ema_crossover_reports_bullish_cross(self) -> None:
        closes = [10.0, 10.0, 10.0, 9.0, 8.0, 8.0, 8.0, 12.0]

        bullish, bearish, prev_fast, prev_slow, last_fast, last_slow = detect_ema_crossover(
            closes,
            fast_period=2,
            slow_period=4,
        )

        self.assertTrue(bullish)
        self.assertFalse(bearish)
        self.assertLessEqual(prev_fast, prev_slow)
        self.assertGreater(last_fast, last_slow)

    def test_volume_ratio_uses_previous_completed_candle(self) -> None:
        ohlcv = [
            [0, 1, 2, 0.5, 1.2, 10.0],
            [1, 1, 2, 0.5, 1.2, 20.0],
            [2, 1, 2, 0.5, 1.2, 40.0],
            [3, 1, 2, 0.5, 1.2, 999.0],
        ]

        self.assertEqual(calc_volume_ratio(ohlcv, lookback=2), 40.0 / 15.0)

    def test_atr_swing_and_exit_price_contract(self) -> None:
        ohlcv = [
            [0, 10.0, 11.0, 9.5, 10.5, 1.0],
            [1, 10.5, 12.0, 10.0, 11.5, 1.0],
            [2, 11.5, 13.0, 11.0, 12.5, 1.0],
        ]
        settings = SimpleNamespace(
            stop_mode="atr",
            take_profit_mode="atr",
            stop_atr_multiple=1.5,
            take_profit_atr_multiple=1.0,
        )

        atr_value = calc_atr(ohlcv, period=2)
        stop_price, take_profit_price = build_exit_prices(
            entry_price=12.0,
            atr_value=atr_value,
            recent_swing_low=get_recent_swing_low(ohlcv, lookback=2),
            recent_swing_high=get_recent_swing_high(ohlcv, lookback=2),
            min_take_profit_pct=0.5,
            settings=settings,
        )

        self.assertAlmostEqual(atr_value, 2.0)
        self.assertAlmostEqual(stop_price, 9.0)
        self.assertAlmostEqual(take_profit_price, 14.0)


if __name__ == "__main__":
    unittest.main()
