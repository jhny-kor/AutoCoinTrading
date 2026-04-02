"""
작업 요약
- trade_history 기반 체결률 가드를 공통 helper 로 분리했다.
- 최근 체결 비율이 낮은 심볼은 일정 시간 신규 진입을 막아 실행 품질 악화를 자동 회피하도록 보강했다.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class FillQualitySnapshot:
    """최근 체결 품질 판단 결과."""

    active: bool
    avg_fill_ratio: float | None
    sample_count: int
    latest_recorded_at: str | None
    reason: str


def _safe_float(value) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_iso_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


class ExecutionQualityGuard:
    """최근 체결 품질을 캐시하며 조회한다."""

    def __init__(self, refresh_interval_sec: int = 30) -> None:
        self.refresh_interval_sec = refresh_interval_sec
        self._last_refresh_at = 0.0
        self._last_seen_signature: tuple[tuple[str, float], ...] = ()
        self._records: list[dict] = []

    def _compute_signature(self) -> tuple[tuple[str, float], ...]:
        signature: list[tuple[str, float]] = []
        for path in sorted(Path("trade_logs").rglob("trade_history.jsonl")):
            try:
                signature.append((str(path), path.stat().st_mtime))
            except FileNotFoundError:
                continue
        return tuple(signature)

    def _refresh_if_needed(self) -> None:
        now_ts = time.time()
        signature = self._compute_signature()
        if (
            signature == self._last_seen_signature
            and (now_ts - self._last_refresh_at) < self.refresh_interval_sec
        ):
            return

        loaded: list[dict] = []
        for path, _ in signature:
            try:
                text = Path(path).read_text(encoding="utf-8")
            except FileNotFoundError:
                continue
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    loaded.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        self._records = loaded
        self._last_seen_signature = signature
        self._last_refresh_at = now_ts

    def get_fill_quality_snapshot(
        self,
        *,
        exchange_name: str,
        symbol: str,
        since_seconds: int,
        min_fill_ratio: float,
        min_sample_count: int,
        only_buy_side: bool = True,
    ) -> FillQualitySnapshot:
        """최근 체결률 기준으로 심볼의 신규 진입 차단 여부를 반환한다."""
        self._refresh_if_needed()

        now_ts = time.time()
        recent_fill_ratios: list[float] = []
        latest_dt: datetime | None = None
        for record in self._records:
            if str(record.get("exchange", "")).upper() != exchange_name.upper():
                continue
            if str(record.get("symbol", "")) != symbol:
                continue
            if only_buy_side and str(record.get("side", "")).lower() != "buy":
                continue

            recorded_at = _parse_iso_ts(str(record.get("recorded_at_local", "")))
            if recorded_at is None:
                recorded_at = _parse_iso_ts(str(record.get("recorded_at", "")))
            if recorded_at is None:
                continue
            if recorded_at.timestamp() < (now_ts - since_seconds):
                continue

            fill_ratio = _safe_float(record.get("fill_ratio"))
            if fill_ratio is None:
                continue
            recent_fill_ratios.append(fill_ratio)
            if latest_dt is None or recorded_at > latest_dt:
                latest_dt = recorded_at

        if len(recent_fill_ratios) < max(1, min_sample_count):
            return FillQualitySnapshot(
                active=False,
                avg_fill_ratio=(
                    sum(recent_fill_ratios) / len(recent_fill_ratios)
                    if recent_fill_ratios
                    else None
                ),
                sample_count=len(recent_fill_ratios),
                latest_recorded_at=latest_dt.isoformat() if latest_dt else None,
                reason="insufficient_samples",
            )

        avg_fill_ratio = sum(recent_fill_ratios) / len(recent_fill_ratios)
        active = avg_fill_ratio < min_fill_ratio
        return FillQualitySnapshot(
            active=active,
            avg_fill_ratio=avg_fill_ratio,
            sample_count=len(recent_fill_ratios),
            latest_recorded_at=latest_dt.isoformat() if latest_dt else None,
            reason="fill_quality_blocked" if active else "fill_quality_ok",
        )
