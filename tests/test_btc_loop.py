"""
작업 요약
- BTC 루프 진입/추가매수/청산 퍼널 helper 가 기존 ready stage/reason 을 유지하는지 검증한다.
"""

from __future__ import annotations

import unittest

from core.strategy.btc_loop import (
    run_btc_add_on_funnel,
    run_btc_entry_funnel,
    run_btc_exit_funnel,
)


class FakeStructuredLogger:
    def __init__(self, ready: bool = True) -> None:
        self.ready = ready
        self.calls: list[dict] = []

    def run_funnel(self, **kwargs):
        self.calls.append(kwargs)
        return self.ready, []


class BtcLoopTests(unittest.TestCase):
    def test_entry_funnel_uses_standard_entry_stage(self) -> None:
        logger = FakeStructuredLogger(ready=True)

        ready = run_btc_entry_funnel(
            structured_logger=logger,
            symbol="BTC/USDT",
            entry_steps=["step"],
            metrics={"score": 80},
        )

        self.assertTrue(ready)
        self.assertEqual("entry", logger.calls[0]["side"])
        self.assertEqual("buy_ready", logger.calls[0]["ready_stage"])
        self.assertEqual("entry_conditions_met", logger.calls[0]["ready_reason"])

    def test_add_on_funnel_uses_existing_ready_extra(self) -> None:
        logger = FakeStructuredLogger(ready=True)

        ready = run_btc_add_on_funnel(
            structured_logger=logger,
            symbol="BTC/USDT",
            add_on_steps=["step"],
            metrics={"pnl": 2.0},
        )

        self.assertTrue(ready)
        self.assertEqual("entry", logger.calls[0]["side"])
        self.assertEqual("add_on_ready", logger.calls[0]["ready_stage"])
        self.assertEqual("add_on_conditions_met", logger.calls[0]["ready_reason"])
        self.assertEqual({"entry_type": "add_on_winner"}, logger.calls[0]["ready_extra"])

    def test_exit_funnel_uses_btc_exit_reason_priority(self) -> None:
        logger = FakeStructuredLogger(ready=False)

        ready = run_btc_exit_funnel(
            structured_logger=logger,
            symbol="BTC/USDT",
            exit_steps=["step"],
            metrics={"pnl": 1.2},
            stop_loss_triggered=False,
            partial_take_profit_triggered=False,
            profit_protect_triggered=False,
            trailing_stop_triggered=True,
            donchian_failure_triggered=True,
            trend_exit_triggered=True,
        )

        self.assertFalse(ready)
        self.assertEqual("exit", logger.calls[0]["side"])
        self.assertEqual("sell_ready", logger.calls[0]["ready_stage"])
        self.assertEqual("trailing_stop_triggered", logger.calls[0]["ready_reason"])


if __name__ == "__main__":
    unittest.main()
