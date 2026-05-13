"""
작업 요약
- 주문 요청/체결 구조화 로그 helper 가 기존 stage/result 값을 유지하는지 검증한다.
"""

from __future__ import annotations

import unittest

from core.execution.order_logging import log_order_filled, log_order_requested


class FakeStructuredLogger:
    def __init__(self) -> None:
        self.strategy_events: list[dict] = []
        self.trade_events: list[dict] = []

    def log_strategy(self, **kwargs) -> None:
        self.strategy_events.append(kwargs)

    def log_trade_event(self, **kwargs) -> None:
        self.trade_events.append(kwargs)


class OrderLoggingTests(unittest.TestCase):
    def test_log_order_requested_uses_standard_stage(self) -> None:
        logger = FakeStructuredLogger()

        log_order_requested(
            structured_logger=logger,
            symbol="SOL/USDT",
            side="entry",
            reason="market_buy_requested",
            actual={"order_value_quote": 10.0},
            metrics={"score": 75},
        )

        self.assertEqual(
            {
                "symbol": "SOL/USDT",
                "side": "entry",
                "stage": "order_requested",
                "result": "requested",
                "reason": "market_buy_requested",
                "actual": {"order_value_quote": 10.0},
                "metrics": {"score": 75},
            },
            logger.strategy_events[0],
        )

    def test_log_order_filled_writes_strategy_and_trade_events(self) -> None:
        logger = FakeStructuredLogger()

        log_order_filled(
            structured_logger=logger,
            symbol="SOL/USDT",
            strategy_side="exit",
            trade_side="sell",
            strategy_reason="take_profit_filled",
            trade_reason="take_profit",
            actual={"filled_amount": 1.0},
            metrics={"holding_seconds": 60},
        )

        self.assertEqual("filled", logger.strategy_events[0]["stage"])
        self.assertEqual("filled", logger.strategy_events[0]["result"])
        self.assertEqual("take_profit_filled", logger.strategy_events[0]["reason"])
        self.assertEqual("sell", logger.trade_events[0]["side"])
        self.assertEqual("take_profit", logger.trade_events[0]["reason"])
        self.assertEqual({"filled_amount": 1.0}, logger.trade_events[0]["actual"])


if __name__ == "__main__":
    unittest.main()
