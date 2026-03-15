"""
공통 로그 유틸

- 터미널에는 색상 로그를 보여주고
- 파일에는 ANSI 색상 코드를 제거한 로그를 저장한다.
- 프로그램별로 별도 로그 파일을 만들어 관리한다.
"""

import os
import re
from datetime import datetime


BOLD = "\033[1m"
RED = "\033[31m"
BLUE = "\033[34m"
RESET = "\033[0m"

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


class BotLogger:
    """터미널 출력과 파일 기록을 함께 처리하는 간단한 로거."""

    def __init__(self, program_name: str, log_dir: str = "logs"):
        self.program_name = program_name
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_path = os.path.join(self.log_dir, f"{self.program_name}.log")

    def _strip_ansi(self, text: str) -> str:
        return ANSI_ESCAPE_RE.sub("", text)

    def log(self, msg: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{now}] {msg}"
        print(line)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(self._strip_ansi(line) + "\n")

    def log_signal(self, symbol: str, bullish: bool, bearish: bool):
        if bullish:
            self.log(f"{BOLD}{RED}[{symbol}] 매수 신호 감지{RESET}")
        elif bearish:
            self.log(f"{BOLD}{BLUE}[{symbol}] 매도 신호 감지{RESET}")
        else:
            self.log(f"[{symbol}] 신호 없음")

    def log_trade_banner(self, color: str, title: str, detail: str):
        border = "=" * 72
        self.log(f"{BOLD}{color}{border}{RESET}")
        self.log(f"{BOLD}{color}{title}{RESET}")
        self.log(f"{BOLD}{color}{detail}{RESET}")
        self.log(f"{BOLD}{color}{border}{RESET}")
