"""
수정 요약
- system / strategy / trade 로그를 분리 저장하는 구조화 로거를 추가
- 전략 로그에 stage / result / reason 코드와 실제값 / 기준값을 함께 남기도록 추가
- 퍼널 분석용 1시간 요약 파일을 자동으로 갱신하도록 추가
- 시간 버킷 요약에 체결 사유, 시스템 이벤트, 마지막 갱신 시각까지 함께 남기도록 확장

구조화 로그 매니저

- 실거래 봇의 장애 로그는 system.jsonl
- 전략 판단과 차단 사유는 strategy.jsonl
- 체결 결과는 trade.jsonl
- 1시간 단위 퍼널 요약은 summary_1h/*.json 에 저장한다.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from log_path_utils import dated_dir


def _json_safe(value: Any) -> Any:
    """JSON 직렬화가 가능한 값으로 바꾼다."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _write_jsonl(path: Path, record: dict[str, Any]) -> None:
    """JSONL 한 줄을 추가한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def _compact_record_fields(record: dict[str, Any]) -> dict[str, Any]:
    """빈 값이나 불필요한 빈 컨테이너를 제거한다."""
    compact: dict[str, Any] = {}
    for key, value in record.items():
        if value is None:
            continue
        if isinstance(value, dict) and not value:
            continue
        if isinstance(value, list) and not value:
            continue
        compact[key] = value
    return compact


def _sanitize_symbol(symbol: str) -> str:
    """파일명에 쓰기 쉽게 심볼 문자열을 바꾼다."""
    return symbol.replace("/", "_").replace("-", "_")


def _floor_hour(dt: datetime) -> datetime:
    """시각을 1시간 버킷 시작 시각으로 내린다."""
    return dt.replace(minute=0, second=0, microsecond=0)


@dataclass(frozen=True)
class FunnelStep:
    """전략 퍼널 한 단계를 표현한다."""

    stage: str
    passed: bool
    reason: str
    actual: dict[str, Any] | None = None
    required: dict[str, Any] | None = None
    extra: dict[str, Any] | None = None


class StructuredLogManager:
    """실거래 봇용 구조화 이벤트 로거."""

    def __init__(
        self,
        program_name: str,
        *,
        mode: str = "live",
        root_dir: str = "structured_logs",
    ) -> None:
        self.program_name = program_name
        self.root_dir = Path(root_dir)
        self.mode = mode

    def _base_dir(self, date_str: str | None = None) -> Path:
        """현재 날짜 기준 프로그램 로그 디렉토리를 반환한다."""
        return dated_dir(self.root_dir / self.mode, date_str=date_str) / self.program_name

    def _system_path(self) -> Path:
        return self._base_dir() / "system.jsonl"

    def _strategy_path(self) -> Path:
        return self._base_dir() / "strategy.jsonl"

    def _trade_path(self) -> Path:
        return self._base_dir() / "trade.jsonl"

    def _summary_dir(self, date_str: str | None = None) -> Path:
        return self._base_dir(date_str=date_str) / "summary_1h"

    def _build_base_record(self) -> dict[str, Any]:
        now_utc = datetime.now(timezone.utc)
        now_local = datetime.now().astimezone()
        return {
            "recorded_at": now_utc.isoformat(),
            "recorded_at_local": now_local.isoformat(),
            "program_name": self.program_name,
        }

    def log_system(
        self,
        *,
        level: str,
        event: str,
        message: str,
        symbol: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """시스템 이벤트를 system.jsonl 에 남긴다."""
        record = {
            **self._build_base_record(),
            "log_type": "system",
            "level": level.upper(),
            "event": event,
            "symbol": symbol,
            "message": message,
            "context": _json_safe(context or {}),
        }
        _write_jsonl(self._system_path(), record)

    def log_strategy(
        self,
        *,
        symbol: str,
        side: str,
        stage: str,
        result: str,
        reason: str,
        actual: dict[str, Any] | None = None,
        required: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
        level: str | None = None,
    ) -> None:
        """전략 이벤트를 strategy.jsonl 에 남기고 시간 버킷 요약을 갱신한다."""
        if level is None:
            if result in {"blocked", "error"}:
                level = "INFO"
            elif result in {"ready", "requested", "filled"}:
                level = "INFO"
            else:
                level = "DEBUG"

        record = {
            **self._build_base_record(),
            "log_type": "strategy",
            "level": level,
            "symbol": symbol,
            "side": side,
            "stage": stage,
            "result": result,
            "reason": reason,
            "actual": _json_safe(actual or {}),
            "required": _json_safe(required or {}),
            "metrics": _json_safe(metrics or {}),
            "extra": _json_safe(extra or {}),
        }
        _write_jsonl(self._strategy_path(), _compact_record_fields(record))
        self._update_hourly_summary(record)

    def log_trade_event(
        self,
        *,
        symbol: str,
        side: str,
        reason: str,
        result: str,
        actual: dict[str, Any] | None = None,
        required: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """trade.jsonl 에 체결 관련 이벤트를 남긴다."""
        record = {
            **self._build_base_record(),
            "log_type": "trade",
            "symbol": symbol,
            "side": side,
            "result": result,
            "reason": reason,
            "actual": _json_safe(actual or {}),
            "required": _json_safe(required or {}),
            "metrics": _json_safe(metrics or {}),
            "extra": _json_safe(extra or {}),
        }
        _write_jsonl(self._trade_path(), record)

    def run_funnel(
        self,
        *,
        symbol: str,
        side: str,
        steps: list[FunnelStep],
        metrics: dict[str, Any] | None = None,
        ready_stage: str,
        ready_reason: str,
        ready_extra: dict[str, Any] | None = None,
    ) -> tuple[bool, str | None]:
        """퍼널 단계를 순서대로 기록하고 최종 통과 여부를 반환한다."""
        self.log_strategy(
            symbol=symbol,
            side=side,
            stage="scan",
            result="seen",
            reason="scan_started",
            metrics=metrics,
        )

        for step in steps:
            if step.passed:
                self.log_strategy(
                    symbol=symbol,
                    side=side,
                    stage=step.stage,
                    result="pass",
                    reason="passed",
                    actual=step.actual,
                    required=step.required,
                    extra=step.extra,
                )
                continue

            self.log_strategy(
                symbol=symbol,
                side=side,
                stage=step.stage,
                result="blocked",
                reason=step.reason,
                actual=step.actual,
                required=step.required,
                extra=step.extra,
            )
            return False, step.reason

        self.log_strategy(
            symbol=symbol,
            side=side,
            stage=ready_stage,
            result="ready",
            reason=ready_reason,
            metrics=metrics,
            extra=ready_extra,
        )
        return True, None

    def _update_hourly_summary(self, record: dict[str, Any]) -> None:
        """전략 이벤트를 기준으로 1시간 요약 JSON 파일을 갱신한다."""
        symbol = record.get("symbol")
        if not symbol:
            return

        bucket_dt = _floor_hour(datetime.fromisoformat(record["recorded_at_local"]))
        bucket_key = bucket_dt.strftime("%Y-%m-%dT%H:00:00%z")
        summary_path = (
            self._summary_dir(date_str=bucket_dt.strftime("%Y-%m-%d"))
            / f"{self.program_name}__{_sanitize_symbol(symbol)}__{bucket_key}.json"
        )
        summary_path.parent.mkdir(parents=True, exist_ok=True)

        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        else:
            summary = {
                "time_bucket": bucket_dt.isoformat(),
                "program_name": self.program_name,
                "symbol": symbol,
                "last_updated_at": record.get("recorded_at_local"),
                "scan_count": 0,
                "entry_ready_count": 0,
                "exit_ready_count": 0,
                "order_requested_count": 0,
                "filled_count": 0,
                "buy_filled_count": 0,
                "sell_filled_count": 0,
                "order_failed_count": 0,
                "stage_pass_counts": {},
                "stage_block_counts": {},
                "block_reason_counts": {},
                "filled_reason_counts": {},
                "top_block_reason": None,
            }

        stage = str(record.get("stage", ""))
        result = str(record.get("result", ""))
        side = str(record.get("side", ""))
        reason = str(record.get("reason", ""))

        if stage == "scan" and result == "seen":
            summary["scan_count"] += 1
        if stage == "buy_ready" and result == "ready":
            summary["entry_ready_count"] += 1
        if stage == "sell_ready" and result == "ready":
            summary["exit_ready_count"] += 1
        if stage == "order_requested" and result == "requested":
            summary["order_requested_count"] += 1
        if stage == "filled" and result == "filled":
            summary["filled_count"] += 1
            if side == "entry":
                summary["buy_filled_count"] += 1
            elif side == "exit":
                summary["sell_filled_count"] += 1
            filled_reason_counts = Counter(summary.get("filled_reason_counts", {}))
            filled_reason_counts[reason] += 1
            summary["filled_reason_counts"] = dict(filled_reason_counts)
        if stage == "filled" and result == "error":
            summary["order_failed_count"] += 1

        summary["last_updated_at"] = record.get("recorded_at_local")

        if result == "pass":
            stage_pass_counts = Counter(summary.get("stage_pass_counts", {}))
            stage_pass_counts[stage] += 1
            summary["stage_pass_counts"] = dict(stage_pass_counts)

        if result == "blocked":
            stage_block_counts = Counter(summary.get("stage_block_counts", {}))
            stage_block_counts[stage] += 1
            summary["stage_block_counts"] = dict(stage_block_counts)
            block_reason_counts = Counter(summary.get("block_reason_counts", {}))
            block_reason_counts[reason] += 1
            summary["block_reason_counts"] = dict(block_reason_counts)
            top_block = block_reason_counts.most_common(1)
            summary["top_block_reason"] = top_block[0][0] if top_block else None

        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def choose_volatility_reason(
    value: float | None,
    *,
    min_value: float,
    max_value: float,
) -> str:
    """변동성 값에 맞는 차단 사유 코드를 반환한다."""
    if value is None:
        return "volatility_data_missing"
    if value < min_value:
        return "volatility_low"
    if value > max_value:
        return "volatility_high"
    return "volatility_out_of_range"


def choose_atr_reason(
    value: float | None,
    *,
    min_value: float,
    max_value: float,
) -> str:
    """ATR 값에 맞는 차단 사유 코드를 반환한다."""
    if value is None:
        return "atr_data_missing"
    if value < min_value:
        return "atr_low"
    if value > max_value:
        return "atr_high"
    return "atr_out_of_range"
