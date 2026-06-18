"""짧은 TTL 기반 fetch 캐시 helper.

느리게 변하는 데이터(상위 타임프레임 캔들 등)를 매 루프 재조회하지 않고
TTL 동안 재사용해 REST 왕복을 줄이기 위한 순수 함수 모음.
"""

from __future__ import annotations

from typing import Any, Hashable


def get_fresh_cached(
    cache: dict[Hashable, tuple[float, Any]],
    key: Hashable,
    now_ts: float,
    ttl_sec: float,
) -> Any | None:
    """TTL 이내의 캐시 값이 있으면 반환하고, 없거나 만료됐으면 None 을 반환한다.

    ttl_sec <= 0 이면 캐시를 사용하지 않는다(항상 None).
    """
    if ttl_sec <= 0:
        return None
    entry = cache.get(key)
    if entry is None:
        return None
    cached_at, value = entry
    if now_ts - cached_at <= ttl_sec:
        return value
    return None


def store_cached(
    cache: dict[Hashable, tuple[float, Any]],
    key: Hashable,
    now_ts: float,
    value: Any,
) -> None:
    """캐시에 (시각, 값) 을 저장한다."""
    cache[key] = (now_ts, value)
