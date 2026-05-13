"""
작업 요약
- 주문 요청/체결 구조화 로그 입력을 공통 helper 로 분리해 봇 본문의 중복 호출을 줄였다.
"""

from __future__ import annotations

from typing import Any


def log_order_requested(
    *,
    structured_logger: Any,
    symbol: str,
    side: str,
    reason: str,
    actual: dict[str, Any],
    metrics: dict[str, Any],
) -> None:
    """주문 요청 strategy 로그를 표준 stage/result 로 남긴다."""
    structured_logger.log_strategy(
        symbol=symbol,
        side=side,
        stage="order_requested",
        result="requested",
        reason=reason,
        actual=actual,
        metrics=metrics,
    )


def log_order_filled(
    *,
    structured_logger: Any,
    symbol: str,
    strategy_side: str,
    trade_side: str,
    strategy_reason: str,
    trade_reason: str,
    actual: dict[str, Any],
    metrics: dict[str, Any],
) -> None:
    """주문 체결 strategy/trade 로그를 같은 actual/metrics 로 함께 남긴다."""
    structured_logger.log_strategy(
        symbol=symbol,
        side=strategy_side,
        stage="filled",
        result="filled",
        reason=strategy_reason,
        actual=actual,
        metrics=metrics,
    )
    structured_logger.log_trade_event(
        symbol=symbol,
        side=trade_side,
        reason=trade_reason,
        result="filled",
        actual=actual,
        metrics=metrics,
    )
