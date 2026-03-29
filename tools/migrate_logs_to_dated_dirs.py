"""기존 평면 로그를 날짜별 폴더 구조로 옮기는 마이그레이션 도구."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from log_path_utils import dated_path


TEXT_TS_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2}\]")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def append_text_grouped(src: Path, dry_run: bool) -> int:
    """루트 logs 의 평면 텍스트 로그를 날짜별로 분리한다."""
    groups: dict[str, list[str]] = defaultdict(list)
    current_day: str | None = None
    for line in src.read_text(encoding="utf-8").splitlines():
        match = TEXT_TS_RE.match(line)
        if match:
            current_day = match.group(1)
        if current_day is None:
            current_day = datetime.fromtimestamp(src.stat().st_mtime).strftime("%Y-%m-%d")
        groups[current_day].append(line)

    for day, lines in groups.items():
        dst = dated_path("logs", src.name, date_str=day)
        if dry_run:
            continue
        ensure_parent(dst)
        with dst.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    if not dry_run:
        src.unlink()
    return sum(len(lines) for lines in groups.values())


def parse_json_line_day(line: str, keys: list[str], fallback_day: str) -> tuple[str, dict] | None:
    """JSONL 한 줄에서 날짜와 레코드를 추출한다."""
    stripped = line.strip()
    if not stripped:
        return None
    try:
        record = json.loads(stripped)
    except (ValueError, json.JSONDecodeError):
        return None

    for key in keys:
        value = str(record.get(key, "")).strip()
        if value:
            return value[:10], record
    return fallback_day, record


def append_jsonl_grouped(src: Path, dst_root: Path, filename: str, keys: list[str], dry_run: bool) -> int:
    """평면 JSONL 로그를 날짜별로 분리한다."""
    fallback_day = datetime.fromtimestamp(src.stat().st_mtime).strftime("%Y-%m-%d")
    groups: dict[str, list[str]] = defaultdict(list)
    for line in src.read_text(encoding="utf-8").splitlines():
        parsed = parse_json_line_day(line, keys, fallback_day)
        if parsed is None:
            continue
        day, record = parsed
        groups[day].append(json.dumps(record, ensure_ascii=False, separators=(",", ":")))

    for day, lines in groups.items():
        dst = dated_path(dst_root, filename, date_str=day)
        if dry_run:
            continue
        ensure_parent(dst)
        with dst.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    if not dry_run:
        src.unlink()
    return sum(len(lines) for lines in groups.values())


def migrate_structured_program_jsonl(src: Path, dry_run: bool) -> int:
    """기존 structured_logs/live/<program>/*.jsonl 을 날짜별로 옮긴다."""
    program_name = src.parent.name
    return append_jsonl_grouped(
        src,
        Path("structured_logs/live"),
        f"{program_name}/{src.name}",
        ["recorded_at_local", "recorded_at"],
        dry_run,
    )


def migrate_summary_file(src: Path, dry_run: bool) -> int:
    """기존 summary_1h 파일을 날짜별 디렉토리로 옮긴다."""
    program_name = src.parent.parent.name
    day = None
    try:
        payload = json.loads(src.read_text(encoding="utf-8"))
        time_bucket = str(payload.get("time_bucket", "")).strip()
        if time_bucket:
            day = time_bucket[:10]
    except (OSError, ValueError, json.JSONDecodeError):
        day = None

    if day is None:
        day = datetime.fromtimestamp(src.stat().st_mtime).strftime("%Y-%m-%d")

    dst = dated_path(
        "structured_logs/live",
        program_name,
        "summary_1h",
        src.name,
        date_str=day,
    )
    if not dry_run:
        ensure_parent(dst)
        shutil.copy2(src, dst)
        src.unlink()
    return 1


def migrate_logs(dry_run: bool = False) -> dict[str, int]:
    """기존 평면 로그를 날짜별 구조로 옮긴다."""
    moved_counts = defaultdict(int)

    for src in Path("logs").glob("*.log"):
        moved_counts["logs_lines"] += append_text_grouped(src, dry_run)

    for src in Path("analysis_logs").glob("*.jsonl"):
        moved_counts["analysis_records"] += append_jsonl_grouped(
            src,
            Path("analysis_logs"),
            src.name,
            ["collected_at_local", "collected_at"],
            dry_run,
        )

    for src in Path("trade_logs").glob("*.jsonl"):
        moved_counts["trade_records"] += append_jsonl_grouped(
            src,
            Path("trade_logs"),
            src.name,
            ["recorded_at_local", "recorded_at"],
            dry_run,
        )

    for src in Path("structured_logs/live").glob("*/*.jsonl"):
        if src.parent.name == "summary_1h":
            continue
        moved_counts["structured_records"] += migrate_structured_program_jsonl(src, dry_run)

    for src in Path("structured_logs/live").glob("*/summary_1h/*.json"):
        moved_counts["summary_files"] += migrate_summary_file(src, dry_run)

    return dict(moved_counts)


def main() -> None:
    parser = argparse.ArgumentParser(description="기존 로그를 날짜별 폴더 구조로 옮깁니다.")
    parser.add_argument("--dry-run", action="store_true", help="실제 변경 없이 대상만 점검합니다.")
    args = parser.parse_args()

    result = migrate_logs(dry_run=args.dry_run)
    print("=== 로그 마이그레이션 결과 ===")
    if not result:
        print("옮길 기존 평면 로그가 없습니다.")
        return
    for key, value in sorted(result.items()):
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
