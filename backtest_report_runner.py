"""
수정 요약
- snapshot 도 기간에 맞춰 fetch 범위를 자동 확장할 수 있도록 보강해 기준선 스냅샷과 주간 배치의 비교 조건을 맞추도록 개선
- weekly 기본 fetch 범위를 타임프레임과 일수에 맞춰 자동 확장하고, 배치 요약에 실제 데이터 커버 구간과 표본 부족 상태 플래그를 함께 남기도록 보강
- 관리 심볼 기준 주간 배치 백테스트와 설정 변경 전후 비교를 한 번에 돌리는 러너를 추가
- fetch -> run -> compare 흐름을 심볼별로 묶고 배치 요약 Markdown/JSON 을 생성하도록 구성
- weekly, snapshot, diff 서브커맨드로 운영 루틴과 전후 비교 루틴을 분리해 실행할 수 있도록 확장

배치 백테스트 리포트 러너

- weekly: 관리 심볼 전체를 기준으로 최근 구간 백테스트와 실거래 비교를 배치 실행한다.
- snapshot: 임의 라벨로 배치 실행해 설정 변경 전/후 결과를 저장한다.
- diff: 두 배치 디렉토리를 비교해 변화 요약을 만든다.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from analysis_log_collector import create_okx_public_client, create_upbit_public_client
from backtest_replay import (
    build_output_dir,
    load_candles,
    parse_timeframe_to_minutes,
    resolve_default_fee_rate,
    resolve_default_max_daily_loss,
    resolve_default_min_buy_order_value,
    save_fetch_output,
    simulate_alt_strategy,
    simulate_btc_strategy,
    write_json,
    write_jsonl,
)
from compare_backtest_to_live import build_comparison_payload, save_comparison_payload
from strategy_settings import load_managed_symbols


DEFAULT_WEEKLY_DAYS = 7
DEFAULT_FETCH_LIMIT = 3000
DEFAULT_WEEKLY_BUFFER_MULTIPLIER = 1.2


def infer_strategy_type(symbol: str) -> str:
    """심볼 기준으로 사용할 전략 타입을 추론한다."""
    base = symbol.split("/", 1)[0] if "/" in symbol else symbol
    return "btc" if base == "BTC" else "alt"


def infer_initial_cash(symbol: str) -> float:
    """심볼 호가 통화 기준 기본 시작 자금을 고른다."""
    quote = symbol.split("/", 1)[1] if "/" in symbol else ""
    return 1_000_000.0 if quote == "KRW" else 1_000.0


def sanitize_symbol(symbol: str) -> str:
    """심볼을 파일명용 문자열로 바꾼다."""
    return symbol.replace("/", "_").replace("-", "_")


def fetch_symbol_ohlcv(
    *,
    exchange_name: str,
    symbol: str,
    timeframe: str,
    limit: int,
) -> list[list[float]]:
    """공개 거래소에서 심볼별 OHLCV 를 가져온다."""
    if exchange_name.lower() == "okx":
        return fetch_okx_ohlcv_paginated(symbol=symbol, timeframe=timeframe, limit=limit)
    return fetch_upbit_ohlcv_paginated(symbol=symbol, timeframe=timeframe, limit=limit)


def fetch_okx_ohlcv_paginated(*, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
    """OKX 공개 캔들을 여러 번 호출해 필요한 개수까지 모은다."""
    exchange = create_okx_public_client()
    inst_id = symbol.replace("/", "-")
    timeframe_map = {
        "1m": "1m",
        "3m": "3m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1H",
        "4h": "4H",
        "1d": "1D",
    }
    bar = timeframe_map.get(timeframe, timeframe)
    batch_limit = min(300, max(1, limit))
    rows_by_ts: dict[int, list[float]] = {}
    cursor_after: int | None = None

    while len(rows_by_ts) < limit:
        request = {
            "instId": inst_id,
            "bar": bar,
            "limit": min(batch_limit, limit - len(rows_by_ts)),
        }
        if cursor_after is not None:
            request["after"] = cursor_after
        response = exchange.publicGetMarketHistoryCandles(request)
        data = response.get("data", []) if isinstance(response, dict) else response
        if not data:
            break

        parsed_batch: list[list[float]] = []
        for item in data:
            parsed_batch.append(
                [
                    int(item[0]),
                    float(item[1]),
                    float(item[2]),
                    float(item[3]),
                    float(item[4]),
                    float(item[5]),
                ]
            )
        parsed_batch.sort(key=lambda row: row[0])
        for row in parsed_batch:
            rows_by_ts[row[0]] = row

        oldest_ts = parsed_batch[0][0]
        next_cursor = oldest_ts - 1
        if cursor_after is not None and next_cursor >= cursor_after:
            break
        if len(parsed_batch) < request["limit"]:
            break
        cursor_after = next_cursor

    return [rows_by_ts[ts] for ts in sorted(rows_by_ts)[-limit:]]


def fetch_upbit_ohlcv_paginated(*, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
    """업비트 공개 캔들을 여러 번 호출해 필요한 개수까지 모은다."""
    exchange = create_upbit_public_client()
    batch_limit = min(200, max(1, limit))
    rows_by_ts: dict[int, list[float]] = {}
    to_ts: int | None = None

    while len(rows_by_ts) < limit:
        params: dict[str, Any] = {}
        if to_ts is not None:
            params["to"] = exchange.iso8601(to_ts)
        batch = exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            limit=min(batch_limit, limit - len(rows_by_ts)),
            params=params,
        )
        if not batch:
            break

        batch.sort(key=lambda row: row[0])
        for row in batch:
            rows_by_ts[int(row[0])] = row

        oldest_ts = int(batch[0][0])
        next_to_ts = oldest_ts - 1
        if to_ts is not None and next_to_ts >= to_ts:
            break
        if len(batch) < min(batch_limit, limit - (len(rows_by_ts) - len(batch))):
            break
        to_ts = next_to_ts

    return [rows_by_ts[ts] for ts in sorted(rows_by_ts)[-limit:]]


def calculate_required_fetch_limit(
    *,
    timeframe: str,
    days: int,
    buffer_multiplier: float = DEFAULT_WEEKLY_BUFFER_MULTIPLIER,
) -> int:
    """지정 일수를 커버하기 위한 대략적인 fetch limit 을 계산한다."""
    timeframe_minutes = parse_timeframe_to_minutes(timeframe)
    candles_per_day = max(1, int((24 * 60) / timeframe_minutes))
    raw_limit = candles_per_day * max(1, days)
    return max(200, math.ceil(raw_limit * max(buffer_multiplier, 1.0)))


def resolve_targets(args: argparse.Namespace) -> list[tuple[str, str]]:
    """실행 대상 거래소/심볼 목록을 만든다."""
    targets: list[tuple[str, str]] = []
    requested_symbols = {symbol.strip() for symbol in (args.symbols or "").split(",") if symbol.strip()}
    requested_exchanges = {exchange.strip().lower() for exchange in (args.exchanges or "okx,upbit").split(",") if exchange.strip()}

    if "okx" in requested_exchanges:
        for symbol in load_managed_symbols("okx"):
            if requested_symbols and symbol not in requested_symbols:
                continue
            targets.append(("okx", symbol))
    if "upbit" in requested_exchanges:
        for symbol in load_managed_symbols("upbit"):
            if requested_symbols and symbol not in requested_symbols:
                continue
            targets.append(("upbit", symbol))
    return targets


def build_batch_root(base_dir: Path, label: str) -> Path:
    """배치 실행 결과 루트 디렉토리를 만든다."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    root = base_dir / f"{timestamp}__{label}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def run_single_backtest(
    *,
    batch_root: Path,
    exchange_name: str,
    symbol: str,
    timeframe: str,
    limit: int,
    since: str | None,
    until: str | None,
    risk_per_trade: float,
) -> dict[str, Any]:
    """심볼 1개 기준 fetch -> run -> compare 를 수행한다."""
    strategy_type = infer_strategy_type(symbol)
    data_dir = batch_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_path = data_dir / f"{exchange_name}__{sanitize_symbol(symbol)}__{timeframe}.jsonl"
    rows = fetch_symbol_ohlcv(
        exchange_name=exchange_name,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
    )
    save_fetch_output(data_path, rows)

    candles = load_candles(data_path)
    data_start = None
    data_end = None
    covered_days = 0.0
    if rows:
        data_start = datetime.fromtimestamp(rows[0][0] / 1000).astimezone().isoformat()
        data_end = datetime.fromtimestamp(rows[-1][0] / 1000).astimezone().isoformat()
        covered_days = max(0.0, (rows[-1][0] - rows[0][0]) / 1000 / 60 / 60 / 24)
    initial_cash = infer_initial_cash(symbol)
    fee_rate_pct = resolve_default_fee_rate(exchange_name)
    min_buy_order_value = resolve_default_min_buy_order_value(exchange_name)
    max_daily_loss_quote = resolve_default_max_daily_loss(exchange_name)
    if strategy_type == "alt":
        summary, trades, equity_curve = simulate_alt_strategy(
            candles=candles,
            source_timeframe=timeframe,
            symbol=symbol,
            exchange_name=exchange_name,
            initial_cash=initial_cash,
            fee_rate_pct=fee_rate_pct,
            risk_per_trade=risk_per_trade,
            min_buy_order_value=min_buy_order_value,
            max_daily_loss_quote=max_daily_loss_quote,
        )
    else:
        summary, trades, equity_curve = simulate_btc_strategy(
            candles=candles,
            source_timeframe=timeframe,
            symbol=symbol,
            exchange_name=exchange_name,
            initial_cash=initial_cash,
            fee_rate_pct=fee_rate_pct,
            risk_per_trade=risk_per_trade,
            min_buy_order_value=min_buy_order_value,
            max_daily_loss_quote=max_daily_loss_quote,
        )

    result_dir = batch_root / "results" / f"{strategy_type}__{exchange_name}__{sanitize_symbol(symbol)}"
    result_dir.mkdir(parents=True, exist_ok=True)
    write_json(result_dir / "summary.json", summary)
    write_jsonl(result_dir / "trades.jsonl", trades)
    write_jsonl(result_dir / "equity_curve.jsonl", equity_curve)

    comparison_payload = build_comparison_payload(
        backtest_dir=result_dir,
        exchange_name=exchange_name,
        symbol=symbol,
        since=since,
        until=until,
    )
    save_comparison_payload(result_dir, comparison_payload)
    flags: list[str] = []
    expected_days = 0.0
    if since and until:
        try:
            since_date = datetime.strptime(since, "%Y-%m-%d").date()
            until_date = datetime.strptime(until, "%Y-%m-%d").date()
            expected_days = max(0.0, float((until_date - since_date).days))
        except ValueError:
            expected_days = 0.0
    backtest_sell_count = int(summary.get("sell_count", 0) or 0)
    live_sell_count = int(comparison_payload.get("live", {}).get("sell_count", 0) or 0)
    if expected_days > 0 and covered_days < expected_days * 0.9:
        flags.append("data_window_short_for_period")
    if backtest_sell_count == 0:
        flags.append("no_backtest_trades")
    if 0 < backtest_sell_count < 3:
        flags.append("backtest_sample_too_small")
    if backtest_sell_count == 0 and live_sell_count > 0:
        flags.append("live_exists_without_backtest")
    return {
        "exchange_name": exchange_name,
        "symbol": symbol,
        "strategy_type": strategy_type,
        "result_dir": str(result_dir),
        "data_candle_count": len(rows),
        "data_start": data_start,
        "data_end": data_end,
        "covered_days": covered_days,
        "expected_days": expected_days,
        "flags": flags,
        "summary": summary,
        "comparison": comparison_payload,
    }


def build_batch_markdown(
    *,
    label: str,
    timeframe: str,
    limit: int,
    since: str | None,
    until: str | None,
    rows: list[dict[str, Any]],
) -> str:
    """배치 실행 결과 Markdown 요약을 만든다."""
    lines = [
        f"# {label} 백테스트 배치 요약",
        "",
        f"- 생성 시각: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        f"- 타임프레임: `{timeframe}`",
        f"- fetch limit: `{limit}`",
        f"- 실거래 비교 시작: `{since or '-'}`",
        f"- 실거래 비교 종료: `{until or '-'}`",
        "",
    ]
    for row in rows:
        summary = row["summary"]
        comparison = row["comparison"]
        comments = comparison.get("comments", []) if isinstance(comparison.get("comments"), list) else []
        live = comparison.get("live", {}) if isinstance(comparison.get("live"), dict) else {}
        lines.extend(
            [
                f"## {row['exchange_name'].upper()} {row['symbol']} ({row['strategy_type']})",
                "",
                f"- 결과 디렉토리: `{row['result_dir']}`",
                f"- 데이터 캔들 수: `{row['data_candle_count']}`",
                f"- 데이터 구간: `{row['data_start'] or '-'}` -> `{row['data_end'] or '-'}`",
                f"- 데이터 커버: `{row['covered_days']:.2f}일` (목표 `{row['expected_days']:.2f}일`)",
                f"- 백테스트 수익률: `{float(summary.get('net_return_pct', 0.0) or 0.0):.2f}%`",
                f"- 백테스트 거래 수: `{summary.get('trade_count', 0)}`",
                f"- 백테스트 최대 낙폭: `{float(summary.get('max_drawdown_pct', 0.0) or 0.0):.2f}%`",
                f"- 실거래 매도 수: `{live.get('sell_count', 0)}`",
                f"- 상태 플래그: `{', '.join(row['flags']) if row['flags'] else '-'}`",
                f"- 비교 코멘트: `{' / '.join(str(comment) for comment in comments[:3]) if comments else '-'}`",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def collect_result_summaries(root: Path) -> dict[str, dict[str, Any]]:
    """배치 결과 디렉토리에서 심볼별 요약을 모은다."""
    summaries: dict[str, dict[str, Any]] = {}
    for summary_path in root.glob("results/*/summary.json"):
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        key = f"{payload.get('exchange_name', '')}::{payload.get('symbol', '')}"
        summaries[key] = payload
    return summaries


def run_batch(args: argparse.Namespace, *, label: str, since: str | None, until: str | None) -> int:
    """배치 실행 공통 본문."""
    targets = resolve_targets(args)
    if not targets:
        raise ValueError("실행 대상 심볼이 없습니다.")
    batch_root = build_batch_root(Path(args.output_dir), label)
    effective_limit = args.limit
    if getattr(args, "auto_limit", False):
        if since and until:
            try:
                since_date = datetime.strptime(since, "%Y-%m-%d").date()
                until_date = datetime.strptime(until, "%Y-%m-%d").date()
                days_for_limit = max(1, (until_date - since_date).days)
            except ValueError:
                days_for_limit = int(getattr(args, "days", DEFAULT_WEEKLY_DAYS) or DEFAULT_WEEKLY_DAYS)
        else:
            days_for_limit = int(getattr(args, "days", DEFAULT_WEEKLY_DAYS) or DEFAULT_WEEKLY_DAYS)
        effective_limit = calculate_required_fetch_limit(
            timeframe=args.timeframe,
            days=days_for_limit,
        )
    rows: list[dict[str, Any]] = []
    for exchange_name, symbol in targets:
        rows.append(
            run_single_backtest(
                batch_root=batch_root,
                exchange_name=exchange_name,
                symbol=symbol,
                timeframe=args.timeframe,
                limit=effective_limit,
                since=since,
                until=until,
                risk_per_trade=args.risk_per_trade,
            )
        )

    batch_summary = {
        "label": label,
        "created_at": datetime.now().isoformat(),
        "timeframe": args.timeframe,
        "limit": effective_limit,
        "since": since,
        "until": until,
        "rows": rows,
    }
    write_json(batch_root / "batch_summary.json", batch_summary)
    (batch_root / "batch_summary.md").write_text(
        build_batch_markdown(
            label=label,
            timeframe=args.timeframe,
            limit=effective_limit,
            since=since,
            until=until,
            rows=rows,
        ),
        encoding="utf-8",
    )
    print(f"배치 리포트 완료: {batch_root}")
    return 0


def run_diff(args: argparse.Namespace) -> int:
    """두 배치 디렉토리의 결과를 비교한다."""
    before_root = Path(args.before_dir)
    after_root = Path(args.after_dir)
    before_summaries = collect_result_summaries(before_root)
    after_summaries = collect_result_summaries(after_root)
    keys = sorted(set(before_summaries) | set(after_summaries))
    rows: list[dict[str, Any]] = []
    for key in keys:
        before = before_summaries.get(key, {})
        after = after_summaries.get(key, {})
        rows.append(
            {
                "key": key,
                "before_return_pct": float(before.get("net_return_pct", 0.0) or 0.0),
                "after_return_pct": float(after.get("net_return_pct", 0.0) or 0.0),
                "return_diff_pct": float(after.get("net_return_pct", 0.0) or 0.0)
                - float(before.get("net_return_pct", 0.0) or 0.0),
                "before_trade_count": int(before.get("trade_count", 0) or 0),
                "after_trade_count": int(after.get("trade_count", 0) or 0),
                "before_max_drawdown_pct": float(before.get("max_drawdown_pct", 0.0) or 0.0),
                "after_max_drawdown_pct": float(after.get("max_drawdown_pct", 0.0) or 0.0),
            }
        )

    output_dir = build_batch_root(Path(args.output_dir), "diff")
    write_json(output_dir / "diff_summary.json", rows)
    markdown_lines = [
        "# 전후 비교 요약",
        "",
        f"- before: `{before_root}`",
        f"- after: `{after_root}`",
        "",
    ]
    for row in rows:
        markdown_lines.append(
            f"- {row['key']} | 수익률 {row['before_return_pct']:.2f}% -> {row['after_return_pct']:.2f}% "
            f"({row['return_diff_pct']:+.2f}%p) | 거래 수 {row['before_trade_count']} -> {row['after_trade_count']} | "
            f"MDD {row['before_max_drawdown_pct']:.2f}% -> {row['after_max_drawdown_pct']:.2f}%"
        )
    (output_dir / "diff_summary.md").write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    print(f"전후 비교 완료: {output_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 만든다."""
    parser = argparse.ArgumentParser(description="주간/전후 비교용 배치 백테스트 러너")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--timeframe", default="1m")
    common.add_argument("--limit", type=int, default=DEFAULT_FETCH_LIMIT)
    common.add_argument("--risk-per-trade", type=float, default=0.05)
    common.add_argument("--symbols", help="쉼표 구분 심볼 목록, 비우면 관리 심볼 전체")
    common.add_argument("--exchanges", default="okx,upbit", help="쉼표 구분 거래소 목록")
    common.add_argument("--output-dir", default="reports/backtest_batches")

    weekly_parser = subparsers.add_parser("weekly", parents=[common], help="최근 7일 비교 기준 주간 배치 실행")
    weekly_parser.add_argument("--days", type=int, default=DEFAULT_WEEKLY_DAYS)
    weekly_parser.add_argument("--auto-limit", action="store_true", default=True)

    snapshot_parser = subparsers.add_parser("snapshot", parents=[common], help="임의 라벨 배치 실행")
    snapshot_parser.add_argument("--label", required=True)
    snapshot_parser.add_argument("--since", help="실거래 비교 시작 YYYY-MM-DD")
    snapshot_parser.add_argument("--until", help="실거래 비교 종료 YYYY-MM-DD")
    snapshot_parser.add_argument("--auto-limit", action="store_true", default=True)

    diff_parser = subparsers.add_parser("diff", help="두 배치 결과 전후 비교")
    diff_parser.add_argument("--before-dir", required=True)
    diff_parser.add_argument("--after-dir", required=True)
    diff_parser.add_argument("--output-dir", default="reports/backtest_batches")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "weekly":
        until = datetime.now().date().strftime("%Y-%m-%d")
        since = (datetime.now().date() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        return run_batch(args, label="weekly", since=since, until=until)
    if args.command == "snapshot":
        return run_batch(args, label=args.label, since=args.since, until=args.until)
    if args.command == "diff":
        return run_diff(args)
    parser.error("지원하지 않는 명령입니다.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
