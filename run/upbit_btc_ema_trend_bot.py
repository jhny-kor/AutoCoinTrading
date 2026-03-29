"""업비트 BTC 봇 실행 진입점 래퍼."""

from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    runpy.run_module("upbit_btc_ema_trend_bot", run_name="__main__")
