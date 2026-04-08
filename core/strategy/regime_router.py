"""
작업 요약
- BTC/알트가 레짐을 단순 필터가 아니라 전략 선택기로 쓰도록 공통 레짐 라우터를 추가했다.
- 현재 구현은 기존 전략 엔진을 유지한 채 `skip / breakout / trend_follow` 경로를 명시적으로 고르게 만든다.
"""

from __future__ import annotations

from dataclasses import dataclass

from market_regime_guard import RegimePolicy, get_alt_regime_policy, get_btc_regime_policy


@dataclass(frozen=True)
class StrategyRoute:
    """레짐에 따라 선택된 전략 경로와 정책을 묶는다."""

    regime: str
    strategy_key: str
    policy: RegimePolicy


def _choose_strategy_key(regime: str) -> str:
    """레짐 이름을 기존 전략 경로 키로 변환한다."""
    if regime in {"LOW_ENERGY", "EXHAUSTION_RISK", "OVERHEATED", "CHOPPY_LOW_VOL"}:
        return "skip"
    if regime in {"BREAKOUT_ATTEMPT", "CHOPPY_HIGH_VOL"}:
        return "breakout"
    if regime in {"TRENDING_EARLY", "TRENDING_MATURE"}:
        return "trend_follow"
    return "trend_follow"


def route_btc_strategy(regime: str | None) -> StrategyRoute:
    """BTC 레짐을 기존 전략 경로로 라우팅한다."""
    normalized = str(regime or "UNKNOWN").strip().upper() or "UNKNOWN"
    return StrategyRoute(
        regime=normalized,
        strategy_key=_choose_strategy_key(normalized),
        policy=get_btc_regime_policy(normalized),
    )


def route_alt_strategy(regime: str | None) -> StrategyRoute:
    """알트 레짐을 기존 전략 경로로 라우팅한다."""
    normalized = str(regime or "UNKNOWN").strip().upper() or "UNKNOWN"
    return StrategyRoute(
        regime=normalized,
        strategy_key=_choose_strategy_key(normalized),
        policy=get_alt_regime_policy(normalized),
    )
