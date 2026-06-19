"""OKX 웹소켓 캔들 스냅샷을 읽는 파일 기반 provider.

전략 봇이 1m/5m 캔들을 REST 대신 웹소켓 스냅샷에서 우선 읽되, 데이터가
오래됐거나(stale) 수집기가 끊겼으면 None 을 반환해 REST fallback 으로 넘긴다.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from core.market_data.okx_candle_store import sanitize_symbol_for_filename


class OkxMarketDataProvider:
    """OKX 웹소켓 캔들 스냅샷 provider."""

    def __init__(
        self,
        root_dir: str | Path = "logs/runtime/okx_ws",
        *,
        cache_ttl_sec: float = 0.25,
        stale_sec: float = 8.0,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.candle_dir = self.root_dir / "candles"
        self.health_path = self.root_dir / "health.json"
        self.cache_ttl_sec = cache_ttl_sec
        self.stale_sec = stale_sec
        self._ohlcv_cache: dict[tuple[str, str, int], tuple[float, list[list[float]]]] = {}
        self._health_cache: tuple[float, dict[str, Any] | None] = (0.0, None)

    def read_health(self) -> dict[str, Any] | None:
        now_ts = time.time()
        cached_ts, cached_payload = self._health_cache
        if (now_ts - cached_ts) <= self.cache_ttl_sec:
            return cached_payload
        try:
            payload = json.loads(self.health_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            payload = None
        self._health_cache = (now_ts, payload)
        return payload

    def is_connected(self) -> bool:
        health = self.read_health()
        if not isinstance(health, dict):
            return False
        return health.get("connected") is True

    def get_recent_ohlcv(
        self, symbol: str, timeframe: str, limit: int
    ) -> list[list[float]] | None:
        """심볼/timeframe 의 최근 OHLCV 를 fresh 상태일 때만 반환한다. 아니면 None."""
        normalized = timeframe.strip().lower()
        cache_key = (symbol, normalized, limit)
        now_ts = time.time()
        cached = self._ohlcv_cache.get(cache_key)
        if cached and (now_ts - cached[0]) <= self.cache_ttl_sec:
            return cached[1]

        if not self.is_connected():
            return None

        path = self.candle_dir / f"{sanitize_symbol_for_filename(symbol)}__{normalized}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None
        if not isinstance(payload, dict):
            return None

        updated_at_ms = payload.get("updated_at_ms")
        if updated_at_ms in (None, ""):
            return None
        try:
            age_sec = max(0.0, (now_ts * 1000 - float(updated_at_ms)) / 1000)
        except (TypeError, ValueError):
            return None
        if age_sec > self.stale_sec:
            return None

        rows_raw = payload.get("rows")
        if not isinstance(rows_raw, list) or len(rows_raw) < limit:
            return None
        rows: list[list[float]] = []
        for row in rows_raw[-limit:]:
            try:
                rows.append([
                    int(row[0]),
                    float(row[1]),
                    float(row[2]),
                    float(row[3]),
                    float(row[4]),
                    float(row[5]),
                ])
            except (TypeError, ValueError, IndexError):
                return None
        if len(rows) < limit:
            return None
        self._ohlcv_cache[cache_key] = (now_ts, rows)
        return rows


def create_okx_market_data_provider(config: dict[str, Any] | None = None) -> OkxMarketDataProvider | None:
    """설정에 따라 OKX 웹소켓 provider 를 생성한다. 비활성화면 None."""
    config = config or {}
    if not config.get("enable_okx_ws_provider", False):
        return None
    return OkxMarketDataProvider(
        root_dir=config.get("okx_ws_root_dir", "logs/runtime/okx_ws"),
        stale_sec=float(config.get("okx_ws_stale_sec", 8.0)),
    )
