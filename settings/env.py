"""
수정 요약
- 2026-04-10: 백테스트 실험 세트용 추가 TOML override 레이어와 임시 적용 context manager 를 추가했다.
- 2026-04-03: `config/runtime.toml` 을 canonical 기준으로 읽고 `config/runtime.local.toml` 을 최종 override 로 적용하도록 정리
- 2026-04-03: 프로세스에 이미 주입된 env 값은 파일 로더가 덮어쓰지 않도록 보존 순서를 보강
- `.env.settings`, `.env.secrets`, `.env.local` 이 있으면 우선 사용하고, 없을 때만 legacy `.env` 를 읽는 중앙 환경 로더로 확장
- 여러 모듈이 직접 `load_dotenv()` 를 호출하던 구조를 공통 로더로 정리할 수 있는 기반을 마련

환경 로더

- 기본 호환성: 기존 `.env` 만 있어도 그대로 동작한다.
- 확장 경로: `config/runtime.toml` -> env override 레이어 -> `config/runtime.local.toml` 순서로 로딩한다.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
import tomllib

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
BASE_TOML_PATHS = [
    ROOT_DIR / "config" / "runtime.toml",
]
RUNTIME_LOCAL_TOML_PATH = ROOT_DIR / "config" / "runtime.local.toml"
SECTION_PREFIX_MAP = {
    "okx": "OKX",
    "upbit": "UPBIT",
    "telegram": "TELEGRAM",
    "portfolio": "PORTFOLIO",
    "market_guard": "MARKET_GUARD",
    "regime": "REGIME",
    "btc_trend": "BTC_TREND",
    "strategy": "STRATEGY",
    "analysis": "ANALYSIS",
    "upbit_ws": "UPBIT_WS",
    "upbit_private": "UPBIT_PRIVATE",
}
DEFAULT_ENV_PATHS = [
    ROOT_DIR / ".env.settings",
    ROOT_DIR / ".env.secrets",
    ROOT_DIR / ".env.local",
]
LEGACY_ENV_PATH = ROOT_DIR / ".env"
EXTRA_TOML_ENV_KEY = "AUTOCOIN_EXTRA_TOML"


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


def get_extra_toml_paths() -> list[Path]:
    """추가 TOML override 경로 목록을 반환한다."""
    raw = os.getenv(EXTRA_TOML_ENV_KEY, "").strip()
    if not raw:
        return []
    paths: list[Path] = []
    for item in raw.split(","):
        token = item.strip()
        if not token:
            continue
        path = Path(token)
        if not path.is_absolute():
            path = ROOT_DIR / token
        paths.append(path)
    return paths


def _stringify_config_value(value: object) -> str:
    """structured config 값을 환경변수 문자열로 바꾼다."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, dict):
        items: list[str] = []
        for key, inner_value in value.items():
            if isinstance(inner_value, dict):
                for nested_key, nested_value in inner_value.items():
                    items.append(f"{key}|{nested_key}:{nested_value}")
            else:
                items.append(f"{key}:{inner_value}")
        return ",".join(items)
    return str(value)


def _flatten_toml_section(section_name: str, payload: dict) -> dict[str, str]:
    """1단계 table 을 ENV_KEY 형태로 평탄화한다."""
    prefix = SECTION_PREFIX_MAP.get(section_name, section_name.upper())
    flattened: dict[str, str] = {}
    for key, value in payload.items():
        env_key = f"{prefix}_{str(key).upper()}"
        flattened[env_key] = _stringify_config_value(value)
    return flattened


def load_structured_config(paths: list[Path]) -> tuple[str, ...]:
    """지정된 TOML config 를 읽어 환경변수로 반영한다."""
    loaded: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        for section_name, section_payload in payload.items():
            if not isinstance(section_payload, dict):
                continue
            for env_key, env_value in _flatten_toml_section(section_name, section_payload).items():
                os.environ[env_key] = env_value
        loaded.append(str(path))
    return tuple(loaded)


@lru_cache(maxsize=1)
def load_project_env() -> tuple[str, ...]:
    """프로젝트 환경 파일을 한 번만 로드하고 실제 읽은 경로를 반환한다."""
    preserved_env = dict(os.environ)
    loaded: list[str] = []
    loaded.extend(load_structured_config(BASE_TOML_PATHS))
    for path in get_env_paths():
        if not path.exists():
            continue
        load_dotenv(path, override=True)
        loaded.append(str(path))
    loaded.extend(load_structured_config([RUNTIME_LOCAL_TOML_PATH]))
    loaded.extend(load_structured_config(get_extra_toml_paths()))
    os.environ.update(preserved_env)
    return tuple(loaded)


def reset_env_loader_cache() -> None:
    """환경 로더 캐시를 비운다."""
    load_project_env.cache_clear()


@contextmanager
def temporary_runtime_overrides(paths: list[str | Path] | None):
    """백테스트 등에서 추가 TOML override 를 임시 적용한다."""
    previous = os.getenv(EXTRA_TOML_ENV_KEY)
    try:
        serialized = ",".join(str(Path(path)) for path in (paths or []) if str(path).strip())
        if serialized:
            os.environ[EXTRA_TOML_ENV_KEY] = serialized
        else:
            os.environ.pop(EXTRA_TOML_ENV_KEY, None)
        reset_env_loader_cache()
        yield
    finally:
        if previous is None:
            os.environ.pop(EXTRA_TOML_ENV_KEY, None)
        else:
            os.environ[EXTRA_TOML_ENV_KEY] = previous
        reset_env_loader_cache()
