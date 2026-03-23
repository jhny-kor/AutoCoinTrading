"""
저에너지 장 감지 공통 모듈

- 심볼별 최신 분석 로그를 기준으로 레짐을 분류하고, 레짐 변경 알림 상태를 기록하는 기능을 추가했다.
- 분석 수집 로그의 최신 상태를 읽어 거래소별 저에너지 장 여부를 공통으로 판단하도록 추가했다.
- 단타 봇들이 같은 기준으로 신규 진입을 줄일 수 있게 평균 거래량 배수, 평균 절대 변화율, 공개 기준 준비 건수를 함께 계산한다.
- 최신 분석 로그가 너무 오래됐으면 잘못된 차단을 막기 위해 저에너지 가드를 비활성화하도록 보강했다.
"""

from __future__ import annotations

import json
import os
import time
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


@dataclass(frozen=True)
class SymbolRegimeSnapshot:
    """심볼별 현재 레짐 판단 결과."""

    regime: str
    volume_ratio: float | None
    avg_abs_change_pct: float | None
    gap_pct: float | None
    rsi: float | None
    public_buy_ready: bool
    bullish_signal: bool
    bearish_signal: bool
    above_ma: bool
    htf_bullish: bool | None
    recorded_at_local: str | None


def load_regime_thresholds() -> dict[str, float | int | bool]:
    """심볼별 레짐 분류에 사용할 임계값을 읽는다."""
    load_dotenv()
    return {
        "breakout_volume_ratio_threshold": float(
            os.getenv("REGIME_BREAKOUT_VOLUME_RATIO_THRESHOLD", "1.20")
        ),
        "breakout_gap_pct_threshold": float(
            os.getenv("REGIME_BREAKOUT_GAP_PCT_THRESHOLD", "0.12")
        ),
        "trending_volume_ratio_threshold": float(
            os.getenv("REGIME_TRENDING_VOLUME_RATIO_THRESHOLD", "1.00")
        ),
        "trending_avg_abs_change_pct_threshold": float(
            os.getenv("REGIME_TRENDING_AVG_ABS_CHANGE_PCT_THRESHOLD", "0.08")
        ),
        "exhaustion_rsi_threshold": float(
            os.getenv("REGIME_EXHAUSTION_RSI_THRESHOLD", "80")
        ),
        "overheated_rsi_threshold": float(
            os.getenv("REGIME_OVERHEATED_RSI_THRESHOLD", "90")
        ),
        "overheated_volume_ratio_threshold": float(
            os.getenv("REGIME_OVERHEATED_VOLUME_RATIO_THRESHOLD", "1.50")
        ),
        "alert_min_interval_sec": int(
            os.getenv("REGIME_ALERT_MIN_INTERVAL_SEC", "900")
        ),
    }


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


def load_latest_symbol_record(
    *,
    exchange_name: str,
    symbol: str,
    analysis_root: str | Path = "analysis_logs",
) -> dict | None:
    """심볼별 최신 분석 로그 1건을 읽는다."""
    today_dir = Path(analysis_root) / current_date_str()
    if not today_dir.exists():
        return None
    candidate = today_dir / f"{exchange_name.strip().lower()}__{symbol.replace('/', '_')}.jsonl"
    if not candidate.exists():
        return None
    last_line = ""
    for line in candidate.read_text(encoding="utf-8").splitlines():
        if line.strip():
            last_line = line.strip()
    if not last_line:
        return None
    try:
        return json.loads(last_line)
    except (ValueError, json.JSONDecodeError):
        return None


def classify_symbol_regime(record: dict | None) -> SymbolRegimeSnapshot:
    """최신 분석 로그 1건으로 심볼별 레짐을 분류한다."""
    if not record:
        return SymbolRegimeSnapshot(
            regime="UNKNOWN",
            volume_ratio=None,
            avg_abs_change_pct=None,
            gap_pct=None,
            rsi=None,
            public_buy_ready=False,
            bullish_signal=False,
            bearish_signal=False,
            above_ma=False,
            htf_bullish=None,
            recorded_at_local=None,
        )

    thresholds = load_regime_thresholds()
    volume_ratio = safe_float(record.get("volume_ratio"))
    avg_abs_change_pct = safe_float(record.get("avg_abs_change_pct"))
    gap_pct = safe_float(record.get("gap_pct"))
    rsi = safe_float(record.get("rsi"))
    public_buy_ready = bool(record.get("public_buy_ready"))
    bullish_signal = bool(record.get("bullish_signal"))
    bearish_signal = bool(record.get("bearish_signal"))
    above_ma = bool(record.get("above_ma"))
    htf_bullish_raw = record.get("htf_bullish")
    htf_bullish = None if htf_bullish_raw is None else bool(htf_bullish_raw)

    regime = "CHOPPY"
    if (
        volume_ratio is not None
        and avg_abs_change_pct is not None
        and volume_ratio < float(load_low_energy_guard_settings().avg_volume_ratio_threshold)
        and avg_abs_change_pct < float(load_low_energy_guard_settings().avg_abs_change_pct_threshold)
        and not public_buy_ready
    ):
        regime = "LOW_ENERGY"
    elif (
        rsi is not None
        and volume_ratio is not None
        and above_ma
        and rsi >= float(thresholds["overheated_rsi_threshold"])
        and volume_ratio >= float(thresholds["overheated_volume_ratio_threshold"])
    ):
        regime = "OVERHEATED"
    elif (
        rsi is not None
        and above_ma
        and rsi >= float(thresholds["exhaustion_rsi_threshold"])
        and not public_buy_ready
    ):
        regime = "EXHAUSTION_RISK"
    elif (
        public_buy_ready
        or (
            bullish_signal
            and volume_ratio is not None
            and gap_pct is not None
            and volume_ratio >= float(thresholds["breakout_volume_ratio_threshold"])
            and gap_pct >= float(thresholds["breakout_gap_pct_threshold"])
        )
    ):
        regime = "BREAKOUT_ATTEMPT"
    elif (
        above_ma
        and (htf_bullish is True)
        and volume_ratio is not None
        and avg_abs_change_pct is not None
        and volume_ratio >= float(thresholds["trending_volume_ratio_threshold"])
        and avg_abs_change_pct >= float(thresholds["trending_avg_abs_change_pct_threshold"])
    ):
        regime = "TRENDING"

    return SymbolRegimeSnapshot(
        regime=regime,
        volume_ratio=volume_ratio,
        avg_abs_change_pct=avg_abs_change_pct,
        gap_pct=gap_pct,
        rsi=rsi,
        public_buy_ready=public_buy_ready,
        bullish_signal=bullish_signal,
        bearish_signal=bearish_signal,
        above_ma=above_ma,
        htf_bullish=htf_bullish,
        recorded_at_local=str(record.get("collected_at_local", "")) or None,
    )


REGIME_STATE_PATH = Path("logs") / "market_regime_state.json"


def update_regime_state(
    *,
    exchange_name: str,
    symbol: str,
    new_regime: str,
) -> tuple[bool, str | None]:
    """심볼별 이전 레짐과 비교해 알림이 필요한지 판단하고 상태를 저장한다."""
    thresholds = load_regime_thresholds()
    now_ts = time.time()
    key = f"{exchange_name.strip().lower()}::{symbol}"
    state: dict[str, dict] = {}
    if REGIME_STATE_PATH.exists():
        try:
            state = json.loads(REGIME_STATE_PATH.read_text(encoding="utf-8"))
        except (ValueError, json.JSONDecodeError):
            state = {}

    previous = state.get(key, {})
    previous_regime = previous.get("regime")
    last_alert_ts = float(previous.get("last_alert_ts", 0) or 0)
    changed = previous_regime != new_regime
    should_alert = changed and (now_ts - last_alert_ts >= int(thresholds["alert_min_interval_sec"]))

    state[key] = {
        "regime": new_regime,
        "updated_at_ts": now_ts,
        "last_alert_ts": now_ts if should_alert else last_alert_ts,
    }
    REGIME_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGIME_STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return should_alert, previous_regime


def build_regime_change_message(
    *,
    exchange_name: str,
    symbol: str,
    previous_regime: str | None,
    snapshot: SymbolRegimeSnapshot,
) -> str:
    """레짐 변경 알림 메시지를 만든다."""
    previous_text = previous_regime or "UNKNOWN"
    volume_text = "-" if snapshot.volume_ratio is None else f"{snapshot.volume_ratio:.3f}"
    abs_text = "-" if snapshot.avg_abs_change_pct is None else f"{snapshot.avg_abs_change_pct:.4f}%"
    gap_text = "-" if snapshot.gap_pct is None else f"{snapshot.gap_pct:.4f}%"
    rsi_text = "-" if snapshot.rsi is None else f"{snapshot.rsi:.1f}"
    return (
        f"[REGIME] {exchange_name.upper()} {symbol}\\n"
        f"이전 레짐: {previous_text}\\n"
        f"현재 레짐: {snapshot.regime}\\n"
        f"거래량 배수: {volume_text}\\n"
        f"평균 절대 변화율: {abs_text}\\n"
        f"이격도: {gap_text}\\n"
        f"RSI: {rsi_text}\\n"
        f"공개 준비: {'Y' if snapshot.public_buy_ready else 'N'}"
    )
