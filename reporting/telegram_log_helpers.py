"""
작업 요약
- 텔레그램 명령 리스너의 시간 판정과 최근 로그 파일 읽기 helper 를 분리했다.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from log_path_utils import iter_files, latest_file, read_all_lines
from reporting.telegram_formatting import extract_symbol_from_log_line


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


def is_in_recent_days(raw: str, days: int, *, now: datetime | None = None) -> bool:
    """지정된 최근 일수 범위 안의 시각인지 확인한다."""
    parsed = parse_local_timestamp(raw)
    if parsed is None:
        return False
    current = now or datetime.now()
    lower_bound = current - timedelta(days=days)
    return lower_bound <= parsed <= current


def is_today_timestamp(ts: str) -> bool:
    """로그 타임스탬프가 오늘 날짜인지 확인한다."""
    return ts.startswith(datetime.now().strftime("%Y-%m-%d"))


def iter_log_lines(filename: str) -> list[str]:
    """같은 이름의 날짜별 로그 파일 줄 목록을 모두 읽는다."""
    return read_all_lines(iter_files("logs", filename))


def latest_log_file(filename: str) -> Path | None:
    """같은 이름의 날짜별 로그 중 가장 최근 파일을 반환한다."""
    return latest_file("logs", filename)


def read_recent_lines(path: Path | None, line_count: int) -> list[str]:
    """파일 끝부분의 최근 줄만 읽는다."""
    if path is None or not path.exists():
        return ["로그 파일이 없습니다."]

    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return ["로그 내용이 없습니다."]
    return lines[-line_count:]


def read_recent_lines_by_symbol(
    filename: str,
    line_count: int,
    symbol_order: list[str] | None = None,
    lookback_multiplier: int = 20,
) -> dict[str, list[str]]:
    """파일 끝부분에서 심볼별 최근 줄을 모아 반환한다."""
    path = latest_log_file(filename)
    if path is None or not path.exists():
        return {"공통": ["로그 파일이 없습니다."]}

    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return {"공통": ["로그 내용이 없습니다."]}

    lookback_count = max(line_count * lookback_multiplier, 80)
    recent_lines = lines[-lookback_count:]
    grouped: dict[str, list[str]] = {}

    for line in recent_lines:
        symbol = extract_symbol_from_log_line(line) or "공통"
        grouped.setdefault(symbol, []).append(line)

    trimmed = {
        symbol: entries[-line_count:]
        for symbol, entries in grouped.items()
        if entries
    }

    has_symbol_specific_logs = any(symbol != "공통" for symbol in trimmed)
    if has_symbol_specific_logs and "공통" in trimmed:
        trimmed.pop("공통", None)

    if not symbol_order:
        return trimmed

    ordered: dict[str, list[str]] = {}
    for symbol in symbol_order:
        if symbol in trimmed:
            ordered[symbol] = trimmed[symbol]
    for symbol, entries in trimmed.items():
        if symbol not in ordered:
            ordered[symbol] = entries
    return ordered
