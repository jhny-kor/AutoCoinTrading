"""
수정 요약
- 2026-05-06: 텔레그램 문구가 단순 0->0 나열에 그치지 않도록 시간당 흐름과 판정 문구를 추가했다.
- 최근 변경 시점 전후의 전략 퍼널, 체결, 손절 변화를 자동 비교하는 리포트 모듈을 추가했다.

변경 효과 자동 비교 리포트

- structured_logs/live 의 strategy.jsonl 을 기준으로 scan / ready / order / filled / block reason 을 비교한다.
- trade_logs 의 trade_history.jsonl 을 함께 읽어 실현 손익과 손절 건수 변화를 비교한다.
- 기본 변경 시점은 CLI 에서 최신 git commit 시각으로 주입하고, 모듈은 명시 시각을 받아 테스트 가능하게 유지한다.
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from log_path_utils import iter_files


@dataclass(frozen=True)
class EffectWindow:
    """변경 효과 비교에 사용할 전후 기간."""

    label: str
    start_at: datetime
    end_at: datetime


def parse_timestamp(value: Any) -> datetime | None:
    """ISO 시각 문자열을 로컬 naive datetime 으로 변환한다."""
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone().replace(tzinfo=None)
    return parsed


def safe_float(value: Any) -> float | None:
    """숫자 후보를 float 으로 안전하게 변환한다."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_line_timestamp(line: str) -> datetime | None:
    """JSONL 한 줄에서 timestamp 필드만 가볍게 추출한다."""
    for key in ("recorded_at_local", "recorded_at"):
        marker = f'"{key}":"'
        start = line.find(marker)
        if start < 0:
            continue
        start += len(marker)
        end = line.find('"', start)
        if end < 0:
            continue
        parsed = parse_timestamp(line[start:end])
        if parsed is not None:
            return parsed
    return None


def read_jsonl(
    path: Path,
    *,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """JSONL 파일을 안전하게 읽는다."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        f = path.open("r", encoding="utf-8")
    except OSError:
        return rows
    with f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            line_ts = extract_line_timestamp(stripped)
            if line_ts is not None:
                if start_at is not None and line_ts < start_at:
                    continue
                if end_at is not None and line_ts >= end_at:
                    break
            try:
                payload = json.loads(stripped)
            except (ValueError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def extract_path_date(path: Path) -> date | None:
    """경로 조각에서 YYYY-MM-DD 날짜를 찾는다."""
    for part in path.parts:
        try:
            return datetime.strptime(part, "%Y-%m-%d").date()
        except ValueError:
            continue
    return None


def path_overlaps_window(path: Path, start_at: datetime | None, end_at: datetime | None) -> bool:
    """파일 경로의 날짜가 조회 구간과 겹치는지 확인한다."""
    if start_at is None and end_at is None:
        return True
    path_date = extract_path_date(path)
    if path_date is None:
        return True
    if start_at is not None and path_date < start_at.date():
        return False
    if end_at is not None and path_date > end_at.date():
        return False
    return True


def iter_jsonl_records(
    base_dir: Path,
    filename: str,
    *,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """base_dir 아래의 JSONL 파일들을 모두 읽는다."""
    rows: list[dict[str, Any]] = []
    if not base_dir.exists():
        return rows
    for path in iter_files(base_dir, filename):
        if not path_overlaps_window(path, start_at, end_at):
            continue
        rows.extend(read_jsonl(path, start_at=start_at, end_at=end_at))
    return rows


def load_latest_git_commit_time() -> datetime | None:
    """최신 git commit 시각을 로컬 naive datetime 으로 반환한다."""
    try:
        raw = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return parse_timestamp(raw)


def build_windows(
    change_at: datetime,
    *,
    hours: float = 12.0,
    now: datetime | None = None,
) -> tuple[EffectWindow, EffectWindow]:
    """변경 시점 전후 비교 기간을 만든다."""
    current = now or datetime.now()
    span = timedelta(hours=hours)
    before = EffectWindow("before", change_at - span, change_at)
    after = EffectWindow("after", change_at, min(current, change_at + span))
    return before, after


def in_window(record: dict[str, Any], window: EffectWindow) -> bool:
    """레코드의 로컬 시각이 window 안에 포함되는지 확인한다."""
    ts = parse_timestamp(record.get("recorded_at_local") or record.get("recorded_at"))
    if ts is None:
        return False
    return window.start_at <= ts < window.end_at


def summarize_strategy_window(
    records: list[dict[str, Any]],
    window: EffectWindow,
) -> dict[str, Any]:
    """전략 로그에서 퍼널 지표를 집계한다."""
    duration_hours = max(
        (window.end_at - window.start_at).total_seconds() / 3600.0,
        0.0001,
    )
    selected = [record for record in records if in_window(record, window)]
    entry_records = [
        record for record in selected if str(record.get("side", "")).lower() == "entry"
    ]
    scans = [
        record
        for record in entry_records
        if record.get("stage") == "scan" and record.get("result") == "seen"
    ]
    ready = [
        record
        for record in entry_records
        if record.get("stage") == "buy_ready" and record.get("result") == "ready"
    ]
    requested = [
        record
        for record in entry_records
        if record.get("stage") == "order_requested"
        and record.get("result") == "requested"
    ]
    filled = [
        record
        for record in entry_records
        if record.get("stage") == "filled" and record.get("result") == "filled"
    ]
    blocked = [
        record
        for record in entry_records
        if record.get("result") == "blocked"
        and str(record.get("reason", "")) not in {"no_position"}
    ]

    block_reasons = Counter(str(record.get("reason", "")) for record in blocked)
    block_stages = Counter(str(record.get("stage", "")) for record in blocked)
    signal_scores: list[float] = []
    position_ratios: list[float] = []
    for record in scans:
        metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
        score = safe_float(metrics.get("signal_score"))
        ratio = safe_float(metrics.get("effective_position_ratio"))
        if ratio is None:
            ratio = safe_float(metrics.get("position_ratio"))
        if score is not None:
            signal_scores.append(score)
        if ratio is not None:
            position_ratios.append(ratio)

    scan_count = len(scans)
    ready_count = len(ready)
    requested_count = len(requested)
    filled_count = len(filled)
    return {
        "window": window.label,
        "start_at": window.start_at.isoformat(),
        "end_at": window.end_at.isoformat(),
        "duration_hours": duration_hours,
        "scan_count": scan_count,
        "ready_count": ready_count,
        "order_requested_count": requested_count,
        "entry_filled_count": filled_count,
        "blocked_count": len(blocked),
        "scan_per_hour": scan_count / duration_hours,
        "ready_per_hour": ready_count / duration_hours,
        "entry_filled_per_hour": filled_count / duration_hours,
        "blocked_per_hour": len(blocked) / duration_hours,
        "ready_rate_pct": (ready_count / scan_count) * 100 if scan_count else 0.0,
        "request_rate_pct": (requested_count / ready_count) * 100 if ready_count else 0.0,
        "fill_rate_pct": (filled_count / requested_count) * 100 if requested_count else 0.0,
        "avg_signal_score": (
            sum(signal_scores) / len(signal_scores) if signal_scores else None
        ),
        "avg_effective_position_ratio": (
            sum(position_ratios) / len(position_ratios) if position_ratios else None
        ),
        "top_block_reasons": block_reasons.most_common(8),
        "top_block_stages": block_stages.most_common(8),
    }


def summarize_trade_window(
    records: list[dict[str, Any]],
    window: EffectWindow,
) -> dict[str, Any]:
    """체결 이력에서 실현 손익과 손절 건수를 집계한다."""
    selected = [record for record in records if in_window(record, window)]
    sells = [record for record in selected if str(record.get("side", "")).lower() == "sell"]
    buys = [record for record in selected if str(record.get("side", "")).lower() == "buy"]
    pnl_values: list[float] = []
    pnl_quote_values: list[float] = []
    for record in sells:
        pnl_pct = safe_float(record.get("net_realized_pnl_pct"))
        if pnl_pct is None:
            pnl_pct = safe_float(record.get("realized_pnl_pct"))
        pnl_quote = safe_float(record.get("net_realized_pnl_quote"))
        if pnl_quote is None:
            pnl_quote = safe_float(record.get("realized_pnl_quote"))
        if pnl_pct is not None:
            pnl_values.append(pnl_pct)
        if pnl_quote is not None:
            pnl_quote_values.append(pnl_quote)

    stop_loss_count = sum(
        1 for record in sells if "stop" in str(record.get("reason", "")).lower()
    )
    win_count = sum(1 for value in pnl_values if value > 0)
    return {
        "buy_count": len(buys),
        "sell_count": len(sells),
        "stop_loss_count": stop_loss_count,
        "win_count": win_count,
        "win_rate_pct": (win_count / len(pnl_values)) * 100 if pnl_values else 0.0,
        "avg_net_pnl_pct": sum(pnl_values) / len(pnl_values) if pnl_values else None,
        "total_net_pnl_quote": sum(pnl_quote_values),
        "pnl_sample_count": len(pnl_values),
    }


def build_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """전후 요약의 핵심 차이를 계산한다."""
    numeric_keys = [
        "scan_count",
        "ready_count",
        "order_requested_count",
        "entry_filled_count",
        "blocked_count",
        "ready_rate_pct",
        "request_rate_pct",
        "fill_rate_pct",
        "buy_count",
        "sell_count",
        "stop_loss_count",
        "win_rate_pct",
        "total_net_pnl_quote",
    ]
    delta: dict[str, Any] = {}
    for key in numeric_keys:
        delta[key] = float(after.get(key, 0.0) or 0.0) - float(before.get(key, 0.0) or 0.0)
    if before.get("avg_net_pnl_pct") is not None and after.get("avg_net_pnl_pct") is not None:
        delta["avg_net_pnl_pct"] = float(after["avg_net_pnl_pct"]) - float(before["avg_net_pnl_pct"])
    else:
        delta["avg_net_pnl_pct"] = None
    if before.get("avg_signal_score") is not None and after.get("avg_signal_score") is not None:
        delta["avg_signal_score"] = float(after["avg_signal_score"]) - float(before["avg_signal_score"])
    else:
        delta["avg_signal_score"] = None
    return delta


def build_change_effect_report(
    *,
    change_at: datetime | None = None,
    hours: float = 12.0,
    now: datetime | None = None,
    strategy_log_root: Path | str = Path("structured_logs/live"),
    trade_log_root: Path | str = Path("trade_logs"),
) -> dict[str, Any]:
    """전략 로그와 체결 로그를 읽어 변경 효과 비교 payload 를 만든다."""
    resolved_change_at = change_at or load_latest_git_commit_time()
    if resolved_change_at is None:
        raise ValueError("변경 기준 시각을 찾을 수 없습니다. change_at 을 명시해 주세요.")

    before_window, after_window = build_windows(
        resolved_change_at,
        hours=hours,
        now=now,
    )
    strategy_records = iter_jsonl_records(
        Path(strategy_log_root),
        "strategy.jsonl",
        start_at=before_window.start_at,
        end_at=after_window.end_at,
    )
    trade_records = iter_jsonl_records(
        Path(trade_log_root),
        "trade_history.jsonl",
        start_at=before_window.start_at,
        end_at=after_window.end_at,
    )

    before_strategy = summarize_strategy_window(strategy_records, before_window)
    after_strategy = summarize_strategy_window(strategy_records, after_window)
    before_trade = summarize_trade_window(trade_records, before_window)
    after_trade = summarize_trade_window(trade_records, after_window)
    before = {**before_strategy, **before_trade}
    after = {**after_strategy, **after_trade}

    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "change_at": resolved_change_at.isoformat(),
        "hours": hours,
        "before": before,
        "after": after,
        "delta": build_delta(before, after),
    }


def format_count_delta(value: float) -> str:
    """정수형 delta 를 표시한다."""
    return f"{value:+.0f}"


def format_pct(value: float | None) -> str:
    """퍼센트 값을 표시한다."""
    if value is None:
        return "-"
    return f"{value:.2f}%"


def format_float(value: float | None, decimals: int = 4) -> str:
    """실수 값을 표시한다."""
    if value is None:
        return "-"
    return f"{value:.{decimals}f}"


def format_signed_float(value: float | None, decimals: int = 2) -> str:
    """부호를 포함한 실수 값을 표시한다."""
    if value is None:
        return "표본부족"
    return f"{value:+.{decimals}f}"


def format_top_reasons(reasons: list[Any], limit: int = 3) -> str:
    """상위 차단 사유 목록을 짧게 표시한다."""
    normalized: list[tuple[str, int]] = []
    for item in reasons[:limit]:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            normalized.append((str(item[0]), int(item[1])))
    if not normalized:
        return "없음"
    return ", ".join(f"{name}:{count}" for name, count in normalized)


def build_change_effect_verdict(before: dict[str, Any], after: dict[str, Any], delta: dict[str, Any]) -> str:
    """변경 효과를 사람이 바로 판단할 수 있는 한 줄로 요약한다."""
    after_filled = int(after.get("entry_filled_count", 0) or 0)
    after_sells = int(after.get("sell_count", 0) or 0)
    after_stop_losses = int(after.get("stop_loss_count", 0) or 0)
    after_ready_rate = float(after.get("ready_rate_pct", 0.0) or 0.0)
    avg_pnl_delta = delta.get("avg_net_pnl_pct")

    if after_filled == 0 and after_sells == 0:
        if after_ready_rate <= 0:
            return "판정: 실체결 표본 없음. 현재는 진입 게이트가 계속 막혀 있어 병목과 가상 후보를 우선 봐야 합니다."
        return "판정: 실체결 표본 없음. ready 후보는 있으므로 다음 체결 후 손익 품질을 재확인해야 합니다."
    if after_stop_losses > 0 and float(delta.get("stop_loss_count", 0.0) or 0.0) > 0:
        return "판정: 손절이 늘었습니다. 완화보다 손절 발생 후보의 공통 조건을 먼저 조여야 합니다."
    if after_sells > 0 and avg_pnl_delta is not None and float(avg_pnl_delta) > 0 and after_stop_losses == 0:
        return "판정: 전후 비교상 실현 손익은 개선 방향입니다. 같은 조건의 표본을 더 쌓아 유지 여부를 확인합니다."
    if after_sells > 0 and avg_pnl_delta is not None and float(avg_pnl_delta) < 0:
        return "판정: 평균 손익이 악화됐습니다. 진입 완화 조건을 다시 분해해서 확인해야 합니다."
    return "판정: 방향성은 아직 중립입니다. 체결 표본과 미체결 후보 결과를 함께 보며 다음 조정을 판단합니다."


def format_change_effect_text(report: dict[str, Any]) -> str:
    """변경 효과 비교 payload 를 텔레그램/CLI 문구로 만든다."""
    before = report.get("before", {}) if isinstance(report.get("before"), dict) else {}
    after = report.get("after", {}) if isinstance(report.get("after"), dict) else {}
    delta = report.get("delta", {}) if isinstance(report.get("delta"), dict) else {}
    signal_delta = delta.get("avg_signal_score")
    pnl_delta = delta.get("avg_net_pnl_pct")
    lines = [
        "변경 효과 자동 비교",
        f"- 기준: {report.get('change_at')} / 전후 최대 {report.get('hours')}시간",
        f"- {build_change_effect_verdict(before, after, delta)}",
        (
            "- 진입 흐름: "
            f"scan/h {format_float(before.get('scan_per_hour'), 1)}"
            f"->{format_float(after.get('scan_per_hour'), 1)} | "
            f"ready {int(before.get('ready_count', 0))}->{int(after.get('ready_count', 0))} | "
            f"진입체결 {int(before.get('entry_filled_count', 0))}->{int(after.get('entry_filled_count', 0))}"
        ),
        (
            "- 게이트 품질: "
            f"ready율 {format_pct(before.get('ready_rate_pct'))}->{format_pct(after.get('ready_rate_pct'))} | "
            f"평균 점수 {format_float(before.get('avg_signal_score'), 2)}"
            f"->{format_float(after.get('avg_signal_score'), 2)} "
            f"({format_signed_float(signal_delta, 2)})"
        ),
        (
            "- 실현 결과: "
            f"매도 {int(before.get('sell_count', 0))}->{int(after.get('sell_count', 0))} | "
            f"손절 {int(before.get('stop_loss_count', 0))}->{int(after.get('stop_loss_count', 0))} "
            f"({format_count_delta(float(delta.get('stop_loss_count', 0.0)))}) | "
            f"평균 순손익 {format_float(before.get('avg_net_pnl_pct'), 3)}%"
            f"->{format_float(after.get('avg_net_pnl_pct'), 3)}% "
            f"({format_signed_float(pnl_delta, 3)})"
        ),
        f"- 이전 주요 차단: {format_top_reasons(before.get('top_block_reasons', []))}",
        f"- 이후 주요 차단: {format_top_reasons(after.get('top_block_reasons', []))}",
    ]
    return "\n".join(lines)


def write_report(report: dict[str, Any], output_dir: Path | str = Path("reports/change_effect")) -> Path:
    """변경 효과 비교 결과를 JSON 파일로 저장한다."""
    output_root = Path(output_dir)
    generated_at = parse_timestamp(report.get("generated_at")) or datetime.now()
    date_dir = output_root / generated_at.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    path = date_dir / f"change_effect_{generated_at.strftime('%H%M%S')}.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
