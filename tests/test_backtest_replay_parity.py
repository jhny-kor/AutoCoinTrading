"""
수정 요약
- 리플레이가 probe 비중과 XRP lower-near 억제 결과를 실제 진입 계산에 전달하는지 검증한다.
- 백테스트 진입 경로가 실시간 공통 helper 를 재사용하는지 검증한다.
"""

from __future__ import annotations

import unittest
from contextlib import ExitStack
from dataclasses import replace
from unittest.mock import patch

from core.risk.allocation import build_alt_position_sizing
from core.strategy.low_energy import LowEnergyProbeDecision
from core.strategy.regime_router import StrategyRoute, route_alt_strategy
from core.strategy.sol_probe import SolProbeDecision, SolProbeEntryState
from core.strategy.timing import update_entry_timing_state
from core.strategy.xrp_rebound_probe import XrpReboundProbeDecision, XrpReboundProbeState
from market_regime_guard import get_alt_regime_policy
from strategy_settings import load_strategy_settings
from tools.backtest_models import Candle, ExecutionModel
from tools.backtest_replay import build_replay_entry_metadata, simulate_alt_strategy


class BacktestReplayParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candles = [
            Candle(1_700_000_000_000 + index * 60_000, 100.0, 101.0, 99.0, 100.0, 1_000.0)
            for index in range(100)
        ]
        self.execution = ExecutionModel(0.0, 1.0, 1.0, 0)
        self.signal_state = {
            "bullish": True,
            "bearish": False,
            "prev_close": 100.0,
            "prev_ma": 100.0,
            "last_close": 100.0,
            "last_ma": 100.0,
            "gap_pct": 0.2,
            "signal_is_strong": True,
            "signal_score": 80.0,
            "rsi_filter_passed": True,
            "macd_filter_passed": True,
            "trend_follow_entry": False,
            "entry_signal": True,
        }

    def _run(self, symbol: str = "XRP/KRW", settings_overrides=None, **patches):
        settings = replace(
            load_strategy_settings("TEST_MIN_ORDER", 1.0),
            **(settings_overrides or {}),
        )
        with ExitStack() as stack:
            stack.enter_context(patch("tools.backtest_replay.load_strategy_settings", return_value=settings))
            stack.enter_context(patch("tools.backtest_replay.compute_alt_signal_state", return_value=self.signal_state))
            for name, value in patches.items():
                stack.enter_context(patch(f"tools.backtest_replay.{name}", value))
            return simulate_alt_strategy(
                candles=self.candles,
                btc_reference_candles=None,
                source_timeframe="1m",
                symbol=symbol,
                exchange_name="upbit",
                initial_cash=100_000.0,
                fee_rate_pct=0.05,
                risk_per_trade=0.05,
                min_buy_order_value=1.0,
                max_daily_loss_quote=5_000.0,
                execution_model=self.execution,
            )

    def test_symbol_score_map_and_macro_gate_are_replayed(self):
        settings = load_strategy_settings("TEST_MIN_ORDER", 1.0)
        with patch("tools.backtest_replay.load_strategy_settings", return_value=settings), patch(
            "tools.backtest_replay.compute_alt_signal_state", return_value=self.signal_state
        ) as signal, patch(
            "tools.backtest_replay.compute_macro_trend_gate", return_value=(False, 99.0)
        ) as macro:
            summary, trades, _ = simulate_alt_strategy(
                candles=self.candles,
                btc_reference_candles=None,
                source_timeframe="1m",
                symbol="XRP/KRW",
                exchange_name="upbit",
                initial_cash=100_000.0,
                fee_rate_pct=0.05,
                risk_per_trade=0.05,
                min_buy_order_value=5_000.0,
                max_daily_loss_quote=5_000.0,
                execution_model=self.execution,
            )
        self.assertEqual(settings.get_signal_score_min("XRP/KRW"), signal.call_args.kwargs["signal_score_min"])
        self.assertTrue(macro.called)
        self.assertFalse(trades)
        self.assertFalse(summary["orderbook_funding_live_snapshot_available"])

    def test_route_and_mean_reversion_helper_are_used(self):
        route = route_alt_strategy("CHOPPY_LOW_VOL")
        mean_state = dict(self.signal_state)
        mean_state.update({"lower_reclaim_confirmed": True, "falling_knife_blocked": False})
        with patch("tools.backtest_replay.route_alt_strategy", return_value=route) as routed, patch(
            "tools.backtest_replay.compute_bollinger_mean_reversion_state", return_value=mean_state
        ) as mean:
            self._run()
        self.assertTrue(routed.called)
        self.assertTrue(mean.called)
        self.assertEqual("mean_reversion", route.strategy_key)

    def test_skip_route_cannot_create_candidate(self):
        route = StrategyRoute("OVERHEATED", "skip", get_alt_regime_policy("OVERHEATED"))
        with patch("tools.backtest_replay.route_alt_strategy", return_value=route):
            _summary, trades, _ = self._run()
        self.assertFalse(trades)

    def test_confirmation_metadata_declares_closed_candle_boundary(self):
        metadata = build_replay_entry_metadata(
            strategy_key="low_energy_probe",
            effective_signal_score_min=65.0,
            macro_trend_passed=True,
            confirmation_loops=4,
        )
        self.assertEqual("closed_candle", metadata["confirmation_unit"])
        self.assertEqual(65.0, metadata["effective_signal_score_min"])
        self.assertFalse(metadata["orderbook_funding_live_snapshot_available"])

    def test_short_input_returns_summary_without_unbound_score(self):
        settings = load_strategy_settings("TEST_MIN_ORDER", 1.0)
        with patch("tools.backtest_replay.load_strategy_settings", return_value=settings):
            summary, trades, equity = simulate_alt_strategy(
                candles=self.candles[:5],
                btc_reference_candles=None,
                source_timeframe="1m",
                symbol="ETH/USDT",
                exchange_name="okx",
                initial_cash=1_000.0,
                fee_rate_pct=0.1,
                risk_per_trade=0.05,
                min_buy_order_value=1.0,
                max_daily_loss_quote=5.0,
                execution_model=self.execution,
            )
        self.assertEqual([], trades)
        self.assertEqual([], equity)
        self.assertEqual(settings.get_signal_score_min("ETH/USDT"), summary["entry_signal_score_min_effective"])
        self.assertFalse(summary["deployment_evidence_eligible"])
        self.assertIn("in_progress_candle_confirmations", summary["replay_unavailable_context"])

    def test_probe_scales_are_forwarded_to_position_sizing(self):
        route = StrategyRoute("LOW_ENERGY", "low_energy_probe", get_alt_regime_policy("LOW_ENERGY"))
        low_energy = LowEnergyProbeDecision(True, "test", 0.30, 0)
        xrp = XrpReboundProbeState(
            XrpReboundProbeDecision(True, "test", 0.25, 0),
            True,
            True,
            True,
            False,
            0,
            True,
        )
        sol = SolProbeEntryState(
            SolProbeDecision(True, "test", 0.20),
            True,
            True,
            1,
            False,
            False,
        )
        with patch("tools.backtest_replay.evaluate_low_energy_probe", return_value=low_energy), patch(
            "tools.backtest_replay.resolve_xrp_rebound_probe_state", return_value=xrp
        ), patch(
            "tools.backtest_replay.resolve_sol_probe_entry_state", return_value=sol
        ), patch("tools.backtest_replay.build_alt_position_sizing", wraps=build_alt_position_sizing) as sizing:
            _summary, trades, _ = self._run(
                symbol="SOL/USDT",
                settings_overrides={
                    "enable_volume_filter": False,
                    "enable_volatility_filter": False,
                    "enable_higher_timeframe_filter": False,
                    "enable_sol_probe": True,
                    "entry_confirmation_loops": 1,
                },
                route_alt_strategy=lambda _regime: route,
                compute_macro_trend_gate=lambda **_kwargs: (True, 100.0),
            )
        kwargs = sizing.call_args.kwargs
        self.assertTrue(kwargs["low_energy_probe_allowed"])
        self.assertEqual(0.30, kwargs["low_energy_probe_position_scale"])
        self.assertTrue(kwargs["xrp_rebound_probe_allowed"])
        self.assertEqual(0.25, kwargs["xrp_rebound_probe_position_scale"])
        self.assertTrue(kwargs["sol_probe_allowed"])
        self.assertEqual(0.20, kwargs["sol_probe_position_scale"])
        scaled_ratio = build_alt_position_sizing(**kwargs).position_ratio
        unscaled_ratio = build_alt_position_sizing(
            **{**kwargs, "sol_probe_position_scale": 1.0}
        ).position_ratio
        buy = next(record for record in trades if record.side == "buy")
        self.assertLess(scaled_ratio, unscaled_ratio)
        self.assertAlmostEqual(scaled_ratio, buy.extra["position_ratio"])

    def test_xrp_lower_near_suppression_removes_extra_confirmations(self):
        route = route_alt_strategy("CHOPPY_LOW_VOL")
        mean_state = dict(self.signal_state)
        mean_state.update({"lower_near_probe_allowed": True, "lower_near_extra_confirmation_loops": 4})
        xrp = XrpReboundProbeState(
            XrpReboundProbeDecision(False, "test", 0.25, 0),
            False,
            True,
            False,
            False,
            0,
            True,
        )
        low_energy = LowEnergyProbeDecision(False, "test", 0.30, 0)
        settings = load_strategy_settings("TEST_MIN_ORDER", 1.0)
        with patch("tools.backtest_replay.route_alt_strategy", return_value=route), patch(
            "tools.backtest_replay.compute_bollinger_mean_reversion_state", return_value=mean_state
        ), patch(
            "tools.backtest_replay.resolve_xrp_rebound_probe_state", return_value=xrp
        ), patch(
            "tools.backtest_replay.evaluate_low_energy_probe", return_value=low_energy
        ), patch(
            "tools.backtest_replay.update_entry_timing_state", wraps=update_entry_timing_state
        ) as timing:
            self._run()
        self.assertTrue(timing.called)
        self.assertTrue(all(
            call.kwargs["required_confirmations"] == settings.entry_confirmation_loops
            for call in timing.call_args_list
        ))

    def test_sol_time_exit_uses_opened_at_and_creates_sell(self):
        route = StrategyRoute("LOW_ENERGY", "low_energy_probe", get_alt_regime_policy("LOW_ENERGY"))
        low_energy = LowEnergyProbeDecision(True, "test", 0.30, 0)
        xrp = XrpReboundProbeState(
            XrpReboundProbeDecision(False, "test", 0.25, 0),
            True,
            True,
            True,
            False,
            0,
            False,
        )
        sol = SolProbeEntryState(
            SolProbeDecision(True, "test", 0.20),
            True,
            True,
            1,
            False,
            False,
        )
        with patch(
            "tools.backtest_replay.resolve_sol_probe_exit_state", wraps=__import__(
                "core.strategy.sol_probe", fromlist=["resolve_sol_probe_exit_state"]
            ).resolve_sol_probe_exit_state
        ) as sol_exit:
            _summary, trades, _ = self._run(
                symbol="SOL/USDT",
                settings_overrides={
                    "enable_volume_filter": False,
                    "enable_volatility_filter": False,
                    "enable_higher_timeframe_filter": False,
                    "enable_sol_probe": True,
                    "entry_confirmation_loops": 1,
                    "sol_probe_max_hold_minutes": 1,
                },
                route_alt_strategy=lambda _regime: route,
                compute_macro_trend_gate=lambda **_kwargs: (True, 100.0),
                evaluate_low_energy_probe=lambda **_kwargs: low_energy,
                resolve_xrp_rebound_probe_state=lambda **_kwargs: xrp,
                resolve_sol_probe_entry_state=lambda **_kwargs: sol,
            )
        self.assertTrue(sol_exit.called)
        self.assertTrue(any(call.kwargs["opened_at"] is not None for call in sol_exit.call_args_list))
        self.assertTrue(any(record.reason == "sol_probe_time_exit" for record in trades))


if __name__ == "__main__":
    unittest.main()
