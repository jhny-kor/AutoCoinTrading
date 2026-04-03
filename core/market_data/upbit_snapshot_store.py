"""
수정 요약
- latest/health/private latest JSON 저장 시 임시 파일명을 고유하게 만들어 동시 저장 충돌 가능성을 줄였다.
- 업비트 private 웹소켓의 내 주문/내 자산 이벤트를 latest/jsonl 로 저장하는 helper 를 추가했다.
- 업비트 웹소켓 수집기가 최신 시세/호가/캔들 상태를 로컬 JSON/JSONL 파일로 저장하는 스냅샷 저장소를 추가했다.
- latest 스냅샷은 짧은 debounce 로 저장하고 1분 캔들은 봉 기준으로 중복 없이 append 하도록 구성했다.
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


class UpbitSnapshotStore:
    """업비트 웹소켓 스냅샷 파일 저장소."""

    def __init__(
        self,
        root_dir: str | Path = "logs/runtime/upbit_ws",
        *,
        latest_write_interval_sec: float = 0.4,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.latest_dir = self.root_dir / "latest"
        self.candle_dir = self.root_dir / "candles_1m"
        self.private_dir = self.root_dir / "private"
        self.health_path = self.root_dir / "health.json"
        self.latest_write_interval_sec = latest_write_interval_sec
        self._last_latest_write_ts: dict[str, float] = {}
        self._last_candle_key: dict[str, str] = {}
        self._ensure_dirs()

    def write_latest(self, snapshot: dict[str, Any]) -> None:
        """심볼별 최신 스냅샷 JSON 을 저장한다."""
        symbol = str(snapshot.get("symbol", "") or "")
        if not symbol:
            return
        now_ts = time.time()
        last_write_ts = self._last_latest_write_ts.get(symbol, 0.0)
        if (now_ts - last_write_ts) < self.latest_write_interval_sec:
            return
        self._write_json_atomic(self.latest_dir / f"{sanitize_symbol_for_filename(symbol)}.json", snapshot)
        self._last_latest_write_ts[symbol] = now_ts

    def append_candle_1m(self, snapshot: dict[str, Any]) -> None:
        """1분 캔들 스냅샷을 심볼별 JSONL 파일에 append 한다."""
        symbol = str(snapshot.get("symbol", "") or "")
        candle = snapshot.get("candle_1m")
        if not symbol or not isinstance(candle, dict):
            return
        candle_time = str(candle.get("candle_date_time_kst") or candle.get("timestamp_ms") or "")
        if not candle_time:
            return
        last_key = self._last_candle_key.get(symbol)
        if last_key == candle_time:
            return
        path = self.candle_dir / f"{sanitize_symbol_for_filename(symbol)}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(candle, ensure_ascii=False, separators=(",", ":")) + "\n")
        self._last_candle_key[symbol] = candle_time

    def write_health(self, payload: dict[str, Any]) -> None:
        """수집기 상태 health JSON 을 저장한다."""
        self._write_json_atomic(self.health_path, payload)

    def write_private_latest(self, name: str, payload: dict[str, Any]) -> None:
        """private latest 스냅샷 JSON 을 저장한다."""
        self._write_json_atomic(self.private_dir / f"{name}.json", payload)

    def append_private_event(self, name: str, payload: dict[str, Any]) -> None:
        """private 이벤트를 JSONL 로 append 한다."""
        path = self.private_dir / f"{name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")

    def _ensure_dirs(self) -> None:
        self.latest_dir.mkdir(parents=True, exist_ok=True)
        self.candle_dir.mkdir(parents=True, exist_ok=True)
        self.private_dir.mkdir(parents=True, exist_ok=True)

    def _write_json_atomic(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(
            f"{path.name}.{os.getpid()}.{time.time_ns()}.tmp"
        )
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(path)
