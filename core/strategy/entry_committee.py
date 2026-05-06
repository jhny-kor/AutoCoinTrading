"""
작업 요약
- 매수 신호를 전략/리스크/체결/포트폴리오/레짐 관점으로 독립 평가하는 entry committee 를 추가했다.
- 기본 shadow 모드에서는 실제 진입을 막지 않고 투표 결과만 구조화 로그에 남길 수 있도록 구성했다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from settings.config_access import config_bool, config_float, config_int, config_str


@dataclass(frozen=True)
class EntryCommitteeSettings:
    """매수 검토 위원회 설정."""

    enabled: bool
    mode: str
    min_approve_votes: int
    require_risk_approval: bool
    require_execution_approval: bool
    min_signal_score: float
    min_orderbook_pressure_score: float
    min_fill_ratio: float
    high_atr_percentile: float
    upper_range_position_pct: float


@dataclass(frozen=True)
class CommitteeVote:
    """개별 관점의 투표 결과."""

    role: str
    decision: str
    confidence: float
    reason: str
    severity: str = "info"

    def to_dict(self) -> dict[str, Any]:
        """구조화 로그에 저장할 dict 로 변환한다."""
        return {
            "role": self.role,
            "decision": self.decision,
            "confidence": self.confidence,
            "reason": self.reason,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class EntryCommitteeResult:
    """매수 검토 위원회 최종 판정."""

    enabled: bool
    mode: str
    approved: bool
    active_blocks_entry: bool
    hard_veto: bool
    approve_votes: int
    reject_votes: int
    min_approve_votes: int
    reason: str
    votes: tuple[CommitteeVote, ...]

    def to_metrics(self) -> dict[str, Any]:
        """공통 metrics 에 합칠 요약값을 만든다."""
        return {
            "entry_committee_enabled": self.enabled,
            "entry_committee_mode": self.mode,
            "entry_committee_approved": self.approved,
            "entry_committee_active_blocks_entry": self.active_blocks_entry,
            "entry_committee_hard_veto": self.hard_veto,
            "entry_committee_approve_votes": self.approve_votes,
            "entry_committee_reject_votes": self.reject_votes,
            "entry_committee_reason": self.reason,
        }

    def actual(self) -> dict[str, Any]:
        """퍼널/전략 로그의 actual 필드를 만든다."""
        return {
            "approved": self.approved,
            "active_blocks_entry": self.active_blocks_entry,
            "hard_veto": self.hard_veto,
            "approve_votes": self.approve_votes,
            "reject_votes": self.reject_votes,
            "mode": self.mode,
        }

    def required(self) -> dict[str, Any]:
        """퍼널/전략 로그의 required 필드를 만든다."""
        return {
            "approved": True,
            "min_approve_votes": self.min_approve_votes,
            "hard_veto": False,
        }

    def extra(self) -> dict[str, Any]:
        """퍼널/전략 로그의 extra 필드를 만든다."""
        return {"votes": [vote.to_dict() for vote in self.votes]}


def load_entry_committee_settings() -> EntryCommitteeSettings:
    """runtime config 에서 매수 검토 위원회 설정을 읽는다."""
    mode = config_str("entry_committee", "mode", "shadow", env_key="ENTRY_COMMITTEE_MODE").strip().lower()
    if mode not in {"shadow", "active", "off"}:
        mode = "shadow"
    return EntryCommitteeSettings(
        enabled=config_bool("entry_committee", "enabled", True, env_key="ENTRY_COMMITTEE_ENABLED"),
        mode=mode,
        min_approve_votes=config_int("entry_committee", "min_approve_votes", 3, env_key="ENTRY_COMMITTEE_MIN_APPROVE_VOTES"),
        require_risk_approval=config_bool("entry_committee", "require_risk_approval", True, env_key="ENTRY_COMMITTEE_REQUIRE_RISK_APPROVAL"),
        require_execution_approval=config_bool("entry_committee", "require_execution_approval", True, env_key="ENTRY_COMMITTEE_REQUIRE_EXECUTION_APPROVAL"),
        min_signal_score=config_float("entry_committee", "min_signal_score", 50.0, env_key="ENTRY_COMMITTEE_MIN_SIGNAL_SCORE"),
        min_orderbook_pressure_score=config_float("entry_committee", "min_orderbook_pressure_score", 45.0, env_key="ENTRY_COMMITTEE_MIN_ORDERBOOK_PRESSURE_SCORE"),
        min_fill_ratio=config_float("entry_committee", "min_fill_ratio", 0.70, env_key="ENTRY_COMMITTEE_MIN_FILL_RATIO"),
        high_atr_percentile=config_float("entry_committee", "high_atr_percentile", 95.0, env_key="ENTRY_COMMITTEE_HIGH_ATR_PERCENTILE"),
        upper_range_position_pct=config_float("entry_committee", "upper_range_position_pct", 80.0, env_key="ENTRY_COMMITTEE_UPPER_RANGE_POSITION_PCT"),
    )


def disabled_entry_committee_result() -> EntryCommitteeResult:
    """비활성화 상태의 통과 결과를 만든다."""
    return EntryCommitteeResult(
        enabled=False,
        mode="off",
        approved=True,
        active_blocks_entry=False,
        hard_veto=False,
        approve_votes=0,
        reject_votes=0,
        min_approve_votes=0,
        reason="entry_committee_disabled",
        votes=(),
    )


def _safe_float(metrics: dict[str, Any], *keys: str, default: float | None = None) -> float | None:
    """metrics 후보 키를 float 로 안전하게 읽는다."""
    for key in keys:
        value = metrics.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return default


def _safe_bool(metrics: dict[str, Any], key: str, default: bool = False) -> bool:
    """metrics 값을 bool 로 안전하게 읽는다."""
    value = metrics.get(key, default)
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _true_flags(metrics: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    """True 로 표시된 위험 플래그 목록을 반환한다."""
    return [key for key in keys if _safe_bool(metrics, key)]


def _vote_strategy(metrics: dict[str, Any], settings: EntryCommitteeSettings) -> CommitteeVote:
    """전략 신호 관점의 투표를 만든다."""
    signal_score = _safe_float(metrics, "signal_score", default=0.0) or 0.0
    min_signal_score = (
        _safe_float(metrics, "effective_signal_score_min", "min_signal_score", default=settings.min_signal_score)
        or settings.min_signal_score
    )
    entry_signal = _safe_bool(metrics, "entry_signal", default=True)
    signal_is_strong = _safe_bool(metrics, "signal_is_strong", default=signal_score >= min_signal_score)
    probe_allowed = (
        _safe_bool(metrics, "low_energy_probe_allowed")
        or _safe_bool(metrics, "mean_reversion_lower_near_probe_allowed")
        or _safe_bool(metrics, "volume_spike_entry_downgrade_allowed")
    )

    if not entry_signal and not probe_allowed:
        return CommitteeVote("strategy", "reject", 0.90, "entry_signal_missing", "medium")
    if signal_score < min_signal_score and not probe_allowed:
        return CommitteeVote("strategy", "reject", 0.85, "signal_score_below_contract", "medium")
    if not signal_is_strong and not probe_allowed:
        return CommitteeVote("strategy", "reject", 0.75, "signal_strength_not_confirmed", "medium")
    if signal_score < min_signal_score:
        return CommitteeVote("strategy", "caution", 0.65, "probe_entry_below_normal_signal_min", "low")
    return CommitteeVote("strategy", "approve", 0.80, "strategy_signal_confirmed")


def _vote_risk(metrics: dict[str, Any], settings: EntryCommitteeSettings) -> CommitteeVote:
    """리스크 관점의 투표를 만든다."""
    hard_flags = _true_flags(
        metrics,
        (
            "daily_loss_limit_reached",
            "htf_bearish_entry_blocked",
            "overheated_entry_blocked",
            "btc_correlation_volatility_blocked",
            "volume_atr_execution_blocked",
            "stop_loss_context_reentry_blocked",
            "correlation_entry_blocked",
        ),
    )
    if hard_flags:
        return CommitteeVote("risk", "reject", 0.95, "risk_flags_active:" + ",".join(hard_flags), "high")

    atr_percentile = _safe_float(metrics, "atr_percentile")
    range_position_pct = _safe_float(metrics, "range_position_pct")
    if (
        atr_percentile is not None
        and range_position_pct is not None
        and atr_percentile >= settings.high_atr_percentile
        and range_position_pct >= settings.upper_range_position_pct
    ):
        return CommitteeVote("risk", "reject", 0.90, "high_atr_upper_range_chase_risk", "high")

    return CommitteeVote("risk", "approve", 0.82, "risk_guards_clear")


def _vote_execution(metrics: dict[str, Any], settings: EntryCommitteeSettings) -> CommitteeVote:
    """체결 품질 관점의 투표를 만든다."""
    if _safe_bool(metrics, "fill_quality_entry_blocked"):
        return CommitteeVote("execution", "reject", 0.88, "fill_quality_guard_blocked", "medium")

    avg_fill_ratio = _safe_float(metrics, "fill_quality_avg_fill_ratio")
    sample_count = _safe_float(metrics, "fill_quality_sample_count", default=0.0) or 0.0
    if avg_fill_ratio is not None and sample_count >= 3 and avg_fill_ratio < settings.min_fill_ratio:
        return CommitteeVote("execution", "reject", 0.82, "recent_fill_ratio_too_low", "medium")

    orderbook_score = _safe_float(metrics, "orderbook_pressure_score")
    if orderbook_score is not None and orderbook_score < settings.min_orderbook_pressure_score:
        return CommitteeVote("execution", "reject", 0.78, "orderbook_pressure_weak", "medium")

    return CommitteeVote("execution", "approve", 0.75, "execution_quality_acceptable")


def _vote_portfolio(metrics: dict[str, Any]) -> CommitteeVote:
    """포트폴리오/예산 관점의 투표를 만든다."""
    remaining_budget = _safe_float(
        metrics,
        "portfolio_remaining_budget_quote",
        "remaining_budget_quote",
        default=0.0,
    ) or 0.0
    position_ratio = _safe_float(metrics, "effective_position_ratio", "position_ratio", default=0.0) or 0.0
    order_value = _safe_float(
        metrics,
        "executable_order_value_quote",
        "requested_order_value_quote",
        "order_value",
        default=0.0,
    ) or 0.0

    if remaining_budget <= 0:
        return CommitteeVote("portfolio", "reject", 0.92, "portfolio_budget_exhausted", "high")
    if position_ratio <= 0:
        return CommitteeVote("portfolio", "reject", 0.80, "position_ratio_zero", "medium")
    if order_value <= 0:
        return CommitteeVote("portfolio", "reject", 0.80, "order_value_zero", "medium")
    return CommitteeVote("portfolio", "approve", 0.76, "portfolio_budget_available")


def _vote_regime(metrics: dict[str, Any]) -> CommitteeVote:
    """레짐/시장상태 관점의 투표를 만든다."""
    if _safe_bool(metrics, "symbol_regime_blocks_entry"):
        return CommitteeVote("regime", "reject", 0.88, "symbol_regime_blocks_entry", "medium")
    if _safe_bool(metrics, "effective_low_energy_guard_active") and not _safe_bool(metrics, "low_energy_probe_allowed"):
        return CommitteeVote("regime", "reject", 0.84, "low_energy_without_probe_permission", "medium")
    strategy_key = str(metrics.get("regime_strategy_key") or metrics.get("entry_strategy_key") or "").lower()
    if strategy_key == "skip":
        return CommitteeVote("regime", "reject", 0.86, "regime_router_skip", "medium")
    if _safe_bool(metrics, "low_energy_probe_allowed"):
        return CommitteeVote("regime", "caution", 0.70, "low_energy_probe_entry", "low")
    return CommitteeVote("regime", "approve", 0.74, "regime_allows_entry")


def evaluate_entry_committee(
    metrics: dict[str, Any],
    settings: EntryCommitteeSettings | None = None,
) -> EntryCommitteeResult:
    """매수 후보를 여러 관점에서 평가하고 최종 통과 여부를 반환한다."""
    settings = settings or load_entry_committee_settings()
    if not settings.enabled or settings.mode == "off":
        return disabled_entry_committee_result()

    votes = (
        _vote_strategy(metrics, settings),
        _vote_risk(metrics, settings),
        _vote_execution(metrics, settings),
        _vote_portfolio(metrics),
        _vote_regime(metrics),
    )
    approve_votes = sum(1 for vote in votes if vote.decision == "approve")
    reject_votes = sum(1 for vote in votes if vote.decision == "reject")
    hard_veto = any(vote.decision == "reject" and vote.severity == "high" for vote in votes)
    risk_approved = not settings.require_risk_approval or any(
        vote.role == "risk" and vote.decision == "approve" for vote in votes
    )
    execution_approved = not settings.require_execution_approval or any(
        vote.role == "execution" and vote.decision == "approve" for vote in votes
    )
    approved = (
        not hard_veto
        and approve_votes >= settings.min_approve_votes
        and risk_approved
        and execution_approved
    )

    if approved:
        reason = "entry_committee_approved"
    elif hard_veto:
        reason = "entry_committee_hard_veto"
    elif not risk_approved:
        reason = "entry_committee_risk_rejected"
    elif not execution_approved:
        reason = "entry_committee_execution_rejected"
    else:
        reason = "entry_committee_insufficient_approvals"

    active_blocks_entry = settings.mode == "active" and not approved
    return EntryCommitteeResult(
        enabled=True,
        mode=settings.mode,
        approved=approved,
        active_blocks_entry=active_blocks_entry,
        hard_veto=hard_veto,
        approve_votes=approve_votes,
        reject_votes=reject_votes,
        min_approve_votes=settings.min_approve_votes,
        reason=reason,
        votes=votes,
    )


def record_entry_committee_result(
    *,
    structured_logger,
    symbol: str,
    metrics: dict[str, Any],
    entry_steps: list[Any],
    result: EntryCommitteeResult,
) -> None:
    """위원회 결과를 shadow 로그 또는 active 퍼널 단계로 연결한다."""
    if not result.enabled:
        return

    if result.mode == "active":
        from structured_log_manager import FunnelStep

        entry_steps.append(
            FunnelStep(
                stage="entry_committee",
                passed=not result.active_blocks_entry,
                reason=result.reason,
                actual=result.actual(),
                required=result.required(),
                extra=result.extra(),
            )
        )
        return

    structured_logger.log_strategy(
        symbol=symbol,
        side="entry",
        stage="entry_committee",
        result="pass" if result.approved else "shadow_reject",
        reason=result.reason,
        actual=result.actual(),
        required=result.required(),
        metrics=metrics,
        extra=result.extra(),
    )
