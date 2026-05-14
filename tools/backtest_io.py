"""
작업 요약
- 백테스트 리플레이의 캔들 파일 입출력, 리샘플링, 결과 저장 helper 를 분리했다.
"""

from __future__ import annotations

import csv
import json
from bisect import bisect_right
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.backtest_math import parse_timeframe_to_minutes, safe_float, safe_int
from tools.backtest_models import Candle


def load_candles(path: Path) -> list[Candle]:
    """CSV 또는 JSONL 파일에서 캔들 목록을 읽는다."""
    if not path.exists():
        raise FileNotFoundError(f"입력 파일이 없습니다: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return load_candles_from_csv(path)
    if suffix in {".jsonl", ".json"}:
        return load_candles_from_jsonl(path)
    raise ValueError(f"지원하지 않는 파일 형식입니다: {path.suffix}")


def load_candles_from_csv(path: Path) -> list[Candle]:
    """CSV 파일에서 캔들을 읽는다."""
    candles: list[Candle] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            timestamp_ms = safe_int(row.get("timestamp_ms") or row.get("timestamp") or row.get("ts"))
            open_price = safe_float(row.get("open"))
            high_price = safe_float(row.get("high"))
            low_price = safe_float(row.get("low"))
            close_price = safe_float(row.get("close"))
            volume = safe_float(row.get("volume"))
            if None in {timestamp_ms, open_price, high_price, low_price, close_price, volume}:
                continue
            candles.append(
                Candle(
                    timestamp_ms=timestamp_ms,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                )
            )
    return sorted(candles, key=lambda candle: candle.timestamp_ms)


def load_candles_from_jsonl(path: Path) -> list[Candle]:
    """JSONL 파일에서 캔들을 읽는다."""
    candles: list[Candle] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            candle = parse_candle_payload(payload)
            if candle is not None:
                candles.append(candle)
    return sorted(candles, key=lambda candle: candle.timestamp_ms)


def parse_candle_payload(payload: Any) -> Candle | None:
    """다양한 JSON 구조에서 캔들 1건을 해석한다."""
    if isinstance(payload, list) and len(payload) >= 6:
        timestamp_ms = safe_int(payload[0])
        open_price = safe_float(payload[1])
        high_price = safe_float(payload[2])
        low_price = safe_float(payload[3])
        close_price = safe_float(payload[4])
        volume = safe_float(payload[5])
    elif isinstance(payload, dict):
        timestamp_ms = safe_int(
            payload.get("timestamp_ms")
            or payload.get("timestamp")
            or payload.get("ts")
            or payload.get("last_candle_ts")
        )
        open_price = safe_float(payload.get("open"))
        high_price = safe_float(payload.get("high"))
        low_price = safe_float(payload.get("low"))
        close_price = safe_float(payload.get("close"))
        volume = safe_float(payload.get("volume"))
    else:
        return None

    if None in {timestamp_ms, open_price, high_price, low_price, close_price, volume}:
        return None
    return Candle(
        timestamp_ms=timestamp_ms,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
    )


def resample_candles(candles: list[Candle], source_timeframe: str, target_timeframe: str) -> list[Candle]:
    """낮은 주기 캔들을 높은 주기 캔들로 리샘플링한다."""
    if source_timeframe == target_timeframe:
        return list(candles)

    source_minutes = parse_timeframe_to_minutes(source_timeframe)
    target_minutes = parse_timeframe_to_minutes(target_timeframe)
    if target_minutes < source_minutes:
        raise ValueError("더 낮은 주기로는 리샘플링할 수 없습니다.")
    if target_minutes % source_minutes != 0:
        raise ValueError("입력 주기가 목표 주기를 정확히 나누지 못합니다.")

    bucket_ms = target_minutes * 60 * 1000
    grouped: dict[int, list[Candle]] = {}
    for candle in candles:
        bucket = (candle.timestamp_ms // bucket_ms) * bucket_ms
        grouped.setdefault(bucket, []).append(candle)

    resampled: list[Candle] = []
    for bucket, rows in sorted(grouped.items()):
        rows.sort(key=lambda candle: candle.timestamp_ms)
        resampled.append(
            Candle(
                timestamp_ms=bucket,
                open=rows[0].open,
                high=max(row.high for row in rows),
                low=min(row.low for row in rows),
                close=rows[-1].close,
                volume=sum(row.volume for row in rows),
            )
        )
    return resampled


def get_active_candles_by_time(
    candles: list[Candle],
    timestamps: list[int],
    current_timestamp_ms: int,
) -> list[Candle]:
    """현재 시각까지 확정된 상위 주기 캔들 목록을 반환한다."""
    end = bisect_right(timestamps, current_timestamp_ms)
    return candles[:end]


def get_recent_active_candles_by_time(
    candles: list[Candle],
    timestamps: list[int],
    current_timestamp_ms: int,
    max_count: int,
) -> list[Candle]:
    """현재 시각까지 확정된 상위 주기 캔들 중 최근 필요한 개수만 반환한다."""
    if max_count <= 0:
        return []
    end = bisect_right(timestamps, current_timestamp_ms)
    start = max(0, end - max_count)
    return candles[start:end]


def format_iso(timestamp_ms: int) -> str:
    """밀리초 타임스탬프를 ISO 문자열로 바꾼다."""
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).isoformat()


def local_date_key(timestamp_ms: int) -> str:
    """밀리초 타임스탬프를 로컬 날짜 키로 바꾼다."""
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).astimezone().strftime("%Y-%m-%d")


def build_output_dir(base_dir: Path, strategy_type: str, symbol: str) -> Path:
    """리포트 디렉토리를 만든다."""
    slug = symbol.replace("/", "_").replace("-", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = base_dir / f"{timestamp}__{strategy_type}__{slug}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_json(path: Path, payload: Any) -> None:
    """JSON 파일을 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[Any]) -> None:
    """JSONL 파일을 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            payload = asdict(row) if not isinstance(row, dict) else row
            f.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
