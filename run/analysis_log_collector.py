"""분석 로그 수집기 실행 진입점 래퍼."""

from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    runpy.run_module("analysis_log_collector", run_name="__main__")
