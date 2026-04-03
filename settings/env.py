"""
수정 요약
- `.env.settings`, `.env.secrets`, `.env.local` 이 있으면 우선 사용하고, 없을 때만 legacy `.env` 를 읽는 중앙 환경 로더로 확장
- 여러 모듈이 직접 `load_dotenv()` 를 호출하던 구조를 공통 로더로 정리할 수 있는 기반을 마련

환경 로더

- 기본 호환성: 기존 `.env` 만 있어도 그대로 동작한다.
- 확장 경로: `.env.settings`, `.env.secrets`, `.env.local` 을 순서대로 덮어써 로딩한다.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATHS = [
    ROOT_DIR / ".env.settings",
    ROOT_DIR / ".env.secrets",
    ROOT_DIR / ".env.local",
]
LEGACY_ENV_PATH = ROOT_DIR / ".env"


def get_env_paths() -> list[Path]:
    """로딩 대상 환경 파일 목록을 반환한다."""
    custom = os.getenv("AUTOCOIN_ENV_FILES", "").strip()
    if not custom:
        split_paths = [path for path in DEFAULT_ENV_PATHS if path.exists()]
        if split_paths:
            return split_paths
        return [LEGACY_ENV_PATH]
    paths: list[Path] = []
    for item in custom.split(","):
        raw = item.strip()
        if not raw:
            continue
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT_DIR / raw
        paths.append(path)
    return paths or [LEGACY_ENV_PATH]


@lru_cache(maxsize=1)
def load_project_env() -> tuple[str, ...]:
    """프로젝트 환경 파일을 한 번만 로드하고 실제 읽은 경로를 반환한다."""
    loaded: list[str] = []
    for path in get_env_paths():
        if not path.exists():
            continue
        load_dotenv(path, override=True)
        loaded.append(str(path))
    return tuple(loaded)
