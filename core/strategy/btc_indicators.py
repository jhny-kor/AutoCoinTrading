"""
작업 요약
- BTC 실거래 봇에서 공통으로 쓰는 EMA/ATR/스윙/청산가 계산 helper 를 분리했다.
"""

from __future__ import annotations

from core.strategy.btc_position import build_btc_exit_prices
from core.strategy.indicators import calc_ema_series as calc_ema_series_core


def calc_ema_series(prices: list[float], period: int) -> list[float]:
    """EMA 시리즈를 계산한다."""
    return calc_ema_series_core(prices, period)


def detect_ema_crossover(
    closes: list[float], fast_period: int, slow_period: int
) -> tuple[bool, bool, float, float, float, float]:
    """EMA 골든/데드 크로스를 계산한다."""
    if len(closes) < slow_period + 2:
        raise ValueError("EMA 크로스를 계산하기 위한 캔들 수가 부족합니다.")

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


def calc_atr(ohlcv: list[list[float]], period: int) -> float:
    """ATR 을 계산한다."""
    if len(ohlcv) < period + 1:
        raise ValueError("ATR 계산에 필요한 캔들 수가 부족합니다.")

    trs: list[float] = []
    for prev, curr in zip(ohlcv[:-1], ohlcv[1:]):
        high = curr[2]
        low = curr[3]
        prev_close = prev[4]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    recent = trs[-period:]
    return sum(recent) / len(recent)


def get_recent_swing_low(ohlcv: list[list[float]], lookback: int) -> float:
    """최근 스윙 저점을 계산한다."""
    recent = ohlcv[-lookback:] if len(ohlcv) >= lookback else ohlcv
    return min(row[3] for row in recent)


def get_recent_swing_high(ohlcv: list[list[float]], lookback: int) -> float:
    """최근 스윙 고점을 계산한다."""
    recent = ohlcv[-lookback:] if len(ohlcv) >= lookback else ohlcv
    return max(row[2] for row in recent)


def build_exit_prices(
    *,
    entry_price: float,
    atr_value: float,
    recent_swing_low: float,
    recent_swing_high: float,
    min_take_profit_pct: float,
    settings,
) -> tuple[float, float]:
    """BTC 포지션 평가 helper 와 같은 청산 가격 계산을 사용한다."""
    return build_btc_exit_prices(
        entry_price=entry_price,
        atr_value=atr_value,
        recent_swing_low=recent_swing_low,
        recent_swing_high=recent_swing_high,
        min_take_profit_pct=min_take_profit_pct,
        settings=settings,
    )
