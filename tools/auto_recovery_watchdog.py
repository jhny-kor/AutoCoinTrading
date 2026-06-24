"""
작업 요약
- healthcheck 결과를 주기적으로 확인해 장애 프로세스를 자동 재기동하는 운영 watchdog 을 추가했다.
- 자동 조치 결과는 runtime 로그와 텔레그램 알림으로 남기고, 쿨다운/시간당 재기동 제한으로 restart loop 를 막는다.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot_manager import handle_start, handle_stop, is_pid_alive, read_pid_file
from core.runtime.program_registry import PROGRAM_BY_NAME, PROGRAMS, PROGRAM_TITLES
from log_path_utils import dated_path
from telegram_notifier import load_telegram_notifier
from tools.healthcheck import build_health_report


STATE_PATH = Path("logs/runtime/auto_recovery/state.json")
EVENTS_PATH = Path("logs/runtime/auto_recovery/events.jsonl")
RECOVERABLE_PROGRAMS = tuple(name for name in PROGRAMS if name != "auto_recovery")


@dataclass(frozen=True)
class RecoveryTarget:
    """자동복구 대상 프로그램과 원인."""

    name: str
    status: str
    reason: str
    item: dict[str, Any]


def _now_text(ts: float | None = None) -> str:
    """현재 시각을 로그용 문자열로 반환한다."""
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(ts or time.time()))


def _read_state(path: Path = STATE_PATH) -> dict[str, Any]:
    """자동복구 상태 파일을 읽는다."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return {"programs": {}}
    if not isinstance(payload, dict):
        return {"programs": {}}
    programs = payload.get("programs")
    if not isinstance(programs, dict):
        payload["programs"] = {}
    return payload


def _write_state(state: dict[str, Any], path: Path = STATE_PATH) -> None:
    """자동복구 상태 파일을 원자적으로 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.{int(time.time() * 1000)}.tmp")
    temp_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(path)


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """JSONL 이벤트를 추가한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def _append_text_log(message: str) -> None:
    """healthcheck 가 볼 수 있는 날짜별 운영 로그를 남긴다."""
    path = dated_path("logs", "auto_recovery_watchdog.log")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{_now_text()} {message}\n")


def _program_state(state: dict[str, Any], name: str) -> dict[str, Any]:
    """프로그램별 상태 dict 를 반환한다."""
    programs = state.setdefault("programs", {})
    if not isinstance(programs, dict):
        state["programs"] = {}
        programs = state["programs"]
    item = programs.setdefault(name, {})
    if not isinstance(item, dict):
        programs[name] = {}
        item = programs[name]
    return item


def _prune_recent_restarts(restarts: list[Any], now_ts: float, window_sec: int = 3600) -> list[float]:
    """최근 window 안의 재기동 시각만 남긴다."""
    pruned: list[float] = []
    for value in restarts:
        try:
            restart_ts = float(value)
        except (TypeError, ValueError):
            continue
        if now_ts - restart_ts <= window_sec:
            pruned.append(restart_ts)
    return pruned


def classify_failure(name: str, item: dict[str, Any]) -> str:
    """헬스체크 항목을 자동복구 reason 코드로 분류한다."""
    if not item.get("alive"):
        return "process_down"
    if name in ("upbit_stream", "okx_stream"):
        ws_health = item.get("ws_health") if isinstance(item.get("ws_health"), dict) else {}
        if not ws_health.get("connected"):
            return "websocket_disconnected"
        return "websocket_heartbeat_stale"
    if item.get("latest_log_age_sec") is None:
        return "log_missing"
    return "log_stale"


def detect_recovery_targets(
    report: dict[str, Any],
    *,
    recover_warnings: bool,
    recoverable_programs: tuple[str, ...] = RECOVERABLE_PROGRAMS,
) -> list[RecoveryTarget]:
    """healthcheck 리포트에서 자동복구 대상을 추출한다."""
    targets: list[RecoveryTarget] = []
    programs = report.get("programs", {})
    if not isinstance(programs, dict):
        return targets

    for name in recoverable_programs:
        item = programs.get(name)
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "OK"))
        should_recover = status == "FAIL" or (recover_warnings and status == "WARN")
        if not should_recover:
            continue
        targets.append(
            RecoveryTarget(
                name=name,
                status=status,
                reason=classify_failure(name, item),
                item=item,
            )
        )
    return targets


def _can_recover(
    state: dict[str, Any],
    target: RecoveryTarget,
    *,
    now_ts: float,
    cooldown_sec: int,
    max_restarts_per_hour: int,
) -> tuple[bool, str]:
    """쿨다운과 시간당 제한을 확인한다."""
    item = _program_state(state, target.name)
    last_recovery_ts = float(item.get("last_recovery_ts", 0.0) or 0.0)
    if now_ts - last_recovery_ts < cooldown_sec:
        return False, "recovery_cooldown_active"

    restarts = _prune_recent_restarts(item.get("restart_timestamps", []), now_ts)
    item["restart_timestamps"] = restarts
    if len(restarts) >= max_restarts_per_hour:
        return False, "restart_rate_limit_reached"
    return True, "recoverable"


def _record_recovery_attempt(
    state: dict[str, Any],
    target: RecoveryTarget,
    *,
    now_ts: float,
    result: str,
    new_pid: int | None,
    detail: str,
) -> None:
    """복구 시도 결과를 상태에 저장한다."""
    item = _program_state(state, target.name)
    restarts = _prune_recent_restarts(item.get("restart_timestamps", []), now_ts)
    if result == "recovered":
        restarts.append(now_ts)
        item["last_recovery_ts"] = now_ts
        item["last_recovery_at"] = _now_text(now_ts)
    item["restart_timestamps"] = restarts
    item["last_status"] = target.status
    item["last_reason"] = target.reason
    item["last_result"] = result
    item["last_detail"] = detail
    item["last_pid"] = new_pid


def _send_recovery_message(
    *,
    program_name: str,
    reason: str,
    result: str,
    new_pid: int | None,
    detail: str,
    notify: bool,
) -> None:
    """자동복구 결과 텔레그램 메시지를 전송한다."""
    if not notify:
        return
    notifier = load_telegram_notifier()
    title = PROGRAM_TITLES.get(program_name, program_name)
    if result == "recovered":
        body = (
            f"{title} 장애 발생하여 해결완료\n"
            f"원인: {reason}\n"
            f"조치: 재기동\n"
            f"새 PID: {new_pid}\n"
            f"상세: {detail}"
        )
        notifier.send_message(f"[자동복구] {body}")
        return

    if result == "skipped":
        notifier.notify_attention_required(
            "자동복구",
            f"{title} 장애 감지, 자동 조치 보류\n원인: {reason}\n상세: {detail}",
        )
        return

    notifier.notify_attention_required(
        "자동복구",
        f"{title} 장애 감지, 자동 조치 실패\n원인: {reason}\n상세: {detail}",
    )


def recover_target(
    target: RecoveryTarget,
    *,
    state: dict[str, Any],
    now_ts: float,
    cooldown_sec: int,
    max_restarts_per_hour: int,
    dry_run: bool,
    notify: bool,
    stop_func: Callable[[str], int] = handle_stop,
    start_func: Callable[[str], int] = handle_start,
) -> dict[str, Any]:
    """단일 프로그램을 자동복구한다."""
    allowed, gate_reason = _can_recover(
        state,
        target,
        now_ts=now_ts,
        cooldown_sec=cooldown_sec,
        max_restarts_per_hour=max_restarts_per_hour,
    )
    title = PROGRAM_TITLES.get(target.name, target.name)
    if not allowed:
        detail = f"{gate_reason}: {title} 최근 재기동 제한에 걸렸습니다."
        _record_recovery_attempt(
            state,
            target,
            now_ts=now_ts,
            result="skipped",
            new_pid=target.item.get("pid"),
            detail=detail,
        )
        _send_recovery_message(
            program_name=target.name,
            reason=target.reason,
            result="skipped",
            new_pid=target.item.get("pid"),
            detail=detail,
            notify=notify,
        )
        return {
            "program": target.name,
            "result": "skipped",
            "reason": target.reason,
            "detail": detail,
        }

    if dry_run:
        detail = f"dry_run: {title} 재기동 예정"
        _record_recovery_attempt(
            state,
            target,
            now_ts=now_ts,
            result="dry_run",
            new_pid=target.item.get("pid"),
            detail=detail,
        )
        return {
            "program": target.name,
            "result": "dry_run",
            "reason": target.reason,
            "detail": detail,
        }

    stop_code = stop_func(target.name)
    start_code = start_func(target.name)
    time.sleep(1.0)
    new_pid = read_pid_file(target.name)
    recovered = start_code == 0 and new_pid is not None and is_pid_alive(new_pid)
    result = "recovered" if recovered else "failed"
    detail = (
        f"stop_code={stop_code}, start_code={start_code}, pid={new_pid}, "
        f"script={PROGRAM_BY_NAME[target.name].script if target.name in PROGRAM_BY_NAME else target.name}"
    )
    _record_recovery_attempt(
        state,
        target,
        now_ts=now_ts,
        result=result,
        new_pid=new_pid,
        detail=detail,
    )
    _send_recovery_message(
        program_name=target.name,
        reason=target.reason,
        result=result,
        new_pid=new_pid,
        detail=detail,
        notify=notify,
    )
    return {
        "program": target.name,
        "result": result,
        "reason": target.reason,
        "detail": detail,
        "new_pid": new_pid,
    }


def run_once(
    *,
    max_log_age_sec: int,
    mode: str,
    recover_warnings: bool,
    cooldown_sec: int,
    max_restarts_per_hour: int,
    dry_run: bool,
    notify: bool,
    state_path: Path = STATE_PATH,
) -> list[dict[str, Any]]:
    """헬스체크 1회 실행 후 필요한 자동복구를 수행한다."""
    report = build_health_report(max_log_age_sec, mode=mode)
    targets = detect_recovery_targets(report, recover_warnings=recover_warnings)
    state = _read_state(state_path)
    now_ts = time.time()
    events: list[dict[str, Any]] = []

    for target in targets:
        event = recover_target(
            target,
            state=state,
            now_ts=now_ts,
            cooldown_sec=cooldown_sec,
            max_restarts_per_hour=max_restarts_per_hour,
            dry_run=dry_run,
            notify=notify,
        )
        event["recorded_at"] = _now_text(now_ts)
        events.append(event)
        _append_jsonl(EVENTS_PATH, event)
        _append_text_log(
            f"{event['program']} {event['result']} reason={event['reason']} detail={event['detail']}"
        )

    if not events:
        _append_text_log(f"healthcheck {report.get('status')} no_recovery_target")

    _write_state(state, state_path)
    return events


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 만든다."""
    parser = argparse.ArgumentParser(description="자동복구 watchdog")
    parser.add_argument("--once", action="store_true", help="1회만 점검하고 종료합니다.")
    parser.add_argument("--interval-sec", type=int, default=60)
    parser.add_argument("--initial-delay-sec", type=int, default=60)
    parser.add_argument("--max-log-age-sec", type=int, default=1800)
    parser.add_argument("--mode", choices=("warning", "strict"), default="warning")
    parser.add_argument("--cooldown-sec", type=int, default=300)
    parser.add_argument("--max-restarts-per-hour", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-notify", action="store_true")
    parser.add_argument(
        "--no-recover-warnings",
        action="store_true",
        help="WARN 상태 프로그램은 자동복구하지 않습니다.",
    )
    return parser


def main() -> int:
    """watchdog 진입점."""
    args = build_parser().parse_args()
    notify = not args.no_notify
    recover_warnings = not args.no_recover_warnings
    _append_text_log("auto_recovery_watchdog_started")

    if args.once:
        events = run_once(
            max_log_age_sec=args.max_log_age_sec,
            mode=args.mode,
            recover_warnings=recover_warnings,
            cooldown_sec=args.cooldown_sec,
            max_restarts_per_hour=args.max_restarts_per_hour,
            dry_run=args.dry_run,
            notify=notify,
        )
        print(json.dumps(events, ensure_ascii=False, indent=2))
        return 0

    if args.initial_delay_sec > 0:
        time.sleep(args.initial_delay_sec)

    while True:
        run_once(
            max_log_age_sec=args.max_log_age_sec,
            mode=args.mode,
            recover_warnings=recover_warnings,
            cooldown_sec=args.cooldown_sec,
            max_restarts_per_hour=args.max_restarts_per_hour,
            dry_run=args.dry_run,
            notify=notify,
        )
        time.sleep(max(5, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
