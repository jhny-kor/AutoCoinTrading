"""
작업 요약
- 최근 ATR 과 ATR 퍼센트를 공통으로 계산하는 helper 를 추가해 BTC 변동성 기반 진입 비중 조절에 재사용할 수 있게 확장했다.
- 알트/BTC/분석 수집기가 함께 쓰는 공통 보조지표 계산 함수를 추가했다.
- RSI, MACD 히스토그램, 볼린저 밴드 폭, ADX, 기울기 계산을 한 곳에서 재사용하도록 정리했다.
- 수익률 상관계수 계산 helper 를 추가해 BTC-알트 동조화 진입을 제어할 수 있게 보강했다.
- 최근 캔들 잡음 수준을 동적으로 읽을 수 있게 노이즈 비율 계산 helper 를 추가했다.
"""

from __future__ import annotations


def calc_sma(prices: list[float], period: int) -> float:
    """단순 이동평균을 계산한다."""
    if period <= 0 or len(prices) < period:
        raise ValueError("SMA 계산에 필요한 가격 데이터가 부족합니다.")
    window = prices[-period:]
    return sum(window) / len(window)


def calc_ema_series(prices: list[float], period: int) -> list[float]:
    """EMA 시리즈를 계산한다."""
    if period <= 0 or len(prices) < period:
        raise ValueError("EMA 계산에 필요한 가격 데이터가 부족합니다.")

    multiplier = 2 / (period + 1)
    ema_values = [sum(prices[:period]) / period]
    for price in prices[period:]:
        ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
    return ema_values


def calc_rsi(prices: list[float], period: int) -> float | None:
    """단순 RSI 값을 계산한다."""
    if period <= 0 or len(prices) < period + 1:
        return None

    gains: list[float] = []
    losses: list[float] = []
    recent = prices[-(period + 1):]
    for prev, curr in zip(recent, recent[1:]):
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


def calc_macd_histogram(
    prices: list[float],
    *,
    fast_period: int,
    slow_period: int,
    signal_period: int,
) -> tuple[float | None, float | None, float | None]:
    """MACD 선, 시그널 선, 히스토그램 값을 계산한다."""
    if (
        fast_period <= 0
        or slow_period <= 0
        or signal_period <= 0
        or fast_period >= slow_period
    ):
        raise ValueError("MACD 기간 설정이 잘못되었습니다.")
    if len(prices) < slow_period + signal_period:
        return None, None, None

    fast_series = calc_ema_series(prices, fast_period)
    slow_series = calc_ema_series(prices, slow_period)
    align_len = min(len(fast_series), len(slow_series))
    fast_tail = fast_series[-align_len:]
    slow_tail = slow_series[-align_len:]
    macd_series = [fast - slow for fast, slow in zip(fast_tail, slow_tail)]
    if len(macd_series) < signal_period:
        return None, None, None
    signal_series = calc_ema_series(macd_series, signal_period)
    signal_value = signal_series[-1]
    macd_value = macd_series[-1]
    histogram = macd_value - signal_value
    return macd_value, signal_value, histogram


def calc_bollinger_band_width_pct(
    prices: list[float],
    *,
    period: int,
    stddev_multiplier: float,
) -> float | None:
    """볼린저 밴드 폭을 중심선 대비 퍼센트로 계산한다."""
    if period <= 1 or stddev_multiplier <= 0 or len(prices) < period:
        return None

    window = prices[-period:]
    mean = sum(window) / len(window)
    if mean == 0:
        return None
    variance = sum((price - mean) ** 2 for price in window) / len(window)
    stddev = variance ** 0.5
    upper = mean + stddev * stddev_multiplier
    lower = mean - stddev * stddev_multiplier
    return (upper - lower) / mean * 100


def calc_pct_slope(values: list[float], lookback: int) -> float | None:
    """lookback 기준 시작값 대비 마지막 값의 변화율을 계산한다."""
    if lookback <= 0 or len(values) < lookback + 1:
        return None
    start = values[-(lookback + 1)]
    end = values[-1]
    if start == 0:
        return None
    return (end - start) / start * 100


def calc_adx(ohlcv: list[list[float]], period: int) -> float | None:
    """Wilder 방식에 가까운 단순 ADX 값을 계산한다."""
    if period <= 0 or len(ohlcv) < period + 1:
        return None

    trs: list[float] = []
    plus_dms: list[float] = []
    minus_dms: list[float] = []
    for prev, curr in zip(ohlcv[:-1], ohlcv[1:]):
        prev_high = prev[2]
        prev_low = prev[3]
        prev_close = prev[4]
        high = curr[2]
        low = curr[3]

        up_move = high - prev_high
        down_move = prev_low - low
        plus_dm = up_move if up_move > down_move and up_move > 0 else 0.0
        minus_dm = down_move if down_move > up_move and down_move > 0 else 0.0
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))

        trs.append(tr)
        plus_dms.append(plus_dm)
        minus_dms.append(minus_dm)

    if len(trs) < period:
        return None

    dx_values: list[float] = []
    for idx in range(period - 1, len(trs)):
        tr_sum = sum(trs[idx - period + 1 : idx + 1])
        plus_dm_sum = sum(plus_dms[idx - period + 1 : idx + 1])
        minus_dm_sum = sum(minus_dms[idx - period + 1 : idx + 1])
        if tr_sum <= 0:
            continue
        plus_di = plus_dm_sum / tr_sum * 100
        minus_di = minus_dm_sum / tr_sum * 100
        di_sum = plus_di + minus_di
        if di_sum <= 0:
            continue
        dx_values.append(abs(plus_di - minus_di) / di_sum * 100)

    if not dx_values:
        return None
    recent_dx = dx_values[-period:] if len(dx_values) >= period else dx_values
    return sum(recent_dx) / len(recent_dx)


def calc_atr(ohlcv: list[list[float]], period: int) -> float | None:
    """최근 완료 봉 기준 단순 ATR 값을 계산한다."""
    if period <= 0 or len(ohlcv) < period + 2:
        return None

    completed = ohlcv[:-1]
    if len(completed) < period + 1:
        return None

    true_ranges: list[float] = []
    for prev, curr in zip(completed[:-1], completed[1:]):
        prev_close = prev[4]
        high = curr[2]
        low = curr[3]
        true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))

    if len(true_ranges) < period:
        return None
    recent_tr = true_ranges[-period:]
    return sum(recent_tr) / len(recent_tr)


def calc_return_correlation(
    prices_a: list[float],
    prices_b: list[float],
    *,
    lookback: int,
) -> float | None:
    """두 가격 시리즈의 최근 수익률 상관계수를 계산한다."""
    if lookback <= 1:
        return None
    aligned_len = min(len(prices_a), len(prices_b), lookback + 1)
    if aligned_len < lookback + 1:
        return None

    series_a = prices_a[-aligned_len:]
    series_b = prices_b[-aligned_len:]
    returns_a: list[float] = []
    returns_b: list[float] = []
    for prev_a, curr_a, prev_b, curr_b in zip(series_a, series_a[1:], series_b, series_b[1:]):
        if prev_a == 0 or prev_b == 0:
            continue
        returns_a.append((curr_a - prev_a) / prev_a)
        returns_b.append((curr_b - prev_b) / prev_b)

    if len(returns_a) < 2 or len(returns_b) < 2:
        return None

    mean_a = sum(returns_a) / len(returns_a)
    mean_b = sum(returns_b) / len(returns_b)
    covariance = sum((a - mean_a) * (b - mean_b) for a, b in zip(returns_a, returns_b))
    variance_a = sum((a - mean_a) ** 2 for a in returns_a)
    variance_b = sum((b - mean_b) ** 2 for b in returns_b)
    if variance_a <= 0 or variance_b <= 0:
        return None
    return covariance / ((variance_a ** 0.5) * (variance_b ** 0.5))


def calc_noise_ratio(ohlcv: list[list[float]], lookback: int) -> float | None:
    """최근 완료 봉 기준 평균 노이즈 비율을 계산한다."""
    if lookback <= 0 or len(ohlcv) < 3:
        return None

    completed = ohlcv[:-1]
    if not completed:
        return None
    recent = completed[-lookback:] if len(completed) >= lookback else completed
    noise_values: list[float] = []
    for row in recent:
        high = row[2]
        low = row[3]
        open_price = row[1]
        close_price = row[4]
        candle_range = high - low
        if candle_range <= 0:
            continue
        body = abs(open_price - close_price)
        noise = 1 - (body / candle_range)
        noise_values.append(max(0.0, min(1.0, noise)))

    if not noise_values:
        return None
    return sum(noise_values) / len(noise_values)
