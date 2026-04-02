"""
수정 요약
- 업비트 웹소켓 수신 payload 를 심볼별 최신 시세/호가/캔들 상태로 정규화하는 메모리 저장소를 추가했다.
- 업비트 마켓 코드와 프로젝트 심볼 표기를 서로 변환하는 helper 를 함께 추가했다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def upbit_market_to_symbol(market: str) -> str:
    """`KRW-BTC` 형식 업비트 마켓 코드를 `BTC/KRW` 형식으로 바꾼다."""
    quote, base = market.split("-", 1)
    return f"{base}/{quote}"


def symbol_to_upbit_market(symbol: str) -> str:
    """`BTC/KRW` 형식 프로젝트 심볼을 `KRW-BTC` 형식으로 바꾼다."""
    base, quote = symbol.split("/", 1)
    return f"{quote}-{base}"


@dataclass
class UpbitSymbolMarketState:
    """심볼 1개의 최신 웹소켓 상태를 보관한다."""

    market: str
    symbol: str
    last_message_type: str | None = None
    updated_at_ms: int | None = None
    trade_price: float | None = None
    trade_volume: float | None = None
    trade_side: str | None = None
    trade_timestamp_ms: int | None = None
    best_bid_price: float | None = None
    best_ask_price: float | None = None
    best_bid_size: float | None = None
    best_ask_size: float | None = None
    total_bid_size: float | None = None
    total_ask_size: float | None = None
    orderbook_timestamp_ms: int | None = None
    candle_1m: dict[str, Any] | None = None
    candle_timestamp_ms: int | None = None
    raw_preview: dict[str, Any] = field(default_factory=dict)

    def to_snapshot(self) -> dict[str, Any]:
        """외부 프로세스 공유용 최신 스냅샷을 만든다."""
        return {
            "market": self.market,
            "symbol": self.symbol,
            "last_message_type": self.last_message_type,
            "updated_at_ms": self.updated_at_ms,
            "trade": {
                "price": self.trade_price,
                "volume": self.trade_volume,
                "side": self.trade_side,
                "timestamp_ms": self.trade_timestamp_ms,
            },
            "orderbook": {
                "best_bid_price": self.best_bid_price,
                "best_ask_price": self.best_ask_price,
                "best_bid_size": self.best_bid_size,
                "best_ask_size": self.best_ask_size,
                "total_bid_size": self.total_bid_size,
                "total_ask_size": self.total_ask_size,
                "timestamp_ms": self.orderbook_timestamp_ms,
            },
            "candle_1m": self.candle_1m,
            "raw_preview": self.raw_preview,
        }


class UpbitMarketStateStore:
    """업비트 웹소켓 최신 상태를 심볼별로 관리한다."""

    def __init__(self, markets: list[str]) -> None:
        self._states = {
            market: UpbitSymbolMarketState(
                market=market,
                symbol=upbit_market_to_symbol(market),
            )
            for market in markets
        }

    def known_markets(self) -> list[str]:
        """관리 중인 업비트 마켓 코드 목록을 반환한다."""
        return sorted(self._states)

    def apply_payload(self, payload: dict[str, Any]) -> UpbitSymbolMarketState | None:
        """payload 1개를 반영하고 갱신된 심볼 상태를 반환한다."""
        market = str(payload.get("code", "") or "")
        if not market or market not in self._states:
            return None

        state = self._states[market]
        message_type = str(payload.get("type", "") or "")
        updated_at_ms = _to_int(payload.get("timestamp")) or _to_int(payload.get("trade_timestamp"))
        state.last_message_type = message_type or state.last_message_type
        state.updated_at_ms = updated_at_ms or state.updated_at_ms
        state.raw_preview = _build_raw_preview(payload)

        if message_type == "trade":
            state.trade_price = _to_float(payload.get("trade_price"))
            state.trade_volume = _to_float(payload.get("trade_volume"))
            state.trade_side = str(payload.get("ask_bid", "") or "") or state.trade_side
            state.trade_timestamp_ms = _to_int(payload.get("trade_timestamp")) or updated_at_ms
        elif message_type == "orderbook":
            orderbook_units = payload.get("orderbook_units") or []
            first_unit = orderbook_units[0] if orderbook_units else {}
            state.best_bid_price = _to_float(first_unit.get("bid_price"))
            state.best_ask_price = _to_float(first_unit.get("ask_price"))
            state.best_bid_size = _to_float(first_unit.get("bid_size"))
            state.best_ask_size = _to_float(first_unit.get("ask_size"))
            state.total_bid_size = _to_float(payload.get("total_bid_size"))
            state.total_ask_size = _to_float(payload.get("total_ask_size"))
            state.orderbook_timestamp_ms = updated_at_ms or state.orderbook_timestamp_ms
        elif message_type.startswith("candle"):
            state.candle_1m = _extract_candle_payload(payload, market)
            state.candle_timestamp_ms = _to_int(payload.get("timestamp")) or state.candle_timestamp_ms

        return state

    def snapshot_by_market(self, market: str) -> dict[str, Any] | None:
        """업비트 마켓 코드 기준 최신 스냅샷을 반환한다."""
        state = self._states.get(market)
        return state.to_snapshot() if state else None

    def snapshots(self) -> list[dict[str, Any]]:
        """전체 심볼 최신 스냅샷 목록을 반환한다."""
        return [state.to_snapshot() for state in self._states.values()]


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _build_raw_preview(payload: dict[str, Any]) -> dict[str, Any]:
    """원본 payload 의 핵심 필드만 미리보기로 보관한다."""
    preview_keys = (
        "type",
        "code",
        "stream_type",
        "timestamp",
        "trade_timestamp",
        "trade_price",
        "best_ask_price",
        "best_bid_price",
    )
    return {
        str(key): payload.get(key)
        for key in preview_keys
        if payload.get(key) is not None
    }


def _extract_candle_payload(payload: dict[str, Any], market: str) -> dict[str, Any]:
    """캔들 payload 에서 전략이 바로 읽기 쉬운 필드만 추린다."""
    return {
        "market": market,
        "symbol": upbit_market_to_symbol(market),
        "type": str(payload.get("type", "") or ""),
        "stream_type": str(payload.get("stream_type", "") or ""),
        "timestamp_ms": _to_int(payload.get("timestamp")),
        "candle_date_time_kst": payload.get("candle_date_time_kst"),
        "opening_price": _to_float(payload.get("opening_price")),
        "high_price": _to_float(payload.get("high_price")),
        "low_price": _to_float(payload.get("low_price")),
        "trade_price": _to_float(payload.get("trade_price")),
        "candle_acc_trade_volume": _to_float(payload.get("candle_acc_trade_volume")),
        "candle_acc_trade_price": _to_float(payload.get("candle_acc_trade_price")),
        "unit": payload.get("unit"),
    }
