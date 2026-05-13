"""
작업 요약
- 매수 금액/매도 금액/손익 금액 precision 을 분리해 기존 거래소별 알림 형식을 보존했다.
- 거래소별 체결 알림 숫자 포맷과 메시지 본문 조립을 공통 helper 로 분리했다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TradeMessageFormat:
    """거래소별 체결 알림 숫자 포맷을 나타낸다."""

    buy_quote_decimals: int
    sell_quote_decimals: int
    price_decimals: int
    amount_decimals: int = 8
    pnl_quote_decimals: int = 4


OKX_TRADE_MESSAGE_FORMAT = TradeMessageFormat(
    buy_quote_decimals=8,
    sell_quote_decimals=4,
    price_decimals=4,
    pnl_quote_decimals=4,
)
UPBIT_TRADE_MESSAGE_FORMAT = TradeMessageFormat(
    buy_quote_decimals=0,
    sell_quote_decimals=0,
    price_decimals=0,
    pnl_quote_decimals=2,
)


def _fmt(value: Any, decimals: int) -> str:
    return f"{float(value):.{decimals}f}"


def format_buy_fill_message(
    *,
    symbol_regime: str | None,
    quote: str,
    base: str,
    buy_summary: dict[str, Any],
    base_position_ratio: float,
    position_ratio: float,
    executed_ratio_pct: float,
    fmt: TradeMessageFormat,
) -> str:
    """매수 체결 텔레그램 메시지 본문을 만든다."""
    return (
        f"현재 레짐: {symbol_regime}\n"
        f"매수 금액: {_fmt(buy_summary['executed_order_value_quote'], fmt.buy_quote_decimals)} {quote}\n"
        f"매수 단가: {_fmt(buy_summary['executed_price'], fmt.price_decimals)}\n"
        f"체결 수량: {_fmt(buy_summary['executed_amount'], fmt.amount_decimals)} {base}\n"
        f"기본 비중: {base_position_ratio * 100:.2f}%\n"
        f"최종 비중: {position_ratio * 100:.2f}%\n"
        f"실행 비중: {executed_ratio_pct:.2f}%"
    )


def format_sell_fill_message(
    *,
    symbol_regime: str | None,
    quote: str,
    base: str,
    sell_summary: dict[str, Any],
    realized_pnl_pct: float,
    realized_pnl_quote: float,
    fmt: TradeMessageFormat,
) -> str:
    """매도/손절 체결 텔레그램 메시지 본문을 만든다."""
    return (
        f"현재 레짐: {symbol_regime}\n"
        f"매도 금액: {_fmt(sell_summary['executed_order_value_quote'], fmt.sell_quote_decimals)} {quote}\n"
        f"매도 단가: {_fmt(sell_summary['executed_price'], fmt.price_decimals)}\n"
        f"체결 수량: {_fmt(sell_summary['executed_amount'], fmt.amount_decimals)} {base}\n"
        f"수익률: {realized_pnl_pct:.2f}%\n"
        f"실현 손익: {_fmt(realized_pnl_quote, fmt.pnl_quote_decimals)} {quote}"
    )
