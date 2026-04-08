"""
작업 요약
- 2026-04-08: 현재 레짐 스냅샷 루트 래퍼가 run_module 경고 없이 직접 main() 을 호출하도록 정리
"""

from reporting.current_regime_snapshot import *  # noqa: F401,F403

if __name__ == "__main__":
    from reporting.current_regime_snapshot import main

    raise SystemExit(main())
