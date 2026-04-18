"""
월간 PnL 캘린더 스냅샷 저장기

- trade_logs 원본에서 일자/통화별 실현 손익 합계를 계산한다.
- 기존 스냅샷이 있으면 이미 삭제된 과거 날짜 값은 유지하고, 현재 원본 로그가 있는 날짜는 최신 값으로 덮어쓴다.
- 로그 삭제 배치 전에 실행해 웹 월간 PnL 캘린더가 원본 삭제 후에도 값을 유지하도록 돕는다.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
TRADE_LOG_ROOT = ROOT_DIR / "trade_logs"
SNAPSHOT_PATH = ROOT_DIR / "reports" / "pnl_calendar" / "daily_realized_pnl.json"


def safe_float(value) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def load_existing_snapshot() -> dict[str, dict[str, float]]:
    if not SNAPSHOT_PATH.exists():
        return {}
    try:
        payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    daily = payload.get("daily_totals")
    if not isinstance(daily, dict):
        return {}
    result: dict[str, dict[str, float]] = {}
    for day_text, values in daily.items():
        if not isinstance(values, dict):
            continue
        bucket: dict[str, float] = {}
        for currency, raw_value in values.items():
            parsed = safe_float(raw_value)
            if parsed is not None:
                bucket[str(currency)] = parsed
        if bucket:
            result[str(day_text)] = bucket
    return result


def collect_current_trade_totals() -> dict[str, dict[str, float]]:
    daily_totals: dict[str, dict[str, float]] = {}
    if not TRADE_LOG_ROOT.exists():
        return daily_totals

    for day_dir in sorted(TRADE_LOG_ROOT.iterdir()):
        if not day_dir.is_dir():
            continue
        history_path = day_dir / "trade_history.jsonl"
        if not history_path.is_file():
            continue
        try:
            lines = history_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(record.get("side", "")).lower() != "sell":
                continue

            pnl_value = safe_float(record.get("net_realized_pnl_quote"))
            if pnl_value is None:
                pnl_value = safe_float(record.get("realized_pnl_quote"))
            if pnl_value is None:
                continue

            local_time = str(record.get("recorded_at_local") or record.get("recorded_at") or "").strip()
            date_text = local_time[:10] if len(local_time) >= 10 else day_dir.name
            currency = str(record.get("quote_currency") or "QUOTE").strip() or "QUOTE"

            bucket = daily_totals.setdefault(date_text, {})
            bucket[currency] = bucket.get(currency, 0.0) + pnl_value

    return daily_totals


def write_snapshot(daily_totals: dict[str, dict[str, float]]) -> None:
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "daily_totals": daily_totals,
    }
    SNAPSHOT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main() -> int:
    existing = load_existing_snapshot()
    current = collect_current_trade_totals()

    merged = existing.copy()
    merged.update(current)
    write_snapshot(merged)

    print("[PNL 스냅샷] 월간 PnL 캘린더 저장")
    print(f"저장 경로: {SNAPSHOT_PATH}")
    print(f"저장 일수: {len(merged)}")
    print(f"현재 로그 기준 갱신 일수: {len(current)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
