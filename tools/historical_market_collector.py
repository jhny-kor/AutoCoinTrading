"""
작업 요약
- BTC/ETH 는 3년, 그 외 알트는 1년 기준으로 공개 과거 시장 데이터를 수집하는 도구를 추가했다.
- OHLCV 는 백테스트와 바로 호환되는 JSONL 필드로 저장하고, OKX 는 funding rate history 도 함께 수집할 수 있게 구성했다.
- 장기 1분봉 수집이 느려지지 않도록 기존 timestamp 는 target 시작 시 한 번만 읽고 메모리에서 중복을 제거한다.
- 장시간 전체 수집은 launch/status 서브커맨드로 백그라운드 실행과 PID 확인이 가능하게 했다.

과거 시장 데이터 수집기

- OKX: /api/v5/market/history-candles 와 /api/v5/public/funding-rate-history 사용
- 업비트: /v1/candles/minutes/{unit} 사용
- 저장 경로: historical_data/{exchange}/{symbol}/{timeframe}/ohlcv.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import ccxt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.execution.okx import call_okx_with_retry, spot_symbol_to_okx_swap_inst_id
from settings.env import load_project_env
from strategy_settings import load_managed_symbols
from tools.analysis_log_collector import create_okx_public_client


DEFAULT_TIMEFRAME = "1m"
CORE_ASSETS = {"BTC", "ETH"}
DEFAULT_OUTPUT_ROOT = Path("historical_data")
UPBIT_BASE_URL = "https://api.upbit.com"
DEFAULT_LOG_PATH = Path("logs/historical_market_collector.log")
DEFAULT_PID_PATH = Path("logs/pids/historical_market_collector.pid")


@dataclass(frozen=True)
class CollectionTarget:
    """과거 데이터 수집 대상."""

    exchange: str
    symbol: str
    timeframe: str
    years: int


@dataclass(frozen=True)
class CollectionResult:
    """수집 결과 요약."""

    exchange: str
    symbol: str
    timeframe: str
    years: int
    output_path: str
    fetched_rows: int
    written_rows: int
    skipped_existing_rows: int
    page_count: int
    started_at_ms: int
    ended_at_ms: int


@dataclass(frozen=True)
class FundingCollectionResult:
    """funding rate 수집 결과 요약."""

    exchange: str
    symbol: str
    swap_inst_id: str
    output_path: str
    fetched_rows: int
    written_rows: int
    skipped_existing_rows: int
    page_count: int


def now_ms() -> int:
    """현재 UTC 시각을 ms 로 반환한다."""
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def iso_utc(timestamp_ms: int) -> str:
    """ms timestamp 를 UTC ISO 문자열로 변환한다."""
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).isoformat()


def parse_date_to_ms(raw: str | None, default_ms: int) -> int:
    """YYYY-MM-DD 또는 ISO 날짜 문자열을 ms timestamp 로 변환한다."""
    if not raw:
        return default_ms
    text = raw.strip()
    if not text:
        return default_ms
    if len(text) == 10:
        dt = datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
    else:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)


def timeframe_to_ms(timeframe: str) -> int:
    """timeframe 문자열을 ms 로 변환한다."""
    raw = timeframe.strip().lower()
    if raw.endswith("m"):
        return int(raw[:-1]) * 60 * 1000
    if raw.endswith("h"):
        return int(raw[:-1]) * 60 * 60 * 1000
    if raw.endswith("d"):
        return int(raw[:-1]) * 24 * 60 * 60 * 1000
    raise ValueError(f"지원하지 않는 timeframe 입니다: {timeframe}")


def okx_bar(timeframe: str) -> str:
    """OKX bar 문자열로 변환한다."""
    mapping = {
        "1m": "1m",
        "3m": "3m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1H",
        "4h": "4H",
        "1d": "1D",
    }
    if timeframe not in mapping:
        raise ValueError(f"OKX 미지원 timeframe 입니다: {timeframe}")
    return mapping[timeframe]


def upbit_unit(timeframe: str) -> int:
    """업비트 분봉 unit 으로 변환한다."""
    raw = timeframe.strip().lower()
    if not raw.endswith("m"):
        raise ValueError("업비트 장기 수집은 분봉 timeframe 만 지원합니다.")
    unit = int(raw[:-1])
    if unit not in {1, 3, 5, 10, 15, 30, 60, 240}:
        raise ValueError(f"업비트 미지원 분봉 unit 입니다: {unit}")
    return unit


def sanitize_symbol(symbol: str) -> str:
    """심볼을 경로에 안전한 이름으로 바꾼다."""
    return symbol.replace("/", "_").replace("-", "_")


def symbol_to_upbit_market(symbol: str) -> str:
    """BTC/KRW 형식 심볼을 KRW-BTC 마켓 코드로 바꾼다."""
    if "/" not in symbol:
        raise ValueError(f"업비트 심볼 형식이 아닙니다: {symbol}")
    base, quote = symbol.split("/", 1)
    return f"{quote.upper()}-{base.upper()}"


def base_asset(symbol: str) -> str:
    """심볼의 base asset 을 반환한다."""
    return symbol.split("/", 1)[0].strip().upper()


def years_for_symbol(symbol: str, *, core_years: int, alt_years: int) -> int:
    """BTC/ETH 와 알트의 보관 기간을 결정한다."""
    return core_years if base_asset(symbol) in CORE_ASSETS else alt_years


def merge_symbols(*symbol_groups: Iterable[str]) -> list[str]:
    """순서를 유지하며 중복 심볼을 제거한다."""
    seen: set[str] = set()
    symbols: list[str] = []
    for group in symbol_groups:
        for symbol in group:
            normalized = symbol.strip().upper()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            symbols.append(normalized)
    return symbols


def default_symbols_for_exchange(exchange: str) -> list[str]:
    """운영 심볼과 BTC/ETH 필수 심볼을 합쳐 기본 수집 대상을 만든다."""
    exchange_key = exchange.lower()
    if exchange_key == "okx":
        return merge_symbols(("BTC/USDT", "ETH/USDT"), load_managed_symbols("okx"))
    if exchange_key == "upbit":
        return merge_symbols(("BTC/KRW", "ETH/KRW"), load_managed_symbols("upbit"))
    raise ValueError(f"지원하지 않는 거래소입니다: {exchange}")


def build_default_targets(
    *,
    exchanges: Iterable[str],
    timeframe: str,
    core_years: int,
    alt_years: int,
    symbols: list[str] | None = None,
) -> list[CollectionTarget]:
    """기본 수집 target 목록을 만든다."""
    targets: list[CollectionTarget] = []
    for exchange in exchanges:
        exchange_key = exchange.lower()
        exchange_symbols = symbols if symbols is not None else default_symbols_for_exchange(exchange_key)
        for symbol in exchange_symbols:
            targets.append(
                CollectionTarget(
                    exchange=exchange_key,
                    symbol=symbol,
                    timeframe=timeframe,
                    years=years_for_symbol(
                        symbol,
                        core_years=core_years,
                        alt_years=alt_years,
                    ),
                )
            )
    return targets


def output_dir_for_target(output_root: Path, target: CollectionTarget) -> Path:
    """target 별 출력 디렉터리를 반환한다."""
    return output_root / target.exchange / sanitize_symbol(target.symbol) / target.timeframe


def ohlcv_output_path(output_root: Path, target: CollectionTarget) -> Path:
    """OHLCV JSONL 출력 경로를 반환한다."""
    return output_dir_for_target(output_root, target) / "ohlcv.jsonl"


def funding_output_path(output_root: Path, exchange: str, symbol: str) -> Path:
    """funding rate JSONL 출력 경로를 반환한다."""
    return output_root / exchange / sanitize_symbol(symbol) / "funding_rate.jsonl"


def load_existing_timestamps(path: Path, key: str = "timestamp_ms") -> set[int]:
    """기존 JSONL 파일에서 timestamp key 집합을 읽는다."""
    if not path.exists():
        return set()
    timestamps: set[int] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            value = payload.get(key)
            try:
                timestamps.add(int(value))
            except (TypeError, ValueError):
                continue
    return timestamps


def append_jsonl_unique(
    path: Path,
    rows: Iterable[dict[str, Any]],
    *,
    key: str,
    existing_keys: set[int] | None = None,
) -> tuple[int, int]:
    """중복 timestamp 를 제외하고 JSONL 을 append 한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = existing_keys if existing_keys is not None else load_existing_timestamps(path, key=key)
    written = 0
    skipped = 0
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            try:
                row_key = int(row[key])
            except (KeyError, TypeError, ValueError):
                skipped += 1
                continue
            if row_key in existing:
                skipped += 1
                continue
            existing.add(row_key)
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            written += 1
    return written, skipped


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    """수집 메타데이터 manifest 를 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_pid(path: Path) -> int | None:
    """PID 파일에서 실행 중인 process id 를 읽는다."""
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, OSError, ValueError):
        return None


def is_pid_alive(pid: int) -> bool:
    """PID 가 살아 있는지 확인한다."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def write_pid(path: Path, pid: int) -> None:
    """PID 파일을 기록한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(pid), encoding="utf-8")


def parse_okx_history_candles(
    *,
    exchange_name: str,
    symbol: str,
    timeframe: str,
    rows: Iterable[list[Any]],
    collected_at: str,
) -> list[dict[str, Any]]:
    """OKX history-candles 응답을 canonical OHLCV row 로 변환한다."""
    market_id = symbol.replace("/", "-")
    parsed: list[dict[str, Any]] = []
    for item in rows:
        if len(item) < 6:
            continue
        timestamp_ms = int(item[0])
        volume_base = float(item[5])
        quote_volume = float(item[7]) if len(item) > 7 and item[7] not in (None, "") else None
        parsed.append(
            {
                "exchange": exchange_name,
                "symbol": symbol,
                "market_id": market_id,
                "timeframe": timeframe,
                "timestamp_ms": timestamp_ms,
                "datetime_utc": iso_utc(timestamp_ms),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": volume_base,
                "volume_base": volume_base,
                "quote_volume": quote_volume,
                "okx_vol_ccy": float(item[6]) if len(item) > 6 and item[6] not in (None, "") else None,
                "okx_vol_ccy_quote": quote_volume,
                "confirm": int(item[8]) if len(item) > 8 and item[8] not in (None, "") else None,
                "source": "okx.market.history-candles",
                "collected_at": collected_at,
            }
        )
    return sorted(parsed, key=lambda row: row["timestamp_ms"])


def parse_upbit_candles(
    *,
    symbol: str,
    timeframe: str,
    rows: Iterable[dict[str, Any]],
    collected_at: str,
) -> list[dict[str, Any]]:
    """업비트 candles 응답을 canonical OHLCV row 로 변환한다."""
    parsed: list[dict[str, Any]] = []
    market_id = symbol_to_upbit_market(symbol)
    for item in rows:
        timestamp_ms = int(item["timestamp"])
        volume_base = float(item["candle_acc_trade_volume"])
        quote_volume = float(item["candle_acc_trade_price"])
        parsed.append(
            {
                "exchange": "upbit",
                "symbol": symbol,
                "market_id": market_id,
                "timeframe": timeframe,
                "timestamp_ms": timestamp_ms,
                "datetime_utc": iso_utc(timestamp_ms),
                "candle_date_time_utc": item.get("candle_date_time_utc"),
                "candle_date_time_kst": item.get("candle_date_time_kst"),
                "open": float(item["opening_price"]),
                "high": float(item["high_price"]),
                "low": float(item["low_price"]),
                "close": float(item["trade_price"]),
                "volume": volume_base,
                "volume_base": volume_base,
                "quote_volume": quote_volume,
                "source": "upbit.candles.minutes",
                "collected_at": collected_at,
            }
        )
    return sorted(parsed, key=lambda row: row["timestamp_ms"])


def fetch_okx_history_page(
    exchange: ccxt.okx,
    *,
    symbol: str,
    timeframe: str,
    cursor_after_ms: int | None,
    limit: int,
) -> list[list[Any]]:
    """OKX 과거 캔들 한 페이지를 조회한다."""
    params: dict[str, Any] = {
        "instId": symbol.replace("/", "-"),
        "bar": okx_bar(timeframe),
        "limit": str(min(limit, 100)),
    }
    if cursor_after_ms is not None:
        params["after"] = str(cursor_after_ms)
    response = call_okx_with_retry(exchange, exchange.publicGetMarketHistoryCandles, params)
    data = response.get("data", []) if isinstance(response, dict) else response
    return data if isinstance(data, list) else []


def fetch_upbit_candles_page(
    *,
    symbol: str,
    timeframe: str,
    cursor_to_ms: int | None,
    limit: int,
) -> list[dict[str, Any]]:
    """업비트 과거 분봉 한 페이지를 조회한다."""
    unit = upbit_unit(timeframe)
    params = {
        "market": symbol_to_upbit_market(symbol),
        "count": str(min(limit, 200)),
    }
    if cursor_to_ms is not None:
        params["to"] = datetime.fromtimestamp(cursor_to_ms / 1000, timezone.utc).isoformat()
    url = f"{UPBIT_BASE_URL}/v1/candles/minutes/{unit}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, list) else []


def collect_ohlcv_target(
    target: CollectionTarget,
    *,
    output_root: Path,
    start_ms: int | None = None,
    end_ms: int | None = None,
    limit: int | None = None,
    request_delay_sec: float = 0.15,
    max_pages: int | None = None,
) -> CollectionResult:
    """단일 target 의 OHLCV 를 수집한다."""
    end_ts = end_ms or now_ms()
    start_ts = start_ms or int((datetime.fromtimestamp(end_ts / 1000, timezone.utc) - timedelta(days=365 * target.years)).timestamp() * 1000)
    output_path = ohlcv_output_path(output_root, target)
    page_limit = limit or (100 if target.exchange == "okx" else 200)
    cursor: int | None = end_ts
    page_count = 0
    fetched_rows = 0
    written_rows = 0
    skipped_rows = 0
    exchange = create_okx_public_client() if target.exchange == "okx" else None
    existing_timestamps = load_existing_timestamps(output_path, key="timestamp_ms")

    while True:
        if max_pages is not None and page_count >= max_pages:
            break
        collected_at = datetime.now(timezone.utc).isoformat()
        if target.exchange == "okx":
            raw_rows = fetch_okx_history_page(
                exchange,
                symbol=target.symbol,
                timeframe=target.timeframe,
                cursor_after_ms=cursor,
                limit=page_limit,
            )
            rows = parse_okx_history_candles(
                exchange_name="okx",
                symbol=target.symbol,
                timeframe=target.timeframe,
                rows=raw_rows,
                collected_at=collected_at,
            )
        elif target.exchange == "upbit":
            raw_rows = fetch_upbit_candles_page(
                symbol=target.symbol,
                timeframe=target.timeframe,
                cursor_to_ms=cursor,
                limit=page_limit,
            )
            rows = parse_upbit_candles(
                symbol=target.symbol,
                timeframe=target.timeframe,
                rows=raw_rows,
                collected_at=collected_at,
            )
        else:
            raise ValueError(f"지원하지 않는 거래소입니다: {target.exchange}")

        page_count += 1
        if not rows:
            break

        bounded_rows = [
            row for row in rows if start_ts <= int(row["timestamp_ms"]) <= end_ts
        ]
        written, skipped = append_jsonl_unique(
            output_path,
            bounded_rows,
            key="timestamp_ms",
            existing_keys=existing_timestamps,
        )
        fetched_rows += len(rows)
        written_rows += written
        skipped_rows += skipped

        oldest_ts = min(int(row["timestamp_ms"]) for row in rows)
        if oldest_ts <= start_ts:
            break
        cursor = oldest_ts
        time.sleep(max(0.0, request_delay_sec))

    write_manifest(
        output_dir_for_target(output_root, target) / "manifest.json",
        {
            "target": asdict(target),
            "output_path": str(output_path),
            "requested_start_ms": start_ts,
            "requested_end_ms": end_ts,
            "requested_start_utc": iso_utc(start_ts),
            "requested_end_utc": iso_utc(end_ts),
            "fields": [
                "exchange",
                "symbol",
                "market_id",
                "timeframe",
                "timestamp_ms",
                "datetime_utc",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "volume_base",
                "quote_volume",
                "confirm",
                "source",
                "collected_at",
            ],
            "last_result": {
                "fetched_rows": fetched_rows,
                "written_rows": written_rows,
                "skipped_existing_rows": skipped_rows,
                "page_count": page_count,
            },
        },
    )
    return CollectionResult(
        exchange=target.exchange,
        symbol=target.symbol,
        timeframe=target.timeframe,
        years=target.years,
        output_path=str(output_path),
        fetched_rows=fetched_rows,
        written_rows=written_rows,
        skipped_existing_rows=skipped_rows,
        page_count=page_count,
        started_at_ms=start_ts,
        ended_at_ms=end_ts,
    )


def parse_okx_funding_rows(
    *,
    symbol: str,
    swap_inst_id: str,
    rows: Iterable[dict[str, Any]],
    collected_at: str,
) -> list[dict[str, Any]]:
    """OKX funding-rate-history 응답을 canonical row 로 변환한다."""
    parsed: list[dict[str, Any]] = []
    for item in rows:
        funding_time_ms = int(item["fundingTime"])
        parsed.append(
            {
                "exchange": "okx",
                "symbol": symbol,
                "swap_inst_id": swap_inst_id,
                "funding_time_ms": funding_time_ms,
                "datetime_utc": iso_utc(funding_time_ms),
                "funding_rate": float(item["fundingRate"]) if item.get("fundingRate") not in (None, "") else None,
                "realized_rate": float(item["realizedRate"]) if item.get("realizedRate") not in (None, "") else None,
                "method": item.get("method"),
                "formula_type": item.get("formulaType"),
                "inst_type": item.get("instType"),
                "source": "okx.public.funding-rate-history",
                "collected_at": collected_at,
            }
        )
    return sorted(parsed, key=lambda row: row["funding_time_ms"])


def fetch_okx_funding_page(
    exchange: ccxt.okx,
    *,
    swap_inst_id: str,
    cursor_after_ms: int | None,
    limit: int = 400,
) -> list[dict[str, Any]]:
    """OKX funding history 한 페이지를 조회한다."""
    params: dict[str, Any] = {"instId": swap_inst_id, "limit": str(min(limit, 400))}
    if cursor_after_ms is not None:
        params["after"] = str(cursor_after_ms)
    response = call_okx_with_retry(exchange, exchange.publicGetPublicFundingRateHistory, params)
    data = response.get("data", []) if isinstance(response, dict) else response
    return data if isinstance(data, list) else []


def collect_okx_funding_history(
    target: CollectionTarget,
    *,
    output_root: Path,
    start_ms: int | None = None,
    end_ms: int | None = None,
    request_delay_sec: float = 0.15,
    max_pages: int | None = None,
) -> FundingCollectionResult | None:
    """OKX spot 심볼의 대응 SWAP funding history 를 수집한다."""
    if target.exchange != "okx":
        return None
    swap_inst_id = spot_symbol_to_okx_swap_inst_id(target.symbol)
    if swap_inst_id is None:
        return None
    end_ts = end_ms or now_ms()
    start_ts = start_ms or int((datetime.fromtimestamp(end_ts / 1000, timezone.utc) - timedelta(days=365 * target.years)).timestamp() * 1000)
    output_path = funding_output_path(output_root, target.exchange, target.symbol)
    exchange = create_okx_public_client()
    cursor: int | None = end_ts
    fetched_rows = 0
    written_rows = 0
    skipped_rows = 0
    page_count = 0
    existing_timestamps = load_existing_timestamps(output_path, key="funding_time_ms")

    while True:
        if max_pages is not None and page_count >= max_pages:
            break
        collected_at = datetime.now(timezone.utc).isoformat()
        raw_rows = fetch_okx_funding_page(
            exchange,
            swap_inst_id=swap_inst_id,
            cursor_after_ms=cursor,
        )
        page_count += 1
        if not raw_rows:
            break
        rows = parse_okx_funding_rows(
            symbol=target.symbol,
            swap_inst_id=swap_inst_id,
            rows=raw_rows,
            collected_at=collected_at,
        )
        bounded_rows = [
            row for row in rows if start_ts <= int(row["funding_time_ms"]) <= end_ts
        ]
        written, skipped = append_jsonl_unique(
            output_path,
            bounded_rows,
            key="funding_time_ms",
            existing_keys=existing_timestamps,
        )
        fetched_rows += len(rows)
        written_rows += written
        skipped_rows += skipped
        oldest_ts = min(int(row["funding_time_ms"]) for row in rows)
        if oldest_ts <= start_ts:
            break
        cursor = oldest_ts
        time.sleep(max(0.0, request_delay_sec))

    write_manifest(
        output_path.parent / "funding_manifest.json",
        {
            "exchange": target.exchange,
            "symbol": target.symbol,
            "swap_inst_id": swap_inst_id,
            "requested_start_ms": start_ts,
            "requested_end_ms": end_ts,
            "requested_start_utc": iso_utc(start_ts),
            "requested_end_utc": iso_utc(end_ts),
            "output_path": str(output_path),
            "fields": [
                "exchange",
                "symbol",
                "swap_inst_id",
                "funding_time_ms",
                "datetime_utc",
                "funding_rate",
                "realized_rate",
                "method",
                "formula_type",
                "inst_type",
                "source",
                "collected_at",
            ],
            "last_result": {
                "fetched_rows": fetched_rows,
                "written_rows": written_rows,
                "skipped_existing_rows": skipped_rows,
                "page_count": page_count,
            },
        },
    )
    return FundingCollectionResult(
        exchange="okx",
        symbol=target.symbol,
        swap_inst_id=swap_inst_id,
        output_path=str(output_path),
        fetched_rows=fetched_rows,
        written_rows=written_rows,
        skipped_existing_rows=skipped_rows,
        page_count=page_count,
    )


def collect_targets(
    targets: list[CollectionTarget],
    *,
    output_root: Path,
    start_ms: int | None,
    end_ms: int | None,
    request_delay_sec: float,
    max_pages: int | None,
    include_funding: bool,
) -> dict[str, Any]:
    """여러 target 을 순차 수집한다."""
    results: list[CollectionResult] = []
    funding_results: list[FundingCollectionResult] = []
    for target in targets:
        print(
            f"[수집] {target.exchange} {target.symbol} {target.timeframe} {target.years}년",
            flush=True,
        )
        result = collect_ohlcv_target(
            target,
            output_root=output_root,
            start_ms=start_ms,
            end_ms=end_ms,
            request_delay_sec=request_delay_sec,
            max_pages=max_pages,
        )
        results.append(result)
        print(
            f"  OHLCV 저장 {result.written_rows}개 "
            f"(기존 중복 {result.skipped_existing_rows}개, page {result.page_count})",
            flush=True,
        )
        if include_funding and target.exchange == "okx":
            funding_result = collect_okx_funding_history(
                target,
                output_root=output_root,
                start_ms=start_ms,
                end_ms=end_ms,
                request_delay_sec=request_delay_sec,
                max_pages=max_pages,
            )
            if funding_result is not None:
                funding_results.append(funding_result)
                print(
                    f"  Funding 저장 {funding_result.written_rows}개 "
                    f"(기존 중복 {funding_result.skipped_existing_rows}개, page {funding_result.page_count})",
                    flush=True,
                )
    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target_count": len(targets),
        "ohlcv": [asdict(result) for result in results],
        "funding": [asdict(result) for result in funding_results],
    }
    write_manifest(output_root / "collection_summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 만든다."""
    parser = argparse.ArgumentParser(description="장기 과거 시장 데이터 수집기")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="수집 대상과 예상 캔들 수를 출력")
    collect_parser = subparsers.add_parser("collect", help="수집 실행")
    launch_parser = subparsers.add_parser("launch", help="백그라운드 전체 수집 실행")
    status_parser = subparsers.add_parser("status", help="백그라운드 수집 상태 확인")
    for sub in (plan_parser, collect_parser, launch_parser):
        sub.add_argument("--exchange", choices=["okx", "upbit", "all"], default="all")
        sub.add_argument("--symbols", help="쉼표 구분 심볼 목록. 지정하면 모든 선택 거래소에 동일 적용")
        sub.add_argument("--timeframe", default=DEFAULT_TIMEFRAME)
        sub.add_argument("--core-years", type=int, default=3)
        sub.add_argument("--alt-years", type=int, default=1)
        sub.add_argument("--start", help="강제 시작일 YYYY-MM-DD 또는 ISO")
        sub.add_argument("--end", help="강제 종료일 YYYY-MM-DD 또는 ISO")
        sub.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
        sub.add_argument("--max-pages", type=int, help="테스트용 최대 페이지 수")
    collect_parser.add_argument("--request-delay-sec", type=float, default=0.15)
    collect_parser.add_argument("--skip-funding", action="store_true")
    launch_parser.add_argument("--request-delay-sec", type=float, default=0.2)
    launch_parser.add_argument("--skip-funding", action="store_true")
    launch_parser.add_argument("--log-path", default=str(DEFAULT_LOG_PATH))
    launch_parser.add_argument("--pid-path", default=str(DEFAULT_PID_PATH))
    status_parser.add_argument("--pid-path", default=str(DEFAULT_PID_PATH))

    return parser


def _parse_exchanges(raw: str) -> list[str]:
    """CLI exchange 값을 목록으로 바꾼다."""
    if raw == "all":
        return ["okx", "upbit"]
    return [raw]


def _parse_symbols(raw: str | None) -> list[str] | None:
    """쉼표 구분 심볼을 파싱한다."""
    if not raw:
        return None
    return [symbol.strip().upper() for symbol in raw.split(",") if symbol.strip()]


def _build_targets_from_args(args: argparse.Namespace) -> list[CollectionTarget]:
    """CLI args 에서 수집 target 을 만든다."""
    load_project_env()
    return build_default_targets(
        exchanges=_parse_exchanges(args.exchange),
        timeframe=args.timeframe,
        core_years=args.core_years,
        alt_years=args.alt_years,
        symbols=_parse_symbols(args.symbols),
    )


def print_plan(args: argparse.Namespace) -> int:
    """수집 계획을 출력한다."""
    targets = _build_targets_from_args(args)
    timeframe_ms = timeframe_to_ms(args.timeframe)
    end_ms = parse_date_to_ms(args.end, now_ms())
    output_root = Path(args.output_root)
    print("장기 과거 시장 데이터 수집 계획")
    for target in targets:
        start_ms = parse_date_to_ms(
            args.start,
            int((datetime.fromtimestamp(end_ms / 1000, timezone.utc) - timedelta(days=365 * target.years)).timestamp() * 1000),
        )
        expected_candles = max(0, int((end_ms - start_ms) / timeframe_ms))
        print(
            f"- {target.exchange} {target.symbol} {target.timeframe}: "
            f"{iso_utc(start_ms)} ~ {iso_utc(end_ms)} | "
            f"예상 {expected_candles:,} candles | "
            f"{ohlcv_output_path(output_root, target)}"
        )
    print("수집 OHLCV 필드: timestamp_ms, open, high, low, close, volume, volume_base, quote_volume, source")
    print("OKX 추가 필드: okx_vol_ccy, okx_vol_ccy_quote, confirm")
    print("업비트 추가 필드: candle_date_time_utc, candle_date_time_kst")
    print("OKX funding 필드: funding_time_ms, funding_rate, realized_rate, method, formula_type")
    print("과거 호가 스냅샷은 공개 API로 장기 소급 수집하지 않고 live snapshot 누적분을 사용합니다.")
    return 0


def run_collect(args: argparse.Namespace) -> int:
    """수집을 실행한다."""
    targets = _build_targets_from_args(args)
    end_default = now_ms()
    end_ms = parse_date_to_ms(args.end, end_default)
    start_ms = parse_date_to_ms(args.start, 0) if args.start else None
    summary = collect_targets(
        targets,
        output_root=Path(args.output_root),
        start_ms=start_ms,
        end_ms=end_ms,
        request_delay_sec=args.request_delay_sec,
        max_pages=args.max_pages,
        include_funding=not args.skip_funding,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0


def build_collect_argv(args: argparse.Namespace) -> list[str]:
    """launch args 를 collect 서브커맨드 실행 인자로 변환한다."""
    argv = [
        sys.executable,
        str(Path(__file__).resolve()),
        "collect",
        "--exchange",
        args.exchange,
        "--timeframe",
        args.timeframe,
        "--core-years",
        str(args.core_years),
        "--alt-years",
        str(args.alt_years),
        "--output-root",
        args.output_root,
        "--request-delay-sec",
        str(args.request_delay_sec),
    ]
    if args.symbols:
        argv.extend(["--symbols", args.symbols])
    if args.start:
        argv.extend(["--start", args.start])
    if args.end:
        argv.extend(["--end", args.end])
    if args.max_pages is not None:
        argv.extend(["--max-pages", str(args.max_pages)])
    if args.skip_funding:
        argv.append("--skip-funding")
    return argv


def run_launch(args: argparse.Namespace) -> int:
    """장기 수집을 백그라운드 프로세스로 실행한다."""
    pid_path = Path(args.pid_path)
    existing_pid = read_pid(pid_path)
    if existing_pid is not None and is_pid_alive(existing_pid):
        print(f"장기 과거 데이터 수집이 이미 실행 중입니다. PID {existing_pid}")
        return 0

    if existing_pid is not None:
        try:
            pid_path.unlink()
        except FileNotFoundError:
            pass

    log_path = Path(args.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            build_collect_argv(args),
            cwd=str(ROOT),
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
        )
    write_pid(pid_path, process.pid)
    print(
        json.dumps(
            {
                "status": "started",
                "pid": process.pid,
                "pid_path": str(pid_path),
                "log_path": str(log_path),
                "output_root": args.output_root,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def run_status(args: argparse.Namespace) -> int:
    """백그라운드 장기 수집 상태를 출력한다."""
    pid_path = Path(args.pid_path)
    pid = read_pid(pid_path)
    if pid is None:
        print("장기 과거 데이터 수집 PID 파일이 없습니다.")
        return 1
    if is_pid_alive(pid):
        print(f"장기 과거 데이터 수집 실행 중: PID {pid}")
        return 0
    print(f"장기 과거 데이터 수집 PID {pid} 는 종료되었습니다.")
    try:
        pid_path.unlink()
    except FileNotFoundError:
        pass
    return 1


def main() -> int:
    """CLI 진입점."""
    args = build_parser().parse_args()
    if args.command == "plan":
        return print_plan(args)
    if args.command == "collect":
        return run_collect(args)
    if args.command == "launch":
        return run_launch(args)
    if args.command == "status":
        return run_status(args)
    raise ValueError(f"지원하지 않는 명령입니다: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
