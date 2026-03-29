"""
수정 요약
- 현재 운영 심볼들의 최신 분석 로그를 읽어 심볼별 현재 레짐 스냅샷을 JSON 으로 출력하는 보조 유틸을 추가했다.
- 런타임 봇 로직과 분리된 점검용 스크립트라는 점이 바로 보이도록 파일 목적을 상단에 명시했다.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import analyze_logs
from market_regime_guard import classify_symbol_regime
from strategy_settings import load_managed_symbols


ROOT = Path(__file__).resolve().parent


def main() -> int:
    records = analyze_logs.load_records(ROOT / "analysis_logs")
    managed_symbols = set(load_managed_symbols("okx") + load_managed_symbols("upbit"))

    latest_by_key: dict[tuple[str, str], dict] = {}
    latest_ts_by_key: dict[tuple[str, str], datetime] = {}

    for record in records:
        exchange = str(record.get("exchange", "")).strip().lower()
        symbol = str(record.get("symbol", "")).strip()
        raw_ts = str(record.get("collected_at", "")).strip()
        if not exchange or not symbol or symbol not in managed_symbols or not raw_ts:
            continue

        try:
            parsed_ts = datetime.fromisoformat(raw_ts)
        except ValueError:
            continue

        key = (exchange, symbol)
        current_ts = latest_ts_by_key.get(key)
        if current_ts is None or parsed_ts > current_ts:
            latest_ts_by_key[key] = parsed_ts
            latest_by_key[key] = record

    rows = []
    for (exchange, symbol), row in latest_by_key.items():
        snapshot = classify_symbol_regime(row)
        rows.append(
            {
                "exchange": exchange.upper(),
                "symbol": symbol,
                "regime": snapshot.regime,
                "volume_ratio": snapshot.volume_ratio,
                "gap_pct": snapshot.gap_pct,
                "rsi": snapshot.rsi,
            }
        )

    rows.sort(
        key=lambda item: (
            0 if item["exchange"] == "UPBIT" else 1,
            0 if str(item["symbol"]).startswith("BTC/") else 1,
            str(item["symbol"]),
        )
    )
    print(json.dumps(rows, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
