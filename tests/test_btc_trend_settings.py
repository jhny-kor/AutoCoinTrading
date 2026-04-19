import os
import unittest
from unittest.mock import patch

from btc_trend_settings import load_btc_trend_settings


class BtcTrendSettingsTests(unittest.TestCase):
    def test_loads_symbol_specific_entry_confirmation_loops(self):
        with patch.dict(
            os.environ,
            {
                "BTC_TREND_ENTRY_CONFIRMATION_LOOPS": "3",
                "BTC_TREND_ENTRY_CONFIRMATION_LOOPS_MAP": "BTC/USDT:3,BTC/KRW:5",
            },
            clear=False,
        ):
            settings = load_btc_trend_settings()

        self.assertEqual(3, settings.get_entry_confirmation_loops("BTC/USDT"))
        self.assertEqual(5, settings.get_entry_confirmation_loops("BTC/KRW"))
        self.assertEqual(3, settings.get_entry_confirmation_loops("BTC/UNKNOWN"))

    def test_loads_atr_position_scale_thresholds(self):
        with patch.dict(
            os.environ,
            {
                "BTC_TREND_ENABLE_ATR_POSITION_SCALING": "true",
                "BTC_TREND_ATR_POSITION_SCALE_THRESHOLD_MAP": "0.16:0.80,0.13:0.60,0.10:0.35",
            },
            clear=False,
        ):
            settings = load_btc_trend_settings()

        self.assertTrue(settings.enable_atr_position_scaling)
        self.assertEqual(settings.get_atr_position_scale(0.20), 1.0)
        self.assertEqual(settings.get_atr_position_scale(0.15), 0.8)
        self.assertEqual(settings.get_atr_position_scale(0.12), 0.6)
        self.assertEqual(settings.get_atr_position_scale(0.09), 0.35)

    def test_loads_high_volume_atr_and_confirmation_overrides(self):
        with patch.dict(
            os.environ,
            {
                "BTC_TREND_HIGH_VOLUME_RATIO_THRESHOLD_MAP": "BTC/USDT:3.0,BTC/KRW:3.0",
                "BTC_TREND_HIGH_VOLUME_MIN_ATR_PCT_MAP": "BTC/USDT:0.16,BTC/KRW:0.14",
                "BTC_TREND_HIGH_VOLUME_EXTRA_CONFIRMATION_LOOPS_MAP": "BTC/KRW:1",
            },
            clear=False,
        ):
            settings = load_btc_trend_settings()

        self.assertEqual(3.0, settings.get_high_volume_ratio_threshold("BTC/USDT"))
        self.assertEqual(0.14, settings.get_high_volume_min_atr_pct("BTC/KRW"))
        self.assertEqual(1, settings.get_high_volume_extra_confirmation_loops("BTC/KRW"))
        self.assertEqual(0, settings.get_high_volume_extra_confirmation_loops("BTC/USDT"))

    def test_loads_okx_funding_rate_guard_settings(self):
        with patch.dict(
            os.environ,
            {
                "BTC_TREND_ENABLE_OKX_FUNDING_RATE_GUARD": "true",
                "BTC_TREND_OKX_FUNDING_RATE_MAX_LONG_BIAS": "0.0004",
                "BTC_TREND_OKX_FUNDING_RATE_CACHE_TTL_SEC": "180",
            },
            clear=False,
        ):
            settings = load_btc_trend_settings()

        self.assertTrue(settings.enable_okx_funding_rate_guard)
        self.assertEqual(0.0004, settings.okx_funding_rate_max_long_bias)
        self.assertEqual(180.0, settings.okx_funding_rate_cache_ttl_sec)


if __name__ == "__main__":
    unittest.main()
