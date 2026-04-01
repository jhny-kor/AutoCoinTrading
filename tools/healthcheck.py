"""
작업 요약
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


def file_age_seconds(path: Path | None) -> float | None:
    if path is None or not path.exists():
        return None
    return max(0.0, time.time() - path.stat().st_mtime)


def latest_program_log(script: str) -> Path | None:
    return latest_file(Path("logs") / current_date_str(), f"{Path(script).stem}.log")


def build_health_report(max_log_age_sec: int) -> dict:
    results: dict[str, dict] = {}
    overall_ok = True
    analysis_file = latest_file(Path("analysis_logs") / current_date_str(), "*.jsonl")
    structured_file = latest_file(Path("structured_logs") / "live" / current_date_str(), "*.jsonl")
    analysis_age = file_age_seconds(analysis_file)
    structured_age = file_age_seconds(structured_file)

    for name, script in PROGRAMS.items():
        pid = read_pid_file(name)
        alive = pid is not None and is_pid_alive(pid)
        log_path = latest_program_log(script)
        log_age = file_age_seconds(log_path)
        if name == "collector":
            log_ok = analysis_age is not None and analysis_age <= max_log_age_sec
        elif name == "telegram":
            log_ok = True
        else:
            log_ok = log_age is not None and log_age <= max_log_age_sec
        ok = alive and log_ok
        overall_ok = overall_ok and ok
        results[name] = {
            "script": script,
            "pid": pid,
            "alive": alive,
            "latest_log": str(log_path) if log_path else None,
            "latest_log_age_sec": log_age,
            "ok": ok,
        }

    analysis_ok = (analysis_age or 10**9) <= max_log_age_sec
    structured_ok = (structured_age or 10**9) <= max_log_age_sec
    overall_ok = overall_ok and analysis_ok and structured_ok

    return {
        "ok": overall_ok,
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
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_health_report(args.max_log_age_sec)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("운영 헬스체크")
        print(f"- overall: {'OK' if report['ok'] else 'FAIL'}")
        for name, item in report["programs"].items():
            print(
                f"- {name}: {'OK' if item['ok'] else 'FAIL'} | "
                f"pid={item['pid']} | log_age={item['latest_log_age_sec']}"
            )
        print(f"- analysis_logs: {report['analysis_logs_latest']}")
        print(f"- structured_logs: {report['structured_logs_latest']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
