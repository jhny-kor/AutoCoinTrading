"""
저에너지 장 감지 공통 모듈

- 분석 수집 로그의 최신 상태를 읽어 거래소별 저에너지 장 여부를 공통으로 판단하도록 추가했다.
- 단타 봇들이 같은 기준으로 신규 진입을 줄일 수 있게 평균 거래량 배수, 평균 절대 변화율, 공개 기준 준비 건수를 함께 계산한다.
- 최신 분석 로그가 너무 오래됐으면 잘못된 차단을 막기 위해 저에너지 가드를 비활성화하도록 보강했다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from log_path_utils import current_date_str


def parse_bool(raw: str | None, default: bool = False) -> bool:
    """문자열 불리언 값을 파싱한다."""
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def safe_float(value) -> float | None:
    """숫자 후보를 안전하게 float로 변환한다."""
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_local_timestamp(raw: str) -> datetime | None:
    """로컬 시각 문자열을 datetime 으로 안전하게 변환한다."""
    try:
        if not raw:
            return None
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is not None:
            return parsed.astimezone().replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


@dataclass(frozen=True)
class LowEnergyGuardSettings:
    """저에너지 장 가드 설정."""

    enabled: bool
    avg_volume_ratio_threshold: float
    avg_abs_change_pct_threshold: float
    require_ready_count_zero: bool
    max_record_age_sec: int


@dataclass(frozen=True)
class LowEnergySnapshot:
    """현재 거래소 기준 저에너지 장 판단 결과."""

    active: bool
    avg_volume_ratio: float
    avg_abs_change_pct: float
    ready_count: int
    sample_count: int
    latest_collected_at_local: str | None
    reason: str


def load_low_energy_guard_settings() -> LowEnergyGuardSettings:
    """저에너지 장 가드 설정을 환경 변수에서 읽는다."""
    load_dotenv()
    return LowEnergyGuardSettings(
        enabled=parse_bool(os.getenv("MARKET_GUARD_ENABLE_LOW_ENERGY", "true"), True),
        avg_volume_ratio_threshold=float(
            os.getenv("MARKET_GUARD_LOW_ENERGY_AVG_VOLUME_RATIO", "0.80")
        ),
        avg_abs_change_pct_threshold=float(
            os.getenv("MARKET_GUARD_LOW_ENERGY_AVG_ABS_CHANGE_PCT", "0.05")
        ),
        require_ready_count_zero=parse_bool(
            os.getenv("MARKET_GUARD_LOW_ENERGY_REQUIRE_READY_COUNT_ZERO", "true"),
            True,
        ),
        max_record_age_sec=int(
            os.getenv("MARKET_GUARD_LOW_ENERGY_MAX_RECORD_AGE_SEC", "180")
        ),
    )


def load_low_energy_snapshot(
    *,
    exchange_name: str,
    managed_symbols: list[str],
    analysis_root: str | Path = "analysis_logs",
) -> LowEnergySnapshot:
    """거래소별 최신 분석 로그를 읽어 저에너지 장 여부를 계산한다."""
    settings = load_low_energy_guard_settings()
    if not settings.enabled:
        return LowEnergySnapshot(
            active=False,
            avg_volume_ratio=0.0,
            avg_abs_change_pct=0.0,
            ready_count=0,
            sample_count=0,
            latest_collected_at_local=None,
            reason="disabled",
        )

    today_dir = Path(analysis_root) / current_date_str()
    if not today_dir.exists():
        return LowEnergySnapshot(
            active=False,
            avg_volume_ratio=0.0,
            avg_abs_change_pct=0.0,
            ready_count=0,
            sample_count=0,
            latest_collected_at_local=None,
            reason="no_analysis_dir",
        )

    target_exchange = exchange_name.strip().lower()
    latest_rows: dict[str, dict] = {}
    latest_dt: datetime | None = None

    for symbol in managed_symbols:
        symbol_slug = symbol.replace("/", "_")
        candidate = today_dir / f"{target_exchange}__{symbol_slug}.jsonl"
        if not candidate.exists():
            continue
        last_line = ""
        for line in candidate.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last_line = line.strip()
        if not last_line:
            continue
        try:
            record = __import__("json").loads(last_line)
        except Exception:
            continue
        latest_rows[symbol] = record
        parsed = parse_local_timestamp(str(record.get("collected_at_local", "")))
        if parsed is not None and (latest_dt is None or parsed > latest_dt):
            latest_dt = parsed

    if not latest_rows:
        return LowEnergySnapshot(
            active=False,
            avg_volume_ratio=0.0,
            avg_abs_change_pct=0.0,
            ready_count=0,
            sample_count=0,
            latest_collected_at_local=None,
            reason="no_latest_rows",
        )

    if latest_dt is not None:
        age_sec = (datetime.now() - latest_dt).total_seconds()
        if age_sec > settings.max_record_age_sec:
            return LowEnergySnapshot(
                active=False,
                avg_volume_ratio=0.0,
                avg_abs_change_pct=0.0,
                ready_count=0,
                sample_count=len(latest_rows),
                latest_collected_at_local=latest_dt.isoformat(),
                reason="stale_analysis_rows",
            )

    volume_values = [
        value
        for value in (safe_float(row.get("volume_ratio")) for row in latest_rows.values())
        if value is not None
    ]
    abs_change_values = [
        value
        for value in (safe_float(row.get("avg_abs_change_pct")) for row in latest_rows.values())
        if value is not None
    ]
    ready_count = sum(1 for row in latest_rows.values() if row.get("public_buy_ready"))
    avg_volume_ratio = (
        sum(volume_values) / len(volume_values) if volume_values else 0.0
    )
    avg_abs_change_pct = (
        sum(abs_change_values) / len(abs_change_values) if abs_change_values else 0.0
    )

    active = (
        avg_volume_ratio < settings.avg_volume_ratio_threshold
        and avg_abs_change_pct < settings.avg_abs_change_pct_threshold
        and (
            not settings.require_ready_count_zero
            or ready_count == 0
        )
    )

    return LowEnergySnapshot(
        active=active,
        avg_volume_ratio=avg_volume_ratio,
        avg_abs_change_pct=avg_abs_change_pct,
        ready_count=ready_count,
        sample_count=len(latest_rows),
        latest_collected_at_local=latest_dt.isoformat() if latest_dt is not None else None,
        reason="low_energy_active" if active else "low_energy_inactive",
    )
