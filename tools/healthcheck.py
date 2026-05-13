"""
작업 요약
- analysis/structured 로그도 오늘자 파일이 아직 없으면 전날 최신 파일을 fallback 으로 사용한다.
- 자정 직후 오늘자 로그가 아직 없을 때 전날 최신 로그를 fallback 으로 사용해 log_missing 오탐 재기동을 줄였다.
- upbit_stream 은 프로그램 로그 대신 `logs/runtime/upbit_ws/health.json` heartbeat 를 우선 기준으로 판단하도록 개선
- 2026-04-08: 헬스체크를 warning/strict 모드로 분리하고 비핵심 프로그램은 warning 모드에서 전체 실패로 보지 않도록 확장
- 관리 대상 프로세스와 최신 로그 갱신 상태를 점검하는 운영 헬스체크를 추가했다.
- collector/telegram 특성에 맞는 로그 판정 기준을 포함해 JSON/텍스트 출력이 가능하도록 구성했다.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot_manager import read_pid_file, is_pid_alive
from core.runtime.program_registry import PROGRAMS
from log_path_utils import current_date_str, latest_file


WARNING_PROGRAMS = {"upbit_stream"}


def file_age_seconds(path: Path | None) -> float | None:
    if path is None or not path.exists():
        return None
    return max(0.0, time.time() - path.stat().st_mtime)


def latest_dated_file(root: Path, pattern: str, date_text: str | None = None) -> Path | None:
    """오늘자 파일이 없으면 날짜별 디렉터리 전체에서 가장 최근 파일을 찾는다."""
    today_log = latest_file(root / (date_text or current_date_str()), pattern)
    if today_log is not None:
        return today_log

    candidates = [path for path in root.glob(f"*/{pattern}") if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def latest_program_log(script: str, date_text: str | None = None) -> Path | None:
    """오늘자 로그가 없으면 전체 날짜 로그 중 가장 최근 파일을 사용한다."""
    return latest_dated_file(Path("logs"), f"{Path(script).stem}.log", date_text)


def read_json_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return {}


def build_upbit_stream_health(max_log_age_sec: int) -> dict:
    """업비트 웹소켓 health heartbeat 기준 상태를 반환한다."""
    health_path = Path("logs/runtime/upbit_ws/health.json")
    payload = read_json_file(health_path)
    health_age = file_age_seconds(health_path)
    public_state = payload.get("public") if isinstance(payload.get("public"), dict) else {}
    private_state = payload.get("private") if isinstance(payload.get("private"), dict) else {}
    last_message_received_at = public_state.get("last_message_received_at") or payload.get(
        "last_message_received_at"
    )
    last_message_age = None
    try:
        if last_message_received_at:
            last_message_age = max(0.0, time.time() - float(last_message_received_at))
    except (TypeError, ValueError):
        last_message_age = None

    connected = bool(payload.get("connected") or public_state.get("connected"))
    return {
        "path": health_path,
        "payload": payload,
        "health_age_sec": health_age,
        "last_message_age_sec": last_message_age,
        "connected": connected,
        "public_event": public_state.get("event"),
        "private_event": private_state.get("event"),
        "ok": health_age is not None and health_age <= max_log_age_sec and connected,
    }


def build_health_report(max_log_age_sec: int, mode: str = "warning") -> dict:
    results: dict[str, dict] = {}
    overall_ok = True
    warning_detected = False
    date_text = current_date_str()
    analysis_file = latest_dated_file(Path("analysis_logs"), "*.jsonl", date_text)
    structured_file = latest_dated_file(
        Path("structured_logs") / "live",
        "*/*.jsonl",
        date_text,
    )
    analysis_age = file_age_seconds(analysis_file)
    structured_age = file_age_seconds(structured_file)

    for name, script in PROGRAMS.items():
        pid = read_pid_file(name)
        alive = pid is not None and is_pid_alive(pid)
        log_path = latest_program_log(script, date_text)
        log_age = file_age_seconds(log_path)
        severity = "warning" if name in WARNING_PROGRAMS else "strict"
        if name == "collector":
            log_ok = analysis_age is not None and analysis_age <= max_log_age_sec
        elif name == "telegram":
            log_ok = True
        elif name == "upbit_stream":
            upbit_ws_health = build_upbit_stream_health(max_log_age_sec)
            log_ok = bool(upbit_ws_health["ok"])
        else:
            log_ok = log_age is not None and log_age <= max_log_age_sec
        healthy = alive and log_ok
        if healthy:
            status = "OK"
        elif severity == "warning" and mode == "warning":
            status = "WARN"
            warning_detected = True
        else:
            status = "FAIL"
            overall_ok = False
        results[name] = {
            "script": script,
            "pid": pid,
            "alive": alive,
            "latest_log": str(log_path) if log_path else None,
            "latest_log_age_sec": log_age,
            "severity": severity,
            "healthy": healthy,
            "status": status,
            "ok": healthy if severity == "strict" or mode == "strict" else status != "FAIL",
        }
        if name == "upbit_stream":
            results[name]["ws_health"] = {
                "path": str(upbit_ws_health["path"]),
                "health_age_sec": upbit_ws_health["health_age_sec"],
                "last_message_age_sec": upbit_ws_health["last_message_age_sec"],
                "connected": upbit_ws_health["connected"],
                "public_event": upbit_ws_health["public_event"],
                "private_event": upbit_ws_health["private_event"],
            }

    analysis_ok = (analysis_age or 10**9) <= max_log_age_sec
    structured_ok = (structured_age or 10**9) <= max_log_age_sec
    if not analysis_ok or not structured_ok:
        overall_ok = False

    overall_status = "OK"
    if not overall_ok:
        overall_status = "FAIL"
    elif warning_detected:
        overall_status = "WARN"

    return {
        "ok": overall_ok,
        "mode": mode,
        "warning": warning_detected,
        "status": overall_status,
        "max_log_age_sec": max_log_age_sec,
        "programs": results,
        "analysis_logs_latest": str(analysis_file) if analysis_file else None,
        "structured_logs_latest": str(structured_file) if structured_file else None,
        "analysis_logs_age_sec": analysis_age,
        "structured_logs_age_sec": structured_age,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="운영 헬스체크")
    parser.add_argument("--max-log-age-sec", type=int, default=1800)
    parser.add_argument("--mode", choices=("warning", "strict"), default="warning")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_health_report(args.max_log_age_sec, mode=args.mode)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("운영 헬스체크")
        print(f"- overall: {report['status']}")
        print(f"- mode: {report['mode']}")
        for name, item in report["programs"].items():
            print(
                f"- {name}: {item['status']} | "
                f"severity={item['severity']} | pid={item['pid']} | log_age={item['latest_log_age_sec']}"
            )
        print(f"- analysis_logs: {report['analysis_logs_latest']}")
        print(f"- structured_logs: {report['structured_logs_latest']}")
    return 0 if report["status"] in {"OK", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
