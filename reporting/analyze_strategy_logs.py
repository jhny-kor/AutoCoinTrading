"""
수정 요약
- 2026-05-24: 텔레그램 분석 명령이 전체 구조화 로그를 읽지 않도록 최신 날짜 제한 옵션을 추가했다.
- 2026-09-07: 디스크 부족으로 잘린 JSONL 한 줄이 전략 리포트 전체를 중단시키지 않도록 손상 행을 건너뛰게 보강했다.
- 주문 실행 품질 평균값(API 지연, 슬리피지, 체결 비율)도 거래 품질 요약에 함께 집계하도록 확장
- MFE/MAE, 트레일링 활성화 소요 시간, 시간대 성과, 필터 기준 부족 폭까지 함께 집계하도록 확장
- 구조화된 strategy / trade 로그를 읽어 퍼널 병목과 차단 사유를 집계하는 분석 스크립트 추가
- 심볼별 scan / ready / requested / filled / top_block_reason 을 표처럼 빠르게 확인하도록 추가
- CSV 파일로 내보내기 쉽게 기본 요약 행을 생성하도록 추가

구조화 전략 로그 분석기

- structured_logs/live/<program>/strategy.jsonl 을 읽어 퍼널 통과율과 차단 사유를 집계한다.
- structured_logs/live/<program>/trade.jsonl 을 함께 읽어 체결 수와 손익도 요약한다.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from log_path_utils import iter_files

DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """JSONL 파일을 한 줄씩 흘려보내며 읽는다(메모리 상수)."""
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """JSONL 파일을 읽는다."""
    return list(iter_jsonl(path))


def iter_recent_date_dirs(base_dir: Path, max_date_dirs: int | None = None) -> list[Path]:
    """최신 날짜 디렉터리를 내림차순으로 반환한다."""
    if not base_dir.exists():
        return []
    date_dirs = sorted(
        (
            path
            for path in base_dir.iterdir()
            if path.is_dir() and DATE_DIR_RE.match(path.name)
        ),
        key=lambda path: path.name,
        reverse=True,
    )
    if max_date_dirs is None:
        return date_dirs
    return date_dirs[:max(max_date_dirs, 0)]


def iter_program_log_files(
    base_dir: Path,
    filename: str,
    *,
    program_name: str | None = None,
    max_date_dirs: int | None = None,
) -> list[Path]:
    """구조화 로그 파일 목록을 날짜 제한과 함께 반환한다."""
    if not base_dir.exists():
        return []

    if max_date_dirs is None:
        files = iter_files(base_dir, filename)
    else:
        files: list[Path] = []
        for date_dir in iter_recent_date_dirs(base_dir, max_date_dirs=max_date_dirs):
            files.extend(iter_files(date_dir, filename))
        if not files:
            files = iter_files(base_dir, filename)

    if program_name is not None:
        files = [path for path in files if path.parent.name == program_name]
    return sorted(files)


def find_program_names(base_dir: Path, max_date_dirs: int | None = None) -> list[str]:
    """구조화 로그 루트 아래의 프로그램 이름 목록을 찾는다."""
    names = {
        path.parent.name
        for path in iter_program_log_files(
            base_dir,
            "strategy.jsonl",
            max_date_dirs=max_date_dirs,
        )
    }
    return sorted(names)


def read_program_records(
    base_dir: Path,
    program_name: str,
    filename: str,
    *,
    max_date_dirs: int | None = None,
) -> list[dict[str, Any]]:
    """날짜별로 흩어진 특정 프로그램 로그를 모두 읽는다."""
    return list(
        iter_program_records(
            base_dir,
            program_name,
            filename,
            max_date_dirs=max_date_dirs,
        )
    )


def iter_program_records(
    base_dir: Path,
    program_name: str,
    filename: str,
    *,
    max_date_dirs: int | None = None,
) -> Iterator[dict[str, Any]]:
    """날짜별로 흩어진 특정 프로그램 로그를 한 줄씩 흘려보낸다(메모리 상수)."""
    for path in iter_program_log_files(
        base_dir,
        filename,
        program_name=program_name,
        max_date_dirs=max_date_dirs,
    ):
        yield from iter_jsonl(path)


def format_ratio(numerator: int, denominator: int) -> str:
    """비율을 문자열로 만든다."""
    if denominator <= 0:
        return "-"
    return f"{(numerator / denominator) * 100:.1f}%"


def build_summary_rows(
    base_dir: Path,
    *,
    max_date_dirs: int | None = None,
) -> list[dict[str, Any]]:
    """프로그램별 strategy / trade 로그를 읽어 요약 행을 만든다."""
    rows: list[dict[str, Any]] = []
    for program_name in find_program_names(base_dir, max_date_dirs=max_date_dirs):
        # 거대한 strategy.jsonl 을 통째로 메모리에 올리지 않고 한 줄씩 흘려보내며
        # (symbol, side) 별 집계만 누적한다.
        strategy_aggs: dict[tuple[str, str], dict[str, Any]] = {}
        key_order: list[tuple[str, str]] = []

        def get_agg(key: tuple[str, str]) -> dict[str, Any]:
            agg = strategy_aggs.get(key)
            if agg is None:
                agg = {
                    "block_counter": Counter(),
                    "pass_counter": Counter(),
                    "scans": 0,
                    "ready": 0,
                    "requested": 0,
                    "filled": 0,
                }
                strategy_aggs[key] = agg
                key_order.append(key)
            return agg

        for record in iter_program_records(
            base_dir, program_name, "strategy.jsonl", max_date_dirs=max_date_dirs
        ):
            key = (str(record.get("symbol", "")), str(record.get("side", "")))
            agg = get_agg(key)
            result = record.get("result")
            stage = record.get("stage")
            if result == "blocked":
                agg["block_counter"][record.get("reason")] += 1
            elif result == "pass":
                agg["pass_counter"][stage] += 1
            if stage == "scan" and result == "seen":
                agg["scans"] += 1
            elif result == "ready" and stage in {"buy_ready", "sell_ready"}:
                agg["ready"] += 1
            elif stage == "order_requested" and result == "requested":
                agg["requested"] += 1
            elif stage == "filled" and result == "filled":
                agg["filled"] += 1

        # 체결 손익은 trade.jsonl 에서 (symbol, side) 별 합/건수만 누적한다.
        pnl_sum: dict[tuple[str, str], float] = defaultdict(float)
        pnl_count: dict[tuple[str, str], int] = defaultdict(int)
        for record in iter_program_records(
            base_dir, program_name, "trade.jsonl", max_date_dirs=max_date_dirs
        ):
            if record.get("log_type") != "trade":
                continue
            if record.get("result") != "filled":
                continue
            actual = record.get("actual")
            if not isinstance(actual, dict):
                continue
            pnl = actual.get("realized_pnl_pct")
            if pnl is None:
                continue
            side = "entry" if record.get("side") == "buy" else "exit"
            key = (str(record.get("symbol", "")), side)
            pnl_sum[key] += float(pnl)
            pnl_count[key] += 1

        for key in sorted(key_order):
            symbol, side = key
            agg = strategy_aggs[key]
            block_counter = agg["block_counter"]
            pass_counter = agg["pass_counter"]
            scan_count = agg["scans"]
            ready_count = agg["ready"]
            order_requested_count = agg["requested"]
            filled_count = agg["filled"]
            pnl_n = pnl_count.get(key, 0)

            rows.append(
                {
                    "program_name": program_name,
                    "symbol": symbol,
                    "side": side,
                    "scans": scan_count,
                    "ready": ready_count,
                    "requested": order_requested_count,
                    "filled": filled_count,
                    "ready_rate": format_ratio(ready_count, scan_count),
                    "fill_rate_vs_ready": format_ratio(filled_count, ready_count),
                    "top_block_reason": block_counter.most_common(1)[0][0]
                    if block_counter
                    else "-",
                    "top_block_count": block_counter.most_common(1)[0][1]
                    if block_counter
                    else 0,
                    "trend_pass": pass_counter.get("trend", 0),
                    "distance_pass": pass_counter.get("distance", 0),
                    "volume_pass": pass_counter.get("volume", 0),
                    "volatility_or_atr_pass": pass_counter.get("volatility", 0)
                    + pass_counter.get("atr", 0),
                    "cooldown_pass": pass_counter.get("cooldown", 0),
                    "avg_realized_pnl_pct": (
                        f"{pnl_sum[key] / pnl_n:.3f}" if pnl_n else "-"
                    ),
                }
            )
    return rows


def _to_float(value: Any) -> float | None:
    """숫자 형태를 안전하게 float 로 바꾼다."""
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def read_trade_history(path: Path | None = None) -> list[dict[str, Any]]:
    """통합 체결 이력 JSONL 을 읽는다."""
    if path is not None:
        return read_jsonl(path)
    rows: list[dict[str, Any]] = []
    for trade_path in iter_files("trade_logs", "trade_history.jsonl"):
        rows.extend(read_jsonl(trade_path))
    return rows


def build_trade_quality_rows(
    trade_history_path: Path | None = None,
) -> list[dict[str, Any]]:
    """체결 이력 기준으로 거래 품질 요약 행을 만든다."""
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    grouped_execution: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in read_trade_history(trade_history_path):
        key = (
            str(record.get("program_name", "")),
            str(record.get("symbol", "")),
            str(record.get("quote_currency", "")),
        )
        grouped_execution[key].append(record)
        if record.get("side") != "sell":
            continue
        grouped[key].append(record)

    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        program_name, symbol, quote_currency = key
        records = grouped[key]
        execution_records = grouped_execution.get(key, [])
        pnl_values: list[float] = []
        holding_values: list[float] = []
        mfe_values: list[float] = []
        mae_values: list[float] = []
        arm_values: list[float] = []
        active_values: list[float] = []
        api_latency_values: list[float] = []
        slippage_values: list[float] = []
        fill_ratio_values: list[float] = []
        exit_reasons = Counter(str(record.get("reason", "")) for record in records)
        trailing_count = 0

        for record in records:
            pnl_value = _to_float(record.get("net_realized_pnl_pct"))
            if pnl_value is None:
                pnl_value = _to_float(record.get("realized_pnl_pct"))
            if pnl_value is not None:
                pnl_values.append(pnl_value)

            holding = _to_float(record.get("holding_seconds"))
            if holding is not None:
                holding_values.append(holding)

            mfe_pct = _to_float(record.get("mfe_pct"))
            if mfe_pct is not None:
                mfe_values.append(mfe_pct)

            mae_pct = _to_float(record.get("mae_pct"))
            if mae_pct is not None:
                mae_values.append(mae_pct)

            arm_seconds = _to_float(record.get("trailing_armed_seconds"))
            if arm_seconds is not None:
                arm_values.append(arm_seconds)

            active_seconds = _to_float(record.get("activation_to_exit_seconds"))
            if active_seconds is not None:
                active_values.append(active_seconds)

            if record.get("trailing_armed") or record.get("trailing_armed_at"):
                trailing_count += 1

        for record in execution_records:
            api_latency = _to_float(record.get("api_latency_ms"))
            if api_latency is not None:
                api_latency_values.append(api_latency)

            slippage_bps = _to_float(record.get("slippage_bps"))
            if slippage_bps is not None:
                slippage_values.append(slippage_bps)

            fill_ratio = _to_float(record.get("fill_ratio"))
            if fill_ratio is not None:
                fill_ratio_values.append(fill_ratio * 100)

        rows.append(
            {
                "program_name": program_name,
                "symbol": symbol,
                "quote_currency": quote_currency,
                "trades": len(records),
                "avg_net_pnl_pct": (
                    f"{sum(pnl_values) / len(pnl_values):.3f}" if pnl_values else "-"
                ),
                "avg_holding_seconds": (
                    f"{sum(holding_values) / len(holding_values):.1f}"
                    if holding_values
                    else "-"
                ),
                "avg_mfe_pct": (
                    f"{sum(mfe_values) / len(mfe_values):.3f}" if mfe_values else "-"
                ),
                "avg_mae_pct": (
                    f"{sum(mae_values) / len(mae_values):.3f}" if mae_values else "-"
                ),
                "trailing_arm_rate": (
                    f"{(trailing_count / len(records)) * 100:.1f}%"
                    if records
                    else "-"
                ),
                "avg_trailing_armed_seconds": (
                    f"{sum(arm_values) / len(arm_values):.1f}" if arm_values else "-"
                ),
                "avg_activation_to_exit_seconds": (
                    f"{sum(active_values) / len(active_values):.1f}"
                    if active_values
                    else "-"
                ),
                "avg_api_latency_ms": (
                    f"{sum(api_latency_values) / len(api_latency_values):.1f}"
                    if api_latency_values
                    else "-"
                ),
                "avg_slippage_bps": (
                    f"{sum(slippage_values) / len(slippage_values):.2f}"
                    if slippage_values
                    else "-"
                ),
                "avg_fill_ratio_pct": (
                    f"{sum(fill_ratio_values) / len(fill_ratio_values):.1f}"
                    if fill_ratio_values
                    else "-"
                ),
                "execution_samples": len(execution_records),
                "top_exit_reason": exit_reasons.most_common(1)[0][0]
                if exit_reasons
                else "-",
            }
        )
    return rows


def build_time_of_day_rows(
    trade_history_path: Path | None = None,
) -> list[dict[str, Any]]:
    """체결 이력 기준으로 시간대 성과 요약 행을 만든다."""
    grouped: dict[int, list[float]] = defaultdict(list)
    for record in read_trade_history(trade_history_path):
        if record.get("side") != "sell":
            continue
        ts = str(record.get("recorded_at_local", "")).strip()
        if not ts:
            continue
        try:
            hour = datetime.fromisoformat(ts).hour
        except ValueError:
            continue
        pnl_value = _to_float(record.get("net_realized_pnl_pct"))
        if pnl_value is None:
            pnl_value = _to_float(record.get("realized_pnl_pct"))
        if pnl_value is None:
            continue
        grouped[hour].append(pnl_value)

    rows: list[dict[str, Any]] = []
    for hour in sorted(grouped):
        values = grouped[hour]
        rows.append(
            {
                "hour": hour,
                "trades": len(values),
                "avg_net_pnl_pct": f"{sum(values) / len(values):.3f}",
            }
        )
    return rows


def extract_threshold_gap(record: dict[str, Any]) -> tuple[str, float, float, float] | None:
    """blocked 레코드에서 실제값과 기준값의 차이를 추출한다."""
    reason = str(record.get("reason", ""))
    actual = record.get("actual") if isinstance(record.get("actual"), dict) else {}
    required = (
        record.get("required") if isinstance(record.get("required"), dict) else {}
    )

    candidates = {
        "distance_too_small": ("gap_pct", "min_gap_pct"),
        "volume_low": ("volume_ratio", "min_volume_ratio"),
        "volatility_low": ("avg_abs_change_pct", "min_volatility_pct"),
        "atr_low": ("atr_pct", "min_atr_pct"),
        "order_value_too_small": ("order_value_quote", "min_buy_order_value"),
        "order_amount_too_small": ("order_amount", "min_order_amount"),
        "sell_amount_too_small": ("sell_amount", "sell_amount_gt"),
        "take_profit_not_reached": ("pnl_pct", "min_take_profit_pct"),
    }
    if reason not in candidates:
        return None

    actual_key, required_key = candidates[reason]
    actual_value = _to_float(actual.get(actual_key))
    required_value = _to_float(required.get(required_key))
    if actual_value is None or required_value is None:
        return None

    shortfall = required_value - actual_value
    return reason, actual_value, required_value, shortfall


def build_filter_gap_rows(
    base_dir: Path,
    *,
    max_date_dirs: int | None = None,
) -> list[dict[str, Any]]:
    """strategy blocked 로그에서 기준 부족 폭을 요약한다."""
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)

    for program_name in find_program_names(base_dir, max_date_dirs=max_date_dirs):
        for record in read_program_records(
            base_dir,
            program_name,
            "strategy.jsonl",
            max_date_dirs=max_date_dirs,
        ):
            if record.get("result") != "blocked":
                continue
            gap = extract_threshold_gap(record)
            if gap is None:
                continue
            reason, _, _, shortfall = gap
            grouped[(program_name, str(record.get("symbol", "")), reason)].append(
                shortfall
            )

    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        program_name, symbol, reason = key
        values = grouped[key]
        rows.append(
            {
                "program_name": program_name,
                "symbol": symbol,
                "reason": reason,
                "count": len(values),
                "avg_shortfall": f"{sum(values) / len(values):.4f}",
                "max_shortfall": f"{max(values):.4f}",
            }
        )
    return rows


def print_named_table(title: str, rows: list[dict[str, Any]], headers: list[str]) -> None:
    """제목이 있는 표를 출력한다."""
    print(f"\n{title}")
    if not rows:
        print("- 데이터가 아직 없습니다.")
        return

    widths = {
        header: max(len(header), *(len(str(row.get(header, ""))) for row in rows))
        for header in headers
    }
    print(" | ".join(header.ljust(widths[header]) for header in headers))
    print("-+-".join("-" * widths[header] for header in headers))
    for row in rows:
        print(" | ".join(str(row.get(header, "")).ljust(widths[header]) for header in headers))


def print_table(rows: list[dict[str, Any]]) -> None:
    """요약 표를 터미널에 출력한다."""
    if not rows:
        print("구조화 전략 로그가 없습니다. 봇을 다시 실행해 새 strategy.jsonl 이 쌓인 뒤 분석해 주세요.")
        return

    headers = [
        "program_name",
        "symbol",
        "side",
        "scans",
        "ready",
        "requested",
        "filled",
        "ready_rate",
        "fill_rate_vs_ready",
        "top_block_reason",
        "top_block_count",
        "avg_realized_pnl_pct",
    ]
    widths = {
        header: max(len(header), *(len(str(row.get(header, ""))) for row in rows))
        for header in headers
    }

    print(" | ".join(header.ljust(widths[header]) for header in headers))
    print("-+-".join("-" * widths[header] for header in headers))
    for row in rows:
        print(" | ".join(str(row.get(header, "")).ljust(widths[header]) for header in headers))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """요약 행을 CSV 로 저장한다."""
    if not rows:
        return
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    headers = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """엔트리 포인트."""
    parser = argparse.ArgumentParser(description="구조화 전략 로그 퍼널 분석기")
    parser.add_argument(
        "--base-dir",
        default="structured_logs/live",
        help="구조화 로그 루트 디렉토리",
    )
    parser.add_argument(
        "--csv",
        default="",
        help="CSV 저장 경로",
    )
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    if not base_dir.exists():
        print("구조화 로그 디렉토리가 없습니다. 먼저 봇을 실행해 주세요.")
        return

    rows = build_summary_rows(base_dir)
    print_table(rows)
    print_named_table(
        "거래 품질 요약",
        build_trade_quality_rows(),
        [
            "program_name",
            "symbol",
            "quote_currency",
            "trades",
            "avg_net_pnl_pct",
            "avg_holding_seconds",
            "avg_mfe_pct",
            "avg_mae_pct",
            "trailing_arm_rate",
            "avg_trailing_armed_seconds",
            "avg_activation_to_exit_seconds",
            "top_exit_reason",
        ],
    )
    print_named_table(
        "시간대 성과 요약",
        build_time_of_day_rows(),
        ["hour", "trades", "avg_net_pnl_pct"],
    )
    print_named_table(
        "필터 기준 부족 폭 요약",
        build_filter_gap_rows(base_dir),
        ["program_name", "symbol", "reason", "count", "avg_shortfall", "max_shortfall"],
    )
    if args.csv:
        write_csv(Path(args.csv), rows)
        print(f"\nCSV 저장 완료: {args.csv}")


if __name__ == "__main__":
    main()
