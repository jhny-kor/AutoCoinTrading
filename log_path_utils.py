"""일자별 로그 경로와 탐색을 돕는 공통 유틸."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable


def current_date_str() -> str:
    """현재 로컬 날짜를 YYYY-MM-DD 문자열로 반환한다."""
    return datetime.now().strftime("%Y-%m-%d")


def dated_dir(root: str | Path, date_str: str | None = None) -> Path:
    """루트 아래의 일자별 디렉토리를 반환한다."""
    return Path(root) / (date_str or current_date_str())


def dated_path(root: str | Path, *parts: str, date_str: str | None = None) -> Path:
    """루트 아래 일자별 디렉토리의 파일 경로를 만든다."""
    return dated_dir(root, date_str=date_str).joinpath(*parts)


def is_archived_path(path: Path) -> bool:
    """압축 보관 디렉토리 하위 경로인지 확인한다."""
    return "_archive" in path.parts


def iter_files(root: str | Path, pattern: str) -> list[Path]:
    """루트 아래 파일을 재귀적으로 찾되 보관 디렉토리는 제외한다."""
    base = Path(root)
    if not base.exists():
        return []
    return sorted(
        path
        for path in base.rglob(pattern)
        if path.is_file() and not is_archived_path(path)
    )


def latest_file(root: str | Path, pattern: str) -> Path | None:
    """루트 아래에서 가장 최근 수정된 파일을 찾는다."""
    files = iter_files(root, pattern)
    if not files:
        return None
    return max(files, key=lambda item: item.stat().st_mtime)


def read_all_lines(paths: Iterable[Path]) -> list[str]:
    """여러 파일의 줄을 순서대로 읽는다."""
    lines: list[str] = []
    for path in paths:
        try:
            lines.extend(path.read_text(encoding="utf-8").splitlines())
        except FileNotFoundError:
            continue
    return lines
