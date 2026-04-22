import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from settings.strategy_settings import _build_symbol_auto_tune_adjustment_map
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

    def test_auto_tune_adjustment_map_uses_recent_final_exits(self):
        with TemporaryDirectory() as tmp_dir:
            trade_path = Path(tmp_dir) / "trade_history.jsonl"
            trade_path.write_text(
                "\n".join(
                    [
                        '{"recorded_at_local":"2026-04-18T10:00:00+09:00","symbol":"ETH/KRW","is_final_exit":true,"net_realized_pnl_quote":100}',
                        '{"recorded_at_local":"2026-04-18T11:00:00+09:00","symbol":"ETH/KRW","is_final_exit":true,"net_realized_pnl_quote":80}',
                        '{"recorded_at_local":"2026-04-18T12:00:00+09:00","symbol":"XRP/KRW","is_final_exit":true,"net_realized_pnl_quote":-50}',
                        '{"recorded_at_local":"2026-04-18T13:00:00+09:00","symbol":"XRP/KRW","is_final_exit":true,"net_realized_pnl_quote":-20}',
                    ]
                ),
                encoding="utf-8",
            )
            with patch("settings.strategy_settings.Path.rglob", return_value=[trade_path]):
                adjustments = _build_symbol_auto_tune_adjustment_map(
                    window_days=7,
                    min_trades=2,
                    positive_win_rate=0.6,
                    positive_profit_factor=1.3,
                    negative_win_rate=0.4,
                    negative_profit_factor=0.9,
                    adjustment_limit_pct=0.1,
                )

        self.assertEqual(0.1, adjustments["ETH/KRW"])
        self.assertEqual(-0.1, adjustments["XRP/KRW"])

    def test_loads_okx_funding_rate_guard_settings(self):
        with patch.dict(
            os.environ,
            {
                "STRATEGY_ENABLE_OKX_FUNDING_RATE_GUARD": "true",
                "STRATEGY_OKX_FUNDING_RATE_MAX_LONG_BIAS": "0.0004",
                "STRATEGY_OKX_FUNDING_RATE_CACHE_TTL_SEC": "180",
            },
            clear=False,
        ):
            settings = load_strategy_settings("UPBIT_MIN_BUY_ORDER_VALUE", 5000)

        self.assertTrue(settings.enable_okx_funding_rate_guard)
        self.assertEqual(0.0004, settings.okx_funding_rate_max_long_bias)
        self.assertEqual(180.0, settings.okx_funding_rate_cache_ttl_sec)

    def test_loads_alt_atr_position_sizing_settings(self):
        with patch.dict(
            os.environ,
            {
                "STRATEGY_ENABLE_ALT_ATR_POSITION_SIZING": "true",
                "STRATEGY_ALT_ATR_POSITION_SCALE_THRESHOLD_MAP": "0.12:1.10,0.20:0.90,0.35:0.65",
            },
            clear=False,
        ):
            settings = load_strategy_settings("UPBIT_MIN_BUY_ORDER_VALUE", 5000)

        self.assertTrue(settings.enable_alt_atr_position_sizing)
        self.assertEqual(1.10, settings.get_alt_atr_position_scale(0.10))
        self.assertEqual(0.90, settings.get_alt_atr_position_scale(0.18))
        self.assertEqual(0.65, settings.get_alt_atr_position_scale(0.30))

    def test_loads_mean_reversion_filter_settings(self):
        with patch.dict(
            os.environ,
            {
                "STRATEGY_MEAN_REVERSION_RSI_MIN": "25",
                "STRATEGY_MEAN_REVERSION_RSI_MAX": "58",
                "STRATEGY_MEAN_REVERSION_ALLOW_NEGATIVE_MACD": "true",
                "STRATEGY_MEAN_REVERSION_REQUIRE_MACD_RECOVERING": "true",
                "STRATEGY_MEAN_REVERSION_MACD_RECOVERY_EPSILON": "0.001",
            },
            clear=False,
        ):
            settings = load_strategy_settings("UPBIT_MIN_BUY_ORDER_VALUE", 5000)

        self.assertEqual(25, settings.mean_reversion_rsi_min)
        self.assertEqual(58, settings.mean_reversion_rsi_max)
        self.assertTrue(settings.mean_reversion_allow_negative_macd)
        self.assertTrue(settings.mean_reversion_require_macd_recovering)
        self.assertEqual(0.001, settings.mean_reversion_macd_recovery_epsilon)


if __name__ == "__main__":
    unittest.main()
