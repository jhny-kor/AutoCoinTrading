"""
작업 요약
- 2026-04-08: 확인필요 백테스트 결과를 디렉토리째 삭제하고 backtest_registry.json 을 즉시 갱신하는 삭제 도구를 추가
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from tools.update_backtest_registry import (
    BACKTEST_BATCH_DIR,
    BACKTEST_SINGLE_DIR,
    REGISTRY_PATH,
    build_all_registry_entries,
    write_registry,
)


ALLOWED_ROOTS = (
    BACKTEST_BATCH_DIR.resolve(),
    BACKTEST_SINGLE_DIR.resolve(),
)


def is_allowed_target(path: Path) -> bool:
    """삭제 대상이 허용된 백테스트 디렉토리인지 확인한다."""
    resolved = path.resolve()
    return any(root == resolved or root in resolved.parents for root in ALLOWED_ROOTS)


def delete_backtest_directory(target: Path) -> None:
    """백테스트 결과 디렉토리를 삭제하고 레지스트리를 갱신한다."""
    if not target.exists():
        raise FileNotFoundError(f"삭제 대상이 없습니다: {target}")
    if not target.is_dir():
        raise NotADirectoryError(f"디렉토리가 아닙니다: {target}")
    if not is_allowed_target(target):
        raise ValueError(f"허용된 백테스트 경로가 아닙니다: {target}")

    shutil.rmtree(target)
    write_registry(REGISTRY_PATH, build_all_registry_entries())


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 만든다."""
    parser = argparse.ArgumentParser(description="백테스트 결과 디렉토리 삭제")
    parser.add_argument("--path", required=True, help="삭제할 백테스트 디렉토리 경로")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    args = build_parser().parse_args(argv)
    target = Path(args.path)
    delete_backtest_directory(target)
    print(f"삭제 완료: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
