"""업비트 웹소켓 수집기 런타임 설정 테스트."""

import os
import unittest
from unittest.mock import patch

from upbit_market_data_stream import build_runtime_settings


class UpbitMarketDataStreamSettingsTests(unittest.TestCase):
    def test_private_ws_idle_reconnect_is_disabled_by_default(self):
        with patch("upbit_market_data_stream.load_project_env", return_value=None), \
             patch.dict(os.environ, {}, clear=True):
            settings = build_runtime_settings()

        self.assertEqual(120.0, settings["max_idle_sec"])
        self.assertEqual(0.0, settings["private_max_idle_sec"])

    def test_private_ws_idle_reconnect_can_be_overridden(self):
        with patch("upbit_market_data_stream.load_project_env", return_value=None), \
             patch.dict(os.environ, {"UPBIT_PRIVATE_WS_MAX_IDLE_SEC": "900"}, clear=True):
            settings = build_runtime_settings()

        self.assertEqual(900.0, settings["private_max_idle_sec"])


if __name__ == "__main__":
    unittest.main()
