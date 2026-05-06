"""
수정 요약
- 2026-05-06: 텔레그램 요약에 가상 후보 판정과 비율 중심 해석을 추가했다.
- 실제 매수되지 않은 진입 후보를 이후 가격 흐름으로 가상 추적하는 분석 모듈을 추가했다.

미체결 후보 가상 추적

- strategy.jsonl 의 entry scan 을 후보로 보고, 직후 blocked 사유와 이후 scan 가격을 연결한다.
- 후보별로 MFE, MAE, 최종 수익률, 가상 TP/SL 도달 여부를 계산한다.
- 실제 주문 로직을 바꾸지 않고 "막힌 진입이 이후에 좋았는지"를 검증하는 보조 리포트를 만든다.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from log_path_utils import iter_files
from reporting.change_effect_report import (
    parse_timestamp,
    path_overlaps_window,
    read_jsonl,
    safe_float,
)


@dataclass
class ShadowCandidate:
    """가상 추적 대상 진입 후보."""

    candidate_id: str
    program_name: str
    symbol: str
    recorded_at_local: str
    entry_price: float
    signal_score: float | None
    effective_position_ratio: float | None
    strategy_key: str
    symbol_regime: str
    block_stage: str | None = None
    block_reason: str | None = None
    status: str = "open"
    outcome: str = "open"
    observed_until: str | None = None
    mfe_pct: float | None = None
    mae_pct: float | None = None
    final_return_pct: float | None = None
    hit_at_local: str | None = None


@dataclass(frozen=True)
class PricePoint:
    """후속 scan 가격 포인트."""

    ts: datetime
    recorded_at_local: str
    price: float


def build_candidate_id(program_name: str, symbol: str, ts: datetime) -> str:
    """후보 식별자를 만든다."""
    safe_symbol = symbol.replace("/", "_").replace("-", "_")
    return f"{program_name}:{safe_symbol}:{ts.strftime('%Y%m%dT%H%M%S')}"


def iter_strategy_records(
    base_dir: Path | str,
    *,
    recent_days: int = 0,
    lookback_hours: float = 6.0,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """구조화 전략 로그를 시간순으로 읽는다."""
    root = Path(base_dir)
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    current = now or datetime.now()
    if recent_days > 0:
        start_at = current - timedelta(days=recent_days)
    elif lookback_hours > 0:
        start_at = current - timedelta(hours=lookback_hours)
    else:
        start_at = None
    for path in iter_files(root, "strategy.jsonl"):
        if not path_overlaps_window(path, start_at, current):
            continue
        rows.extend(read_jsonl(path, start_at=start_at, end_at=current))
    rows.sort(
        key=lambda record: parse_timestamp(
            record.get("recorded_at_local") or record.get("recorded_at")
        )
        or datetime.min
    )
    return rows


def is_entry_scan_candidate(
    record: dict[str, Any],
    *,
    min_signal_score: float,
    min_effective_position_ratio: float,
) -> bool:
    """entry scan 레코드가 가상 추적 후보인지 판단한다."""
    if str(record.get("side", "")).lower() != "entry":
        return False
    if record.get("stage") != "scan" or record.get("result") != "seen":
        return False
    metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
    if bool(metrics.get("has_position")):
        return False
    price = safe_float(metrics.get("price"))
    if price is None or price <= 0:
        return False
    signal_score = safe_float(metrics.get("signal_score"))
    if signal_score is None or signal_score < min_signal_score:
        return False
    ratio = safe_float(metrics.get("effective_position_ratio"))
    if ratio is None:
        ratio = safe_float(metrics.get("position_ratio"))
    if ratio is None or ratio < min_effective_position_ratio:
        return False
    return True


def extract_candidate(record: dict[str, Any]) -> ShadowCandidate | None:
    """scan 레코드에서 후보 정보를 추출한다."""
    ts = parse_timestamp(record.get("recorded_at_local") or record.get("recorded_at"))
    metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
    price = safe_float(metrics.get("price"))
    if ts is None or price is None:
        return None
    program_name = str(record.get("program_name", ""))
    symbol = str(record.get("symbol", ""))
    ratio = safe_float(metrics.get("effective_position_ratio"))
    if ratio is None:
        ratio = safe_float(metrics.get("position_ratio"))
    return ShadowCandidate(
        candidate_id=build_candidate_id(program_name, symbol, ts),
        program_name=program_name,
        symbol=symbol,
        recorded_at_local=str(record.get("recorded_at_local") or record.get("recorded_at")),
        entry_price=price,
        signal_score=safe_float(metrics.get("signal_score")),
        effective_position_ratio=ratio,
        strategy_key=str(metrics.get("regime_strategy_key", "")),
        symbol_regime=str(metrics.get("symbol_regime", "")),
    )


def extract_price_point(record: dict[str, Any]) -> PricePoint | None:
    """scan 레코드에서 가격 포인트를 추출한다."""
    if record.get("stage") != "scan" or record.get("result") != "seen":
        return None
    metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
    price = safe_float(metrics.get("price"))
    ts = parse_timestamp(record.get("recorded_at_local") or record.get("recorded_at"))
    if price is None or price <= 0 or ts is None:
        return None
    return PricePoint(
        ts=ts,
        recorded_at_local=str(record.get("recorded_at_local") or record.get("recorded_at")),
        price=price,
    )


def collect_shadow_candidates(
    records: list[dict[str, Any]],
    *,
    min_signal_score: float = 50.0,
    min_effective_position_ratio: float = 0.01,
    cooldown_seconds: int = 300,
) -> tuple[list[ShadowCandidate], dict[tuple[str, str], list[PricePoint]]]:
    """전략 로그에서 후보와 후속 가격 포인트를 수집한다."""
    candidates: list[ShadowCandidate] = []
    price_points: dict[tuple[str, str], list[PricePoint]] = defaultdict(list)
    pending: dict[tuple[str, str], ShadowCandidate] = {}
    last_candidate_ts: dict[tuple[str, str], datetime] = {}

    for record in records:
        program_name = str(record.get("program_name", ""))
        symbol = str(record.get("symbol", ""))
        key = (program_name, symbol)
        point = extract_price_point(record)
        if point is not None:
            price_points[key].append(point)

        if record.get("result") == "blocked" and key in pending:
            candidate = pending[key]
            if candidate.block_reason is None:
                candidate.block_stage = str(record.get("stage", ""))
                candidate.block_reason = str(record.get("reason", ""))
            pending.pop(key, None)

        if (
            str(record.get("side", "")).lower() == "entry"
            and key in pending
            and record.get("stage") in {"buy_ready", "order_requested", "filled"}
            and record.get("result") in {"ready", "requested", "filled"}
        ):
            pending[key].status = "actual_entry"
            pending.pop(key, None)

        if not is_entry_scan_candidate(
            record,
            min_signal_score=min_signal_score,
            min_effective_position_ratio=min_effective_position_ratio,
        ):
            continue

        ts = parse_timestamp(record.get("recorded_at_local") or record.get("recorded_at"))
        if ts is None:
            continue
        previous_ts = last_candidate_ts.get(key)
        if previous_ts is not None and (ts - previous_ts).total_seconds() < cooldown_seconds:
            continue

        candidate = extract_candidate(record)
        if candidate is None:
            continue
        candidates.append(candidate)
        pending[key] = candidate
        last_candidate_ts[key] = ts

    return candidates, price_points


def evaluate_candidate(
    candidate: ShadowCandidate,
    points: list[PricePoint],
    *,
    horizon_minutes: int,
    take_profit_pct: float,
    stop_loss_pct: float,
) -> ShadowCandidate:
    """후보의 이후 가격 흐름을 평가한다."""
    entry_ts = parse_timestamp(candidate.recorded_at_local)
    if entry_ts is None:
        candidate.status = "invalid"
        candidate.outcome = "invalid"
        return candidate

    horizon_end = entry_ts + timedelta(minutes=horizon_minutes)
    future_points = [
        point
        for point in points
        if entry_ts < point.ts <= horizon_end
    ]
    if not future_points:
        candidate.status = "open"
        candidate.outcome = "not_enough_future_prices"
        return candidate

    max_return = None
    min_return = None
    final_return = None
    first_outcome = "timeout"
    hit_at = None
    for point in future_points:
        return_pct = ((point.price - candidate.entry_price) / candidate.entry_price) * 100
        max_return = return_pct if max_return is None else max(max_return, return_pct)
        min_return = return_pct if min_return is None else min(min_return, return_pct)
        final_return = return_pct
        if first_outcome == "timeout":
            if return_pct >= take_profit_pct:
                first_outcome = "would_take_profit"
                hit_at = point.recorded_at_local
            elif return_pct <= -abs(stop_loss_pct):
                first_outcome = "would_stop_loss"
                hit_at = point.recorded_at_local

    candidate.status = "matured"
    candidate.outcome = first_outcome
    candidate.observed_until = future_points[-1].recorded_at_local
    candidate.mfe_pct = max_return
    candidate.mae_pct = min_return
    candidate.final_return_pct = final_return
    candidate.hit_at_local = hit_at
    return candidate


def build_shadow_candidate_report(
    *,
    strategy_log_root: Path | str = Path("structured_logs/live"),
    recent_days: int = 0,
    lookback_hours: float = 6.0,
    min_signal_score: float = 50.0,
    min_effective_position_ratio: float = 0.01,
    cooldown_seconds: int = 300,
    horizon_minutes: int = 60,
    take_profit_pct: float = 0.5,
    stop_loss_pct: float = 0.8,
) -> dict[str, Any]:
    """미체결 후보 가상 추적 리포트 payload 를 만든다."""
    records = iter_strategy_records(
        strategy_log_root,
        recent_days=recent_days,
        lookback_hours=lookback_hours,
    )
    candidates, price_points = collect_shadow_candidates(
        records,
        min_signal_score=min_signal_score,
        min_effective_position_ratio=min_effective_position_ratio,
        cooldown_seconds=cooldown_seconds,
    )
    shadow_candidates = [
        candidate for candidate in candidates if candidate.status != "actual_entry"
    ]
    evaluated = [
        evaluate_candidate(
            candidate,
            price_points.get((candidate.program_name, candidate.symbol), []),
            horizon_minutes=horizon_minutes,
            take_profit_pct=take_profit_pct,
            stop_loss_pct=stop_loss_pct,
        )
        for candidate in shadow_candidates
    ]
    matured = [candidate for candidate in evaluated if candidate.status == "matured"]
    outcome_counts = Counter(candidate.outcome for candidate in evaluated)
    block_reason_counts = Counter(
        candidate.block_reason or "not_blocked_before_next_scan"
        for candidate in evaluated
    )
    mfe_values = [candidate.mfe_pct for candidate in matured if candidate.mfe_pct is not None]
    mae_values = [candidate.mae_pct for candidate in matured if candidate.mae_pct is not None]
    final_values = [
        candidate.final_return_pct
        for candidate in matured
        if candidate.final_return_pct is not None
    ]

    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "filters": {
            "min_signal_score": min_signal_score,
            "min_effective_position_ratio": min_effective_position_ratio,
            "cooldown_seconds": cooldown_seconds,
            "horizon_minutes": horizon_minutes,
            "take_profit_pct": take_profit_pct,
            "stop_loss_pct": stop_loss_pct,
            "recent_days": recent_days,
            "lookback_hours": lookback_hours,
        },
        "summary": {
            "candidate_count": len(evaluated),
            "matured_count": len(matured),
            "would_take_profit_count": outcome_counts.get("would_take_profit", 0),
            "would_stop_loss_count": outcome_counts.get("would_stop_loss", 0),
            "timeout_count": outcome_counts.get("timeout", 0),
            "open_count": len(evaluated) - len(matured),
            "avg_mfe_pct": sum(mfe_values) / len(mfe_values) if mfe_values else None,
            "avg_mae_pct": sum(mae_values) / len(mae_values) if mae_values else None,
            "avg_final_return_pct": (
                sum(final_values) / len(final_values) if final_values else None
            ),
            "top_block_reasons": block_reason_counts.most_common(8),
            "outcome_counts": outcome_counts.most_common(),
        },
        "candidates": [asdict(candidate) for candidate in evaluated],
    }


def format_float(value: float | None, decimals: int = 3) -> str:
    """실수 값을 표시한다."""
    if value is None:
        return "-"
    return f"{value:.{decimals}f}"


def format_top_items(items: list[Any], limit: int = 3) -> str:
    """상위 항목 목록을 짧게 표시한다."""
    normalized: list[tuple[str, int]] = []
    for item in items[:limit]:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            normalized.append((str(item[0]), int(item[1])))
    if not normalized:
        return "없음"
    return ", ".join(f"{name}:{count}" for name, count in normalized)


def build_shadow_candidate_verdict(summary: dict[str, Any]) -> str:
    """가상 후보 결과를 바로 판단할 수 있는 한 줄로 만든다."""
    matured = int(summary.get("matured_count", 0) or 0)
    would_take_profit = int(summary.get("would_take_profit_count", 0) or 0)
    would_stop_loss = int(summary.get("would_stop_loss_count", 0) or 0)
    avg_mfe = summary.get("avg_mfe_pct")
    avg_final = summary.get("avg_final_return_pct")
    if matured <= 0:
        return "판정: 아직 관찰 완료 후보가 없습니다. 다음 리포트에서 다시 봐야 합니다."
    tp_rate = (would_take_profit / matured) * 100
    sl_rate = (would_stop_loss / matured) * 100
    if would_take_profit <= 0 and would_stop_loss <= 0:
        return "판정: 막힌 후보 대부분이 TP/SL 어느 쪽에도 닿지 못했습니다. 현재 차단은 기회 손실보다 과매매 방지 성격이 큽니다."
    if tp_rate >= 15.0 and would_take_profit >= would_stop_loss * 3:
        return "판정: 막힌 후보 중 일부는 수익 기회였습니다. 상위 차단 사유는 소액/추가확인 후보로 낮출지 검토할 가치가 있습니다."
    if sl_rate >= 5.0 and would_stop_loss >= would_take_profit:
        return "판정: 막힌 후보가 손절로 갈 위험이 큽니다. 해당 차단은 유지하는 편이 안전합니다."
    if avg_final is not None and float(avg_final) < 0 and avg_mfe is not None and float(avg_mfe) < 0.3:
        return "판정: 평균 반등 폭이 작고 최종 수익률도 약합니다. 진입 완화 근거로 쓰기에는 약합니다."
    return "판정: 일부 기회는 있지만 강하지 않습니다. 상위 후보만 추가 확인 대상으로 분리하는 방식이 적합합니다."


def format_shadow_candidate_text(report: dict[str, Any], *, limit: int = 5) -> str:
    """미체결 후보 가상 추적 payload 를 텔레그램/CLI 문구로 만든다."""
    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    filters = report.get("filters", {}) if isinstance(report.get("filters"), dict) else {}
    candidates = report.get("candidates", []) if isinstance(report.get("candidates"), list) else []
    lookback_text = (
        f"최근 {filters.get('recent_days')}일"
        if int(filters.get("recent_days", 0) or 0) > 0
        else f"최근 {filters.get('lookback_hours')}시간"
    )
    lines = [
        "미체결 후보 가상 추적",
        (
            f"- 기준: {lookback_text} / "
            f"점수>={filters.get('min_signal_score')} / "
            f"비중>={filters.get('min_effective_position_ratio')} / "
            f"{filters.get('horizon_minutes')}분 관찰 / "
            f"TP {filters.get('take_profit_pct')}% / SL {filters.get('stop_loss_pct')}%"
        ),
        f"- {build_shadow_candidate_verdict(summary)}",
        (
            "- 요약: "
            f"후보 {summary.get('candidate_count', 0)}개 | "
            f"성숙 {summary.get('matured_count', 0)}개 | "
            f"가상 익절 {summary.get('would_take_profit_count', 0)}개 | "
            f"가상 손절 {summary.get('would_stop_loss_count', 0)}개 | "
            f"시간만료 {summary.get('timeout_count', 0)}개"
        ),
        (
            "- 평균: "
            f"MFE {format_float(summary.get('avg_mfe_pct'))}% | "
            f"MAE {format_float(summary.get('avg_mae_pct'))}% | "
            f"최종 {format_float(summary.get('avg_final_return_pct'))}%"
        ),
        f"- 주요 미체결 사유: {format_top_items(summary.get('top_block_reasons', []))}",
    ]

    ranked = sorted(
        [
            candidate
            for candidate in candidates
            if isinstance(candidate, dict) and candidate.get("status") == "matured"
        ],
        key=lambda item: float(item.get("mfe_pct") or 0.0),
        reverse=True,
    )
    if ranked:
        lines.append("- 가상 기회 상위:")
        for candidate in ranked[:limit]:
            lines.append(
                f"  {candidate.get('program_name')} | {candidate.get('symbol')} | "
                f"{candidate.get('outcome')} | "
                f"MFE {format_float(candidate.get('mfe_pct'))}% / "
                f"MAE {format_float(candidate.get('mae_pct'))}% | "
                f"사유 {candidate.get('block_reason') or '-'}"
            )
    return "\n".join(lines)


def write_report(
    report: dict[str, Any],
    output_dir: Path | str = Path("reports/shadow_candidates"),
) -> Path:
    """가상 추적 결과를 JSON 파일로 저장한다."""
    output_root = Path(output_dir)
    generated_at = parse_timestamp(report.get("generated_at")) or datetime.now()
    date_dir = output_root / generated_at.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    path = date_dir / f"shadow_candidates_{generated_at.strftime('%H%M%S')}.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
