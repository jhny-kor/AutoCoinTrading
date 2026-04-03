"""
수정 요약
- env_overrides 아래 partial env 파일을 현재 .env.settings 에 안전하게 반영하는 전략 세트 적용 도구로 정리
- conservative, medium, mixed 세트 별칭과 직접 파일 지정 방식을 모두 지원하도록 확장
- dry-run 으로 변경 예정 키를 먼저 확인할 수 있게 구성

전략 세트 적용 도구

- 목적: .env.settings 전체를 수동 편집하지 않고 세트 파일의 일부 키만 현재 .env.settings 에 반영한다.
- 입력: 세트 이름 또는 partial env 파일 경로
- 출력: 변경된 키 목록과 반영 결과
"""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env.settings"
SET_DIR = ROOT_DIR / "env_overrides"

SET_ALIASES = {
    "conservative": "conservative.env",
    "medium": "medium.env",
    "mixed": "mixed.env",
}


def parse_partial_env(path: Path) -> dict[str, str]:
    """partial env 파일에서 KEY=VALUE 쌍만 읽는다."""
    pairs: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        pairs[key] = value
    return pairs


def resolve_set_path(name_or_path: str) -> Path:
    """세트 별칭 또는 파일 경로를 실제 Path 로 바꾼다."""
    candidate = SET_DIR / SET_ALIASES.get(name_or_path, name_or_path)
    if candidate.exists():
        return candidate
    direct = Path(name_or_path)
    if direct.exists():
        return direct
    raise FileNotFoundError(f"세트 파일을 찾지 못했습니다: {name_or_path}")


def apply_pairs_to_env(env_path: Path, pairs: dict[str, str], dry_run: bool = False) -> list[str]:
    """현재 .env.settings 에 partial env 키를 반영한다."""
    if not env_path.exists():
        raise FileNotFoundError(f".env 파일이 없습니다: {env_path}")

    original_lines = env_path.read_text(encoding="utf-8").splitlines()
    updated_lines: list[str] = []
    touched: set[str] = set()
    changed_keys: list[str] = []

    for line in original_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            updated_lines.append(line)
            continue
        key, _ = line.split("=", 1)
        key = key.strip()
        if key in pairs:
            new_line = f"{key}={pairs[key]}"
            updated_lines.append(new_line)
            touched.add(key)
            if line != new_line:
                changed_keys.append(key)
        else:
            updated_lines.append(line)

    for key, value in pairs.items():
        if key in touched:
            continue
        updated_lines.append(f"{key}={value}")
        changed_keys.append(key)

    if not dry_run:
        env_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    return changed_keys


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 만든다."""
    parser = argparse.ArgumentParser(description="partial env 전략 세트 적용 도구")
    parser.add_argument(
        "--set",
        required=True,
        help="세트 별칭(conservative|medium|mixed) 또는 partial env 파일 경로",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="실제 반영 없이 변경될 키만 출력",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    args = build_parser().parse_args(argv)
    set_path = resolve_set_path(args.set)
    pairs = parse_partial_env(set_path)
    changed_keys = apply_pairs_to_env(ENV_PATH, pairs, dry_run=args.dry_run)
    mode_label = "미리보기" if args.dry_run else "적용 완료"
    print(f"{mode_label}: {set_path}")
    if not changed_keys:
        print("- 변경된 키 없음")
        return 0
    for key in changed_keys:
        print(f"- {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
