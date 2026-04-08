"""
작업 요약
- 2026-04-08: 백테스트 삭제 도구를 루트에서도 기존 패턴대로 실행할 수 있게 호환 래퍼를 추가
"""

from tools.delete_backtest_entry import *  # noqa: F401,F403


if __name__ == "__main__":
    import runpy

    runpy.run_module("tools.delete_backtest_entry", run_name="__main__")
