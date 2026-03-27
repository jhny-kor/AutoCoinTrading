"""
수정 요약
- 혼합 청산 세트를 위해 알트 리플레이도 심볼별 순익 보호 익절 기준 map 을 읽도록 확장
- 로컬 OHLCV 파일과 공개 거래소 시세를 이용해 전략을 오프라인으로 재생하는 백테스트/리플레이 CLI 를 추가
- 알트 MA 전략과 BTC EMA 전략을 공통 인터페이스로 요약/거래 로그까지 저장하도록 구성
- 결과를 reports/backtests 아래에 summary.json, trades.jsonl, equity_curve.jsonl 로 남기도록 추가
- fetch 서브커맨드로 공개 OHLCV 를 저장해 리플레이 입력 데이터를 준비할 수 있도록 확장

백테스트/리플레이 도구

- 목적: 실거래 전에 전략을 로컬 데이터로 다시 재생해 기대 동작을 검증한다.
- 입력: CSV 또는 JSONL 형식의 OHLCV 파일
- 출력: 요약 JSON, 체결 JSONL, 자산곡선 JSONL
- 범위: 알트 MA 전략, BTC EMA 전략
"""

from __future__ import annotations

import argparse
import csv
import json
from bisect import bisect_right
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis_log_collector import (
    create_okx_public_client,
    create_upbit_public_client,
    fetch_okx_ohlcv,
    fetch_upbit_ohlcv,
)
from btc_trend_settings import load_btc_trend_settings
from strategy_settings import load_strategy_settings


DEFAULT_OKX_FEE_RATE_PCT = 0.10
DEFAULT_UPBIT_FEE_RATE_PCT = 0.05
DEFAULT_OKX_MIN_BUY_ORDER_VALUE = 1.0
DEFAULT_UPBIT_MIN_BUY_ORDER_VALUE = 5000.0
DEFAULT_OKX_MAX_DAILY_LOSS_QUOTE = 5.0
DEFAULT_UPBIT_MAX_DAILY_LOSS_QUOTE = 5000.0
DEFAULT_RISK_PER_TRADE = 0.05


@dataclass(frozen=True)
class Candle:
    """백테스트용 OHLCV 캔들."""

    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class TradeRecord:
    """백테스트 체결 1건."""

    strategy_type: str
    symbol: str
    side: str
    reason: str
    timestamp_ms: int
    recorded_at: str
    price: float
    amount: float
    order_value_quote: float
    fee_quote: float
    realized_pnl_quote: float | None
    realized_pnl_pct: float | None
    net_realized_pnl_quote: float | None
    net_realized_pnl_pct: float | None
    cash_after: float
    position_amount_after: float
    average_entry_price_after: float | None
    entry_count_after: int
    extra: dict[str, Any]


@dataclass(frozen=True)
class EquityPoint:
    """자산곡선 1포인트."""

    timestamp_ms: int
    equity_quote: float
    cash_quote: float
    position_amount: float
    close: float


def parse_bool(raw: str | None, default: bool = False) -> bool:
    """문자열 불리언 값을 파싱한다."""
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_timeframe_to_minutes(timeframe: str) -> int:
    """1m, 5m, 1h 같은 문자열을 분 단위로 바꾼다."""
    raw = timeframe.strip().lower()
    if raw.endswith("m"):
        return int(raw[:-1])
    if raw.endswith("h"):
        return int(raw[:-1]) * 60
    if raw.endswith("d"):
        return int(raw[:-1]) * 60 * 24
    raise ValueError(f"지원하지 않는 타임프레임입니다: {timeframe}")


def _safe_float(value: Any) -> float | None:
    """숫자 후보를 float 로 안전하게 변환한다."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    """정수 후보를 int 로 안전하게 변환한다."""
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def calc_sma(values: list[float], period: int) -> float:
    """단순 이동평균을 계산한다."""
    if len(values) < period:
        raise ValueError("SMA 계산에 필요한 데이터가 부족합니다.")
    window = values[-period:]
    return sum(window) / len(window)


def calc_ema_series(values: list[float], period: int) -> list[float]:
    """EMA 시리즈를 계산한다."""
    if len(values) < period:
        raise ValueError("EMA 계산에 필요한 데이터가 부족합니다.")

    multiplier = 2 / (period + 1)
    ema_values = [sum(values[:period]) / period]
    for value in values[period:]:
        ema_values.append((value - ema_values[-1]) * multiplier + ema_values[-1])
    return ema_values


def detect_sma_crossover(closes: list[float], period: int) -> tuple[bool, bool, float, float, float, float]:
    """SMA 상향/하향 돌파를 계산한다."""
    if len(closes) < period + 1:
        raise ValueError("SMA 돌파 계산에 필요한 데이터가 부족합니다.")

    prev_closes = closes[:-1]
    prev_close = prev_closes[-1]
    last_close = closes[-1]
    prev_ma = calc_sma(prev_closes, period)
    last_ma = calc_sma(closes, period)
    bullish = prev_close < prev_ma and last_close > last_ma
    bearish = prev_close > prev_ma and last_close < last_ma
    return bullish, bearish, prev_close, prev_ma, last_close, last_ma


def detect_ema_crossover(closes: list[float], fast_period: int, slow_period: int) -> tuple[bool, bool, float, float, float, float]:
    """EMA 상향/하향 돌파를 계산한다."""
    if len(closes) < slow_period + 2:
        raise ValueError("EMA 돌파 계산에 필요한 데이터가 부족합니다.")

    fast_series = calc_ema_series(closes, fast_period)
    slow_series = calc_ema_series(closes, slow_period)
    series_len = min(len(fast_series), len(slow_series))
    fast_series = fast_series[-series_len:]
    slow_series = slow_series[-series_len:]

    prev_fast = fast_series[-2]
    prev_slow = slow_series[-2]
    last_fast = fast_series[-1]
    last_slow = slow_series[-1]
    bullish = prev_fast <= prev_slow and last_fast > last_slow
    bearish = prev_fast >= prev_slow and last_fast < last_slow
    return bullish, bearish, prev_fast, prev_slow, last_fast, last_slow


def calc_volume_ratio(candles: list[Candle], lookback: int) -> float | None:
    """직전 마감 봉 거래량이 그 이전 평균 거래량의 몇 배인지 계산한다."""
    if len(candles) < 3:
        return None
    completed = candles[:-1]
    if len(completed) < 2:
        return None
    recent = completed[-(lookback + 1):-1] if len(completed) >= lookback + 1 else completed[:-1]
    if not recent:
        return None
    avg_volume = sum(c.volume for c in recent) / len(recent)
    if avg_volume <= 0:
        return None
    return completed[-1].volume / avg_volume


def calc_avg_abs_change_pct(closes: list[float], lookback: int) -> float | None:
    """최근 절대 등락률 평균을 계산한다."""
    if len(closes) < 2:
        return None
    recent = closes[-(lookback + 1):] if len(closes) >= lookback + 1 else closes
    changes: list[float] = []
    for prev, curr in zip(recent, recent[1:]):
        if prev == 0:
            continue
        changes.append(abs((curr - prev) / prev) * 100)
    if not changes:
        return None
    return sum(changes) / len(changes)


def calc_atr(candles: list[Candle], period: int) -> float:
    """ATR 을 계산한다."""
    if len(candles) < period + 1:
        raise ValueError("ATR 계산에 필요한 데이터가 부족합니다.")

    trs: list[float] = []
    for prev, curr in zip(candles[:-1], candles[1:]):
        tr = max(
            curr.high - curr.low,
            abs(curr.high - prev.close),
            abs(curr.low - prev.close),
        )
        trs.append(tr)
    recent = trs[-period:]
    return sum(recent) / len(recent)


def get_recent_swing_low(candles: list[Candle], lookback: int) -> float:
    """최근 스윙 저점을 계산한다."""
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    return min(c.low for c in recent)


def get_recent_swing_high(candles: list[Candle], lookback: int) -> float:
    """최근 스윙 고점을 계산한다."""
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    return max(c.high for c in recent)


def build_exit_prices(
    *,
    entry_price: float,
    atr_value: float,
    recent_swing_low: float,
    recent_swing_high: float,
    min_take_profit_pct: float,
    settings,
) -> tuple[float, float]:
    """BTC 전략의 손절/익절 가격을 계산한다."""
    if settings.stop_mode == "swing":
        stop_price = recent_swing_low
    else:
        stop_price = entry_price - (atr_value * settings.stop_atr_multiple)

    if settings.take_profit_mode == "swing":
        take_profit_price = recent_swing_high
        if take_profit_price <= entry_price:
            take_profit_price = entry_price + (atr_value * settings.take_profit_atr_multiple)
    else:
        take_profit_price = entry_price + (atr_value * settings.take_profit_atr_multiple)

    fee_floor = entry_price * (1 + (min_take_profit_pct / 100))
    return stop_price, max(take_profit_price, fee_floor)


def load_candles(path: Path) -> list[Candle]:
    """CSV 또는 JSONL 파일에서 캔들 목록을 읽는다."""
    if not path.exists():
        raise FileNotFoundError(f"입력 파일이 없습니다: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return load_candles_from_csv(path)
    if suffix in {".jsonl", ".json"}:
        return load_candles_from_jsonl(path)
    raise ValueError(f"지원하지 않는 파일 형식입니다: {path.suffix}")


def load_candles_from_csv(path: Path) -> list[Candle]:
    """CSV 파일에서 캔들을 읽는다."""
    candles: list[Candle] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            timestamp_ms = _safe_int(row.get("timestamp_ms") or row.get("timestamp") or row.get("ts"))
            open_price = _safe_float(row.get("open"))
            high_price = _safe_float(row.get("high"))
            low_price = _safe_float(row.get("low"))
            close_price = _safe_float(row.get("close"))
            volume = _safe_float(row.get("volume"))
            if None in {timestamp_ms, open_price, high_price, low_price, close_price, volume}:
                continue
            candles.append(
                Candle(
                    timestamp_ms=timestamp_ms,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                )
            )
    return sorted(candles, key=lambda candle: candle.timestamp_ms)


def load_candles_from_jsonl(path: Path) -> list[Candle]:
    """JSONL 파일에서 캔들을 읽는다."""
    candles: list[Candle] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            candle = parse_candle_payload(payload)
            if candle is not None:
                candles.append(candle)
    return sorted(candles, key=lambda candle: candle.timestamp_ms)


def parse_candle_payload(payload: Any) -> Candle | None:
    """다양한 JSON 구조에서 캔들 1건을 해석한다."""
    if isinstance(payload, list) and len(payload) >= 6:
        timestamp_ms = _safe_int(payload[0])
        open_price = _safe_float(payload[1])
        high_price = _safe_float(payload[2])
        low_price = _safe_float(payload[3])
        close_price = _safe_float(payload[4])
        volume = _safe_float(payload[5])
    elif isinstance(payload, dict):
        timestamp_ms = _safe_int(
            payload.get("timestamp_ms")
            or payload.get("timestamp")
            or payload.get("ts")
            or payload.get("last_candle_ts")
        )
        open_price = _safe_float(payload.get("open"))
        high_price = _safe_float(payload.get("high"))
        low_price = _safe_float(payload.get("low"))
        close_price = _safe_float(payload.get("close"))
        volume = _safe_float(payload.get("volume"))
    else:
        return None

    if None in {timestamp_ms, open_price, high_price, low_price, close_price, volume}:
        return None
    return Candle(
        timestamp_ms=timestamp_ms,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
    )


def resample_candles(candles: list[Candle], source_timeframe: str, target_timeframe: str) -> list[Candle]:
    """낮은 주기 캔들을 높은 주기 캔들로 리샘플링한다."""
    if source_timeframe == target_timeframe:
        return list(candles)

    source_minutes = parse_timeframe_to_minutes(source_timeframe)
    target_minutes = parse_timeframe_to_minutes(target_timeframe)
    if target_minutes < source_minutes:
        raise ValueError("더 낮은 주기로는 리샘플링할 수 없습니다.")
    if target_minutes % source_minutes != 0:
        raise ValueError("입력 주기가 목표 주기를 정확히 나누지 못합니다.")

    bucket_ms = target_minutes * 60 * 1000
    grouped: dict[int, list[Candle]] = {}
    for candle in candles:
        bucket = (candle.timestamp_ms // bucket_ms) * bucket_ms
        grouped.setdefault(bucket, []).append(candle)

    resampled: list[Candle] = []
    for bucket, rows in sorted(grouped.items()):
        rows.sort(key=lambda candle: candle.timestamp_ms)
        resampled.append(
            Candle(
                timestamp_ms=bucket,
                open=rows[0].open,
                high=max(row.high for row in rows),
                low=min(row.low for row in rows),
                close=rows[-1].close,
                volume=sum(row.volume for row in rows),
            )
        )
    return resampled


def get_active_candles_by_time(
    candles: list[Candle],
    timestamps: list[int],
    current_timestamp_ms: int,
) -> list[Candle]:
    """현재 시각까지 확정된 상위 주기 캔들 목록을 반환한다."""
    end = bisect_right(timestamps, current_timestamp_ms)
    return candles[:end]


def format_iso(timestamp_ms: int) -> str:
    """밀리초 타임스탬프를 ISO 문자열로 바꾼다."""
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).isoformat()


def local_date_key(timestamp_ms: int) -> str:
    """밀리초 타임스탬프를 로컬 날짜 키로 바꾼다."""
    return datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc).astimezone().strftime("%Y-%m-%d")


def compute_max_drawdown(equity_curve: list[EquityPoint]) -> float:
    """자산곡선 기준 최대 낙폭 퍼센트를 계산한다."""
    peak = 0.0
    max_drawdown = 0.0
    for point in equity_curve:
        peak = max(peak, point.equity_quote)
        if peak <= 0:
            continue
        drawdown = ((peak - point.equity_quote) / peak) * 100
        max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown


def build_output_dir(base_dir: Path, strategy_type: str, symbol: str) -> Path:
    """리포트 디렉토리를 만든다."""
    slug = symbol.replace("/", "_").replace("-", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = base_dir / f"{timestamp}__{strategy_type}__{slug}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_json(path: Path, payload: Any) -> None:
    """JSON 파일을 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[Any]) -> None:
    """JSONL 파일을 저장한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            payload = asdict(row) if not isinstance(row, dict) else row
            f.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def resolve_default_fee_rate(exchange_name: str) -> float:
    """거래소별 기본 수수료율을 반환한다."""
    if exchange_name.lower() == "upbit":
        return DEFAULT_UPBIT_FEE_RATE_PCT
    return DEFAULT_OKX_FEE_RATE_PCT


def resolve_default_min_buy_order_value(exchange_name: str) -> float:
    """거래소별 기본 최소 매수 금액을 반환한다."""
    if exchange_name.lower() == "upbit":
        return DEFAULT_UPBIT_MIN_BUY_ORDER_VALUE
    return DEFAULT_OKX_MIN_BUY_ORDER_VALUE


def resolve_default_max_daily_loss(exchange_name: str) -> float:
    """거래소별 기본 일일 최대 손실 제한을 반환한다."""
    if exchange_name.lower() == "upbit":
        return DEFAULT_UPBIT_MAX_DAILY_LOSS_QUOTE
    return DEFAULT_OKX_MAX_DAILY_LOSS_QUOTE


def simulate_alt_strategy(
    *,
    candles: list[Candle],
    source_timeframe: str,
    symbol: str,
    exchange_name: str,
    initial_cash: float,
    fee_rate_pct: float,
    risk_per_trade: float,
    min_buy_order_value: float,
    max_daily_loss_quote: float,
) -> tuple[dict[str, Any], list[TradeRecord], list[EquityPoint]]:
    """공통 알트 MA 전략을 오프라인으로 재생한다."""
    strategy = load_strategy_settings(
        "UPBIT_MIN_BUY_ORDER_VALUE" if exchange_name.lower() == "upbit" else "OKX_MIN_BUY_ORDER_VALUE",
        min_buy_order_value,
    )
    higher_timeframe_candles = resample_candles(
        candles,
        source_timeframe=source_timeframe,
        target_timeframe=strategy.higher_timeframe,
    )
    higher_timeframe_timestamps = [candle.timestamp_ms for candle in higher_timeframe_candles]

    cash = initial_cash
    units = 0.0
    avg_entry_price: float | None = None
    entry_count = 0
    highest_price_since_entry: float | None = None
    lowest_price_since_entry: float | None = None
    partial_take_profit_done = False
    partial_stop_loss_done = False
    last_trade_ts = 0
    last_partial_take_profit_ts = 0
    daily_realized_pnl_quote = 0.0
    daily_pnl_date: str | None = None
    trade_records: list[TradeRecord] = []
    equity_curve: list[EquityPoint] = []

    min_required = max(strategy.volume_lookback + 3, strategy.volatility_lookback + 3, 25)
    for index in range(min_required, len(candles)):
        window = candles[: index + 1]
        current = window[-1]
        current_date = local_date_key(current.timestamp_ms)
        if current_date != daily_pnl_date:
            daily_pnl_date = current_date
            daily_realized_pnl_quote = 0.0

        closes = [candle.close for candle in window]
        bullish, bearish, prev_close, prev_ma, last_close, last_ma = detect_sma_crossover(closes, 20)
        gap_pct = abs(last_close - last_ma) / last_ma * 100 if last_ma else 0.0
        signal_is_strong = gap_pct >= strategy.get_crossover_gap_pct(symbol)
        trend_follow_entry = (
            strategy.enable_trend_follow_entry
            and last_close > last_ma
            and (
                not strategy.trend_follow_requires_prev_above_ma
                or prev_close > prev_ma
            )
            and (
                not strategy.trend_follow_requires_price_rising
                or last_close > prev_close
            )
        )
        entry_signal = bullish or trend_follow_entry
        volume_ratio = calc_volume_ratio(window, strategy.volume_lookback)
        avg_abs_change_pct = calc_avg_abs_change_pct(closes, strategy.volatility_lookback)

        active_higher_timeframe = get_active_candles_by_time(
            higher_timeframe_candles,
            higher_timeframe_timestamps,
            current.timestamp_ms,
        )
        htf_bullish: bool | None = None
        htf_bearish: bool | None = None
        if strategy.enable_higher_timeframe_filter and len(active_higher_timeframe) >= strategy.higher_timeframe_ma_period:
            htf_closes = [candle.close for candle in active_higher_timeframe]
            htf_last_close = htf_closes[-1]
            htf_last_ma = calc_sma(htf_closes, strategy.higher_timeframe_ma_period)
            htf_bullish = htf_last_close > htf_last_ma
            htf_bearish = htf_last_close < htf_last_ma

        position_quote_value = units * last_close
        has_position = units > 0 and position_quote_value >= min_buy_order_value * 0.5
        if has_position and avg_entry_price is not None:
            highest_price_since_entry = max(highest_price_since_entry or last_close, last_close)
            lowest_price_since_entry = min(lowest_price_since_entry or last_close, last_close)
        elif not has_position:
            highest_price_since_entry = None
            lowest_price_since_entry = None

        in_partial_tp_cooldown = (
            strategy.partial_take_profit_reentry_cooldown_sec > 0
            and (current.timestamp_ms - last_partial_take_profit_ts) / 1000
            < strategy.partial_take_profit_reentry_cooldown_sec
        )
        in_trade_cooldown = (
            strategy.min_trade_interval_sec > 0
            and (current.timestamp_ms - last_trade_ts) / 1000 < strategy.min_trade_interval_sec
        )

        daily_loss_limit_reached = daily_realized_pnl_quote <= -max_daily_loss_quote
        take_profit_pct = strategy.get_take_profit_pct(symbol)
        effective_min_take_profit_pct = max(take_profit_pct, fee_rate_pct * 2 * 1.1)
        stop_loss_pct = strategy.get_stop_loss_pct(symbol)
        fee_protect_min_net_pnl_pct = strategy.get_fee_protect_min_net_pnl_pct(symbol)

        volume_filter_passed = (
            True
            if not strategy.enable_volume_filter
            else volume_ratio is not None and volume_ratio >= strategy.get_min_volume_ratio(symbol)
        )
        volatility_filter_passed = (
            True
            if not strategy.enable_volatility_filter
            else (
                avg_abs_change_pct is not None
                and strategy.min_volatility_pct <= avg_abs_change_pct <= strategy.max_volatility_pct
            )
        )
        higher_timeframe_passed = (
            True
            if not strategy.enable_higher_timeframe_filter
            else htf_bullish is True
        )

        realized_on_this_bar = False

        if has_position and avg_entry_price is not None:
            pnl_pct = ((last_close - avg_entry_price) / avg_entry_price) * 100
            current_net_realized_pnl_pct = pnl_pct - (fee_rate_pct * 2)
            mfe_pct = (
                ((highest_price_since_entry - avg_entry_price) / avg_entry_price) * 100
                if highest_price_since_entry is not None
                else 0.0
            )

            stop_loss_triggered = pnl_pct <= -stop_loss_pct
            profit_protect_triggered = (
                strategy.enable_fee_protect_exit
                and bearish
                and current_net_realized_pnl_pct >= fee_protect_min_net_pnl_pct
                and not stop_loss_triggered
            )
            break_even_guard_triggered = (
                strategy.enable_break_even_guard
                and current_net_realized_pnl_pct > 0
                and mfe_pct >= strategy.get_break_even_guard_min_mfe_pct(symbol)
                and current_net_realized_pnl_pct <= strategy.get_break_even_guard_floor_net_pnl_pct(symbol)
                and not stop_loss_triggered
                and not profit_protect_triggered
            )
            normal_take_profit_triggered = bearish and pnl_pct >= effective_min_take_profit_pct

            exit_ratio = 0.0
            exit_reason = ""
            is_final_exit = True

            if stop_loss_triggered:
                if strategy.uses_partial_stop_loss(symbol) and not partial_stop_loss_done:
                    exit_ratio = strategy.partial_stop_loss_ratio
                    exit_reason = "partial_stop_loss"
                    is_final_exit = False
                else:
                    exit_ratio = 1.0
                    exit_reason = "stop_loss"
            elif profit_protect_triggered:
                exit_ratio = 1.0
                exit_reason = "profit_protect_take_profit"
            elif break_even_guard_triggered:
                exit_ratio = 1.0
                exit_reason = "break_even_guard_exit"
            elif normal_take_profit_triggered:
                if strategy.uses_partial_take_profit(symbol) and not partial_take_profit_done:
                    exit_ratio = strategy.partial_take_profit_ratio
                    exit_reason = "partial_take_profit"
                    is_final_exit = False
                else:
                    exit_ratio = 1.0
                    exit_reason = "take_profit"

            if exit_ratio > 0:
                amount = units * min(max(exit_ratio, 0.0), 1.0)
                if amount > 0:
                    proceeds = amount * last_close
                    sell_fee_quote = proceeds * (fee_rate_pct / 100.0)
                    realized_pnl_quote = (last_close - avg_entry_price) * amount
                    entry_fee_quote = (avg_entry_price * amount) * (fee_rate_pct / 100.0)
                    net_realized_pnl_quote = realized_pnl_quote - entry_fee_quote - sell_fee_quote
                    net_realized_pnl_pct = (
                        (net_realized_pnl_quote / (avg_entry_price * amount)) * 100
                        if avg_entry_price * amount > 0
                        else None
                    )
                    cash += proceeds - sell_fee_quote
                    units = max(0.0, units - amount)
                    daily_realized_pnl_quote += net_realized_pnl_quote
                    if units <= 1e-12:
                        units = 0.0
                        avg_entry_price = None
                        entry_count = 0
                        partial_take_profit_done = False
                        partial_stop_loss_done = False
                        highest_price_since_entry = None
                        lowest_price_since_entry = None
                        is_final_exit = True
                    if exit_reason == "partial_take_profit" and units > 0:
                        partial_take_profit_done = True
                        last_partial_take_profit_ts = current.timestamp_ms
                    if exit_reason == "partial_stop_loss" and units > 0:
                        partial_stop_loss_done = True
                    if exit_reason in {"stop_loss", "profit_protect_take_profit", "break_even_guard_exit", "take_profit"}:
                        last_trade_ts = current.timestamp_ms
                    trade_records.append(
                        TradeRecord(
                            strategy_type="alt",
                            symbol=symbol,
                            side="sell",
                            reason=exit_reason,
                            timestamp_ms=current.timestamp_ms,
                            recorded_at=format_iso(current.timestamp_ms),
                            price=last_close,
                            amount=amount,
                            order_value_quote=proceeds,
                            fee_quote=sell_fee_quote + entry_fee_quote,
                            realized_pnl_quote=realized_pnl_quote,
                            realized_pnl_pct=pnl_pct,
                            net_realized_pnl_quote=net_realized_pnl_quote,
                            net_realized_pnl_pct=net_realized_pnl_pct,
                            cash_after=cash,
                            position_amount_after=units,
                            average_entry_price_after=avg_entry_price,
                            entry_count_after=entry_count,
                            extra={
                                "is_final_exit": is_final_exit,
                                "daily_realized_pnl_quote_after": daily_realized_pnl_quote,
                                "mfe_pct": mfe_pct,
                                "current_net_realized_pnl_pct": current_net_realized_pnl_pct,
                            },
                        )
                    )
                    realized_on_this_bar = True

        position_ratio = strategy.get_position_ratio(symbol, risk_per_trade)
        requested_order_value = cash * position_ratio * strategy.buy_split_ratio
        can_average_down = (
            has_position
            and avg_entry_price is not None
            and last_close <= avg_entry_price * (1 - (strategy.averaging_down_gap_pct / 100))
        )
        entry_allowed = (
            entry_signal
            and signal_is_strong
            and volume_filter_passed
            and volatility_filter_passed
            and higher_timeframe_passed
            and not in_trade_cooldown
            and not in_partial_tp_cooldown
            and not daily_loss_limit_reached
            and requested_order_value >= min_buy_order_value
            and (
                not has_position
                or (
                    can_average_down
                    and entry_count < strategy.max_entry_count
                )
            )
            and not realized_on_this_bar
        )

        if entry_allowed:
            order_value = min(cash, requested_order_value)
            fee_quote = order_value * (fee_rate_pct / 100.0)
            net_order_value = order_value - fee_quote
            if net_order_value >= min_buy_order_value and last_close > 0:
                amount = net_order_value / last_close
                previous_cost = (avg_entry_price or 0.0) * units
                units += amount
                avg_entry_price = ((previous_cost + net_order_value) / units) if units > 0 else last_close
                cash -= order_value
                entry_count += 1
                highest_price_since_entry = last_close
                lowest_price_since_entry = last_close
                last_trade_ts = current.timestamp_ms
                trade_records.append(
                    TradeRecord(
                        strategy_type="alt",
                        symbol=symbol,
                        side="buy",
                        reason="entry" if not has_position else "average_down",
                        timestamp_ms=current.timestamp_ms,
                        recorded_at=format_iso(current.timestamp_ms),
                        price=last_close,
                        amount=amount,
                        order_value_quote=net_order_value,
                        fee_quote=fee_quote,
                        realized_pnl_quote=None,
                        realized_pnl_pct=None,
                        net_realized_pnl_quote=None,
                        net_realized_pnl_pct=None,
                        cash_after=cash,
                        position_amount_after=units,
                        average_entry_price_after=avg_entry_price,
                        entry_count_after=entry_count,
                        extra={
                            "signal_is_strong": signal_is_strong,
                            "gap_pct": gap_pct,
                            "volume_ratio": volume_ratio,
                            "avg_abs_change_pct": avg_abs_change_pct,
                        },
                    )
                )

        equity_curve.append(
            EquityPoint(
                timestamp_ms=current.timestamp_ms,
                equity_quote=cash + (units * last_close),
                cash_quote=cash,
                position_amount=units,
                close=last_close,
            )
        )

    sell_records = [record for record in trade_records if record.side == "sell"]
    winning_trades = [
        record
        for record in sell_records
        if (record.net_realized_pnl_quote or 0.0) > 0
    ]
    summary = {
        "strategy_type": "alt",
        "symbol": symbol,
        "exchange_name": exchange_name,
        "source_timeframe": source_timeframe,
        "strategy_version": strategy.version,
        "initial_cash_quote": initial_cash,
        "final_cash_quote": cash,
        "final_position_amount": units,
        "final_equity_quote": equity_curve[-1].equity_quote if equity_curve else initial_cash,
        "net_return_pct": (
            (((equity_curve[-1].equity_quote if equity_curve else initial_cash) - initial_cash) / initial_cash) * 100
            if initial_cash > 0
            else 0.0
        ),
        "trade_count": len(trade_records),
        "buy_count": len([record for record in trade_records if record.side == "buy"]),
        "sell_count": len(sell_records),
        "win_count": len(winning_trades),
        "win_rate_pct": (len(winning_trades) / len(sell_records) * 100) if sell_records else 0.0,
        "total_net_realized_pnl_quote": sum((record.net_realized_pnl_quote or 0.0) for record in sell_records),
        "max_drawdown_pct": compute_max_drawdown(equity_curve),
    }
    return summary, trade_records, equity_curve


def simulate_btc_strategy(
    *,
    candles: list[Candle],
    source_timeframe: str,
    symbol: str,
    exchange_name: str,
    initial_cash: float,
    fee_rate_pct: float,
    risk_per_trade: float,
    min_buy_order_value: float,
    max_daily_loss_quote: float,
) -> tuple[dict[str, Any], list[TradeRecord], list[EquityPoint]]:
    """BTC EMA 전략을 오프라인으로 재생한다."""
    settings = load_btc_trend_settings()
    base_candles = resample_candles(candles, source_timeframe=source_timeframe, target_timeframe=settings.timeframe)
    confirm_candles = resample_candles(
        candles,
        source_timeframe=source_timeframe,
        target_timeframe=settings.confirm_timeframe,
    )
    confirm_timestamps = [candle.timestamp_ms for candle in confirm_candles]

    cash = initial_cash
    units = 0.0
    entry_price: float | None = None
    partial_take_profit_done = False
    add_on_count = 0
    highest_price_since_entry: float | None = None
    lowest_price_since_entry: float | None = None
    trailing_armed = False
    last_trade_ts = 0
    last_stop_loss_ts = 0
    last_profit_exit_ts = 0
    daily_realized_pnl_quote = 0.0
    daily_pnl_date: str | None = None
    trade_records: list[TradeRecord] = []
    equity_curve: list[EquityPoint] = []

    min_required = max(
        settings.slow_ema_period + 5,
        settings.atr_period + 5,
        settings.volume_lookback + 5,
        settings.swing_lookback + 5,
    )
    for index in range(min_required, len(base_candles)):
        window = base_candles[: index + 1]
        current = window[-1]
        current_date = local_date_key(current.timestamp_ms)
        if current_date != daily_pnl_date:
            daily_pnl_date = current_date
            daily_realized_pnl_quote = 0.0

        closes = [candle.close for candle in window]
        bullish, bearish, _, _, fast_ema, slow_ema = detect_ema_crossover(
            closes,
            settings.fast_ema_period,
            settings.slow_ema_period,
        )
        last_close = closes[-1]
        ema_spread_pct = abs(fast_ema - slow_ema) / slow_ema * 100 if slow_ema else 0.0
        volume_ratio = calc_volume_ratio(window, settings.volume_lookback)
        atr_value = calc_atr(window, settings.atr_period)
        atr_pct = (atr_value / last_close) * 100 if last_close > 0 else 0.0
        confirm_window = get_active_candles_by_time(confirm_candles, confirm_timestamps, current.timestamp_ms)
        confirm_filter_passed = True
        if settings.enable_confirm_timeframe_filter:
            confirm_filter_passed = False
            if len(confirm_window) >= settings.confirm_ema_period:
                confirm_closes = [candle.close for candle in confirm_window]
                confirm_last_close = confirm_closes[-1]
                confirm_last_ema = calc_ema_series(confirm_closes, settings.confirm_ema_period)[-1]
                confirm_filter_passed = confirm_last_close > confirm_last_ema

        ema_aligned = fast_ema > slow_ema
        price_above_fast = last_close > fast_ema
        trend_follow_entry = (
            settings.enable_trend_follow_entry
            and ema_aligned
            and (
                not settings.trend_follow_requires_price_above_fast
                or price_above_fast
            )
        )
        entry_signal = bullish or trend_follow_entry
        volume_filter_passed = volume_ratio is not None and volume_ratio >= settings.get_min_volume_ratio(symbol)
        atr_filter_passed = settings.get_min_atr_pct(symbol) <= atr_pct <= settings.max_atr_pct

        has_position = units > 0
        if has_position and entry_price is not None:
            highest_price_since_entry = max(highest_price_since_entry or last_close, last_close)
            lowest_price_since_entry = min(lowest_price_since_entry or last_close, last_close)
        elif not has_position:
            highest_price_since_entry = None
            lowest_price_since_entry = None
            trailing_armed = False
            partial_take_profit_done = False
            add_on_count = 0

        base_cooldown_remaining = settings.min_trade_interval_sec - ((current.timestamp_ms - last_trade_ts) / 1000)
        stop_loss_cooldown_remaining = settings.stop_loss_reentry_cooldown_sec - ((current.timestamp_ms - last_stop_loss_ts) / 1000)
        profit_exit_cooldown_remaining = settings.profit_exit_reentry_cooldown_sec - ((current.timestamp_ms - last_profit_exit_ts) / 1000)
        in_cooldown = max(base_cooldown_remaining, stop_loss_cooldown_remaining, profit_exit_cooldown_remaining) > 0
        daily_loss_limit_reached = daily_realized_pnl_quote <= -max_daily_loss_quote

        if has_position and entry_price is not None:
            pnl_pct = ((last_close - entry_price) / entry_price) * 100
            current_net_pnl_pct = pnl_pct - (fee_rate_pct * 2)
            recent_swing_low = get_recent_swing_low(window[:-1], settings.swing_lookback)
            recent_swing_high = get_recent_swing_high(window[:-1], settings.swing_lookback)
            fee_floor_take_profit_pct = fee_rate_pct * 2 * 1.05
            stop_price, take_profit_price = build_exit_prices(
                entry_price=entry_price,
                atr_value=atr_value,
                recent_swing_low=recent_swing_low,
                recent_swing_high=recent_swing_high,
                min_take_profit_pct=fee_floor_take_profit_pct,
                settings=settings,
            )
            stop_triggered = last_close <= stop_price
            profit_protect_triggered = (
                settings.enable_fee_protect_exit
                and bearish
                and current_net_pnl_pct >= settings.fee_protect_min_net_pnl_pct
                and not stop_triggered
            )
            if not trailing_armed and last_close >= take_profit_price:
                trailing_armed = True
            trailing_drawdown_pct = (
                ((highest_price_since_entry - last_close) / highest_price_since_entry) * 100
                if trailing_armed and highest_price_since_entry
                else 0.0
            )
            trailing_triggered = trailing_armed and trailing_drawdown_pct >= settings.trailing_drawdown_pct and not stop_triggered
            trend_exit_triggered = (
                settings.exit_on_bearish_cross
                and bearish
                and not trailing_armed
                and not stop_triggered
                and not profit_protect_triggered
            )

            sell_ratio = 0.0
            exit_reason = ""
            if stop_triggered:
                sell_ratio = 1.0
                exit_reason = "stop_loss"
            elif profit_protect_triggered:
                sell_ratio = 1.0
                exit_reason = "profit_protect_take_profit"
            elif trailing_triggered:
                sell_ratio = 1.0
                exit_reason = "trailing_take_profit"
            elif not partial_take_profit_done and settings.enable_partial_take_profit and last_close >= take_profit_price:
                sell_ratio = settings.partial_take_profit_ratio
                exit_reason = "partial_take_profit"
            elif trend_exit_triggered:
                sell_ratio = 1.0
                exit_reason = "trend_exit"

            if sell_ratio > 0:
                amount = units * min(max(sell_ratio, 0.0), 1.0)
                proceeds = amount * last_close
                sell_fee_quote = proceeds * (fee_rate_pct / 100.0)
                realized_pnl_quote = (last_close - entry_price) * amount
                entry_fee_quote = (entry_price * amount) * (fee_rate_pct / 100.0)
                net_realized_pnl_quote = realized_pnl_quote - entry_fee_quote - sell_fee_quote
                net_realized_pnl_pct = (
                    (net_realized_pnl_quote / (entry_price * amount)) * 100
                    if entry_price * amount > 0
                    else None
                )
                cash += proceeds - sell_fee_quote
                units = max(0.0, units - amount)
                daily_realized_pnl_quote += net_realized_pnl_quote
                if exit_reason == "stop_loss":
                    last_stop_loss_ts = current.timestamp_ms
                if exit_reason in {"profit_protect_take_profit", "trailing_take_profit", "trend_exit"}:
                    last_profit_exit_ts = current.timestamp_ms
                if exit_reason == "partial_take_profit" and units > 0:
                    partial_take_profit_done = True
                if units <= 1e-12:
                    units = 0.0
                    entry_price = None
                    trailing_armed = False
                    partial_take_profit_done = False
                    add_on_count = 0
                trade_records.append(
                    TradeRecord(
                        strategy_type="btc",
                        symbol=symbol,
                        side="sell",
                        reason=exit_reason,
                        timestamp_ms=current.timestamp_ms,
                        recorded_at=format_iso(current.timestamp_ms),
                        price=last_close,
                        amount=amount,
                        order_value_quote=proceeds,
                        fee_quote=sell_fee_quote + entry_fee_quote,
                        realized_pnl_quote=realized_pnl_quote,
                        realized_pnl_pct=pnl_pct,
                        net_realized_pnl_quote=net_realized_pnl_quote,
                        net_realized_pnl_pct=net_realized_pnl_pct,
                        cash_after=cash,
                        position_amount_after=units,
                        average_entry_price_after=entry_price,
                        entry_count_after=1 + add_on_count,
                        extra={
                            "trailing_armed": trailing_armed,
                            "atr_pct": atr_pct,
                            "ema_spread_pct": ema_spread_pct,
                        },
                    )
                )
                last_trade_ts = current.timestamp_ms

        position_ratio = settings.get_position_ratio(symbol)
        requested_order_value = cash * risk_per_trade * position_ratio
        requested_add_on_order_value = cash * risk_per_trade * settings.pyramid_position_ratio
        entry_allowed = (
            entry_signal
            and ema_spread_pct >= settings.get_min_ema_spread_pct(symbol)
            and volume_filter_passed
            and atr_filter_passed
            and confirm_filter_passed
            and not in_cooldown
            and not daily_loss_limit_reached
            and requested_order_value >= min_buy_order_value
            and not has_position
        )
        add_on_allowed = (
            has_position
            and entry_price is not None
            and settings.enable_pyramid_add_on
            and add_on_count < settings.pyramid_max_add_ons
            and ((last_close - entry_price) / entry_price) * 100 >= settings.pyramid_trigger_profit_pct
            and entry_signal
            and requested_add_on_order_value >= min_buy_order_value
        )

        if entry_allowed or add_on_allowed:
            reason = "entry" if entry_allowed else "pyramid_add_on"
            order_value = requested_order_value if entry_allowed else requested_add_on_order_value
            order_value = min(cash, order_value)
            fee_quote = order_value * (fee_rate_pct / 100.0)
            net_order_value = order_value - fee_quote
            if net_order_value >= min_buy_order_value and last_close > 0:
                amount = net_order_value / last_close
                previous_cost = (entry_price or 0.0) * units
                units += amount
                entry_price = ((previous_cost + net_order_value) / units) if units > 0 else last_close
                cash -= order_value
                last_trade_ts = current.timestamp_ms
                highest_price_since_entry = last_close
                lowest_price_since_entry = last_close
                if reason == "pyramid_add_on":
                    add_on_count += 1
                trade_records.append(
                    TradeRecord(
                        strategy_type="btc",
                        symbol=symbol,
                        side="buy",
                        reason=reason,
                        timestamp_ms=current.timestamp_ms,
                        recorded_at=format_iso(current.timestamp_ms),
                        price=last_close,
                        amount=amount,
                        order_value_quote=net_order_value,
                        fee_quote=fee_quote,
                        realized_pnl_quote=None,
                        realized_pnl_pct=None,
                        net_realized_pnl_quote=None,
                        net_realized_pnl_pct=None,
                        cash_after=cash,
                        position_amount_after=units,
                        average_entry_price_after=entry_price,
                        entry_count_after=1 + add_on_count,
                        extra={
                            "ema_spread_pct": ema_spread_pct,
                            "atr_pct": atr_pct,
                            "volume_ratio": volume_ratio,
                        },
                    )
                )

        equity_curve.append(
            EquityPoint(
                timestamp_ms=current.timestamp_ms,
                equity_quote=cash + (units * last_close),
                cash_quote=cash,
                position_amount=units,
                close=last_close,
            )
        )

    sell_records = [record for record in trade_records if record.side == "sell"]
    winning_trades = [
        record for record in sell_records if (record.net_realized_pnl_quote or 0.0) > 0
    ]
    summary = {
        "strategy_type": "btc",
        "symbol": symbol,
        "exchange_name": exchange_name,
        "source_timeframe": source_timeframe,
        "strategy_version": settings.version,
        "initial_cash_quote": initial_cash,
        "final_cash_quote": cash,
        "final_position_amount": units,
        "final_equity_quote": equity_curve[-1].equity_quote if equity_curve else initial_cash,
        "net_return_pct": (
            (((equity_curve[-1].equity_quote if equity_curve else initial_cash) - initial_cash) / initial_cash) * 100
            if initial_cash > 0
            else 0.0
        ),
        "trade_count": len(trade_records),
        "buy_count": len([record for record in trade_records if record.side == "buy"]),
        "sell_count": len(sell_records),
        "win_count": len(winning_trades),
        "win_rate_pct": (len(winning_trades) / len(sell_records) * 100) if sell_records else 0.0,
        "total_net_realized_pnl_quote": sum((record.net_realized_pnl_quote or 0.0) for record in sell_records),
        "max_drawdown_pct": compute_max_drawdown(equity_curve),
    }
    return summary, trade_records, equity_curve


def save_fetch_output(path: Path, candles: list[list[float]]) -> None:
    """공개 OHLCV 조회 결과를 파일로 저장한다."""
    suffix = path.suffix.lower()
    path.parent.mkdir(parents=True, exist_ok=True)
    if suffix == ".csv":
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_ms", "open", "high", "low", "close", "volume"])
            for row in candles:
                writer.writerow(row)
        return
    with path.open("w", encoding="utf-8") as f:
        for row in candles:
            payload = {
                "timestamp_ms": row[0],
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5],
            }
            f.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def run_fetch_command(args: argparse.Namespace) -> int:
    """공개 거래소에서 OHLCV 를 가져와 파일로 저장한다."""
    exchange_name = args.exchange.lower()
    if exchange_name == "okx":
        exchange = create_okx_public_client()
        rows = fetch_okx_ohlcv(exchange, args.symbol, timeframe=args.timeframe, limit=args.limit)
    elif exchange_name == "upbit":
        exchange = create_upbit_public_client()
        rows = fetch_upbit_ohlcv(exchange, args.symbol, timeframe=args.timeframe, limit=args.limit)
    else:
        raise ValueError(f"지원하지 않는 거래소입니다: {args.exchange}")
    save_fetch_output(Path(args.output), rows)
    print(f"저장 완료: {args.output} ({len(rows)}개 캔들)")
    return 0


def run_backtest_command(args: argparse.Namespace) -> int:
    """리플레이/백테스트를 실행하고 결과 파일을 저장한다."""
    input_path = Path(args.input)
    candles = load_candles(input_path)
    if len(candles) < 50:
        raise ValueError("백테스트에 필요한 캔들이 너무 적습니다. 최소 50개 이상 준비하세요.")

    fee_rate_pct = args.fee_rate_pct
    if fee_rate_pct is None:
        fee_rate_pct = resolve_default_fee_rate(args.exchange)
    min_buy_order_value = args.min_buy_order_value
    if min_buy_order_value is None:
        min_buy_order_value = resolve_default_min_buy_order_value(args.exchange)
    max_daily_loss_quote = args.max_daily_loss_quote
    if max_daily_loss_quote is None:
        max_daily_loss_quote = resolve_default_max_daily_loss(args.exchange)

    if args.strategy == "alt":
        summary, trades, equity_curve = simulate_alt_strategy(
            candles=candles,
            source_timeframe=args.timeframe,
            symbol=args.symbol,
            exchange_name=args.exchange,
            initial_cash=args.initial_cash,
            fee_rate_pct=fee_rate_pct,
            risk_per_trade=args.risk_per_trade,
            min_buy_order_value=min_buy_order_value,
            max_daily_loss_quote=max_daily_loss_quote,
        )
    else:
        summary, trades, equity_curve = simulate_btc_strategy(
            candles=candles,
            source_timeframe=args.timeframe,
            symbol=args.symbol,
            exchange_name=args.exchange,
            initial_cash=args.initial_cash,
            fee_rate_pct=fee_rate_pct,
            risk_per_trade=args.risk_per_trade,
            min_buy_order_value=min_buy_order_value,
            max_daily_loss_quote=max_daily_loss_quote,
        )

    output_dir = build_output_dir(Path(args.output_dir), args.strategy, args.symbol)
    write_json(output_dir / "summary.json", summary)
    write_jsonl(output_dir / "trades.jsonl", trades)
    write_jsonl(output_dir / "equity_curve.jsonl", equity_curve)

    print(f"리플레이 완료: {output_dir}")
    print(
        f"전략={summary['strategy_type']} "
        f"수익률={summary['net_return_pct']:.2f}% "
        f"거래수={summary['trade_count']} "
        f"최대낙폭={summary['max_drawdown_pct']:.2f}%"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 만든다."""
    parser = argparse.ArgumentParser(description="전략 백테스트/리플레이 도구")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="공개 OHLCV 를 파일로 저장")
    fetch_parser.add_argument("--exchange", required=True, choices=["okx", "upbit"])
    fetch_parser.add_argument("--symbol", required=True)
    fetch_parser.add_argument("--timeframe", required=True)
    fetch_parser.add_argument("--limit", type=int, default=1000)
    fetch_parser.add_argument("--output", required=True)

    run_parser = subparsers.add_parser("run", help="로컬 OHLCV 파일로 전략을 재생")
    run_parser.add_argument("--strategy", required=True, choices=["alt", "btc"])
    run_parser.add_argument("--exchange", required=True, choices=["okx", "upbit"])
    run_parser.add_argument("--symbol", required=True)
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--timeframe", required=True, help="입력 파일 캔들 주기")
    run_parser.add_argument("--initial-cash", type=float, default=1_000_000.0)
    run_parser.add_argument("--fee-rate-pct", type=float, default=None)
    run_parser.add_argument("--risk-per-trade", type=float, default=DEFAULT_RISK_PER_TRADE)
    run_parser.add_argument("--min-buy-order-value", type=float, default=None)
    run_parser.add_argument("--max-daily-loss-quote", type=float, default=None)
    run_parser.add_argument("--output-dir", default="reports/backtests")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "fetch":
        return run_fetch_command(args)
    if args.command == "run":
        return run_backtest_command(args)
    parser.error("지원하지 않는 명령입니다.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
