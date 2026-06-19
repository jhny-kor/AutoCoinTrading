"""OKX 웹소켓 시장데이터 수집기 실행 진입점 래퍼."""

from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    runpy.run_module("okx_market_data_stream", run_name="__main__")
