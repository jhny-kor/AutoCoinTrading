"""
수정 요약
- 2026-04-08: 심볼별 현재 레짐을 JSON/Markdown/HTML 로 함께 생성하고 단계 순서와 의미를 공통 빌더로 제공하도록 확장
- 최신 분석 로그에서 관리 심볼별 마지막 레코드를 뽑아 텔레그램 /regime 과 웹 스냅샷이 같은 데이터 소스를 쓰도록 정리
"""

from __future__ import annotations

import argparse
import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from log_path_utils import iter_files
from market_regime_guard import (
    classify_symbol_regime,
    get_regime_stage_catalog,
    get_regime_stage_info,
)
from strategy_settings import load_managed_symbols


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_PATH = ROOT / "reports" / "current_regime_snapshot.json"
DEFAULT_MD_PATH = ROOT / "reports" / "current_regime_snapshot.md"
DEFAULT_HTML_PATH = ROOT / "reports" / "current_regime_snapshot.html"


def parse_local_timestamp(raw: str) -> datetime | None:
    """로컬 시각 문자열을 datetime 으로 안전하게 변환한다."""
    try:
        if not raw:
            return None
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is not None:
            return parsed.astimezone().replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def load_latest_market_records(
    *,
    analysis_log_dir: Path | None = None,
    managed_symbols: set[str] | None = None,
) -> list[dict[str, Any]]:
    """관리 심볼 기준 최신 분석 로그 1건씩을 읽는다."""
    log_dir = analysis_log_dir or (ROOT / "analysis_logs")
    symbols = managed_symbols or set(load_managed_symbols("okx") + load_managed_symbols("upbit"))
    latest_files_by_name: dict[str, Path] = {}
    for path in iter_files(log_dir, "*.jsonl"):
        current = latest_files_by_name.get(path.name)
        if current is None or path.stat().st_mtime > current.stat().st_mtime:
            latest_files_by_name[path.name] = path

    latest_by_key: dict[tuple[str, str], tuple[datetime, dict[str, Any]]] = {}
    for path in latest_files_by_name.values():
        last_line = ""
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped:
                    last_line = stripped
        except FileNotFoundError:
            continue
        if not last_line:
            continue
        try:
            record = json.loads(last_line)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue

        exchange = str(record.get("exchange", "")).strip().lower()
        symbol = str(record.get("symbol", "")).strip()
        parsed_ts = parse_local_timestamp(str(record.get("collected_at", "")))
        if not exchange or not symbol or symbol not in symbols or parsed_ts is None:
            continue
        key = (exchange, symbol)
        current = latest_by_key.get(key)
        if current is None or parsed_ts > current[0]:
            latest_by_key[key] = (parsed_ts, record)

    rows = [item[1] for item in latest_by_key.values()]
    rows.sort(
        key=lambda row: (
            0 if str(row.get("exchange", "")).upper() == "UPBIT" else 1,
            0 if str(row.get("symbol", "")).startswith("BTC/") else 1,
            str(row.get("symbol", "")),
        )
    )
    return rows


def build_regime_reason(snapshot, row: dict[str, Any]) -> str:
    """레짐 판정의 핵심 이유를 사용자용 한 줄로 만든다."""
    regime = snapshot.regime
    volume_ratio = snapshot.volume_ratio
    avg_abs_change_pct = snapshot.avg_abs_change_pct
    gap_pct = snapshot.gap_pct
    rsi = snapshot.rsi
    adx = snapshot.adx

    if regime == "LOW_ENERGY":
        return (
            f"거래량 {volume_ratio if volume_ratio is not None else '-'}배, "
            f"변화율 {avg_abs_change_pct if avg_abs_change_pct is not None else '-'}% 수준으로 약하고 "
            "공개 기준 매수 준비 신호가 없습니다."
        )
    if regime == "CHOPPY":
        return (
            f"ADX {adx if adx is not None else '-'} 기준으로 추세 강도가 낮거나 "
            "방향성 신호가 약해 혼조 구간으로 분류됩니다."
        )
    if regime == "BREAKOUT_ATTEMPT":
        return (
            f"이격도 {gap_pct if gap_pct is not None else '-'}%, 거래량 {volume_ratio if volume_ratio is not None else '-'}배로 "
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
            f"RSI {rsi if rsi is not None else '-'} 와 거래량 {volume_ratio if volume_ratio is not None else '-'}배가 과열 기준에 가깝습니다."
        )
    return "최신 분석 로그가 부족하거나 분류 근거가 아직 충분하지 않습니다."


def build_regime_rows(
    latest_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """심볼별 현재 레짐 요약 행을 만든다."""
    rows = latest_rows or load_latest_market_records()
    result: list[dict[str, Any]] = []
    for row in rows:
        exchange = str(row.get("exchange", "")).strip().upper()
        symbol = str(row.get("symbol", "")).strip()
        snapshot = classify_symbol_regime(row)
        stage_info = get_regime_stage_info(snapshot.regime)
        result.append(
            {
                "exchange": exchange,
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
                "public_buy_ready": snapshot.public_buy_ready,
                "bullish_signal": snapshot.bullish_signal,
                "bearish_signal": snapshot.bearish_signal,
                "above_ma": snapshot.above_ma,
                "htf_bullish": snapshot.htf_bullish,
                "recorded_at_local": snapshot.recorded_at_local,
            }
        )
    return result


def build_regime_snapshot_payload(
    latest_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """웹/텔레그램/파일 공통 레짐 스냅샷 payload 를 만든다."""
    rows = build_regime_rows(latest_rows)
    return {
        "generated_at": datetime.now().isoformat(),
        "stage_catalog": get_regime_stage_catalog(),
        "rows": rows,
    }


def render_regime_markdown(payload: dict[str, Any]) -> str:
    """레짐 스냅샷 Markdown 을 만든다."""
    lines = ["# 현재 레짐 스냅샷", ""]
    lines.append("## 레짐 단계")
    for item in payload.get("stage_catalog", []):
        lines.append(
            f"- {item['stage_index']}/{item['total_stages']} `{item['regime']}`: {item['meaning']}"
        )
    lines.append("")
    lines.append("## 심볼별 현재 상태")
    for row in payload.get("rows", []):
        stage_text = (
            f"{row['stage_index']}/{row['total_stages']}"
            if row.get("stage_index") is not None
            else f"?/{row.get('total_stages') or '-'}"
        )
        lines.append(
            f"- {row['exchange']} {row['symbol']} | {stage_text} `{row['regime']}` | "
            f"거래량 {row['volume_ratio'] if row['volume_ratio'] is not None else '-'}배 | "
            f"변화율 {row['avg_abs_change_pct'] if row['avg_abs_change_pct'] is not None else '-'}% | "
            f"이격도 {row['gap_pct'] if row['gap_pct'] is not None else '-'}% | "
            f"RSI {row['rsi'] if row['rsi'] is not None else '-'} | "
            f"ADX {row['adx'] if row['adx'] is not None else '-'}"
        )
        lines.append(f"  - 의미: {row['meaning']}")
        lines.append(f"  - 해석: {row['reason']}")
    return "\n".join(lines)


def render_regime_html(payload: dict[str, Any]) -> str:
    """브라우저에서 바로 열 수 있는 레짐 HTML 화면을 만든다."""
    stage_items = []
    for item in payload.get("stage_catalog", []):
        stage_items.append(
            "<li><strong>{}</strong> {}/{} - {}</li>".format(
                html.escape(str(item["regime"])),
                item["stage_index"],
                item["total_stages"],
                html.escape(str(item["meaning"])),
            )
        )
    row_html = []
    for row in payload.get("rows", []):
        stage_text = (
            f"{row['stage_index']}/{row['total_stages']}"
            if row.get("stage_index") is not None
            else f"?/{row.get('total_stages') or '-'}"
        )
        volume_text = "-" if row["volume_ratio"] is None else f"{float(row['volume_ratio']):.3f}"
        change_text = "-" if row["avg_abs_change_pct"] is None else f"{float(row['avg_abs_change_pct']):.4f}%"
        gap_text = "-" if row["gap_pct"] is None else f"{float(row['gap_pct']):.4f}%"
        rsi_text = "-" if row["rsi"] is None else f"{float(row['rsi']):.1f}"
        adx_text = "-" if row["adx"] is None else f"{float(row['adx']):.1f}"
        row_html.append(
            "<tr>"
            f"<td>{html.escape(str(row['exchange']))}</td>"
            f"<td>{html.escape(str(row['symbol']))}</td>"
            f"<td>{html.escape(stage_text)}</td>"
            f"<td><strong>{html.escape(str(row['regime']))}</strong></td>"
            f"<td>{html.escape(str(row['meaning']))}</td>"
            f"<td>{html.escape(str(row['reason']))}</td>"
            f"<td>{html.escape(volume_text)}</td>"
            f"<td>{html.escape(change_text)}</td>"
            f"<td>{html.escape(gap_text)}</td>"
            f"<td>{html.escape(rsi_text)}</td>"
            f"<td>{html.escape(adx_text)}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <title>현재 레짐 스냅샷</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 24px; color: #111827; }}
    h1, h2 {{ margin-bottom: 12px; }}
    .meta {{ color: #6b7280; margin-bottom: 20px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 10px; vertical-align: top; text-align: left; }}
    th {{ background: #f3f4f6; }}
    ul {{ padding-left: 20px; }}
  </style>
</head>
<body>
  <h1>현재 레짐 스냅샷</h1>
  <div class="meta">생성 시각: {html.escape(str(payload.get("generated_at", "-")))}</div>
  <h2>레짐 단계</h2>
  <ul>
    {''.join(stage_items)}
  </ul>
  <h2>심볼별 현재 상태</h2>
  <table>
    <thead>
      <tr>
        <th>거래소</th>
        <th>심볼</th>
        <th>단계</th>
        <th>현재 레짐</th>
        <th>의미</th>
        <th>현재 해석</th>
        <th>거래량 배수</th>
        <th>평균 변화율</th>
        <th>이격도</th>
        <th>RSI</th>
        <th>ADX</th>
      </tr>
    </thead>
    <tbody>
      {''.join(row_html)}
    </tbody>
  </table>
</body>
</html>
"""


def write_snapshot_outputs(
    payload: dict[str, Any],
    *,
    json_path: Path = DEFAULT_JSON_PATH,
    md_path: Path = DEFAULT_MD_PATH,
    html_path: Path = DEFAULT_HTML_PATH,
) -> None:
    """레짐 스냅샷을 파일로 저장한다."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_regime_markdown(payload), encoding="utf-8")
    html_path.write_text(render_regime_html(payload), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(description="현재 레짐 스냅샷 생성")
    parser.add_argument("--print-only", action="store_true", help="파일 저장 없이 JSON 만 출력")
    args = parser.parse_args(argv)

    payload = build_regime_snapshot_payload()
    if not args.print_only:
        write_snapshot_outputs(payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
