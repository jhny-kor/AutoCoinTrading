"""OKX 웹소켓 캔들 스냅샷 파일 저장소 + 버퍼 병합 helper.

스트림이 (심볼, timeframe) 별 최근 N개 캔들을 ccxt OHLCV 포맷
([ts_ms, open, high, low, close, volume]) 으로 원자적 JSON 저장하고,
provider 가 이를 읽어 REST 대신 사용한다.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def sanitize_symbol_for_filename(symbol: str) -> str:
    """심볼 문자열을 파일명 안전 형식으로 바꾼다."""
    return symbol.replace("/", "_").replace("-", "_")


def okx_channel_to_timeframe(channel: str) -> str | None:
    """OKX candle 채널명(candle1m, candle5m, ...)을 timeframe(1m, 5m) 으로 바꾼다."""
    normalized = channel.strip().lower()
    if not normalized.startswith("candle"):
        return None
    suffix = normalized[len("candle"):]
    return suffix or None


def merge_okx_candle_rows(
    existing: list[list[float]],
    incoming: list[list[str]],
    *,
    max_rows: int = 200,
) -> list[list[float]]:
    """기존 ccxt OHLCV rows 에 OKX 웹소켓 캔들 데이터를 병합한다.

    - OKX row: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm] (문자열)
    - 같은 타임스탬프(형성 중 캔들)는 갱신, 새 타임스탬프는 추가, ts 오름차순 정렬 후 최근 max_rows 유지.
    """
    by_ts: dict[int, list[float]] = {}
    for row in existing:
        try:
            by_ts[int(row[0])] = [float(row[0]), float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])]
        except (TypeError, ValueError, IndexError):
            continue
    for row in incoming:
        try:
            ts = int(row[0])
            by_ts[ts] = [
                float(ts),
                float(row[1]),
                float(row[2]),
                float(row[3]),
                float(row[4]),
                float(row[5]),
            ]
        except (TypeError, ValueError, IndexError):
            continue
    ordered = [by_ts[ts] for ts in sorted(by_ts)]
    if len(ordered) > max_rows:
        ordered = ordered[-max_rows:]
    return ordered


class OkxCandleStore:
    """OKX 웹소켓 캔들 스냅샷 파일 저장소."""

    def __init__(
        self,
        root_dir: str | Path = "logs/runtime/okx_ws",
        *,
        write_interval_sec: float = 0.4,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.candle_dir = self.root_dir / "candles"
        self.health_path = self.root_dir / "health.json"
        self.write_interval_sec = write_interval_sec
        self._last_write_ts: dict[str, float] = {}
        self._ensure_dirs()

    def candle_path(self, symbol: str, timeframe: str) -> Path:
        return self.candle_dir / f"{sanitize_symbol_for_filename(symbol)}__{timeframe}.json"

    def write_candles(
        self,
        symbol: str,
        timeframe: str,
        rows: list[list[float]],
        *,
        force: bool = False,
    ) -> None:
        """(심볼, timeframe) 캔들 배열을 디바운스 후 원자적 저장한다."""
        if not rows:
            return
        key = f"{symbol}|{timeframe}"
        now_ts = time.time()
        if not force and (now_ts - self._last_write_ts.get(key, 0.0)) < self.write_interval_sec:
            return
        payload = {
            "symbol": symbol,
            "timeframe": timeframe,
            "updated_at_ms": int(now_ts * 1000),
            "rows": rows,
        }
        self._write_json_atomic(self.candle_path(symbol, timeframe), payload)
        self._last_write_ts[key] = now_ts

    def write_health(self, payload: dict[str, Any]) -> None:
        self._write_json_atomic(self.health_path, payload)

    def _ensure_dirs(self) -> None:
        self.candle_dir.mkdir(parents=True, exist_ok=True)

    def _write_json_atomic(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f"{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        temp_path.replace(path)
