import os
import unittest
from unittest.mock import patch

from strategy_settings import load_strategy_settings


class StrategySettingsTests(unittest.TestCase):
    def test_loads_alt_gap_and_volume_caps(self):
        with patch.dict(
            os.environ,
            {
                "STRATEGY_MAX_VOLUME_RATIO": "2.5",
                "STRATEGY_MAX_VOLUME_RATIO_MAP": "ETH/USDT:2.5,XRP/KRW:2.0",
                "STRATEGY_MAX_ENTRY_GAP_PCT": "0.25",
                "STRATEGY_MAX_ENTRY_GAP_PCT_MAP": "ETH/USDT:0.15,XRP/KRW:0.15",
            },
            clear=False,
        ):
            settings = load_strategy_settings("UPBIT_MIN_BUY_ORDER_VALUE", 5000)

        self.assertEqual(2.5, settings.get_max_volume_ratio("ETH/USDT"))
        self.assertEqual(2.0, settings.get_max_volume_ratio("XRP/KRW"))
        self.assertEqual(2.5, settings.get_max_volume_ratio("UNKNOWN"))
        self.assertEqual(0.15, settings.get_max_entry_gap_pct("ETH/USDT"))
        self.assertEqual(0.15, settings.get_max_entry_gap_pct("XRP/KRW"))
        self.assertEqual(0.25, settings.get_max_entry_gap_pct("UNKNOWN"))

    def test_loads_btc_regime_position_scale_map(self):
        with patch.dict(
            os.environ,
            {
                "STRATEGY_ENABLE_BTC_REGIME_POSITION_SCALING": "true",
                "STRATEGY_BTC_REGIME_POSITION_SCALE_MAP": "LOW_ENERGY:0.50,CHOPPY:0.80",
                "STRATEGY_BTC_REGIME_POSITION_SCALE_OVERRIDE_MAP": (
                    "ETH/KRW|LOW_ENERGY:0.35,XRP/KRW|LOW_ENERGY:0.60"
                ),
                "STRATEGY_ENABLE_BTC_ATR_POSITION_SCALING": "true",
                "STRATEGY_BTC_ATR_POSITION_SCALE_THRESHOLD_MAP": (
                    "0.18:0.70,0.15:0.45,0.12:0.25"
                ),
            },
            clear=False,
        ):
            settings = load_strategy_settings("UPBIT_MIN_BUY_ORDER_VALUE", 5000)

        self.assertTrue(settings.enable_btc_regime_position_scaling)
        self.assertEqual(settings.get_btc_regime_position_scale("LOW_ENERGY"), 0.5)
        self.assertEqual(settings.get_btc_regime_position_scale("CHOPPY"), 0.8)
        self.assertEqual(settings.get_btc_regime_position_scale("TRENDING"), 1.0)
        self.assertEqual(
            settings.get_btc_regime_position_scale_for_symbol("ETH/KRW", "LOW_ENERGY"),
            0.35,
        )
        self.assertEqual(
            settings.get_btc_regime_position_scale_for_symbol("XRP/KRW", "LOW_ENERGY"),
            0.6,
        )
        self.assertEqual(
            settings.get_btc_regime_position_scale_for_symbol("ETH/KRW", "CHOPPY"),
            0.8,
        )
        self.assertEqual(settings.get_btc_atr_position_scale(0.20), 1.0)
        self.assertEqual(settings.get_btc_atr_position_scale(0.17), 0.7)
        self.assertEqual(settings.get_btc_atr_position_scale(0.14), 0.45)
        self.assertEqual(settings.get_btc_atr_position_scale(0.10), 0.25)

    def test_loads_symbol_specific_signal_score_min(self):
        with patch.dict(
            os.environ,
            {
                "STRATEGY_SIGNAL_SCORE_MIN": "55",
                "STRATEGY_SIGNAL_SCORE_MIN_MAP": "ETH/KRW:80",
            },
            clear=False,
        ):
            settings = load_strategy_settings("UPBIT_MIN_BUY_ORDER_VALUE", 5000)

        self.assertEqual(80, settings.get_signal_score_min("ETH/KRW"))
        self.assertEqual(55, settings.get_signal_score_min("XRP/KRW"))


if __name__ == "__main__":
    unittest.main()
