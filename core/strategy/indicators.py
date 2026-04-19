"""
작업 요약
- regime별 지표 가중치 조합에 재사용할 수 있는 weighted signal score helper 를 추가
- 2026-04-12: ATR/거래량 분포 기반 percentile, z-score, 호가 압력 점수를 추가해 약한 지표를 결합 판단에 쓸 수 있게 확장
- 2026-04-08: 볼린저 밴드 계산에서 사용하는 `math.sqrt` 누락 import 를 추가해 알트 봇 런타임 예외를 수정했다.
- 최근 ATR 과 ATR 퍼센트를 공통으로 계산하는 helper 를 추가해 BTC 변동성 기반 진입 비중 조절에 재사용할 수 있게 확장했다.
- 알트/BTC/분석 수집기가 함께 쓰는 공통 보조지표 계산 함수를 추가했다.
- RSI, MACD 히스토그램, 볼린저 밴드 폭, ADX, 기울기 계산을 한 곳에서 재사용하도록 정리했다.
- 수익률 상관계수 계산 helper 를 추가해 BTC-알트 동조화 진입을 제어할 수 있게 보강했다.
- 최근 캔들 잡음 수준을 동적으로 읽을 수 있게 노이즈 비율 계산 helper 를 추가했다.
"""

from __future__ import annotations

import math


def calc_sma(prices: list[float], period: int) -> float:
    """단순 이동평균을 계산한다."""
    if period <= 0 or len(prices) < period:
        raise ValueError("SMA 계산에 필요한 가격 데이터가 부족합니다.")
    window = prices[-period:]
    return sum(window) / len(window)


def calc_weighted_signal_score(
    components: dict[str, float | None],
    weights: dict[str, float],
) -> float:
    """0~100 점수 컴포넌트를 가중 평균해 최종 신호 점수를 계산한다."""
    positive_weights = {
        key: float(weight)
        for key, weight in weights.items()
        if float(weight) > 0 and components.get(key) is not None
    }
    if not positive_weights:
        return 0.0

    total_weight = sum(positive_weights.values())
    if total_weight <= 0:
        return 0.0

    weighted_sum = 0.0
    for key, weight in positive_weights.items():
        value = float(components.get(key) or 0.0)
        value = max(0.0, min(100.0, value))
        weighted_sum += value * weight
    return max(0.0, min(100.0, weighted_sum / total_weight))


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


def calc_bollinger_bands(
    closes: list[float], period: int = 20, stddev_multiplier: float = 2.0
) -> tuple[float | None, float | None, float | None]:
    """
    볼린저 밴드의 상단(upper), 중단(mid), 하단(lower)을 리스트로 계산하여 반환한다.
    반환값: (upper, mid, lower)
    """
    if len(closes) < period:
        return None, None, None

    recent_closes = closes[-period:]
    mid = sum(recent_closes) / period

    variance = sum((c - mid) ** 2 for c in recent_closes) / period
    stddev = math.sqrt(variance)

    upper = mid + (stddev * stddev_multiplier)
    lower = mid - (stddev * stddev_multiplier)

    return upper, mid, lower


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


def calc_percentile_rank(values: list[float], target: float | None) -> float | None:
    """목표값이 최근 분포에서 어느 분위인지 0~100 범위로 반환한다."""
    if target is None:
        return None
    cleaned = sorted(float(value) for value in values if value is not None)
    if not cleaned:
        return None
    below_or_equal = sum(1 for value in cleaned if value <= float(target))
    return below_or_equal / len(cleaned) * 100


def calc_zscore(values: list[float], target: float | None) -> float | None:
    """목표값의 z-score 를 계산한다."""
    if target is None:
        return None
    cleaned = [float(value) for value in values if value is not None]
    if len(cleaned) < 2:
        return None
    mean = sum(cleaned) / len(cleaned)
    variance = sum((value - mean) ** 2 for value in cleaned) / len(cleaned)
    stddev = math.sqrt(max(variance, 0.0))
    if stddev <= 0:
        return None
    return (float(target) - mean) / stddev


def calc_recent_volume_ratio_series(
    ohlcv: list[list[float]], lookback: int, sample_count: int = 20
) -> list[float]:
    """최근 완료 봉 기준 volume_ratio 시리즈를 만든다."""
    if lookback <= 0 or len(ohlcv) < lookback + 3:
        return []
    completed = ohlcv[:-1]
    ratios: list[float] = []
    for idx in range(lookback, len(completed)):
        recent = completed[idx - lookback : idx]
        avg_volume = sum(row[5] for row in recent) / len(recent) if recent else 0.0
        current_volume = completed[idx][5]
        if avg_volume > 0:
            ratios.append(current_volume / avg_volume)
    return ratios[-sample_count:]


def calc_recent_atr_series(
    ohlcv: list[list[float]], period: int, sample_count: int = 20
) -> list[float]:
    """최근 ATR 시리즈를 만든다."""
    if period <= 0 or len(ohlcv) < period + 3:
        return []
    series: list[float] = []
    for end in range(period + 2, len(ohlcv) + 1):
        value = calc_atr(ohlcv[:end], period)
        if value is not None:
            series.append(value)
    return series[-sample_count:]


def calc_orderbook_pressure_score(order_book: dict[str, float | None]) -> float | None:
    """호가 불균형과 스프레드를 가볍게 합성한 압력 점수(0~100)를 계산한다."""
    if not isinstance(order_book, dict):
        return None
    score = 50.0
    spread_pct = order_book.get("spread_pct")
    imbalance = order_book.get("bid_ask_size_imbalance")
    depth_imbalance = order_book.get("depth_size_imbalance_3")

    if spread_pct is not None:
        spread_pct = float(spread_pct)
        if spread_pct <= 0.03:
            score += 5.0
        elif spread_pct >= 0.12:
            score -= 5.0

    if imbalance is not None:
        imbalance = float(imbalance)
        score += max(-10.0, min(10.0, (imbalance - 1.0) * 15.0))

    if depth_imbalance is not None:
        depth_imbalance = float(depth_imbalance)
        score += max(-10.0, min(10.0, (depth_imbalance - 1.0) * 12.0))

    return max(0.0, min(100.0, score))


def calc_donchian_channel(ohlcv: list[list[float]], lookback: int) -> tuple[float | None, float | None]:
    """
    최근 완료된 봉 기준으로 돈치안 채널의 상단(최고가)과 하단(최저가)을 계산한다.
    현재 진행 중인 봉은 제외하며, lookback 개수가 부족하면 None을 반환한다.
    """
    if lookback <= 0 or len(ohlcv) < lookback + 1:
        return None, None
        
    completed = ohlcv[-(lookback + 1):-1]
    if len(completed) < lookback:
        return None, None
        
    highs = [row[2] for row in completed]
    lows = [row[3] for row in completed]
    
    return max(highs), min(lows)
