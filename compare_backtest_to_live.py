"""
수정 요약
- 배치 백테스트 러너가 재사용할 수 있도록 비교 payload 생성 helper 를 추가
- 백테스트 결과 디렉토리와 실거래 trade_history 를 같은 기준으로 비교하는 스크립트를 추가
- 심볼, 프로그램, 날짜 범위 기준으로 실거래 체결을 필터링하고 승률/순손익/종료 사유를 함께 요약하도록 구성
- 비교 결과를 comparison.json 과 comparison.md 로 저장하도록 확장

백테스트 대 실거래 비교 도구

- backtest_replay.py 출력물과 trade_logs/trade_history.jsonl 을 함께 읽는다.
- 동일 심볼/프로그램 기준으로 체결 수, 승률, 평균 손익률, 종료 사유를 비교한다.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from analyze_strategy_logs import read_trade_history, read_jsonl


PROGRAM_NAME_BY_STRATEGY = {
    ("alt", "okx"): "ma_crossover_bot",
    ("alt", "upbit"): "upbit_ma_crossover_bot",
    ("btc", "okx"): "okx_btc_ema_trend_bot",
    ("btc", "upbit"): "upbit_btc_ema_trend_bot",
}


def _to_float(value: Any) -> float | None:
    """숫자 후보를 float 로 안전하게 바꾼다."""
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_iso_date(raw: str | None) -> date | None:
    """YYYY-MM-DD 문자열을 date 로 바꾼다."""
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d").date()


def extract_record_date(record: dict[str, Any]) -> date | None:
    """체결 레코드의 로컬 날짜를 추출한다."""
    for key in ("recorded_at_local", "recorded_at"):
        raw = record.get(key)
        if not raw:
            continue
        try:
            return datetime.fromisoformat(str(raw)).date()
        except ValueError:
            continue
    return None


def infer_program_name(strategy_type: str, exchange_name: str) -> str | None:
    """전략/거래소 조합으로 프로그램 이름을 추론한다."""
    return PROGRAM_NAME_BY_STRATEGY.get((strategy_type.lower(), exchange_name.lower()))


def summarize_sell_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """매도 체결 레코드 집합을 요약한다."""
    sell_records = [record for record in records if str(record.get("side", "")).lower() == "sell"]
    pnl_quotes = [
        value
        for value in (
            _to_float(record.get("net_realized_pnl_quote"))
            if _to_float(record.get("net_realized_pnl_quote")) is not None
            else _to_float(record.get("realized_pnl_quote"))
            for record in sell_records
        )
        if value is not None
    ]
    pnl_pcts = [
        value
        for value in (
            _to_float(record.get("net_realized_pnl_pct"))
            if _to_float(record.get("net_realized_pnl_pct")) is not None
            else _to_float(record.get("realized_pnl_pct"))
            for record in sell_records
        )
        if value is not None
    ]
    holding_seconds = [
        value
        for value in (_to_float(record.get("holding_seconds")) for record in sell_records)
        if value is not None
    ]
    wins = [value for value in pnl_quotes if value > 0]
    reason_counts = Counter(str(record.get("reason", "")) for record in sell_records)

    return {
        "trade_count": len(records),
        "sell_count": len(sell_records),
        "win_count": len(wins),
        "win_rate_pct": (len(wins) / len(sell_records) * 100) if sell_records else 0.0,
        "total_net_realized_pnl_quote": sum(pnl_quotes),
        "avg_net_realized_pnl_quote": (sum(pnl_quotes) / len(pnl_quotes)) if pnl_quotes else 0.0,
        "avg_net_realized_pnl_pct": (sum(pnl_pcts) / len(pnl_pcts)) if pnl_pcts else 0.0,
        "avg_holding_seconds": (sum(holding_seconds) / len(holding_seconds)) if holding_seconds else None,
        "top_exit_reasons": reason_counts.most_common(5),
    }


def generate_comments(backtest: dict[str, Any], live: dict[str, Any]) -> list[str]:
    """백테스트 대비 실거래 차이를 짧은 코멘트로 만든다."""
    comments: list[str] = []
    if backtest["sell_count"] > 0 and live["sell_count"] == 0:
        comments.append("실거래 비교 기간에 청산 표본이 없어 성과 비교보다 표본 확보가 우선입니다.")
    if live["sell_count"] > 0 and backtest["sell_count"] == 0:
        comments.append("백테스트는 거래가 없는데 실거래는 체결이 있어, 입력 데이터 주기나 설정값 불일치 여부를 먼저 확인하는 것이 좋습니다.")

    trade_count_gap = live["trade_count"] - backtest["trade_count"]
    if backtest["trade_count"] > 0 and live["trade_count"] < backtest["trade_count"] * 0.5:
        comments.append("실거래 체결 수가 백테스트보다 크게 적어, 보수적인 필터나 주문 최소금액 제약이 실제 환경에서 더 강하게 작동했을 가능성이 큽니다.")
    elif trade_count_gap > max(3, backtest["trade_count"] * 0.5):
        comments.append("실거래 체결 수가 백테스트보다 많아, 리플레이 가정이 일부 진입 차단 조건을 덜 보수적으로 보고 있을 수 있습니다.")

    win_rate_diff = live["win_rate_pct"] - backtest["win_rate_pct"]
    if win_rate_diff <= -10:
        comments.append("실거래 승률이 백테스트보다 10%p 이상 낮아, 체결 품질이나 장중 조건 변화가 백테스트보다 불리했을 가능성이 큽니다.")
    elif win_rate_diff >= 10:
        comments.append("실거래 승률이 백테스트보다 높아, 현재 리플레이가 일부 청산 가정을 더 보수적으로 보고 있을 수 있습니다.")

    avg_pnl_diff = live["avg_net_realized_pnl_pct"] - backtest["avg_net_realized_pnl_pct"]
    if avg_pnl_diff <= -0.20:
        comments.append("실거래 평균 순손익률이 더 낮아 수수료, 슬리피지, 부분청산 이후 재진입 흐름을 더 엄격히 반영할 필요가 있습니다.")
    elif avg_pnl_diff >= 0.20:
        comments.append("실거래 평균 순손익률이 더 높아 현재 리플레이의 익절/트레일링 가정이 다소 보수적일 수 있습니다.")

    backtest_top_reason = backtest["top_exit_reasons"][0][0] if backtest["top_exit_reasons"] else None
    live_top_reason = live["top_exit_reasons"][0][0] if live["top_exit_reasons"] else None
    if backtest_top_reason and live_top_reason and backtest_top_reason != live_top_reason:
        comments.append(
            f"대표 종료 사유가 백테스트 `{backtest_top_reason}` 와 실거래 `{live_top_reason}` 로 달라, 청산 조건 또는 체결 순서의 차이를 점검하는 것이 좋습니다."
        )

    if live["avg_holding_seconds"] and backtest["avg_holding_seconds"]:
        holding_diff = live["avg_holding_seconds"] - backtest["avg_holding_seconds"]
        if holding_diff > 1800:
            comments.append("실거래 보유 시간이 더 길어, 부분익절 이후 잔량 관리나 추세 종료 청산이 실제 환경에서 늦게 작동했을 수 있습니다.")
        elif holding_diff < -1800:
            comments.append("실거래 보유 시간이 더 짧아, 실제 시장에서는 손절 또는 조기 익절이 더 자주 발생했을 가능성이 큽니다.")

    if not comments:
        comments.append("백테스트와 실거래의 핵심 요약 값 차이가 크지 않아, 현재 비교 범위에서는 방향성이 대체로 비슷합니다.")
    return comments


def build_markdown_report(payload: dict[str, Any]) -> str:
    """비교 결과를 간단한 마크다운으로 만든다."""
    backtest = payload["backtest"]
    live = payload["live"]
    filters = payload["filters"]
    comments = payload.get("comments", [])

    def format_reasons(items: list[list[Any]] | list[tuple[Any, Any]]) -> str:
        if not items:
            return "-"
        return ", ".join(f"{reason}:{count}" for reason, count in items)

    lines = [
        "# 백테스트 vs 실거래 비교",
        "",
        f"- 심볼: `{filters['symbol']}`",
        f"- 프로그램: `{filters['program_name']}`",
        f"- 백테스트 디렉토리: `{filters['backtest_dir']}`",
        f"- 비교 기간 시작: `{filters['since'] or '-'}`",
        f"- 비교 기간 종료: `{filters['until'] or '-'}`",
        "",
        "## 백테스트",
        "",
        f"- 체결 수: `{backtest['trade_count']}`",
        f"- 매도 수: `{backtest['sell_count']}`",
        f"- 승률: `{backtest['win_rate_pct']:.2f}%`",
        f"- 총 순손익: `{backtest['total_net_realized_pnl_quote']:.4f}`",
        f"- 평균 순손익률: `{backtest['avg_net_realized_pnl_pct']:.4f}%`",
        f"- 대표 종료 사유: `{format_reasons(backtest['top_exit_reasons'])}`",
        "",
        "## 실거래",
        "",
        f"- 체결 수: `{live['trade_count']}`",
        f"- 매도 수: `{live['sell_count']}`",
        f"- 승률: `{live['win_rate_pct']:.2f}%`",
        f"- 총 순손익: `{live['total_net_realized_pnl_quote']:.4f}`",
        f"- 평균 순손익률: `{live['avg_net_realized_pnl_pct']:.4f}%`",
        f"- 대표 종료 사유: `{format_reasons(live['top_exit_reasons'])}`",
        "",
        "## 차이 요약",
        "",
        f"- 승률 차이: `{live['win_rate_pct'] - backtest['win_rate_pct']:.2f}%p`",
        f"- 평균 순손익률 차이: `{live['avg_net_realized_pnl_pct'] - backtest['avg_net_realized_pnl_pct']:.4f}%p`",
        f"- 총 순손익 차이: `{live['total_net_realized_pnl_quote'] - backtest['total_net_realized_pnl_quote']:.4f}`",
        "",
        "## 자동 코멘트",
        "",
    ]
    for comment in comments:
        lines.append(f"- {comment}")
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: Any) -> None:
    """JSON 파일을 저장한다."""
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_comparison_payload(
    *,
    backtest_dir: Path,
    program_name: str | None = None,
    exchange_name: str | None = None,
    symbol: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> dict[str, Any]:
    """백테스트 결과 디렉토리와 실거래 이력을 읽어 비교 payload 를 만든다."""
    summary_path = backtest_dir / "summary.json"
    trades_path = backtest_dir / "trades.jsonl"
    if not summary_path.exists() or not trades_path.exists():
        raise FileNotFoundError("백테스트 디렉토리에 summary.json 또는 trades.jsonl 이 없습니다.")

    backtest_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    backtest_trades = read_jsonl(trades_path)
    symbol = symbol or str(backtest_summary.get("symbol", ""))
    exchange_name = exchange_name or str(backtest_summary.get("exchange_name", ""))
    strategy_type = str(backtest_summary.get("strategy_type", ""))
    program_name = program_name or infer_program_name(strategy_type, exchange_name)
    if not program_name:
        raise ValueError("프로그램 이름을 추론하지 못했습니다. --program-name 을 직접 지정하세요.")

    since_date = parse_iso_date(since)
    until_date = parse_iso_date(until)
    live_records: list[dict[str, Any]] = []
    for record in read_trade_history():
        if program_name and str(record.get("program_name", "")) != program_name:
            continue
        if symbol and str(record.get("symbol", "")) != symbol:
            continue
        record_date = extract_record_date(record)
        if since_date is not None and record_date is not None and record_date < since_date:
            continue
        if until_date is not None and record_date is not None and record_date > until_date:
            continue
        live_records.append(record)

    payload = {
        "filters": {
            "symbol": symbol,
            "exchange_name": exchange_name,
            "strategy_type": strategy_type,
            "program_name": program_name,
            "since": since,
            "until": until,
            "backtest_dir": str(backtest_dir),
        },
        "backtest": summarize_sell_records(backtest_trades),
        "live": summarize_sell_records(live_records),
    }
    payload["comments"] = generate_comments(payload["backtest"], payload["live"])
    return payload


def save_comparison_payload(backtest_dir: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    """비교 payload 를 comparison.json/md 로 저장한다."""
    comparison_json_path = backtest_dir / "comparison.json"
    comparison_md_path = backtest_dir / "comparison.md"
    write_json(comparison_json_path, payload)
    comparison_md_path.write_text(build_markdown_report(payload), encoding="utf-8")
    return comparison_json_path, comparison_md_path


def run_comparison(args: argparse.Namespace) -> int:
    """비교를 실행하고 결과 파일을 저장한다."""
    backtest_dir = Path(args.backtest_dir)
    payload = build_comparison_payload(
        backtest_dir=backtest_dir,
        program_name=args.program_name,
        exchange_name=args.exchange,
        symbol=args.symbol,
        since=args.since,
        until=args.until,
    )
    comparison_json_path, comparison_md_path = save_comparison_payload(backtest_dir, payload)
    print(f"비교 완료: {comparison_json_path}")
    print(f"마크다운 저장: {comparison_md_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 만든다."""
    parser = argparse.ArgumentParser(description="백테스트와 실거래 체결 비교 도구")
    parser.add_argument("--backtest-dir", required=True, help="summary.json 이 있는 백테스트 결과 디렉토리")
    parser.add_argument("--program-name", help="실거래 프로그램 이름")
    parser.add_argument("--exchange", choices=["okx", "upbit"], help="실거래 거래소")
    parser.add_argument("--symbol", help="심볼")
    parser.add_argument("--since", help="시작 날짜 YYYY-MM-DD")
    parser.add_argument("--until", help="종료 날짜 YYYY-MM-DD")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_comparison(args)


if __name__ == "__main__":
    raise SystemExit(main())
