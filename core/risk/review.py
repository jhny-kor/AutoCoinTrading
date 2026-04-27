"""
수정 요약
- TradingAgents 의 risk manager / portfolio manager 개념을 실거래 주문 gate 와 분리된 감사용 risk review 로 추가했다.
- 체결 레코드의 신호, 시장, 실행 품질, 결과 지표를 점수화해 allow/reduce/block 성격의 사후 판단을 남긴다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RiskReview:
    """체결/청산 레코드에 대한 감사용 risk review 결과."""

    score: float
    posture: str
    action: str
    concerns: tuple[str, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "posture": self.posture,
            "action": self.action,
            "concerns": list(self.concerns),
            "notes": list(self.notes),
        }


def safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return None


def _posture_for_score(score: float) -> tuple[str, str]:
    if score < 45:
        return "block_candidate", "future_block_or_manual_review"
    if score < 70:
        return "reduce_candidate", "reduce_size_or_require_confirmation"
    return "allow_candidate", "allow_under_current_rules"


def build_trade_risk_review(record: dict[str, Any]) -> RiskReview:
    """trade_history 레코드를 기반으로 사후 risk review 를 만든다."""
    extra = record.get("extra") if isinstance(record.get("extra"), dict) else {}
    side = str(record.get("side", "") or "").lower()
    reason = str(record.get("reason", "") or "")

    score = 100.0
    concerns: list[str] = []
    notes: list[str] = []

    signal_score = safe_float(extra.get("signal_score"))
    if side == "buy":
        if signal_score is not None:
            if signal_score < 55:
                score -= 30
                concerns.append("entry_signal_score_very_low")
            elif signal_score < 70:
                score -= 15
                concerns.append("entry_signal_score_marginal")
            else:
                notes.append("entry_signal_score_ok")

        volume_passed = safe_bool(extra.get("volume_filter_passed"))
        if volume_passed is False:
            score -= 15
            concerns.append("entry_volume_filter_failed")

        volatility_passed = safe_bool(extra.get("volatility_filter_passed"))
        if volatility_passed is False:
            score -= 15
            concerns.append("entry_volatility_filter_failed")

        htf_bullish = safe_bool(extra.get("htf_bullish"))
        if htf_bullish is False:
            score -= 12
            concerns.append("entry_htf_not_bullish")

        gap_pct = safe_float(extra.get("gap_pct"))
        if gap_pct is not None and gap_pct < 0.06:
            score -= 8
            concerns.append("entry_gap_too_small_for_follow_through")

    if side == "sell":
        pnl_pct = safe_float(record.get("net_realized_pnl_pct"))
        if pnl_pct is None:
            pnl_pct = safe_float(record.get("realized_pnl_pct"))
        mfe_pct = safe_float(record.get("mfe_pct"))
        holding_seconds = safe_float(record.get("holding_seconds"))

        if pnl_pct is not None and pnl_pct < 0:
            score -= 25
            concerns.append("exit_negative_pnl")
            if reason in {"stop_loss", "partial_stop_loss"}:
                score -= 15
                concerns.append("stop_loss_exit")
        elif pnl_pct is not None:
            notes.append("exit_positive_or_flat")

        if mfe_pct is not None and mfe_pct < 0.2:
            score -= 15
            concerns.append("trade_never_reached_minimum_profit_buffer")

        if holding_seconds is not None and holding_seconds < 180 and pnl_pct is not None and pnl_pct < 0:
            score -= 15
            concerns.append("fast_failure_after_entry")

        if reason in {
            "profit_protect_take_profit",
            "trailing_take_profit",
            "volume_spike_take_profit",
        }:
            notes.append("protective_exit_worked")

    score = max(0.0, min(100.0, score))
    posture, action = _posture_for_score(score)
    return RiskReview(
        score=round(score, 2),
        posture=posture,
        action=action,
        concerns=tuple(concerns),
        notes=tuple(notes),
    )


def build_reflection(record: dict[str, Any], review: RiskReview) -> str:
    """레코드와 risk review 를 사람이 읽기 쉬운 한 줄 reflection 으로 요약한다."""
    symbol = str(record.get("symbol", "") or "-")
    side = str(record.get("side", "") or "-")
    reason = str(record.get("reason", "") or "-")
    pnl_pct = safe_float(record.get("net_realized_pnl_pct"))
    if pnl_pct is None:
        pnl_pct = safe_float(record.get("realized_pnl_pct"))

    if side.lower() == "sell" and pnl_pct is not None and pnl_pct < 0:
        main = f"{symbol} {reason} 손실: 다음 진입에서는 {review.action} 검토"
    elif side.lower() == "sell" and pnl_pct is not None:
        main = f"{symbol} {reason} 이익/방어 청산: 유지 가능한 조건"
    elif side.lower() == "buy":
        main = f"{symbol} 신규 진입 감사: {review.action}"
    else:
        main = f"{symbol} {side} 감사: {review.action}"

    if review.concerns:
        return f"{main} | 우려: {', '.join(review.concerns[:3])}"
    if review.notes:
        return f"{main} | 근거: {', '.join(review.notes[:3])}"
    return main
