"""
수정 요약
- 루트 래퍼가 tools.log_archive_manager 를 중복 실행하지 않고 main 함수를 직접 호출하도록 정리
- 배치와 수동 실행 시 불필요한 RuntimeWarning 이 남지 않도록 보완
"""

from tools.log_archive_manager import *  # noqa: F401,F403
from tools.log_archive_manager import main as _main

if __name__ == "__main__":
    _main()
