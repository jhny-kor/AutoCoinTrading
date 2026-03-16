"""
봇 프로세스 관리 도구

- 현재 실행 중인 봇 프로세스와 분석 수집기 상태를 확인한다.
- 개별 봇 시작, 전체 시작, 전체 중지, 강제 종료를 지원한다.
- 개별 봇 중지와 텔레그램 리스너 개별 중지를 지원한다.
- 중복 실행을 피하기 위해 이미 실행 중인 프로그램은 다시 시작하지 않는다.
- 텔레그램 명령 리스너까지 함께 관리한다.
- 상태 출력 문자열을 콘솔과 텔레그램에서 함께 재사용할 수 있도록 정리했다.
- start all 이 현재 매일 실행해야 하는 봇 4개와 수집기, 텔레그램 리스너를 모두 시작하도록 정리했다.
- 상태 출력에서는 명령어 전체 문자열을 제외해 핵심 정보만 보이도록 정리했다.

가능한 모든 터미널 명령
- .venv/bin/python bot_manager.py status
- .venv/bin/python bot_manager.py start all
- .venv/bin/python bot_manager.py start okx
- .venv/bin/python bot_manager.py start upbit
- .venv/bin/python bot_manager.py start okx_btc
- .venv/bin/python bot_manager.py start upbit_btc
- .venv/bin/python bot_manager.py start collector
- .venv/bin/python bot_manager.py start telegram
- .venv/bin/python bot_manager.py stop
- .venv/bin/python bot_manager.py stop all
- .venv/bin/python bot_manager.py stop okx
- .venv/bin/python bot_manager.py stop upbit
- .venv/bin/python bot_manager.py stop okx_btc
- .venv/bin/python bot_manager.py stop upbit_btc
- .venv/bin/python bot_manager.py stop collector
- .venv/bin/python bot_manager.py stop telegram
- .venv/bin/python bot_manager.py stop --force
- .venv/bin/python bot_manager.py stop all --force
- .venv/bin/python bot_manager.py stop okx --force
- .venv/bin/python bot_manager.py stop upbit --force
- .venv/bin/python bot_manager.py stop okx_btc --force
- .venv/bin/python bot_manager.py stop upbit_btc --force
- .venv/bin/python bot_manager.py stop collector --force
- .venv/bin/python bot_manager.py stop telegram --force
"""

from __future__ import annotations

import argparse
import os
import shlex
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from log_path_utils import dated_path

PROGRAMS = {
    "okx": "ma_crossover_bot.py",
    "upbit": "upbit_ma_crossover_bot.py",
    "okx_btc": "okx_btc_ema_trend_bot.py",
    "upbit_btc": "upbit_btc_ema_trend_bot.py",
    "collector": "analysis_log_collector.py",
    "telegram": "telegram_command_listener.py",
}

SECTION_TITLES = {
    "okx": "OKX 봇",
    "upbit": "업비트 봇",
    "okx_btc": "OKX BTC EMA 봇",
    "upbit_btc": "업비트 BTC EMA 봇",
    "collector": "분석 수집기",
    "telegram": "텔레그램 명령 리스너",
}

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"


@dataclass
class ManagedProcess:
    """실행 중인 관리 대상 프로세스 정보."""

    name: str
    script: str
    pid: int
    ppid: int
    elapsed: str
    command: str


def command_matches_script(command: str, script: str) -> bool:
    """명령어 문자열 안에 대상 스크립트가 정확히 포함되어 있는지 확인한다."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()

    for token in tokens:
        if Path(token).name == script:
            return True
    return False


def color_text(text: str, color: str, bold: bool = False) -> str:
    """ANSI 색상과 굵기를 적용한다."""
    prefix = color
    if bold:
        prefix = BOLD + color
    return f"{prefix}{text}{RESET}"


def list_managed_processes(exclude_current: bool = True) -> list[ManagedProcess]:
    """현재 실행 중인 관리 대상 프로세스를 조회한다."""
    result = subprocess.run(
        ["ps", "-Ao", "pid=,ppid=,etime=,command="],
        capture_output=True,
        text=True,
        check=True,
    )

    current_pid = os.getpid()
    processes: list[ManagedProcess] = []

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split(None, 3)
        if len(parts) != 4:
            continue

        pid_text, ppid_text, elapsed, command = parts
        pid = int(pid_text)
        if exclude_current and pid == current_pid:
            continue

        for name, script in PROGRAMS.items():
            if command_matches_script(command, script):
                processes.append(
                    ManagedProcess(
                        name=name,
                        script=script,
                        pid=pid,
                        ppid=int(ppid_text),
                        elapsed=elapsed,
                        command=command,
                    )
                )
                break

    return processes


def build_status_lines(
    use_color: bool = True, exclude_current: bool = True
) -> list[str]:
    """관리 대상 프로그램 상태를 문자열 목록으로 만든다."""
    processes = list_managed_processes(exclude_current=exclude_current)
    lines: list[str] = []

    header = "관리 대상 프로그램 상태"
    separator = "=" * 50
    if use_color:
        lines.append(color_text(header, CYAN, bold=True))
        lines.append(color_text(separator, CYAN))
    else:
        lines.append(header)
        lines.append(separator)

    for name, script in PROGRAMS.items():
        matched = [proc for proc in processes if proc.name == name]
        section_title = SECTION_TITLES.get(name, name)

        lines.append("")
        if use_color:
            lines.append(color_text(f"[{section_title}]", BLUE, bold=True))
        else:
            lines.append(f"[{section_title}]")

        if not matched:
            status_text = (
                color_text("중지됨", RED, bold=True) if use_color else "중지됨"
            )
            lines.append(f"  상태: {status_text}  스크립트: {script}")
            continue

        running_text = (
            color_text(f"실행 중 {len(matched)}개", GREEN, bold=True)
            if use_color
            else f"실행 중 {len(matched)}개"
        )
        lines.append(f"  상태: {running_text}  스크립트: {script}")
        for proc in matched:
            lines.append(
                f"  - PID {proc.pid} | PPID {proc.ppid} | 실행시간 {proc.elapsed}"
            )

    return lines


def build_status_text(use_color: bool = True, exclude_current: bool = True) -> str:
    """관리 대상 프로그램 상태를 하나의 문자열로 반환한다."""
    return "\n".join(
        build_status_lines(use_color=use_color, exclude_current=exclude_current)
    )


def get_processes_by_name(name: str) -> list[ManagedProcess]:
    """특정 이름의 실행 중 프로세스를 반환한다."""
    return [proc for proc in list_managed_processes() if proc.name == name]


def print_status():
    """관리 대상 프로그램 상태를 출력한다."""
    print(build_status_text(use_color=True))


def stop_processes(processes: list[ManagedProcess], force: bool = False) -> int:
    """대상 프로세스를 종료한다."""
    if not processes:
        print("중지할 프로세스가 없습니다.")
        return 0

    signal_type = signal.SIGKILL if force else signal.SIGTERM
    signal_name = "SIGKILL" if force else "SIGTERM"
    print(f"{len(processes)}개 프로세스에 {signal_name} 신호를 보냅니다.")

    for proc in processes:
        try:
            os.kill(proc.pid, signal_type)
            print(f"- {proc.name} PID {proc.pid} 종료 신호 전송 완료")
        except ProcessLookupError:
            print(f"- {proc.name} PID {proc.pid} 는 이미 종료되어 있습니다.")
        except PermissionError:
            print(f"- {proc.name} PID {proc.pid} 종료 권한이 없습니다.")

    return 0


def wait_for_exit(timeout_sec: float = 3.0) -> list[ManagedProcess]:
    """잠시 대기 후 남아 있는 프로세스를 다시 확인한다."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        remaining = list_managed_processes()
        if not remaining:
            return []
        time.sleep(0.3)
    return list_managed_processes()


def start_program(name: str) -> int:
    """특정 프로그램을 백그라운드로 시작한다."""
    if name not in PROGRAMS:
        print(f"알 수 없는 프로그램 이름입니다: {name}")
        return 1

    existing = get_processes_by_name(name)
    if existing:
        print(f"{name} 는 이미 실행 중입니다.")
        for proc in existing:
            print(f"- PID {proc.pid} / {proc.command}")
        return 0

    script = PROGRAMS[name]
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    launcher_log = dated_path("logs", f"{Path(script).stem}.launcher.log")
    launcher_log.parent.mkdir(parents=True, exist_ok=True)

    with launcher_log.open("a", encoding="utf-8") as f:
        process = subprocess.Popen(
            [sys.executable, script],
            cwd=os.getcwd(),
            stdout=subprocess.DEVNULL,
            stderr=f,
            start_new_session=True,
        )

    print(f"{name} 시작 요청 완료 (PID {process.pid})")
    return 0


def handle_start(target: str) -> int:
    """시작 명령 처리."""
    if target == "all":
        codes = [
            start_program(name)
            for name in (
                "collector",
                "telegram",
                "okx",
                "upbit",
                "okx_btc",
                "upbit_btc",
            )
        ]
        return 0 if all(code == 0 for code in codes) else 1
    return start_program(target)


def handle_status() -> int:
    """상태 확인 명령 처리."""
    print_status()
    return 0


def handle_stop(target: str = "all", force: bool = False) -> int:
    """중지 명령 처리."""
    if target == "all":
        processes = list_managed_processes()
    else:
        processes = get_processes_by_name(target)

    print_status()
    stop_processes(processes, force=force)

    if not force and processes:
        remaining = wait_for_exit()
        if target != "all":
            remaining = [proc for proc in remaining if proc.name == target]
        if remaining:
            print()
            print("일부 프로세스가 아직 남아 있습니다. 필요하면 --force 옵션을 사용하세요.")
            print_status()
            return 1

    remaining = list_managed_processes()
    if target != "all":
        remaining = [proc for proc in remaining if proc.name == target]
    print()
    if remaining:
        print("아직 실행 중인 관리 대상 프로세스가 남아 있습니다.")
        print_status()
        return 1

    if target == "all":
        print("모든 관리 대상 프로세스가 중지되었습니다.")
    else:
        print(f"{target} 관리 대상 프로세스가 중지되었습니다.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """명령행 인자 파서를 생성한다."""
    parser = argparse.ArgumentParser(description="자동매매 봇 프로세스 관리 도구")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "status",
        help="현재 실행 중인 봇과 분석 수집기 상태를 확인합니다.",
    )

    start_parser = subparsers.add_parser("start", help="봇 또는 분석 수집기를 시작합니다.")
    start_parser.add_argument(
        "target",
        choices=["all", "okx", "upbit", "okx_btc", "upbit_btc", "collector", "telegram"],
        help="시작할 대상",
    )

    stop_parser = subparsers.add_parser(
        "stop",
        help="실행 중인 봇과 분석 수집기를 모두 중지합니다.",
    )
    stop_parser.add_argument(
        "target",
        nargs="?",
        default="all",
        choices=["all", "okx", "upbit", "okx_btc", "upbit_btc", "collector", "telegram"],
        help="중지할 대상 (기본값: all)",
    )
    stop_parser.add_argument(
        "--force",
        action="store_true",
        help="일반 종료가 안 되면 강제 종료(SIGKILL)합니다.",
    )

    return parser


def main() -> int:
    """프로그램 진입점."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "status":
        return handle_status()
    if args.command == "start":
        return handle_start(args.target)
    if args.command == "stop":
        return handle_stop(target=args.target, force=args.force)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
