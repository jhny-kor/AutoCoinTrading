"""
수정 요약
- 최근 7일 로그는 원본 그대로 유지하고, 그 이전 로그는 날짜별 tar.gz 로 묶어 보관하도록 개선
- 루트별 _archive 폴더를 사용해 logs / analysis_logs / trade_logs / structured_logs 를 분리 보관
- status 로 압축 대상 날짜 묶음을 미리 보고, compress 로 실제 압축 실행을 수행하도록 정리

로그 압축/보관 관리자

- logs, analysis_logs, trade_logs, structured_logs 아래의 오래된 로그를 찾아 날짜별 tar.gz 로 압축한다.
- 최근 7일 로그는 활성 분석용 원본으로 유지하고, 7일을 초과한 로그만 압축 대상으로 본다.
- status 로 후보를 미리 보고, compress 로 실제 압축을 수행할 수 있다.

사용 예시
- .venv/bin/python log_archive_manager.py status
- .venv/bin/python log_archive_manager.py compress
- .venv/bin/python log_archive_manager.py status --keep-days 14
"""

from __future__ import annotations

import argparse
import tarfile
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
    root: Path
    size_bytes: int
    modified_at: float

    @property
    def archive_day(self) -> str:
        """파일 수정 시각 기준 날짜 키를 반환한다."""
        return datetime.fromtimestamp(self.modified_at).strftime("%Y-%m-%d")


@dataclass(frozen=True)
class ArchiveGroup:
    root: Path
    archive_day: str
    files: tuple[ArchiveCandidate, ...]

    @property
    def total_size_bytes(self) -> int:
        return sum(item.size_bytes for item in self.files)

    @property
    def archive_path(self) -> Path:
        return self.root / "_archive" / f"{self.archive_day}.tar.gz"


def iter_candidates(keep_days: int) -> list[ArchiveCandidate]:
    """압축 가능한 로그 후보를 수집한다."""
    now = time.time()
    keep_cutoff = now - (keep_days * 86400)
    candidates: list[ArchiveCandidate] = []

    for root in LOG_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if "_archive" in path.parts:
                continue
            if path.suffix == ".gz":
                continue
            if path.suffix not in TARGET_SUFFIXES:
                continue
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            if stat.st_mtime >= keep_cutoff:
                continue
            candidates.append(
                ArchiveCandidate(
                    path=path,
                    root=root,
                    size_bytes=stat.st_size,
                    modified_at=stat.st_mtime,
                )
            )
    return sorted(candidates, key=lambda item: (str(item.path), item.modified_at))


def group_candidates(candidates: list[ArchiveCandidate]) -> list[ArchiveGroup]:
    """압축 후보를 루트/날짜별로 묶는다."""
    grouped: dict[tuple[Path, str], list[ArchiveCandidate]] = {}
    for item in candidates:
        key = (item.root, item.archive_day)
        grouped.setdefault(key, []).append(item)

    groups: list[ArchiveGroup] = []
    for (root, archive_day), items in sorted(grouped.items(), key=lambda entry: (str(entry[0][0]), entry[0][1])):
        groups.append(
            ArchiveGroup(
                root=root,
                archive_day=archive_day,
                files=tuple(sorted(items, key=lambda candidate: str(candidate.path))),
            )
        )
    return groups


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
        print(f"- {item.path} | {format_bytes(item.size_bytes)} | 마지막 수정 {age_hours:.1f}시간 전")
    if len(candidates) > 50:
        print(f"... 외 {len(candidates) - 50}개")


def show_group_status(groups: list[ArchiveGroup], keep_days: int) -> None:
    """날짜별 압축 후보 묶음을 보여준다."""
    total_files = sum(len(group.files) for group in groups)
    total_size = sum(group.total_size_bytes for group in groups)
    print("=== 날짜별 로그 압축 후보 ===")
    print(f"원본 유지 기간: 최근 {keep_days}일")
    print(f"후보 날짜 묶음 수: {len(groups)}")
    print(f"후보 파일 수: {total_files}")
    print(f"총 원본 크기: {format_bytes(total_size)}")
    for group in groups[:50]:
        print(
            f"- {group.root}/{group.archive_day}.tar.gz 예정 | "
            f"{len(group.files)}개 파일 | {format_bytes(group.total_size_bytes)}"
        )
    if len(groups) > 50:
        print(f"... 외 {len(groups) - 50}개 날짜 묶음")


def compress_groups(groups: list[ArchiveGroup]) -> None:
    """후보 파일을 날짜별 tar.gz 로 압축하고 원본을 제거한다."""
    compressed_group_count = 0
    compressed_file_count = 0
    original_total = 0
    compressed_total = 0

    for group in groups:
        archive_path = group.archive_path
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        with tarfile.open(archive_path, "w:gz") as tar:
            for item in group.files:
                arcname = item.path.relative_to(group.root)
                tar.add(item.path, arcname=str(arcname))

        for item in group.files:
            item.path.unlink()

        compressed_size = archive_path.stat().st_size
        compressed_group_count += 1
        compressed_file_count += len(group.files)
        original_total += group.total_size_bytes
        compressed_total += compressed_size
        print(
            f"[압축 완료] {archive_path} | "
            f"{len(group.files)}개 파일 | "
            f"{format_bytes(group.total_size_bytes)} -> {format_bytes(compressed_size)}"
        )

    print("=== 로그 압축 결과 ===")
    print(f"압축 묶음 수: {compressed_group_count}")
    print(f"압축 파일 수: {compressed_file_count}")
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
        "--keep-days",
        type=int,
        default=7,
        help="최근 이 일수만큼은 원본을 유지합니다. 기본값 7일",
    )
    args = parser.parse_args()

    candidates = iter_candidates(args.keep_days)
    groups = group_candidates(candidates)
    if args.command == "status":
        show_group_status(groups, args.keep_days)
        return

    compress_groups(groups)


if __name__ == "__main__":
    main()
