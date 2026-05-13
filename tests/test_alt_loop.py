"""
작업 요약
- 알트 루프 진입/청산 퍼널 helper 가 기존 ready stage/reason 을 유지하는지 검증한다.
"""

from __future__ import annotations

import unittest

from core.strategy.alt_loop import run_alt_entry_funnel, run_alt_exit_funnel


class FakeStructuredLogger:
    def __init__(self, ready: bool = True) -> None:
        self.ready = ready
        self.calls: list[dict] = []

    def run_funnel(self, **kwargs):
        self.calls.append(kwargs)
        return self.ready, []


class AltLoopTests(unittest.TestCase):
    def test_entry_funnel_uses_standard_entry_stage(self) -> None:
        logger = FakeStructuredLogger(ready=True)

        ready = run_alt_entry_funnel(
            structured_logger=logger,
            symbol="SOL/USDT",
            entry_steps=["step"],
            metrics={"score": 70},
        )

        self.assertTrue(ready)
        self.assertEqual("entry", logger.calls[0]["side"])
        self.assertEqual("buy_ready", logger.calls[0]["ready_stage"])
        self.assertEqual("entry_conditions_met", logger.calls[0]["ready_reason"])

    def test_exit_funnel_uses_alt_exit_reason_priority(self) -> None:
        logger = FakeStructuredLogger(ready=False)

        ready = run_alt_exit_funnel(
            structured_logger=logger,
            symbol="SOL/USDT",
            exit_steps=["step"],
            metrics={"pnl": 1.2},
            stop_loss_triggered=False,
            profit_protect_triggered=False,
            break_even_guard_triggered=True,
            volume_spike_exit_triggered=True,
            sol_probe_time_exit_triggered=True,
        )

        self.assertFalse(ready)
        self.assertEqual("exit", logger.calls[0]["side"])
        self.assertEqual("sell_ready", logger.calls[0]["ready_stage"])
        self.assertEqual("break_even_guard_triggered", logger.calls[0]["ready_reason"])


if __name__ == "__main__":
    unittest.main()
