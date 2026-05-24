"""전략 설정 로딩 테스트.

수정 요약
- 2026-05-24: 자동 튜닝 테스트가 현재 날짜 변화에 깨지지 않도록 최근 시각을 동적으로 만들도록 보정했다.
"""

import json
import os
from datetime import datetime, timedelta
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

    def test_loads_volume_spike_entry_downgrade_settings(self):
        with patch.dict(
            os.environ,
            {
                "STRATEGY_ENABLE_VOLUME_SPIKE_ENTRY_DOWNGRADE": "true",
                "STRATEGY_VOLUME_SPIKE_ENTRY_DOWNGRADE_SYMBOLS": "ETH/KRW,XRP/KRW",
                "STRATEGY_VOLUME_SPIKE_ENTRY_MIN_SIGNAL_SCORE": "85",
                "STRATEGY_VOLUME_SPIKE_ENTRY_MIN_ORDERBOOK_PRESSURE_SCORE": "65",
                "STRATEGY_VOLUME_SPIKE_ENTRY_MAX_ATR_PERCENTILE": "60",
                "STRATEGY_VOLUME_SPIKE_ENTRY_HARD_MAX_VOLUME_RATIO": "30",
                "STRATEGY_VOLUME_SPIKE_ENTRY_POSITION_SCALE": "0.25",
                "STRATEGY_VOLUME_SPIKE_ENTRY_EXTRA_CONFIRMATION_LOOPS": "2",
                "STRATEGY_VOLUME_SPIKE_ENTRY_REQUIRE_HTF_BULLISH": "true",
            },
            clear=False,
        ):
            settings = load_strategy_settings("UPBIT_MIN_BUY_ORDER_VALUE", 5000)

        self.assertTrue(settings.enable_volume_spike_entry_downgrade)
        self.assertTrue(settings.allows_volume_spike_entry_downgrade("ETH/KRW"))
        self.assertTrue(settings.allows_volume_spike_entry_downgrade("XRP/KRW"))
        self.assertFalse(settings.allows_volume_spike_entry_downgrade("SOL/KRW"))
        self.assertEqual(85, settings.volume_spike_entry_min_signal_score)
        self.assertEqual(65, settings.volume_spike_entry_min_orderbook_pressure_score)
        self.assertEqual(60, settings.volume_spike_entry_max_atr_percentile)
        self.assertEqual(30, settings.volume_spike_entry_hard_max_volume_ratio)
        self.assertEqual(0.25, settings.volume_spike_entry_position_scale)
        self.assertEqual(2, settings.volume_spike_entry_extra_confirmation_loops)
        self.assertTrue(settings.volume_spike_entry_require_htf_bullish)

    def test_loads_sol_probe_settings(self):
        with patch.dict(
            os.environ,
            {
                "STRATEGY_ENABLE_SOL_PROBE": "true",
                "STRATEGY_SOL_PROBE_SYMBOLS": "SOL/USDT,SOL/KRW",
                "STRATEGY_SOL_PROBE_MIN_SIGNAL_SCORE": "70",
                "STRATEGY_SOL_PROBE_POSITION_SCALE": "0.25",
                "STRATEGY_SOL_PROBE_TAKE_PROFIT_PCT": "0.8",
                "STRATEGY_SOL_PROBE_STOP_LOSS_PCT": "0.5",
                "STRATEGY_SOL_PROBE_MAX_HOLD_MINUTES": "180",
            },
            clear=False,
        ):
            settings = load_strategy_settings("UPBIT_MIN_BUY_ORDER_VALUE", 5000)

        self.assertTrue(settings.enable_sol_probe)
        self.assertTrue(settings.allows_sol_probe("SOL/USDT"))
        self.assertTrue(settings.allows_sol_probe("SOL/KRW"))
        self.assertFalse(settings.allows_sol_probe("XRP/KRW"))
        self.assertEqual(70, settings.sol_probe_min_signal_score)
        self.assertEqual(0.25, settings.sol_probe_position_scale)
        self.assertEqual(0.8, settings.sol_probe_take_profit_pct)
        self.assertEqual(0.5, settings.sol_probe_stop_loss_pct)
        self.assertEqual(180, settings.sol_probe_max_hold_minutes)

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
            now = datetime.now().astimezone().replace(microsecond=0)
            records = [
                {
                    "recorded_at_local": (now - timedelta(hours=4)).isoformat(),
                    "symbol": "ETH/KRW",
                    "is_final_exit": True,
                    "net_realized_pnl_quote": 100,
                },
                {
                    "recorded_at_local": (now - timedelta(hours=3)).isoformat(),
                    "symbol": "ETH/KRW",
                    "is_final_exit": True,
                    "net_realized_pnl_quote": 80,
                },
                {
                    "recorded_at_local": (now - timedelta(hours=2)).isoformat(),
                    "symbol": "XRP/KRW",
                    "is_final_exit": True,
                    "net_realized_pnl_quote": -50,
                },
                {
                    "recorded_at_local": (now - timedelta(hours=1)).isoformat(),
                    "symbol": "XRP/KRW",
                    "is_final_exit": True,
                    "net_realized_pnl_quote": -20,
                },
            ]
            trade_path.write_text(
                "\n".join(json.dumps(record, ensure_ascii=False) for record in records),
                encoding="utf-8",
            )
            with patch("settings.strategy_settings.Path.rglob", return_value=[trade_path]):
                adjustments = _build_symbol_auto_tune_adjustment_map(
                    window_days=30,
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
                "STRATEGY_MEAN_REVERSION_MAX_ATR_PERCENTILE": "80",
                "STRATEGY_MEAN_REVERSION_MAX_RANGE_POSITION_PCT": "35",
                "STRATEGY_MEAN_REVERSION_BLOCK_NEGATIVE_SLOPE_HIGH_VOLUME_ATR": "true",
                "STRATEGY_MEAN_REVERSION_NEGATIVE_SLOPE_THRESHOLD_PCT": "0.0",
                "STRATEGY_MEAN_REVERSION_HIGH_VOLUME_RATIO": "2.0",
                "STRATEGY_MEAN_REVERSION_MID_ATR_PERCENTILE": "60",
                "STRATEGY_MEAN_REVERSION_MIN_DISTANCE_FROM_LOW_PCT": "0.10",
                "STRATEGY_ENABLE_MEAN_REVERSION_LOWER_NEAR_PROBE": "true",
                "STRATEGY_MEAN_REVERSION_LOWER_NEAR_MAX_DISTANCE_PCT": "0.12",
                "STRATEGY_MEAN_REVERSION_LOWER_NEAR_MIN_HEADROOM_PCT": "0.12",
                "STRATEGY_MEAN_REVERSION_LOWER_NEAR_MIN_SIGNAL_SCORE": "40",
                "STRATEGY_MEAN_REVERSION_LOWER_NEAR_POSITION_SCALE": "0.25",
                "STRATEGY_MEAN_REVERSION_LOWER_NEAR_EXTRA_CONFIRMATION_LOOPS": "2",
                "STRATEGY_ENABLE_XRP_REBOUND_PROBE": "true",
                "STRATEGY_XRP_REBOUND_PROBE_SYMBOLS": "XRP/KRW",
                "STRATEGY_XRP_REBOUND_PROBE_MIN_SIGNAL_SCORE": "70",
                "STRATEGY_XRP_REBOUND_PROBE_POSITION_SCALE": "0.25",
                "STRATEGY_XRP_REBOUND_PROBE_EXTRA_CONFIRMATION_LOOPS": "3",
                "STRATEGY_OVERHEAT_GUARD_VOLUME_RATIO": "2.0",
                "STRATEGY_OVERHEAT_GUARD_ATR_PERCENTILE": "85",
                "STRATEGY_OVERHEAT_GUARD_RSI": "68",
                "STRATEGY_OVERHEAT_EXTRA_CONFIRMATION_LOOPS": "1",
                "STRATEGY_ENABLE_COMBINED_STOP_LOSS_GUARDS": "true",
                "STRATEGY_BTC_CORRELATION_VOLATILITY_RISKY_REGIMES": "LOW_ENERGY,OVERHEATED",
                "STRATEGY_BTC_CORRELATION_VOLATILITY_MIN_CORR": "0.75",
                "STRATEGY_BTC_CORRELATION_VOLATILITY_MIN_ATR_PERCENTILE": "70",
                "STRATEGY_VOLUME_ATR_EXECUTION_GUARD_VOLUME_RATIO": "2.0",
                "STRATEGY_VOLUME_ATR_EXECUTION_GUARD_ATR_PERCENTILE": "80",
                "STRATEGY_VOLUME_ATR_EXECUTION_MIN_FILL_RATIO": "0.98",
                "STRATEGY_VOLUME_ATR_EXECUTION_MIN_FILL_SAMPLES": "1",
                "STRATEGY_VOLUME_ATR_EXECUTION_MIN_ORDERBOOK_PRESSURE_SCORE": "45",
                "STRATEGY_STOP_LOSS_CONTEXT_REENTRY_COOLDOWN_SEC": "3600",
                "STRATEGY_STOP_LOSS_CONTEXT_MIN_SIMILARITY_COUNT": "3",
                "STRATEGY_STOP_LOSS_CONTEXT_EXTRA_CONFIRMATION_LOOPS": "2",
            },
            clear=False,
        ):
            settings = load_strategy_settings("UPBIT_MIN_BUY_ORDER_VALUE", 5000)

        self.assertEqual(25, settings.mean_reversion_rsi_min)
        self.assertEqual(58, settings.mean_reversion_rsi_max)
        self.assertTrue(settings.mean_reversion_allow_negative_macd)
        self.assertTrue(settings.mean_reversion_require_macd_recovering)
        self.assertEqual(0.001, settings.mean_reversion_macd_recovery_epsilon)
        self.assertEqual(80, settings.mean_reversion_max_atr_percentile)
        self.assertEqual(35, settings.mean_reversion_max_range_position_pct)
        self.assertTrue(settings.mean_reversion_block_negative_slope_high_volume_atr)
        self.assertEqual(0.0, settings.mean_reversion_negative_slope_threshold_pct)
        self.assertEqual(2.0, settings.mean_reversion_high_volume_ratio)
        self.assertEqual(60, settings.mean_reversion_mid_atr_percentile)
        self.assertEqual(0.10, settings.mean_reversion_min_distance_from_low_pct)
        self.assertTrue(settings.enable_mean_reversion_lower_near_probe)
        self.assertEqual(0.12, settings.mean_reversion_lower_near_max_distance_pct)
        self.assertEqual(0.12, settings.mean_reversion_lower_near_min_headroom_pct)
        self.assertEqual(40, settings.mean_reversion_lower_near_min_signal_score)
        self.assertEqual(0.25, settings.mean_reversion_lower_near_position_scale)
        self.assertEqual(2, settings.mean_reversion_lower_near_extra_confirmation_loops)
        self.assertTrue(settings.enable_xrp_rebound_probe)
        self.assertEqual(("XRP/KRW",), settings.xrp_rebound_probe_symbols)
        self.assertEqual(70, settings.xrp_rebound_probe_min_signal_score)
        self.assertEqual(0.25, settings.xrp_rebound_probe_position_scale)
        self.assertEqual(3, settings.xrp_rebound_probe_extra_confirmation_loops)
        self.assertTrue(settings.allows_xrp_rebound_probe("XRP/KRW"))
        self.assertEqual(2.0, settings.overheat_guard_volume_ratio)
        self.assertEqual(85, settings.overheat_guard_atr_percentile)
        self.assertEqual(68, settings.overheat_guard_rsi)
        self.assertEqual(1, settings.overheat_extra_confirmation_loops)
        self.assertTrue(settings.enable_combined_stop_loss_guards)
        self.assertEqual(("LOW_ENERGY", "OVERHEATED"), settings.btc_correlation_volatility_risky_regimes)
        self.assertEqual(0.75, settings.btc_correlation_volatility_min_corr)
        self.assertEqual(70, settings.btc_correlation_volatility_min_atr_percentile)
        self.assertEqual(2.0, settings.volume_atr_execution_guard_volume_ratio)
        self.assertEqual(80, settings.volume_atr_execution_guard_atr_percentile)
        self.assertEqual(0.98, settings.volume_atr_execution_min_fill_ratio)
        self.assertEqual(1, settings.volume_atr_execution_min_fill_samples)
        self.assertEqual(45, settings.volume_atr_execution_min_orderbook_pressure_score)
        self.assertEqual(3600, settings.stop_loss_context_reentry_cooldown_sec)
        self.assertEqual(3, settings.stop_loss_context_min_similarity_count)
        self.assertEqual(2, settings.stop_loss_context_extra_confirmation_loops)


if __name__ == "__main__":
    unittest.main()
