"""
수정 요약
- 오래된 로그를 gzip 으로 압축해 보관하는 관리 도구 추가
- 최근 수정된 활성 로그는 건드리지 않고, 일정 시간 이상 지난 로그만 안전하게 압축하도록 구성
- 로그 압축 후보 미리보기와 실제 압축 실행을 분리해 운영 중에도 점검하기 쉽게 구성

로그 압축/보관 관리자

- logs, analysis_logs, trade_logs, structured_logs 아래의 오래된 로그를 찾아 gzip 으로 압축한다.
- 기본적으로 최근 6시간 안에 수정된 파일은 활성 로그로 보고 압축하지 않는다.
- status 로 압축 후보를 미리 보고, compress 로 실제 압축을 수행할 수 있다.

사용 예시
- .venv/bin/python log_archive_manager.py status
- .venv/bin/python log_archive_manager.py compress
- .venv/bin/python log_archive_manager.py compress --min-age-hours 24
"""

from __future__ import annotations

import argparse
import gzip
import shutil
import time
from dataclasses import dataclass
from pathlib import Path


LOG_ROOTS = [
    Path("logs"),
    Path("analysis_logs"),
    Path("trade_logs"),
    Path("structured_logs"),
]

TARGET_SUFFIXES = {".log", ".jsonl", ".json"}


@dataclass(frozen=True)
class ArchiveCandidate:
    path: Path
    size_bytes: int
    modified_at: float


def iter_candidates(min_age_hours: float) -> list[ArchiveCandidate]:
    """압축 가능한 로그 후보를 수집한다."""
    now = time.time()
    min_age_sec = min_age_hours * 3600
    candidates: list[ArchiveCandidate] = []

    for root in LOG_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix == ".gz":
                continue
            if path.suffix not in TARGET_SUFFIXES:
                continue
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            if (now - stat.st_mtime) < min_age_sec:
                continue
            candidates.append(
                ArchiveCandidate(
                    path=path,
                    size_bytes=stat.st_size,
                    modified_at=stat.st_mtime,
                )
            )
    return sorted(candidates, key=lambda item: (str(item.path), item.modified_at))


def format_bytes(size: int) -> str:
    """바이트 단위를 보기 쉽게 포맷한다."""
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{size}B"


def show_status(candidates: list[ArchiveCandidate]) -> None:
    """압축 후보를 요약해서 보여준다."""
    total_size = sum(item.size_bytes for item in candidates)
    print("=== 로그 압축 후보 ===")
    print(f"후보 파일 수: {len(candidates)}")
    print(f"총 원본 크기: {format_bytes(total_size)}")
    for item in candidates[:50]:
        age_hours = (time.time() - item.modified_at) / 3600
        print(
            f"- {item.path} | {format_bytes(item.size_bytes)} | "
            f"마지막 수정 {age_hours:.1f}시간 전"
        )
    if len(candidates) > 50:
        print(f"... 외 {len(candidates) - 50}개")


def compress_candidates(candidates: list[ArchiveCandidate]) -> None:
    """후보 파일을 gzip 으로 압축하고 원본을 제거한다."""
    compressed_count = 0
    original_total = 0
    compressed_total = 0

    for item in candidates:
        src = item.path
        dst = src.with_suffix(src.suffix + ".gz")
        if dst.exists():
            continue
        with src.open("rb") as f_in, gzip.open(dst, "wb", compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)
        compressed_size = dst.stat().st_size
        src.unlink()
        compressed_count += 1
        original_total += item.size_bytes
        compressed_total += compressed_size
        print(
            f"[압축 완료] {src} -> {dst} | "
            f"{format_bytes(item.size_bytes)} -> {format_bytes(compressed_size)}"
        )

    print("=== 로그 압축 결과 ===")
    print(f"압축 파일 수: {compressed_count}")
    print(f"원본 총 크기: {format_bytes(original_total)}")
    print(f"압축 총 크기: {format_bytes(compressed_total)}")
    if original_total > 0:
        saved = original_total - compressed_total
        print(f"절감 크기: {format_bytes(saved)}")


def main() -> None:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(description="오래된 로그를 gzip 으로 압축합니다.")
    parser.add_argument(
        "command",
        choices=["status", "compress"],
        help="status 는 후보 조회, compress 는 실제 압축 실행",
    )
    parser.add_argument(
        "--min-age-hours",
        type=float,
        default=6.0,
        help="이 시간 이상 수정되지 않은 파일만 압축 후보로 봅니다. 기본값 6시간",
    )
    args = parser.parse_args()

    candidates = iter_candidates(args.min_age_hours)
    if args.command == "status":
        show_status(candidates)
        return

    compress_candidates(candidates)


if __name__ == "__main__":
    main()
