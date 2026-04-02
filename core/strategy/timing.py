"""
작업 요약
- 진입 상태 머신을 공통 helper 로 분리해 WATCH/ARM/READY/HOLD 흐름을 재사용할 수 있게 정리했다.
- 동일 신호가 연속 확인될 때만 진입하게 만들어 횡보장 오탐을 줄이도록 보강했다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntryTimingSnapshot:
    """진입 상태 머신의 현재 스냅샷."""

    phase: str
    confirmation_count: int
    required_confirmations: int
    ready: bool


def update_entry_timing_state(
    *,
    state_store: dict[str, dict[str, int | str]],
    symbol: str,
    has_position: bool,
    candidate_active: bool,
    required_confirmations: int,
) -> EntryTimingSnapshot:
    """진입 후보 신호를 상태 머신으로 누적해 READY 여부를 반환한다."""
    required = max(1, required_confirmations)

    if has_position:
        state_store[symbol] = {"phase": "HOLD", "confirmation_count": 0}
        return EntryTimingSnapshot(
            phase="HOLD",
            confirmation_count=0,
            required_confirmations=required,
            ready=False,
        )

    previous = state_store.get(symbol, {})
    previous_count = int(previous.get("confirmation_count", 0) or 0)

    if not candidate_active:
        state_store[symbol] = {"phase": "WATCH", "confirmation_count": 0}
        return EntryTimingSnapshot(
            phase="WATCH",
            confirmation_count=0,
            required_confirmations=required,
            ready=False,
        )

    confirmation_count = previous_count + 1
    phase = "READY" if confirmation_count >= required else "ARM"
    ready = phase == "READY"
    state_store[symbol] = {
        "phase": phase,
        "confirmation_count": confirmation_count,
    }
    return EntryTimingSnapshot(
        phase=phase,
        confirmation_count=confirmation_count,
        required_confirmations=required,
        ready=ready,
    )
