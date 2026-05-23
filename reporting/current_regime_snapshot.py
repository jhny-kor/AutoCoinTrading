"""
수정 요약
- 2026-05-24: 전체 분석 로그 대신 최신 심볼 레코드만 읽어 레짐 스냅샷을 빠르게 만들도록 정리했다.
- 2026-04-08: 단계 순서, 의미, 해석을 포함한 레짐 payload 를 출력하도록 확장해 웹/텔레그램이 같은 데이터를 재사용할 수 있게 정리
- 현재 운영 심볼들의 최신 분석 로그를 읽어 심볼별 현재 레짐 스냅샷을 JSON 으로 출력하는 보조 유틸을 추가했다.
- 런타임 봇 로직과 분리된 점검용 스크립트라는 점이 바로 보이도록 파일 목적을 상단에 명시했다.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import analyze_logs
from market_regime_guard import (
    classify_symbol_regime,
    get_regime_stage_catalog,
    get_regime_stage_info,
)
from strategy_settings import load_managed_symbols


ROOT = Path(__file__).resolve().parents[1]


def format_metric(value, digits: int = 4, suffix: str = "") -> str:
    if value in (None, ""):
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    text = f"{number:.{digits}f}".rstrip("0").rstrip(".")
    return f"{text}{suffix}"


def build_regime_reason(snapshot, row: dict) -> str:
    regime = snapshot.regime
    volume_ratio = format_metric(snapshot.volume_ratio, 4, "배")
    avg_abs_change_pct = format_metric(snapshot.avg_abs_change_pct, 4, "%")
    gap_pct = format_metric(snapshot.gap_pct, 4, "%")
    rsi = format_metric(snapshot.rsi, 4)
    adx = format_metric(snapshot.adx, 4)

    if regime == "LOW_ENERGY":
        return (
            f"거래량 {volume_ratio if volume_ratio is not None else '-'}, "
            f"변화율 {avg_abs_change_pct if avg_abs_change_pct is not None else '-'} 수준으로 약하고 "
            "공개 기준 매수 준비 신호가 없습니다."
        )
    if regime == "CHOPPY":
        return (
            f"ADX {adx if adx is not None else '-'} 기준으로 추세 강도가 낮거나 "
            "방향성 신호가 약해 혼조 구간으로 분류됩니다."
        )
    if regime == "BREAKOUT_ATTEMPT":
        return (
            f"이격도 {gap_pct if gap_pct is not None else '-'}, 거래량 {volume_ratio if volume_ratio is not None else '-'}로 "
            "돌파 시도가 관찰됩니다."
        )
    if regime == "TRENDING":
        return (
            f"상위 추세 동의와 ADX {adx if adx is not None else '-'} 수준의 추세 강도가 함께 확인됩니다."
        )
    if regime == "EXHAUSTION_RISK":
        return (
            f"RSI {rsi if rsi is not None else '-'} 로 많이 오른 뒤 힘이 빠질 위험이 커 보입니다."
        )
    if regime == "OVERHEATED":
        return (
            f"RSI {rsi if rsi is not None else '-'} 와 거래량 {volume_ratio if volume_ratio is not None else '-'}가 과열 기준에 가깝습니다."
        )
    return "최신 분석 로그가 부족하거나 분류 근거가 아직 충분하지 않습니다."


def main() -> int:
    managed_symbols = set(load_managed_symbols("okx") + load_managed_symbols("upbit"))
    records = analyze_logs.load_latest_records(
        ROOT / "analysis_logs",
        symbols=managed_symbols,
        max_date_dirs=3,
    )

    rows = []
    for row in records:
        exchange = str(row.get("exchange", "")).strip().lower()
        symbol = str(row.get("symbol", "")).strip()
        snapshot = classify_symbol_regime(row)
        stage_info = get_regime_stage_info(snapshot.regime)
        rows.append(
            {
                "exchange": exchange.upper(),
                "symbol": symbol,
                "regime": snapshot.regime,
                "stage_index": stage_info["stage_index"],
                "total_stages": stage_info["total_stages"],
                "meaning": stage_info["meaning"],
                "reason": build_regime_reason(snapshot, row),
                "volume_ratio": snapshot.volume_ratio,
                "avg_abs_change_pct": snapshot.avg_abs_change_pct,
                "gap_pct": snapshot.gap_pct,
                "rsi": snapshot.rsi,
                "adx": snapshot.adx,
                "recorded_at_local": snapshot.recorded_at_local,
            }
        )

    rows.sort(
        key=lambda item: (
            0 if item["exchange"] == "UPBIT" else 1,
            0 if str(item["symbol"]).startswith("BTC/") else 1,
            str(item["symbol"]),
        )
    )
    payload = {
        "generated_at": datetime.now().isoformat(),
        "stage_catalog": get_regime_stage_catalog(),
        "rows": rows,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
