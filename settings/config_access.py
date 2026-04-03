"""
수정 요약
- 중앙 환경 로더 위에서 typed access 를 제공하는 공통 설정 접근 유틸을 추가
- 문자열 기반 `os.getenv()` 직접 호출을 줄이고 int/float/bool/path 접근을 일관되게 만들도록 구성

typed config access helper

- load_project_env() 를 먼저 보장한 뒤 typed 값으로 읽는다.
"""

from __future__ import annotations

import os
from pathlib import Path

from settings.env import ROOT_DIR, load_project_env


def env_str(key: str, default: str | None = None, *, required: bool = False) -> str:
    """환경변수를 문자열로 읽는다."""
    load_project_env()
    value = os.getenv(key)
    if value in (None, ""):
        if required:
            raise RuntimeError(f"{key} 가 설정되어 있지 않습니다.")
        return "" if default is None else default
    return value


def env_bool(key: str, default: bool = False) -> bool:
    """환경변수를 불리언으로 읽는다."""
    raw = env_str(key, None)
    if raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def env_int(key: str, default: int) -> int:
    """환경변수를 정수로 읽는다."""
    raw = env_str(key, None)
    if raw == "":
        return default
    return int(raw)


def env_float(key: str, default: float) -> float:
    """환경변수를 실수로 읽는다."""
    raw = env_str(key, None)
    if raw == "":
        return default
    return float(raw)


def env_path(key: str, default: str) -> Path:
    """환경변수를 경로로 읽는다."""
    raw = env_str(key, default)
    path = Path(raw)
    if path.is_absolute():
        return path
    return ROOT_DIR / raw
