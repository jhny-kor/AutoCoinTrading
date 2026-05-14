"""
작업 요약
- 백테스트 리플레이의 실행모델, 호가 스냅샷, 슬리피지/지연 체결 helper 를 분리했다.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_right
from datetime import datetime
from pathlib import Path

from tools.backtest_math import safe_float, safe_int
from tools.backtest_models import (
    DEFAULT_OKX_FEE_RATE_PCT,
    DEFAULT_OKX_MAX_DAILY_LOSS_QUOTE,
    DEFAULT_OKX_MIN_BUY_ORDER_VALUE,
    DEFAULT_UPBIT_FEE_RATE_PCT,
    DEFAULT_UPBIT_MAX_DAILY_LOSS_QUOTE,
    DEFAULT_UPBIT_MIN_BUY_ORDER_VALUE,
    Candle,
    ExecutionModel,
    OrderbookSnapshot,
)


def build_execution_model(args: argparse.Namespace) -> ExecutionModel:
    """CLI 인자에서 실행 모델을 만든다."""
    return ExecutionModel(
        slippage_bps=max(0.0, float(args.slippage_bps or 0.0)),
        buy_fill_ratio=min(1.0, max(0.0, float(args.buy_fill_ratio or 1.0))),
        sell_fill_ratio=min(1.0, max(0.0, float(args.sell_fill_ratio or 1.0))),
        latency_ms=max(0, int(args.latency_ms or 0)),
    )


def load_orderbook_snapshots(path: Path | None) -> list[OrderbookSnapshot]:
    """analysis_logs JSONL 에서 호가 스냅샷을 읽는다."""
    if path is None or not path.exists():
        return []
    snapshots: list[OrderbookSnapshot] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        timestamp_ms = safe_int(payload.get("last_candle_ts"))
        if timestamp_ms is None:
            collected_at = payload.get("collected_at")
            if isinstance(collected_at, str):
                try:
                    timestamp_ms = int(datetime.fromisoformat(collected_at).timestamp() * 1000)
                except ValueError:
                    timestamp_ms = None
        if timestamp_ms is None:
            continue
        snapshots.append(
            OrderbookSnapshot(
                timestamp_ms=timestamp_ms,
                best_bid=safe_float(payload.get("best_bid")),
                best_ask=safe_float(payload.get("best_ask")),
                best_bid_size=safe_float(payload.get("best_bid_size")),
                best_ask_size=safe_float(payload.get("best_ask_size")),
                bid_depth_notional_3=safe_float(payload.get("bid_depth_notional_3")),
                ask_depth_notional_3=safe_float(payload.get("ask_depth_notional_3")),
                spread_pct=safe_float(payload.get("spread_pct")),
            )
        )
    snapshots.sort(key=lambda item: item.timestamp_ms)
    return snapshots


def resolve_orderbook_snapshot(
    snapshots: list[OrderbookSnapshot],
    *,
    target_timestamp_ms: int,
) -> OrderbookSnapshot | None:
    """지정 시점 이전의 가장 가까운 호가 스냅샷을 찾는다."""
    if not snapshots:
        return None
    timestamps = [snapshot.timestamp_ms for snapshot in snapshots]
    index = bisect_right(timestamps, target_timestamp_ms) - 1
    if index < 0:
        return None
    return snapshots[index]


def estimate_orderbook_fill_ratio(
    *,
    side: str,
    snapshot: OrderbookSnapshot | None,
    requested_order_value_quote: float,
) -> float:
    """상위 호가 depth 기준으로 부분체결 비율을 추정한다."""
    if snapshot is None or requested_order_value_quote <= 0:
        return 1.0
    if side == "buy":
        depth_notional = snapshot.ask_depth_notional_3
        if depth_notional is None and snapshot.best_ask is not None and snapshot.best_ask_size is not None:
            depth_notional = snapshot.best_ask * snapshot.best_ask_size
    else:
        depth_notional = snapshot.bid_depth_notional_3
        if depth_notional is None and snapshot.best_bid is not None and snapshot.best_bid_size is not None:
            depth_notional = snapshot.best_bid * snapshot.best_bid_size
    if depth_notional is None or depth_notional <= 0:
        return 1.0
    return min(1.0, depth_notional / requested_order_value_quote)


def resolve_execution_candle(
    candles: list[Candle],
    *,
    current_index: int,
    execution_model: ExecutionModel,
) -> tuple[Candle, int, str]:
    """지연이 있으면 다음 캔들 시가 체결로 근사한 실행 캔들을 고른다."""
    if execution_model.latency_ms <= 0 or current_index + 1 >= len(candles):
        return candles[current_index], current_index, "close"
    return candles[current_index + 1], current_index + 1, "next_open"


def apply_execution_price(
    *,
    reference_price: float,
    side: str,
    slippage_bps: float,
) -> float:
    """사이드 기준으로 불리한 방향의 슬리피지를 적용한다."""
    multiplier = slippage_bps / 10_000.0
    if side == "buy":
        return reference_price * (1.0 + multiplier)
    if side == "sell":
        return reference_price * max(0.0, 1.0 - multiplier)
    return reference_price


def resolve_default_fee_rate(exchange_name: str) -> float:
    """거래소별 기본 수수료율을 반환한다."""
    if exchange_name.lower() == "upbit":
        return DEFAULT_UPBIT_FEE_RATE_PCT
    return DEFAULT_OKX_FEE_RATE_PCT


def resolve_default_min_buy_order_value(exchange_name: str) -> float:
    """거래소별 기본 최소 매수 금액을 반환한다."""
    if exchange_name.lower() == "upbit":
        return DEFAULT_UPBIT_MIN_BUY_ORDER_VALUE
    return DEFAULT_OKX_MIN_BUY_ORDER_VALUE


def resolve_default_max_daily_loss(exchange_name: str) -> float:
    """거래소별 기본 일일 최대 손실 제한을 반환한다."""
    if exchange_name.lower() == "upbit":
        return DEFAULT_UPBIT_MAX_DAILY_LOSS_QUOTE
    return DEFAULT_OKX_MAX_DAILY_LOSS_QUOTE
