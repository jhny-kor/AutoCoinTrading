"""
작업 요약
- 거래소별 체결 텔레그램 메시지 formatter 가 기존 숫자 형식을 보존하는지 검증한다.
"""

from __future__ import annotations

import unittest

from core.notifications.trade_messages import (
    OKX_TRADE_MESSAGE_FORMAT,
    UPBIT_TRADE_MESSAGE_FORMAT,
    format_buy_fill_message,
    format_sell_fill_message,
)


class TradeMessageTests(unittest.TestCase):
    def test_okx_buy_message_keeps_existing_precision(self) -> None:
        message = format_buy_fill_message(
            symbol_regime="TREND",
            quote="USDT",
            base="SOL",
            buy_summary={
                "executed_order_value_quote": 12.345678912,
                "executed_price": 178.123456,
                "executed_amount": 0.069312345,
            },
            base_position_ratio=0.1,
            position_ratio=0.075,
            executed_ratio_pct=7.12,
            fmt=OKX_TRADE_MESSAGE_FORMAT,
        )

        self.assertEqual(
            "\n".join(
                [
                    "현재 레짐: TREND",
                    "매수 금액: 12.34567891 USDT",
                    "매수 단가: 178.1235",
                    "체결 수량: 0.06931234 SOL",
                    "기본 비중: 10.00%",
                    "최종 비중: 7.50%",
                    "실행 비중: 7.12%",
                ]
            ),
            message,
        )

    def test_okx_sell_message_keeps_existing_precision(self) -> None:
        message = format_sell_fill_message(
            symbol_regime="RANGE",
            quote="USDT",
            base="SOL",
            sell_summary={
                "executed_order_value_quote": 12.345678912,
                "executed_price": 181.123456,
                "executed_amount": 0.068312345,
            },
            realized_pnl_pct=1.234,
            realized_pnl_quote=0.123456,
            fmt=OKX_TRADE_MESSAGE_FORMAT,
        )

        self.assertEqual(
            "\n".join(
                [
                    "현재 레짐: RANGE",
                    "매도 금액: 12.3457 USDT",
                    "매도 단가: 181.1235",
                    "체결 수량: 0.06831234 SOL",
                    "수익률: 1.23%",
                    "실현 손익: 0.1235 USDT",
                ]
            ),
            message,
        )

    def test_upbit_messages_keep_krw_precision(self) -> None:
        buy_message = format_buy_fill_message(
            symbol_regime="LOW_ENERGY",
            quote="KRW",
            base="SOL",
            buy_summary={
                "executed_order_value_quote": 15005.4,
                "executed_price": 250123.7,
                "executed_amount": 0.060012345,
            },
            base_position_ratio=0.1,
            position_ratio=0.025,
            executed_ratio_pct=2.5,
            fmt=UPBIT_TRADE_MESSAGE_FORMAT,
        )
        sell_message = format_sell_fill_message(
            symbol_regime="LOW_ENERGY",
            quote="KRW",
            base="SOL",
            sell_summary={
                "executed_order_value_quote": 15100.6,
                "executed_price": 251009.1,
                "executed_amount": 0.060012345,
            },
            realized_pnl_pct=0.634,
            realized_pnl_quote=95.267,
            fmt=UPBIT_TRADE_MESSAGE_FORMAT,
        )

        self.assertIn("매수 금액: 15005 KRW", buy_message)
        self.assertIn("매수 단가: 250124", buy_message)
        self.assertIn("매도 금액: 15101 KRW", sell_message)
        self.assertIn("매도 단가: 251009", sell_message)
        self.assertIn("실현 손익: 95.27 KRW", sell_message)


if __name__ == "__main__":
    unittest.main()
