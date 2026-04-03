"""
수정 요약
- 루트 래퍼가 reporting.telegram_notifier 를 중복 실행하지 않고 main 함수를 직접 호출하도록 정리했다.
- 텔레그램 수동 전송 CLI 가 루트 경로에서도 정상 동작하도록 보완했다.
"""

from reporting.telegram_notifier import *  # noqa: F401,F403
from reporting.telegram_notifier import main as _main

if __name__ == "__main__":
    raise SystemExit(_main())
