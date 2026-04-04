import os
import unittest
from unittest.mock import patch

from btc_trend_settings import load_btc_trend_settings


class BtcTrendSettingsTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
