"""
작업 요약
- 백테스트 리플레이에서 공통으로 쓰는 데이터 모델과 기본 상수를 분리했다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_OKX_FEE_RATE_PCT = 0.10
DEFAULT_UPBIT_FEE_RATE_PCT = 0.05
DEFAULT_OKX_MIN_BUY_ORDER_VALUE = 1.0
DEFAULT_UPBIT_MIN_BUY_ORDER_VALUE = 5000.0
DEFAULT_OKX_MAX_DAILY_LOSS_QUOTE = 5.0
DEFAULT_UPBIT_MAX_DAILY_LOSS_QUOTE = 5000.0
DEFAULT_RISK_PER_TRADE = 0.05


@dataclass(frozen=True)
class Candle:
    """백테스트용 OHLCV 캔들."""

    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class TradeRecord:
    """백테스트 체결 1건."""

    strategy_type: str
    symbol: str
    side: str
    reason: str
    timestamp_ms: int
    recorded_at: str
    price: float
    amount: float
    order_value_quote: float
    fee_quote: float
    realized_pnl_quote: float | None
    realized_pnl_pct: float | None
    net_realized_pnl_quote: float | None
    net_realized_pnl_pct: float | None
    cash_after: float
    position_amount_after: float
    average_entry_price_after: float | None
    entry_count_after: int
    extra: dict[str, Any]


@dataclass(frozen=True)
class EquityPoint:
    """자산곡선 1포인트."""

    timestamp_ms: int
    equity_quote: float
    cash_quote: float
    position_amount: float
    close: float


@dataclass(frozen=True)
class ExecutionModel:
    """백테스트 체결 가정."""

    slippage_bps: float
    buy_fill_ratio: float
    sell_fill_ratio: float
    latency_ms: int


@dataclass(frozen=True)
class OrderbookSnapshot:
    """분석 로그에서 읽은 호가 스냅샷."""

    timestamp_ms: int
    best_bid: float | None
    best_ask: float | None
    best_bid_size: float | None
    best_ask_size: float | None
    bid_depth_notional_3: float | None
    ask_depth_notional_3: float | None
    spread_pct: float | None


@dataclass(frozen=True)
class AltReplayInitialState:
    """알트 리플레이 시작 시 주입할 초기 포지션 상태."""

    cash_quote: float
    units: float
    average_entry_price: float | None
    entry_count: int
    highest_price_since_entry: float | None
    lowest_price_since_entry: float | None
    partial_take_profit_done: bool
    partial_stop_loss_done: bool
    last_trade_ts: float
    last_partial_take_profit_ts: float
    daily_realized_pnl_quote: float


@dataclass(frozen=True)
class BtcReplayInitialState:
    """BTC 리플레이 시작 시 주입할 초기 포지션 상태."""

    cash_quote: float
    units: float
    entry_price: float | None
    partial_take_profit_done: bool
    add_on_count: int
    highest_price_since_entry: float | None
    lowest_price_since_entry: float | None
    trailing_armed: bool
    trailing_armed_at_ts: float | None
    trailing_activation_price: float | None
    last_trade_ts: float
    last_stop_loss_ts: float
    last_profit_exit_ts: float
    daily_realized_pnl_quote: float
