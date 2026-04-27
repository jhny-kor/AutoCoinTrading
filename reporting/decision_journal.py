"""
수정 요약
- TradingAgents 의 decision log / reflection 방식을 실거래 체결 로그와 연결하는 경량 decision journal 을 추가했다.
- 체결마다 risk review 와 사람이 읽을 수 있는 reflection 을 JSONL 로 누적해 텔레그램 분석 리포트에서 재사용할 수 있게 했다.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from core.risk.review import build_reflection, build_trade_risk_review
from log_path_utils import dated_path, iter_files
from trade_history_logger import to_json_safe


DEFAULT_JOURNAL_ROOT = Path("reports") / "decision_journal"
DEFAULT_JOURNAL_FILENAME = "decision_journal.jsonl"


def append_decision_journal_entry(
    trade_record: dict[str, Any],
    *,
    root_dir: str | Path = DEFAULT_JOURNAL_ROOT,
    filename: str = DEFAULT_JOURNAL_FILENAME,
) -> dict[str, Any]:
    """체결 레코드를 risk review 와 reflection 이 포함된 journal entry 로 저장한다."""
    review = build_trade_risk_review(trade_record)
    entry = {
        "recorded_at": datetime.now().astimezone().isoformat(),
        "trade_recorded_at": trade_record.get("recorded_at"),
        "trade_recorded_at_local": trade_record.get("recorded_at_local"),
        "exchange": trade_record.get("exchange"),
        "program_name": trade_record.get("program_name"),
        "symbol": trade_record.get("symbol"),
        "side": trade_record.get("side"),
        "reason": trade_record.get("reason"),
        "is_final_exit": trade_record.get("is_final_exit"),
        "net_realized_pnl_pct": trade_record.get("net_realized_pnl_pct"),
        "realized_pnl_pct": trade_record.get("realized_pnl_pct"),
        "mfe_pct": trade_record.get("mfe_pct"),
        "mae_pct": trade_record.get("mae_pct"),
        "holding_seconds": trade_record.get("holding_seconds"),
        "risk_review": review.to_dict(),
        "reflection": build_reflection(trade_record, review),
    }
    path = dated_path(Path(root_dir), filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(to_json_safe(entry), ensure_ascii=False, separators=(",", ":")) + "\n")
    return entry


def read_recent_decision_journal(
    *,
    days: int = 7,
    root_dir: str | Path = DEFAULT_JOURNAL_ROOT,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """최근 N일 decision journal entry 를 읽는다."""
    cutoff = (now or datetime.now().astimezone()) - timedelta(days=days)
    rows: list[dict[str, Any]] = []
    for path in iter_files(root_dir, DEFAULT_JOURNAL_FILENAME):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except (ValueError, json.JSONDecodeError):
                continue
            recorded_at = _parse_datetime(str(record.get("recorded_at", "") or ""))
            if recorded_at is None or recorded_at < cutoff:
                continue
            rows.append(record)
    rows.sort(key=lambda item: str(item.get("recorded_at", "")))
    return rows


def build_recent_reflection_summary(
    *,
    days: int = 7,
    limit: int = 6,
    root_dir: str | Path = DEFAULT_JOURNAL_ROOT,
) -> str:
    """최근 decision journal 을 텔레그램 리포트용 요약 문자열로 만든다."""
    rows = read_recent_decision_journal(days=days, root_dir=root_dir)
    if not rows:
        rows = build_decision_journal_entries_from_trade_history(days=days)
    if not rows:
        return f"최근 {days}일 의사결정 리뷰\n- 아직 decision journal 기록이 없습니다."

    concern_counts: dict[str, int] = {}
    review_counts: dict[str, int] = {}
    reflections: list[str] = []
    for row in rows:
        review = row.get("risk_review") if isinstance(row.get("risk_review"), dict) else {}
        posture = str(review.get("posture", "") or "unknown")
        review_counts[posture] = review_counts.get(posture, 0) + 1
        for concern in review.get("concerns", []) if isinstance(review.get("concerns"), list) else []:
            concern_text = str(concern)
            concern_counts[concern_text] = concern_counts.get(concern_text, 0) + 1
        reflection = str(row.get("reflection", "") or "").strip()
        if reflection:
            reflections.append(reflection)

    lines = [f"최근 {days}일 의사결정 리뷰"]
    if review_counts:
        posture_text = ", ".join(
            f"{key} {value}건" for key, value in sorted(review_counts.items())
        )
        lines.append(f"- risk posture: {posture_text}")
    if concern_counts:
        top_concerns = sorted(concern_counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
        lines.append(
            "- 주요 우려: "
            + ", ".join(f"{name} {count}건" for name, count in top_concerns)
        )
    if reflections:
        lines.append("- 최근 reflection:")
        for reflection in reflections[-limit:]:
            lines.append(f"  {reflection}")
    return "\n".join(lines)


def build_decision_journal_entries_from_trade_history(*, days: int = 7) -> list[dict[str, Any]]:
    """decision journal 이 없을 때 최근 trade_history 에서 임시 review entry 를 만든다."""
    cutoff = datetime.now().astimezone() - timedelta(days=days)
    rows: list[dict[str, Any]] = []
    for path in iter_files("trade_logs", "trade_history.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except (ValueError, json.JSONDecodeError):
                continue
            recorded_at = _parse_datetime(
                str(record.get("recorded_at_local") or record.get("recorded_at") or "")
            )
            if recorded_at is None or recorded_at < cutoff:
                continue
            review = build_trade_risk_review(record)
            rows.append(
                {
                    "recorded_at": datetime.now().astimezone().isoformat(),
                    "trade_recorded_at": record.get("recorded_at"),
                    "trade_recorded_at_local": record.get("recorded_at_local"),
                    "exchange": record.get("exchange"),
                    "program_name": record.get("program_name"),
                    "symbol": record.get("symbol"),
                    "side": record.get("side"),
                    "reason": record.get("reason"),
                    "is_final_exit": record.get("is_final_exit"),
                    "net_realized_pnl_pct": record.get("net_realized_pnl_pct"),
                    "realized_pnl_pct": record.get("realized_pnl_pct"),
                    "mfe_pct": record.get("mfe_pct"),
                    "mae_pct": record.get("mae_pct"),
                    "holding_seconds": record.get("holding_seconds"),
                    "risk_review": review.to_dict(),
                    "reflection": build_reflection(record, review),
                }
            )
    return rows


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
