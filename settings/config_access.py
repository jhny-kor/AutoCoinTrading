"""
수정 요약
- 2026-04-03: canonical TOML 과 env 레이어를 함께 읽는 typed access helper 를 추가하고 공통 설정 접근을 일관화
- 중앙 환경 로더 위에서 typed access 를 제공하는 공통 설정 접근 유틸을 추가
- 문자열 기반 `os.getenv()` 직접 호출을 줄이고 int/float/bool/path 접근을 일관되게 만들도록 구성

typed config access helper

- load_project_env() 를 먼저 보장한 뒤 typed 값으로 읽는다.
"""

from __future__ import annotations

import os
from pathlib import Path
import tomllib
from functools import lru_cache
from typing import Any

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


def _deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """중첩 dict 를 재귀적으로 병합한다."""
    merged = dict(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


@lru_cache(maxsize=1)
def load_runtime_config() -> dict[str, Any]:
    """canonical runtime TOML 과 local TOML 을 병합해 반환한다."""
    config: dict[str, Any] = {}
    for path in (
        ROOT_DIR / "config" / "runtime.toml",
        ROOT_DIR / "config" / "runtime.local.toml",
    ):
        if not path.exists():
            continue
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        config = _deep_merge_dict(config, payload)
    return config


def config_value(
    section: str,
    key: str,
    default: Any = None,
    *,
    env_key: str | None = None,
) -> Any:
    """runtime config 값을 읽되 env override 가 있으면 우선한다."""
    load_project_env()
    if env_key is not None and env_key in os.environ:
        return os.environ[env_key]
    payload = load_runtime_config()
    section_payload = payload.get(section, {})
    if not isinstance(section_payload, dict):
        return default
    return section_payload.get(key, default)


def config_bool(section: str, key: str, default: bool, *, env_key: str | None = None) -> bool:
    """bool 값을 읽는다."""
    value = config_value(section, key, default, env_key=env_key)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def config_int(section: str, key: str, default: int, *, env_key: str | None = None) -> int:
    """int 값을 읽는다."""
    value = config_value(section, key, default, env_key=env_key)
    return int(value)


def config_float(section: str, key: str, default: float, *, env_key: str | None = None) -> float:
    """float 값을 읽는다."""
    value = config_value(section, key, default, env_key=env_key)
    return float(value)


def config_str(section: str, key: str, default: str, *, env_key: str | None = None) -> str:
    """str 값을 읽는다."""
    value = config_value(section, key, default, env_key=env_key)
    return str(value)


def config_section_float(
    section: str,
    key: str,
    default: float,
    *,
    env_key: str | None = None,
) -> float:
    """section/key 기준 실수 값을 읽되 env override 도 함께 반영한다."""
    return config_float(section, key, default, env_key=env_key)
