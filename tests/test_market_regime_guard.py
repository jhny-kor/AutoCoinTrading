"""8단계 보수형 레짐 분류와 BTC 레짐 정책에 대한 개발 테스트."""

import os
import unittest
from unittest.mock import patch

from market_regime_guard import (
    classify_symbol_regime,
    get_btc_regime_policy,
    load_low_energy_guard_settings,
)


class MarketRegimeGuardTests(unittest.TestCase):
    def test_classifies_trending_early(self):
        snapshot = classify_symbol_regime(
            {
                "volume_ratio": 1.05,
                "avg_abs_change_pct": 0.10,
                "gap_pct": 0.10,
                "rsi": 62.0,
                "adx": 31.0,
                "public_buy_ready": False,
                "bullish_signal": False,
                "bearish_signal": False,
                "above_ma": True,
                "htf_bullish": True,
            }
        )
        self.assertEqual("TRENDING_EARLY", snapshot.regime)

    def test_classifies_trending_mature(self):
        snapshot = classify_symbol_regime(
            {
                "volume_ratio": 2.2,
                "avg_abs_change_pct": 0.18,
                "gap_pct": 0.25,
                "rsi": 78.0,
                "adx": 35.0,
                "public_buy_ready": True,
                "bullish_signal": True,
                "bearish_signal": False,
                "above_ma": True,
                "htf_bullish": True,
            }
        )
        self.assertEqual("TRENDING_MATURE", snapshot.regime)

    def test_classifies_choppy_low_and_high_vol(self):
        low_vol = classify_symbol_regime(
            {
                "volume_ratio": 0.95,
                "avg_abs_change_pct": 0.03,
                "gap_pct": 0.04,
                "rsi": 50.0,
                "adx": 15.0,
                "public_buy_ready": False,
                "bullish_signal": False,
                "bearish_signal": False,
                "above_ma": False,
                "htf_bullish": False,
            }
        )
        high_vol = classify_symbol_regime(
            {
                "volume_ratio": 1.4,
                "avg_abs_change_pct": 0.12,
                "gap_pct": 0.05,
                "rsi": 55.0,
                "adx": 18.0,
                "public_buy_ready": False,
                "bullish_signal": False,
                "bearish_signal": False,
                "above_ma": True,
                "htf_bullish": False,
            }
        )
        self.assertEqual("CHOPPY_LOW_VOL", low_vol.regime)
        self.assertEqual("CHOPPY_HIGH_VOL", high_vol.regime)

    def test_btc_policy_disables_trend_follow_and_pyramiding_in_choppy_high_vol(self):
        policy = get_btc_regime_policy("CHOPPY_HIGH_VOL")
        self.assertEqual(4, policy.required_confirmation_loops)
        self.assertFalse(policy.allow_trend_follow_entry)
        self.assertFalse(policy.allow_pyramiding)

    def test_loads_upbit_specific_low_energy_thresholds(self):
        with patch.dict(
            os.environ,
            {
                "MARKET_GUARD_LOW_ENERGY_AVG_VOLUME_RATIO": "0.80",
                "MARKET_GUARD_LOW_ENERGY_AVG_ABS_CHANGE_PCT": "0.05",
                "MARKET_GUARD_LOW_ENERGY_AVG_VOLUME_RATIO_UPBIT": "0.40",
                "MARKET_GUARD_LOW_ENERGY_AVG_ABS_CHANGE_PCT_UPBIT": "0.018",
            },
            clear=False,
        ):
            settings = load_low_energy_guard_settings()

        self.assertEqual(0.80, settings.get_avg_volume_ratio_threshold("okx"))
        self.assertEqual(0.40, settings.get_avg_volume_ratio_threshold("upbit"))
        self.assertEqual(0.05, settings.get_avg_abs_change_pct_threshold("okx"))
        self.assertEqual(0.018, settings.get_avg_abs_change_pct_threshold("upbit"))


if __name__ == "__main__":
    unittest.main()
