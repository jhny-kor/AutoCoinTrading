"""
작업 요약
- 백테스트 리플레이의 순수 지표/성과 계산 helper 를 분리했다.
"""

from __future__ import annotations

from tools.backtest_models import Candle, EquityPoint, TradeRecord


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


def safe_float(value) -> float | None:
    """숫자 후보를 float 로 안전하게 변환한다."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value) -> int | None:
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


def build_full_ema_series(prices: list[float], period: int) -> list[float | None]:
    """전체 히스토리 기준 EMA 시리즈를 원본 인덱스에 맞춰 계산한다."""
    if period <= 0 or len(prices) < period:
        return [None] * len(prices)

    multiplier = 2 / (period + 1)
    ema_values: list[float | None] = [None] * len(prices)
    seed = sum(prices[:period]) / period
    ema_values[period - 1] = seed
    prev_ema = seed
    for index in range(period, len(prices)):
        prev_ema = (prices[index] - prev_ema) * multiplier + prev_ema
        ema_values[index] = prev_ema
    return ema_values


def build_macd_histogram_series(
    prices: list[float],
    *,
    fast_period: int,
    slow_period: int,
    signal_period: int,
) -> list[float | None]:
    """전체 히스토리 기준 MACD 히스토그램 시리즈를 계산한다."""
    if (
        fast_period <= 0
        or slow_period <= 0
        or signal_period <= 0
        or fast_period >= slow_period
        or len(prices) < slow_period + signal_period
    ):
        return [None] * len(prices)

    fast_series = build_full_ema_series(prices, fast_period)
    slow_series = build_full_ema_series(prices, slow_period)
    compact_macd: list[float] = []
    macd_indexes: list[int] = []
    for index, (fast_value, slow_value) in enumerate(zip(fast_series, slow_series)):
        if fast_value is None or slow_value is None:
            continue
        compact_macd.append(fast_value - slow_value)
        macd_indexes.append(index)

    signal_series = build_full_ema_series(compact_macd, signal_period)
    histogram: list[float | None] = [None] * len(prices)
    for compact_index, signal_value in enumerate(signal_series):
        if signal_value is None:
            continue
        original_index = macd_indexes[compact_index]
        histogram[original_index] = compact_macd[compact_index] - signal_value
    return histogram


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


def compute_profit_factor(sell_records: list[TradeRecord]) -> float | None:
    """최종 청산 순손익 기준 profit factor 를 계산한다."""
    gross_profit = sum(
        (record.net_realized_pnl_quote or 0.0)
        for record in sell_records
        if (record.net_realized_pnl_quote or 0.0) > 0
    )
    gross_loss = abs(
        sum(
            (record.net_realized_pnl_quote or 0.0)
            for record in sell_records
            if (record.net_realized_pnl_quote or 0.0) < 0
        )
    )
    if gross_loss <= 0:
        if gross_profit <= 0:
            return None
        return float("inf")
    return gross_profit / gross_loss


def compute_sharpe_ratio(equity_curve: list[EquityPoint], *, timeframe: str) -> float | None:
    """자산곡선의 캔들 단위 수익률로 단순 Sharpe ratio 를 계산한다."""
    if len(equity_curve) < 3:
        return None
    returns: list[float] = []
    previous_equity = equity_curve[0].equity_quote
    for point in equity_curve[1:]:
        if previous_equity <= 0:
            previous_equity = point.equity_quote
            continue
        returns.append((point.equity_quote / previous_equity) - 1.0)
        previous_equity = point.equity_quote
    if len(returns) < 2:
        return None
    mean_return = sum(returns) / len(returns)
    variance = sum((value - mean_return) ** 2 for value in returns) / (len(returns) - 1)
    if variance <= 0:
        return None
    timeframe_minutes = parse_timeframe_to_minutes(timeframe)
    periods_per_year = max(1.0, (365.0 * 24.0 * 60.0) / max(1, timeframe_minutes))
    return (mean_return / (variance ** 0.5)) * (periods_per_year ** 0.5)
