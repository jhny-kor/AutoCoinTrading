"""
수정 요약
- 분석 수집기 메인 루프 예외도 텔레그램으로 즉시 알리도록 보강
- 분석용 JSONL 에 거래량 배수, 변동성, RSI, 최근 범위 위치 같은 추가 지표를 함께 저장하도록 확장
- 상위 타임프레임 종가/이동평균/이격도와 공개 기준 필터 통과 여부를 함께 저장하도록 확장
- 호가창 최우선 매수/매도호가와 스프레드, 잔량 불균형을 저장하도록 확장
- 전략 설정과 연동해 심볼별 이격도 기준, 익절률, 손절률도 함께 기록하도록 정리
- 공개 데이터 기준의 매수 준비 여부와 스킵 사유를 구조화해서 남기도록 개선
- 거래량 배수 계산을 형성 중인 현재 봉 대신 직전 마감 봉 기준으로 바꿔 분석 왜곡을 줄이도록 조정
- 거래량 기준 봉과 데이터 시차 같은 분석 보조 필드도 함께 남기도록 확장
- 운영 대상 심볼 목록을 알트 공통 설정과 자동 연동하도록 재구조화

분석용 시장 데이터 수집기

- 거래는 하지 않고 시세/이동평균/신호 상태만 구조화 로그로 저장한다.
- 결과는 analysis_logs 폴더 아래에 심볼별 JSONL 파일로 누적된다.
- 나중에 신호 빈도, 이격도 분포, 전략 적합성 분석에 활용할 수 있다.

사용 예시
- .venv/bin/python analysis_log_collector.py
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import ccxt
from dotenv import load_dotenv

from log_path_utils import dated_path
from strategy_settings import load_managed_symbols, load_strategy_settings
from telegram_notifier import load_telegram_notifier


def calc_sma(prices: list[float], period: int) -> float:
    """단순 이동평균을 계산한다."""
    if len(prices) < period:
        raise ValueError("가격 데이터가 이동평균 기간보다 적습니다.")
    window = prices[-period:]
    return sum(window) / len(window)


def parse_bool(raw: str | None, default: bool = False) -> bool:
    """문자열 불리언 값을 파싱한다."""
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def detect_crossover(
    closes: list[float], period: int
) -> tuple[bool, bool, float, float, float, float]:
    """이동평균 돌파 여부를 계산한다."""
    if len(closes) < period + 1:
        raise ValueError("이동평균 돌파를 계산하기 위한 캔들 수가 부족합니다.")

    prev_closes = closes[:-1]
    last_close = closes[-1]
    prev_ma = calc_sma(prev_closes, period)
    last_ma = calc_sma(closes, period)
    prev_close = prev_closes[-1]

    bullish = prev_close < prev_ma and last_close > last_ma
    bearish = prev_close > prev_ma and last_close < last_ma

    return bullish, bearish, prev_close, prev_ma, last_close, last_ma


def calc_volume_ratio(ohlcv: list[list[float]], lookback: int) -> float | None:
    """직전 마감 봉 거래량이 그 이전 평균 거래량의 몇 배인지 계산한다."""
    if len(ohlcv) < 3:
        return None
    completed = ohlcv[:-1]
    if len(completed) < 2:
        return None
    recent = (
        completed[-(lookback + 1):-1]
        if len(completed) >= lookback + 1
        else completed[:-1]
    )
    if not recent:
        return None
    avg_volume = sum(row[5] for row in recent) / len(recent)
    current_volume = completed[-1][5]
    if avg_volume <= 0:
        return None
    return current_volume / avg_volume


def calc_avg_abs_change_pct(closes: list[float], lookback: int) -> float | None:
    """최근 절대 등락률 평균을 계산한다."""
    if len(closes) < 2:
        return None
    recent_closes = closes[-(lookback + 1):] if len(closes) >= lookback + 1 else closes
    changes = []
    for prev, curr in zip(recent_closes, recent_closes[1:]):
        if prev == 0:
            continue
        changes.append(abs((curr - prev) / prev) * 100)
    if not changes:
        return None
    return sum(changes) / len(changes)


def calc_rsi(closes: list[float], period: int) -> float | None:
    """단순 RSI 값을 계산한다."""
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for prev, curr in zip(closes[-(period + 1):], closes[-period:]):
        change = curr - prev
        if change >= 0:
            gains.append(change)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(change))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_recent_range_stats(
    highs: list[float], lows: list[float], last_close: float, lookback: int
) -> dict[str, float | None]:
    """최근 고저 범위 통계를 계산한다."""
    recent_highs = highs[-lookback:] if len(highs) >= lookback else highs
    recent_lows = lows[-lookback:] if len(lows) >= lookback else lows
    if not recent_highs or not recent_lows:
        return {
            "recent_high": None,
            "recent_low": None,
            "recent_range_pct": None,
            "range_position_pct": None,
            "distance_from_recent_high_pct": None,
            "distance_from_recent_low_pct": None,
        }

    recent_high = max(recent_highs)
    recent_low = min(recent_lows)
    price_span = recent_high - recent_low
    range_position_pct = None
    if price_span > 0:
        range_position_pct = (last_close - recent_low) / price_span * 100

    return {
        "recent_high": recent_high,
        "recent_low": recent_low,
        "recent_range_pct": ((recent_high - recent_low) / last_close * 100)
        if last_close
        else None,
        "range_position_pct": range_position_pct,
        "distance_from_recent_high_pct": ((recent_high - last_close) / last_close * 100)
        if last_close
        else None,
        "distance_from_recent_low_pct": ((last_close - recent_low) / last_close * 100)
        if last_close
        else None,
    }


def create_okx_public_client() -> ccxt.okx:
    """공개 시세 조회용 OKX 클라이언트를 만든다."""
    return ccxt.okx(
        {
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",
                "fetchMarkets": ["spot"],
            },
        }
    )


def create_upbit_public_client() -> ccxt.upbit:
    """공개 시세 조회용 업비트 클라이언트를 만든다."""
    return ccxt.upbit(
        {
            "enableRateLimit": True,
            "options": {
                "adjustForTimeDifference": True,
            },
        }
    )


def fetch_okx_ohlcv(
    exchange: ccxt.okx, symbol: str, timeframe: str = "1m", limit: int = 200
) -> list[list[float]]:
    """OKX 공개 캔들 API에서 OHLCV를 가져온다."""
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
    bar = timeframe_map.get(timeframe, "1m")

    response = exchange.publicGetMarketCandles(
        {
            "instId": inst_id,
            "bar": bar,
            "limit": limit,
        }
    )

    data = response.get("data", []) if isinstance(response, dict) else response
    ohlcv: list[list[float]] = []
    for item in data:
        ohlcv.append(
            [
                int(item[0]),
                float(item[1]),
                float(item[2]),
                float(item[3]),
                float(item[4]),
                float(item[5]),
            ]
        )

    ohlcv.sort(key=lambda row: row[0])
    return ohlcv


def fetch_upbit_ohlcv(
    exchange: ccxt.upbit, symbol: str, timeframe: str = "1m", limit: int = 200
) -> list[list[float]]:
    """업비트에서 OHLCV를 가져온다."""
    return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)


def fetch_okx_order_book(exchange: ccxt.okx, symbol: str) -> dict[str, float | None]:
    """OKX 공개 호가창에서 최우선 호가 정보를 가져온다."""
    try:
        inst_id = symbol.replace("/", "-")
        response = exchange.publicGetMarketBooks({"instId": inst_id, "sz": "1"})
        data = response.get("data", []) if isinstance(response, dict) else response
        if not data:
            return {}
        first = data[0]
        bids = first.get("bids", [])
        asks = first.get("asks", [])
        return normalize_order_book_levels(bids=bids, asks=asks)
    except Exception:
        return {}


def fetch_upbit_order_book(exchange: ccxt.upbit, symbol: str) -> dict[str, float | None]:
    """업비트 공개 호가창에서 최우선 호가 정보를 가져온다."""
    try:
        order_book = exchange.fetch_order_book(symbol, limit=1)
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        normalized_bids = [[bid["price"], bid["amount"]] for bid in bids[:1]]
        normalized_asks = [[ask["price"], ask["amount"]] for ask in asks[:1]]
        return normalize_order_book_levels(bids=normalized_bids, asks=normalized_asks)
    except Exception:
        return {}


def normalize_order_book_levels(
    bids: list[list[float]], asks: list[list[float]]
) -> dict[str, float | None]:
    """호가창 최우선 매수/매도호가를 공통 형식으로 정리한다."""
    best_bid = float(bids[0][0]) if bids else None
    best_bid_size = float(bids[0][1]) if bids else None
    best_ask = float(asks[0][0]) if asks else None
    best_ask_size = float(asks[0][1]) if asks else None

    spread = None
    spread_pct = None
    if best_bid is not None and best_ask is not None:
        spread = best_ask - best_bid
        mid_price = (best_ask + best_bid) / 2 if (best_ask + best_bid) else None
        if mid_price:
            spread_pct = spread / mid_price * 100

    bid_ask_size_imbalance = None
    if best_bid_size is not None and best_ask_size is not None and best_ask_size > 0:
        bid_ask_size_imbalance = best_bid_size / best_ask_size

    return {
        "best_bid": best_bid,
        "best_bid_size": best_bid_size,
        "best_ask": best_ask,
        "best_ask_size": best_ask_size,
        "spread": spread,
        "spread_pct": spread_pct,
        "bid_ask_size_imbalance": bid_ask_size_imbalance,
    }


def sanitize_symbol(symbol: str) -> str:
    """파일명에 넣기 좋게 심볼 문자열을 바꾼다."""
    return symbol.replace("/", "_").replace("-", "_")


def write_jsonl(path: Path, record: dict):
    """한 줄 JSON 형식으로 기록한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def compact_record(record: dict[str, object]) -> dict[str, object]:
    """분석 가치가 낮은 빈 필드와 None 값을 제거한다."""
    compact: dict[str, object] = {}
    for key, value in record.items():
        if key == "collected_at_local":
            continue
        if value is None:
            continue
        if isinstance(value, list) and not value:
            continue
        compact[key] = value
    return compact


def build_public_filter_summary(
    bullish: bool,
    bearish: bool,
    signal_is_strong: bool,
    htf_bullish: bool | None,
    htf_bearish: bool | None,
    volume_filter_passed: bool | None,
    volatility_filter_passed: bool | None,
) -> dict[str, object]:
    """공개 데이터 기준의 필터 통과 여부와 스킵 사유를 정리한다."""
    buy_blockers: list[str] = []
    sell_blockers: list[str] = []

    if bullish and not signal_is_strong:
        buy_blockers.append("weak_signal")
    if bullish and htf_bullish is False:
        buy_blockers.append("higher_timeframe_not_bullish")
    if bullish and volume_filter_passed is False:
        buy_blockers.append("low_volume")
    if bullish and volatility_filter_passed is False:
        buy_blockers.append("volatility_out_of_range")

    if bearish and not signal_is_strong:
        sell_blockers.append("weak_signal")
    if bearish and htf_bearish is False:
        sell_blockers.append("higher_timeframe_not_bearish")

    return {
        "public_buy_ready": bullish and not buy_blockers,
        "public_sell_signal_ready": bearish and not sell_blockers,
        "public_buy_blockers": buy_blockers,
        "public_sell_blockers": sell_blockers,
    }


def build_snapshot(
    exchange_name: str,
    symbol: str,
    ohlcv: list[list[float]],
    ma_period: int,
    higher_timeframe_ohlcv: list[list[float]] | None,
    order_book: dict[str, float | None],
    strategy,
    settings: dict[str, object],
):
    """OHLCV와 추가 지표로부터 분석용 스냅샷 1건을 만든다."""
    closes = [row[4] for row in ohlcv]
    highs = [row[2] for row in ohlcv]
    lows = [row[3] for row in ohlcv]
    bullish, bearish, prev_close, prev_ma, last_close, last_ma = detect_crossover(
        closes, ma_period
    )
    last_candle = ohlcv[-1]
    prev_candle = ohlcv[-2]
    gap_pct = abs(last_close - last_ma) / last_ma * 100 if last_ma else 0.0
    close_change_pct = ((last_close - prev_close) / prev_close * 100) if prev_close else 0.0
    candle_range_pct = ((last_candle[2] - last_candle[3]) / last_close * 100) if last_close else 0.0
    candle_body_pct = (abs(last_candle[4] - last_candle[1]) / last_candle[1] * 100) if last_candle[1] else 0.0
    volume_ratio = calc_volume_ratio(ohlcv, int(settings["volume_lookback"]))
    avg_abs_change_pct = calc_avg_abs_change_pct(
        closes, int(settings["volatility_lookback"])
    )
    rsi = calc_rsi(closes, int(settings["rsi_period"]))
    range_stats = calc_recent_range_stats(
        highs=highs,
        lows=lows,
        last_close=last_close,
        lookback=int(settings["recent_range_lookback"]),
    )

    min_gap_pct = strategy.get_crossover_gap_pct(symbol)
    min_take_profit_pct = strategy.get_take_profit_pct(symbol)
    stop_loss_pct = strategy.get_stop_loss_pct(symbol)
    signal_is_strong = gap_pct >= min_gap_pct

    htf_last_close = None
    htf_last_ma = None
    htf_gap_pct = None
    htf_bullish = None
    htf_bearish = None
    if higher_timeframe_ohlcv:
        htf_closes = [row[4] for row in higher_timeframe_ohlcv]
        htf_last_close = htf_closes[-1]
        htf_last_ma = calc_sma(htf_closes, int(settings["higher_timeframe_ma_period"]))
        htf_gap_pct = abs(htf_last_close - htf_last_ma) / htf_last_ma * 100 if htf_last_ma else None
        htf_bullish = htf_last_close > htf_last_ma
        htf_bearish = htf_last_close < htf_last_ma

    volume_filter_passed = None
    if parse_bool(str(settings["enable_volume_filter"]), default=True) and volume_ratio is not None:
        volume_filter_passed = volume_ratio >= float(settings["min_volume_ratio"])

    volatility_filter_passed = None
    if (
        parse_bool(str(settings["enable_volatility_filter"]), default=True)
        and avg_abs_change_pct is not None
    ):
        volatility_filter_passed = (
            float(settings["min_volatility_pct"])
            <= avg_abs_change_pct
            <= float(settings["max_volatility_pct"])
        )

    public_filter_summary = build_public_filter_summary(
        bullish=bullish,
        bearish=bearish,
        signal_is_strong=signal_is_strong,
        htf_bullish=htf_bullish,
        htf_bearish=htf_bearish,
        volume_filter_passed=volume_filter_passed,
        volatility_filter_passed=volatility_filter_passed,
    )

    return compact_record({
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "exchange": exchange_name,
        "symbol": symbol,
        "timeframe": os.getenv("ANALYSIS_TIMEFRAME", "1m"),
        "ma_period": ma_period,
        "higher_timeframe": settings["higher_timeframe"],
        "higher_timeframe_ma_period": settings["higher_timeframe_ma_period"],
        "last_candle_ts": last_candle[0],
        "volume_reference_candle_ts": prev_candle[0],
        "volume_ratio_basis": "last_closed_candle_vs_prior_average",
        "data_delay_sec": max(0.0, time.time() - (last_candle[0] / 1000)),
        "open": last_candle[1],
        "high": last_candle[2],
        "low": last_candle[3],
        "close": last_close,
        "volume": last_candle[5],
        "previous_close": prev_close,
        "previous_ma": prev_ma,
        "last_ma": last_ma,
        "bullish_signal": bullish,
        "bearish_signal": bearish,
        "above_ma": last_close > last_ma,
        "gap_pct": gap_pct,
        "close_change_pct": close_change_pct,
        "candle_range_pct": candle_range_pct,
        "candle_body_pct": candle_body_pct,
        "volume_ratio": volume_ratio,
        "avg_abs_change_pct": avg_abs_change_pct,
        "rsi": rsi,
        "previous_candle_ts": prev_candle[0],
        "configured_min_gap_pct": min_gap_pct,
        "configured_take_profit_pct": min_take_profit_pct,
        "configured_stop_loss_pct": stop_loss_pct,
        "signal_is_strong": signal_is_strong,
        "configured_min_volume_ratio": settings["min_volume_ratio"],
        "configured_min_volatility_pct": settings["min_volatility_pct"],
        "configured_max_volatility_pct": settings["max_volatility_pct"],
        "htf_last_close": htf_last_close,
        "htf_last_ma": htf_last_ma,
        "htf_gap_pct": htf_gap_pct,
        "htf_bullish": htf_bullish,
        "htf_bearish": htf_bearish,
        "volume_filter_passed": volume_filter_passed,
        "volatility_filter_passed": volatility_filter_passed,
        "recent_high": range_stats["recent_high"],
        "recent_low": range_stats["recent_low"],
        "recent_range_pct": range_stats["recent_range_pct"],
        "range_position_pct": range_stats["range_position_pct"],
        "distance_from_recent_high_pct": range_stats["distance_from_recent_high_pct"],
        "distance_from_recent_low_pct": range_stats["distance_from_recent_low_pct"],
        "best_bid": order_book.get("best_bid"),
        "best_bid_size": order_book.get("best_bid_size"),
        "best_ask": order_book.get("best_ask"),
        "best_ask_size": order_book.get("best_ask_size"),
        "spread": order_book.get("spread"),
        "spread_pct": order_book.get("spread_pct"),
        "bid_ask_size_imbalance": order_book.get("bid_ask_size_imbalance"),
        **public_filter_summary,
    })


def iter_targets() -> Iterable[tuple[str, str]]:
    """환경 변수 기준으로 수집 대상 거래소/심볼 조합을 만든다."""
    okx_symbols = load_managed_symbols("okx")
    upbit_symbols = load_managed_symbols("upbit")

    for symbol in okx_symbols:
        yield "okx", symbol
    for symbol in upbit_symbols:
        yield "upbit", symbol


def main():
    """수집기 메인 루프."""
    load_dotenv()
    notifier = load_telegram_notifier()
    last_error_signature: str | None = None

    timeframe = os.getenv("ANALYSIS_TIMEFRAME", "1m")
    interval_sec = int(os.getenv("ANALYSIS_LOG_INTERVAL_SEC", "60"))
    ma_period = int(os.getenv("ANALYSIS_MA_PERIOD", "20"))
    recent_range_lookback = int(os.getenv("ANALYSIS_RECENT_RANGE_LOOKBACK", "20"))
    rsi_period = int(os.getenv("ANALYSIS_RSI_PERIOD", "14"))
    collect_orderbook = parse_bool(
        os.getenv("ANALYSIS_ENABLE_ORDERBOOK", "true"),
        default=True,
    )
    limit = ma_period + 5
    strategy = load_strategy_settings("OKX_MIN_BUY_ORDER_VALUE", 1.0)
    collector_settings = {
        "higher_timeframe": strategy.higher_timeframe,
        "higher_timeframe_ma_period": strategy.higher_timeframe_ma_period,
        "enable_higher_timeframe_filter": strategy.enable_higher_timeframe_filter,
        "enable_volume_filter": strategy.enable_volume_filter,
        "enable_volatility_filter": strategy.enable_volatility_filter,
        "volume_lookback": int(os.getenv("ANALYSIS_VOLUME_LOOKBACK", str(strategy.volume_lookback))),
        "volatility_lookback": int(
            os.getenv("ANALYSIS_VOLATILITY_LOOKBACK", str(strategy.volatility_lookback))
        ),
        "min_volume_ratio": strategy.min_volume_ratio,
        "min_volatility_pct": strategy.min_volatility_pct,
        "max_volatility_pct": strategy.max_volatility_pct,
        "recent_range_lookback": recent_range_lookback,
        "rsi_period": rsi_period,
    }

    okx = create_okx_public_client()
    upbit = create_upbit_public_client()

    print("=== 분석용 시장 데이터 수집기 시작 ===")
    print(f"수집 주기: {interval_sec}초")
    print(f"타임프레임: {timeframe}, MA 기간: {ma_period}")
    print(
        f"상위 타임프레임: {collector_settings['higher_timeframe']}, "
        f"거래량 lookback: {collector_settings['volume_lookback']}, "
        f"변동성 lookback: {collector_settings['volatility_lookback']}, "
        f"RSI 기간: {collector_settings['rsi_period']}"
    )

    while True:
        for exchange_name, symbol in iter_targets():
            try:
                if exchange_name == "okx":
                    ohlcv = fetch_okx_ohlcv(okx, symbol, timeframe=timeframe, limit=limit)
                    higher_timeframe_ohlcv = fetch_okx_ohlcv(
                        okx,
                        symbol,
                        timeframe=str(collector_settings["higher_timeframe"]),
                        limit=int(collector_settings["higher_timeframe_ma_period"]) + 5,
                    )
                    order_book = (
                        fetch_okx_order_book(okx, symbol) if collect_orderbook else {}
                    )
                else:
                    ohlcv = fetch_upbit_ohlcv(
                        upbit, symbol, timeframe=timeframe, limit=limit
                    )
                    higher_timeframe_ohlcv = fetch_upbit_ohlcv(
                        upbit,
                        symbol,
                        timeframe=str(collector_settings["higher_timeframe"]),
                        limit=int(collector_settings["higher_timeframe_ma_period"]) + 5,
                    )
                    order_book = (
                        fetch_upbit_order_book(upbit, symbol) if collect_orderbook else {}
                    )

                snapshot = build_snapshot(
                    exchange_name=exchange_name,
                    symbol=symbol,
                    ohlcv=ohlcv,
                    ma_period=ma_period,
                    higher_timeframe_ohlcv=higher_timeframe_ohlcv,
                    order_book=order_book,
                    strategy=strategy,
                    settings=collector_settings,
                )
                log_path = dated_path(
                    "analysis_logs",
                    f"{exchange_name}__{sanitize_symbol(symbol)}.jsonl",
                )
                write_jsonl(log_path, snapshot)
                print(
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"{exchange_name.upper()} {symbol} 수집 완료 "
                    f"(close={snapshot['close']}, gap={snapshot['gap_pct']:.4f}%, "
                    f"volume_ratio={snapshot['volume_ratio']}, rsi={snapshot['rsi']})"
                )
            except Exception as e:
                error_record = {
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                    "exchange": exchange_name,
                    "symbol": symbol,
                    "error": repr(e),
                }
                write_jsonl(dated_path("analysis_logs", "errors.jsonl"), error_record)
                print(
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"{exchange_name.upper()} {symbol} 수집 실패: {repr(e)}"
                )
                error_signature = f"{exchange_name}:{symbol}:{repr(e)}"
                if error_signature != last_error_signature:
                    notifier.notify_error_message(
                        "ANALYSIS-COLLECTOR",
                        symbol,
                        repr(e),
                    )
                    last_error_signature = error_signature

        time.sleep(interval_sec)


if __name__ == "__main__":
    main()
