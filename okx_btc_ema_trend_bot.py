"""
수정 요약
- OKX BTC 매도 체결 로그에도 왕복 수수료를 반영한 순손익을 함께 저장해 /pnl 집계가 net 기준으로 가능하도록 보강
- OKX BTC 에서 최소 주문 수량 미만 잔량은 포지션으로 보지 않아 잔량 보유 중에도 재진입할 수 있게 조정
- BTC 손절 직후에는 일반 거래 간격보다 더 길게 쉬도록 전용 재진입 쿨다운을 추가
- BTC 전략 버전 이름(strategy_version)을 구조화 로그와 체결 이력에 함께 남겨 버전별 비교가 가능하도록 확장
- BTC 거래 품질 분석용으로 최저가, MFE/MAE, 트레일링 활성화 소요 시간까지 체결 로그에 함께 남기도록 확장
- 트레일링 익절이 이미 활성화된 뒤에는 trend_exit 가 먼저 포지션을 끊지 않도록 조정
- BTC 익절 활성화 가격이 왕복 수수료보다 낮아지지 않도록 수수료 하한선을 적용
- BTC 진입 신호를 골든크로스뿐 아니라 EMA 상승 정렬 유지 구간까지 허용해 진입 기회를 늘리도록 조정
- BTC 전용 5분봉/15분봉 EMA 추세추종 실험용 봇 추가
- EMA 골든크로스 진입, 거래량 확인 유지, ATR 기반 변동성 필터 적용
- 물타기 없이 1회 포지션만 운영하고, 손절/익절은 ATR 또는 최근 스윙 기준으로 계산
- 손절/익절/추세 종료 청산을 모두 텔레그램과 체결 JSONL 에 기록하도록 연결
- 전략 판단 로그를 system / strategy / trade JSONL 로 분리 저장하도록 추가
- 진입/청산 퍼널과 차단 사유를 reason 코드 기준으로 집계 가능하게 기록하도록 추가
- OKX BTC 최소 주문수량 0.00001 BTC 를 코드에서 먼저 확인해 주문 전 단계에서 차단하도록 추가
- 거래량 배수 계산을 형성 중인 현재 봉 대신 직전 마감 봉 기준으로 바꿔 BTC 필터 해석을 안정화하도록 조정
- 익절 구간 도달 후 최고가 대비 되돌림으로 전량 청산하는 트레일링 익절 로직을 추가
- 포지션 ID, 트레일링 활성화 시각, 최고가 대비 되돌림 같은 분석용 로그 필드를 추가

OKX BTC 전용 EMA 추세추종 봇

- 심볼: BTC/USDT
- 기본 개념: 5분봉 EMA 추세추종 + 15분봉 확인
- 진입: 빠른 EMA 가 느린 EMA 를 상향 돌파하거나 상승 정렬 유지 조건을 만족할 때
- 청산: 손절, 익절, 또는 선택적으로 EMA 하향 추세 종료 시
"""

from __future__ import annotations

import os
import time
import traceback
from datetime import datetime

from bot_logger import BLUE, RED, BotLogger
from btc_trend_settings import load_btc_trend_settings
from ma_crossover_bot import (
    create_okx_client,
    fetch_ohlcv,
    get_spot_balances,
    load_config,
    place_market_order_okx,
    safe_amount_to_precision,
)
from structured_log_manager import FunnelStep, StructuredLogManager, choose_atr_reason
from telegram_notifier import load_telegram_notifier
from trade_history_logger import TradeHistoryLogger, estimate_round_trip_net_pnl


def calc_ema_series(prices: list[float], period: int) -> list[float]:
    """EMA 시리즈를 계산한다."""
    if len(prices) < period:
        raise ValueError("EMA 계산에 필요한 가격 데이터가 부족합니다.")

    multiplier = 2 / (period + 1)
    ema_values = [sum(prices[:period]) / period]
    for price in prices[period:]:
        ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
    return ema_values


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
    """손절가와 익절가를 계산한다."""
    if settings.stop_mode == "swing":
        stop_price = recent_swing_low
    else:
        stop_price = entry_price - (atr_value * settings.stop_atr_multiple)

    if settings.take_profit_mode == "swing":
        take_profit_price = recent_swing_high
        if take_profit_price <= entry_price:
            take_profit_price = entry_price + (
                atr_value * settings.take_profit_atr_multiple
            )
    else:
        take_profit_price = entry_price + (
            atr_value * settings.take_profit_atr_multiple
        )

    fee_floor_take_profit_price = entry_price * (1 + (min_take_profit_pct / 100))
    take_profit_price = max(take_profit_price, fee_floor_take_profit_price)

    return stop_price, take_profit_price


def run_bot():
    """OKX BTC 전용 EMA 추세추종 봇 메인 루프."""
    config = load_config()
    settings = load_btc_trend_settings()
    exchange = create_okx_client(config)
    logger = BotLogger("okx_btc_ema_trend_bot")
    structured_logger = StructuredLogManager("okx_btc_ema_trend_bot")
    notifier = load_telegram_notifier()
    trade_history = TradeHistoryLogger()
    log = logger.log

    symbol = "BTC/USDT"
    base = "BTC"
    quote = "USDT"
    entry_price: float | None = None
    entry_opened_at: float | None = None
    position_id: str | None = None
    highest_price_since_entry: float | None = None
    lowest_price_since_entry: float | None = None
    trailing_armed = False
    trailing_armed_at: float | None = None
    trailing_activation_price: float | None = None
    last_trade_at = 0.0
    last_stop_loss_at = 0.0
    daily_realized_pnl_quote = 0.0
    daily_pnl_date = datetime.now().date()
    daily_limit_notified = False
    min_buy_order_value = float(os.getenv("OKX_MIN_BUY_ORDER_VALUE", "1.0"))

    min_ohlcv_limit = max(
        settings.slow_ema_period + 5,
        settings.atr_period + 5,
        settings.volume_lookback + 5,
        settings.swing_lookback + 5,
    )
    confirm_limit = max(settings.confirm_ema_period + 5, settings.slow_ema_period + 5)

    log("=== OKX BTC EMA 추세추종 봇 시작 ===")
    log(
        f"메인 타임프레임: {settings.timeframe}, 확인 타임프레임: {settings.confirm_timeframe}"
    )
    log(
        f"EMA: {settings.fast_ema_period}/{settings.slow_ema_period}, "
        f"확인 EMA: {settings.confirm_ema_period}"
    )
    log(
        f"ATR 기간: {settings.atr_period}, 손절 방식: {settings.stop_mode}, "
        f"익절 방식: {settings.take_profit_mode}"
    )
    log(
        f"트레일링 되돌림 기준: {settings.trailing_drawdown_pct:.2f}% "
        f"(익절 구간 도달 후 활성화)"
    )
    log(f"최소 주문 수량: {settings.min_order_amount:.5f} {base}")
    structured_logger.log_system(
        level="INFO",
        event="bot_started",
        message="OKX BTC EMA 전략 봇을 시작합니다.",
        symbol=symbol,
        context={
            "timeframe": settings.timeframe,
            "confirm_timeframe": settings.confirm_timeframe,
            "fast_ema_period": settings.fast_ema_period,
            "slow_ema_period": settings.slow_ema_period,
            "atr_period": settings.atr_period,
        },
    )

    while True:
        today = datetime.now().date()
        if today != daily_pnl_date:
            daily_pnl_date = today
            daily_realized_pnl_quote = 0.0
            daily_limit_notified = False
            log("일자가 변경되어 BTC 전용 봇의 일일 손익을 초기화합니다.")
            structured_logger.log_system(
                level="INFO",
                event="daily_pnl_reset",
                message="BTC 전용 봇의 일일 손익 누적값을 초기화했습니다.",
                symbol=symbol,
            )

        try:
            ohlcv = fetch_ohlcv(exchange, symbol, timeframe=settings.timeframe, limit=min_ohlcv_limit)
            confirm_ohlcv = fetch_ohlcv(
                exchange,
                symbol,
                timeframe=settings.confirm_timeframe,
                limit=confirm_limit,
            )
            closes = [row[4] for row in ohlcv]
            confirm_closes = [row[4] for row in confirm_ohlcv]
            last_close = closes[-1]

            bullish, bearish, prev_fast, prev_slow, last_fast, last_slow = detect_ema_crossover(
                closes,
                settings.fast_ema_period,
                settings.slow_ema_period,
            )
            volume_ratio = calc_volume_ratio(ohlcv, settings.volume_lookback)
            atr_value = calc_atr(ohlcv, settings.atr_period)
            atr_pct = (atr_value / last_close * 100) if last_close else 0.0
            confirm_ema = calc_ema_series(confirm_closes, settings.confirm_ema_period)[-1]
            confirm_close = confirm_closes[-1]
            confirm_bullish = confirm_close > confirm_ema
            ema_aligned = last_fast > last_slow
            price_above_fast = last_close >= last_fast
            ema_spread_pct = (
                ((last_fast - last_slow) / last_slow) * 100 if last_slow else 0.0
            )
            trend_follow_entry = (
                settings.enable_trend_follow_entry
                and ema_aligned
                and ema_spread_pct >= settings.min_ema_spread_pct
                and (
                    not settings.trend_follow_requires_price_above_fast
                    or price_above_fast
                )
            )
            entry_signal = bullish or trend_follow_entry
            recent_swing_low = get_recent_swing_low(ohlcv[:-1], settings.swing_lookback)
            recent_swing_high = get_recent_swing_high(ohlcv[:-1], settings.swing_lookback)

            base_free, quote_free = get_spot_balances(exchange, base, quote)
            # 최소 주문 수량보다 작은 잔량은 즉시 정리할 수 없으므로 포지션에서 제외한다.
            has_position = base_free >= settings.min_order_amount
            if has_position and entry_price is None:
                entry_price = last_close
                entry_opened_at = entry_opened_at or time.time()
                position_id = position_id or f"{symbol}:{int(time.time())}"
                highest_price_since_entry = last_close
                lowest_price_since_entry = last_close
                trailing_armed = False
                trailing_armed_at = None
                trailing_activation_price = None
                log(
                    f"[{symbol}] 기존 보유 물량이 감지되어 평균 진입가를 현재가({last_close:.2f})로 임시 설정합니다."
                )
                structured_logger.log_system(
                    level="INFO",
                    event="position_bootstrap",
                    message="기존 BTC 포지션을 감지해 평균 진입가를 임시 설정했습니다.",
                    symbol=symbol,
                    context={"bootstrap_entry_price": last_close},
                )

            now_ts = time.time()
            base_cooldown_remaining = max(0.0, settings.min_trade_interval_sec - (now_ts - last_trade_at))
            stop_loss_cooldown_remaining = max(
                0.0,
                settings.stop_loss_reentry_cooldown_sec - (now_ts - last_stop_loss_at),
            )
            cooldown_remaining = max(base_cooldown_remaining, stop_loss_cooldown_remaining)
            in_cooldown = cooldown_remaining > 0
            volume_filter_passed = volume_ratio is not None and volume_ratio >= settings.min_volume_ratio
            atr_filter_passed = settings.min_atr_pct <= atr_pct <= settings.max_atr_pct
            daily_loss_limit_reached = daily_realized_pnl_quote <= -config["max_daily_loss_quote"]

            log("-" * 60)
            log(f"[{symbol}] 현재 종가: {last_close:.2f}")
            log(
                f"[{symbol}] EMA 상태 - 이전 {prev_fast:.2f}/{prev_slow:.2f}, 현재 {last_fast:.2f}/{last_slow:.2f}"
            )
            logger.log_signal(symbol, bullish, bearish)
            log(
                f"[{symbol}] 거래량 배수: {volume_ratio:.4f}배"
                if volume_ratio is not None
                else f"[{symbol}] 거래량 배수 계산 불가"
            )
            log(
                f"[{symbol}] ATR: {atr_value:.2f}, ATR 비율: {atr_pct:.4f}% "
                f"(허용 {settings.min_atr_pct:.4f}% ~ {settings.max_atr_pct:.4f}%)"
            )
            log(
                f"[{symbol}] 확인 타임프레임 종가: {confirm_close:.2f}, "
                f"확인 EMA: {confirm_ema:.2f}, 상승 추세={confirm_bullish}"
            )
            log(
                f"[{symbol}] EMA 정렬 상태: aligned={ema_aligned}, "
                f"price_above_fast={price_above_fast}, spread={ema_spread_pct:.4f}%"
            )
            if trend_follow_entry and not bullish:
                log(
                    f"[{symbol}] 신규 골든크로스는 아니지만 EMA 상승 정렬 유지 조건으로 진입 후보를 허용합니다."
                )

            if has_position and entry_price is not None:
                highest_price_since_entry = max(
                    highest_price_since_entry or last_close,
                    last_close,
                )
                lowest_price_since_entry = min(
                    lowest_price_since_entry or last_close,
                    last_close,
                )
                stop_price, take_profit_price = build_exit_prices(
                    entry_price=entry_price,
                    atr_value=atr_value,
                    recent_swing_low=recent_swing_low,
                    recent_swing_high=recent_swing_high,
                    min_take_profit_pct=(config["fee_rate_pct"] * 2 * 1.1),
                    settings=settings,
                )
                pnl_pct = (last_close - entry_price) / entry_price * 100
                if (not trailing_armed) and take_profit_price is not None and last_close >= take_profit_price:
                    trailing_armed = True
                    trailing_armed_at = time.time()
                    trailing_activation_price = last_close
                    log(
                        f"[{symbol}] 익절 구간에 진입해 트레일링 익절을 활성화합니다. "
                        f"현재 최고가: {highest_price_since_entry:.2f}"
                    )
                    structured_logger.log_system(
                        level="INFO",
                        event="trailing_armed",
                        message="BTC 트레일링 익절이 활성화되었습니다.",
                        symbol=symbol,
                        context={
                            "entry_price": entry_price,
                            "take_profit_price": take_profit_price,
                            "highest_price_since_entry": highest_price_since_entry,
                            "trailing_activation_price": trailing_activation_price,
                        },
                    )
                drawdown_from_high_pct = (
                    ((highest_price_since_entry - last_close) / highest_price_since_entry) * 100
                    if highest_price_since_entry
                    else None
                )
                mfe_pct = (
                    ((highest_price_since_entry - entry_price) / entry_price) * 100
                    if highest_price_since_entry is not None and entry_price
                    else None
                )
                mae_pct = (
                    ((lowest_price_since_entry - entry_price) / entry_price) * 100
                    if lowest_price_since_entry is not None and entry_price
                    else None
                )
                log(
                    f"[{symbol}] 평균 진입가: {entry_price:.2f}, 현재 수익률: {pnl_pct:.2f}%, "
                    f"손절가: {stop_price:.2f}, 익절가: {take_profit_price:.2f}, "
                    f"최고가: {highest_price_since_entry:.2f}, "
                    f"최고가 대비 되돌림: {0.0 if drawdown_from_high_pct is None else drawdown_from_high_pct:.2f}%"
                )
            else:
                stop_price = None
                take_profit_price = None
                pnl_pct = None
                drawdown_from_high_pct = None
                mfe_pct = None
                mae_pct = None
                if not has_position:
                    highest_price_since_entry = None
                    lowest_price_since_entry = None
                    trailing_armed = False
                    trailing_armed_at = None
                    trailing_activation_price = None

            if daily_loss_limit_reached:
                log(f"[{symbol}] 일일 최대 손실 제한에 도달하여 신규 진입을 중단합니다.")
                if not daily_limit_notified:
                    notifier.notify_daily_loss_limit(
                        "OKX-BTC",
                        f"오늘 누적 실현 손익: {daily_realized_pnl_quote:.4f} {quote}\n"
                        f"손실 제한: -{config['max_daily_loss_quote']:.4f} {quote}",
                    )
                    daily_limit_notified = True

            stop_triggered = has_position and stop_price is not None and last_close <= stop_price
            trailing_stop_triggered = (
                has_position
                and trailing_armed
                and drawdown_from_high_pct is not None
                and drawdown_from_high_pct >= settings.trailing_drawdown_pct
            )
            trend_exit_triggered = (
                has_position
                and settings.exit_on_bearish_cross
                and bearish
                and not trailing_armed
            )
            order_value = quote_free * config["risk_per_trade"] * settings.position_ratio
            estimated_entry_amount = safe_amount_to_precision(
                exchange,
                symbol,
                order_value / last_close if last_close else 0.0,
            )
            estimated_exit_amount = safe_amount_to_precision(exchange, symbol, base_free)

            common_metrics = {
                "strategy_name": "okx_btc_ema_trend",
                "strategy_version": settings.version,
                "symbol": symbol,
                "timeframe": settings.timeframe,
                "confirm_timeframe": settings.confirm_timeframe,
                "price": last_close,
                "prev_fast_ema": prev_fast,
                "prev_slow_ema": prev_slow,
                "last_fast_ema": last_fast,
                "last_slow_ema": last_slow,
                "ema_aligned": ema_aligned,
                "price_above_fast": price_above_fast,
                "ema_spread_pct": ema_spread_pct,
                "trend_follow_entry": trend_follow_entry,
                "entry_signal": entry_signal,
                "volume_ratio": volume_ratio,
                "atr_value": atr_value,
                "atr_pct": atr_pct,
                "confirm_bullish": confirm_bullish,
                "base_free": base_free,
                "quote_free": quote_free,
                "has_position": has_position,
                "daily_realized_pnl_quote": daily_realized_pnl_quote,
                "pnl_pct": pnl_pct,
                "min_order_amount": settings.min_order_amount,
                "position_id": position_id,
                "highest_price_since_entry": highest_price_since_entry,
                "lowest_price_since_entry": lowest_price_since_entry,
                "trailing_armed": trailing_armed,
                "drawdown_from_high_pct": drawdown_from_high_pct,
                "trailing_activation_price": trailing_activation_price,
                "mfe_pct": mfe_pct,
                "mae_pct": mae_pct,
            }

            entry_steps = [
                FunnelStep(
                    stage="trend",
                    passed=entry_signal,
                    reason="no_entry_signal",
                    actual={
                        "bullish_signal": bullish,
                        "trend_follow_entry": trend_follow_entry,
                        "ema_aligned": ema_aligned,
                        "price_above_fast": price_above_fast,
                        "ema_spread_pct": ema_spread_pct,
                    },
                    required={
                        "bullish_signal_or_trend_follow_entry": True,
                        "min_ema_spread_pct": settings.min_ema_spread_pct,
                    },
                ),
                FunnelStep(
                    stage="position",
                    passed=not has_position,
                    reason="position_exists",
                    actual={"has_position": has_position},
                    required={"has_position": False},
                ),
                FunnelStep(
                    stage="cooldown",
                    passed=not in_cooldown,
                    reason="cooldown_active",
                    actual={
                        "cooldown_remaining_sec": cooldown_remaining,
                        "base_cooldown_remaining_sec": base_cooldown_remaining,
                        "stop_loss_cooldown_remaining_sec": stop_loss_cooldown_remaining,
                    },
                    required={
                        "base_min_trade_interval_sec": settings.min_trade_interval_sec,
                        "stop_loss_reentry_cooldown_sec": settings.stop_loss_reentry_cooldown_sec,
                        "cooldown_inactive": True,
                    },
                ),
                FunnelStep(
                    stage="volume",
                    passed=volume_filter_passed,
                    reason="volume_low" if volume_ratio is not None else "volume_data_missing",
                    actual={"volume_ratio": volume_ratio},
                    required={"min_volume_ratio": settings.min_volume_ratio},
                ),
                FunnelStep(
                    stage="atr",
                    passed=atr_filter_passed,
                    reason=choose_atr_reason(
                        atr_pct,
                        min_value=settings.min_atr_pct,
                        max_value=settings.max_atr_pct,
                    ),
                    actual={"atr_pct": atr_pct},
                    required={
                        "min_atr_pct": settings.min_atr_pct,
                        "max_atr_pct": settings.max_atr_pct,
                    },
                ),
                FunnelStep(
                    stage="higher_timeframe",
                    passed=(
                        not settings.enable_confirm_timeframe_filter or confirm_bullish
                    ),
                    reason="higher_timeframe_not_bullish",
                    actual={"confirm_bullish": confirm_bullish},
                    required={"confirm_bullish": True},
                ),
                FunnelStep(
                    stage="risk_limit",
                    passed=not daily_loss_limit_reached,
                    reason="daily_loss_limit_reached",
                    actual={"daily_realized_pnl_quote": daily_realized_pnl_quote},
                    required={
                        "min_daily_realized_pnl_quote": -config["max_daily_loss_quote"]
                    },
                ),
                FunnelStep(
                    stage="order_value",
                    passed=order_value > min_buy_order_value,
                    reason="order_value_too_small",
                    actual={"order_value_quote": order_value},
                    required={"min_buy_order_value": min_buy_order_value},
                ),
                FunnelStep(
                    stage="order_amount",
                    passed=estimated_entry_amount >= settings.min_order_amount,
                    reason="order_amount_too_small",
                    actual={"order_amount": estimated_entry_amount},
                    required={"min_order_amount": settings.min_order_amount},
                ),
            ]
            entry_ready, _ = structured_logger.run_funnel(
                symbol=symbol,
                side="entry",
                steps=entry_steps,
                metrics=common_metrics,
                ready_stage="buy_ready",
                ready_reason="entry_conditions_met",
            )

            exit_steps = [
                FunnelStep(
                    stage="position",
                    passed=has_position,
                    reason="no_position",
                    actual={"has_position": has_position},
                    required={"has_position": True},
                ),
                FunnelStep(
                    stage="exit_trigger",
                    passed=(stop_triggered or trailing_stop_triggered or trend_exit_triggered),
                    reason="no_exit_signal",
                    actual={
                        "stop_triggered": stop_triggered,
                        "trailing_stop_triggered": trailing_stop_triggered,
                        "trend_exit_triggered": trend_exit_triggered,
                    },
                    required={"exit_triggered": True},
                ),
                FunnelStep(
                    stage="amount",
                    passed=estimated_exit_amount >= settings.min_order_amount,
                    reason="sell_amount_too_small",
                    actual={"sell_amount": estimated_exit_amount},
                    required={"min_order_amount": settings.min_order_amount},
                ),
            ]
            exit_ready, _ = structured_logger.run_funnel(
                symbol=symbol,
                side="exit",
                steps=exit_steps,
                metrics=common_metrics,
                ready_stage="sell_ready",
                ready_reason=(
                    "stop_loss_triggered"
                    if stop_triggered
                    else "trailing_stop_triggered"
                    if trailing_stop_triggered
                    else "trend_exit_triggered"
                ),
            )

            if entry_ready:
                if order_value <= min_buy_order_value:
                    log(f"[{symbol}] 주문 금액이 너무 작아 진입을 생략합니다.")
                elif estimated_entry_amount < settings.min_order_amount:
                    log(
                        f"[{symbol}] 추정 매수 수량({estimated_entry_amount:.8f} {base})이 "
                        f"최소 주문 수량({settings.min_order_amount:.5f} {base})보다 작아 진입을 생략합니다."
                    )
                else:
                    order_value = float(f"{order_value:.8f}")
                    structured_logger.log_strategy(
                        symbol=symbol,
                        side="entry",
                        stage="order_requested",
                        result="requested",
                        reason="market_buy_requested",
                        actual={"order_value_quote": order_value},
                        metrics=common_metrics,
                    )
                    try:
                        order = place_market_order_okx(
                            exchange,
                            symbol,
                            "buy",
                            order_value,
                            tgt_ccy="quote_ccy",
                        )
                    except Exception as order_error:
                        structured_logger.log_strategy(
                            symbol=symbol,
                            side="entry",
                            stage="filled",
                            result="error",
                            reason="order_failed",
                            actual={"order_value_quote": order_value},
                            metrics=common_metrics,
                            extra={
                                "error": repr(order_error),
                                "strategy_version": settings.version,
                            },
                        )
                        structured_logger.log_system(
                            level="WARNING",
                            event="order_failed",
                            message="BTC 매수 주문 요청이 실패했습니다.",
                            symbol=symbol,
                            context={
                                "side": "buy",
                                "order_value_quote": order_value,
                                "error": repr(order_error),
                            },
                        )
                        raise
                    estimated_amount = estimated_entry_amount
                    entry_price = last_close
                    entry_opened_at = time.time()
                    position_id = f"{symbol}:{int(entry_opened_at)}"
                    highest_price_since_entry = last_close
                    lowest_price_since_entry = last_close
                    trailing_armed = False
                    trailing_armed_at = None
                    trailing_activation_price = None
                    last_trade_at = time.time()
                    structured_logger.log_strategy(
                        symbol=symbol,
                        side="entry",
                        stage="filled",
                        result="filled",
                        reason="buy_filled",
                        actual={
                            "filled_amount": estimated_amount,
                            "order_value_quote": order_value,
                        },
                        metrics={**common_metrics, "estimated_entry_price_after": entry_price},
                    )
                    structured_logger.log_trade_event(
                        symbol=symbol,
                        side="buy",
                        reason="entry",
                        result="filled",
                        actual={
                            "filled_amount": estimated_amount,
                            "order_value_quote": order_value,
                        },
                        metrics={**common_metrics, "estimated_entry_price_after": entry_price},
                    )
                    logger.log_trade_banner(
                        RED,
                        f"[{symbol}] BTC EMA 전략 매수 체결",
                        f"주문 결과: {order}",
                    )
                    notifier.notify_buy_fill(
                        "OKX-BTC",
                        symbol,
                        f"사용 금액: {order_value:.8f} {quote}\n"
                        f"추정 진입가: {entry_price:.2f}",
                    )
                    trade_history.log_fill(
                        exchange_name="OKX",
                        program_name="okx_btc_ema_trend_bot",
                        strategy_version=settings.version,
                        symbol=symbol,
                        side="buy",
                        reason="entry",
                        base_currency=base,
                        quote_currency=quote,
                        amount=estimated_amount,
                        order_value_quote=order_value,
                        reference_price=last_close,
                        estimated_entry_price=entry_price,
                        base_free_before=base_free,
                        quote_free_before=quote_free,
                        remaining_base_after_estimate=base_free + estimated_amount,
                        timeframe=settings.timeframe,
                        ma_period=settings.slow_ema_period,
                        position_id=position_id,
                        leg_index=0,
                        is_final_exit=False,
                        raw_order=order,
                        extra={
                            "strategy_version": settings.version,
                            "strategy": "btc_ema_trend",
                            "volume_ratio": volume_ratio,
                            "atr_value": atr_value,
                            "atr_pct": atr_pct,
                            "confirm_bullish": confirm_bullish,
                        },
                    )

            elif exit_ready:
                amount = estimated_exit_amount
                if amount >= settings.min_order_amount:
                    if stop_triggered:
                        sell_reason = "stop_loss"
                        notify_fn = notifier.notify_stop_loss_fill
                        title = "BTC EMA 전략 손절 체결"
                    elif trailing_stop_triggered:
                        sell_reason = "trailing_take_profit"
                        notify_fn = notifier.notify_sell_fill
                        title = "BTC EMA 전략 트레일링 익절 체결"
                    else:
                        sell_reason = "trend_exit"
                        notify_fn = notifier.notify_sell_fill
                        title = "BTC EMA 전략 추세 종료 청산"

                    structured_logger.log_strategy(
                        symbol=symbol,
                        side="exit",
                        stage="order_requested",
                        result="requested",
                        reason="market_sell_requested",
                        actual={"sell_amount": amount},
                        metrics=common_metrics,
                    )
                    try:
                        order = place_market_order_okx(
                            exchange,
                            symbol,
                            "sell",
                            amount,
                            tgt_ccy="base_ccy",
                        )
                    except Exception as order_error:
                        structured_logger.log_strategy(
                            symbol=symbol,
                            side="exit",
                            stage="filled",
                            result="error",
                            reason="order_failed",
                            actual={"sell_amount": amount},
                            metrics=common_metrics,
                            extra={
                                "error": repr(order_error),
                                "strategy_version": settings.version,
                            },
                        )
                        structured_logger.log_system(
                            level="WARNING",
                            event="order_failed",
                            message="BTC 매도 주문 요청이 실패했습니다.",
                            symbol=symbol,
                            context={
                                "side": "sell",
                                "sell_amount": amount,
                                "error": repr(order_error),
                            },
                        )
                        raise
                    realized_pnl_pct = 0.0
                    realized_pnl_quote = 0.0
                    fee_quote_estimate = None
                    net_realized_pnl_quote = None
                    net_realized_pnl_pct = None
                    holding_seconds = None
                    trailing_armed_seconds = None
                    activation_to_exit_seconds = None
                    trailing_armed_at_iso = (
                        datetime.fromtimestamp(trailing_armed_at).astimezone().isoformat()
                        if trailing_armed_at is not None
                        else None
                    )
                    if entry_opened_at is not None:
                        holding_seconds = max(0.0, time.time() - entry_opened_at)
                    if entry_opened_at is not None and trailing_armed_at is not None:
                        trailing_armed_seconds = max(0.0, trailing_armed_at - entry_opened_at)
                    if trailing_armed_at is not None:
                        activation_to_exit_seconds = max(0.0, time.time() - trailing_armed_at)
                    if entry_price:
                        realized_pnl_pct = (last_close - entry_price) / entry_price * 100
                        realized_pnl_quote = (last_close - entry_price) * amount
                        (
                            fee_quote_estimate,
                            net_realized_pnl_quote,
                            net_realized_pnl_pct,
                        ) = estimate_round_trip_net_pnl(
                            entry_price=entry_price,
                            exit_price=last_close,
                            amount=amount,
                            fee_rate_pct=config["fee_rate_pct"],
                            realized_pnl_quote=realized_pnl_quote,
                        )
                        daily_realized_pnl_quote += realized_pnl_quote
                    if stop_triggered:
                        last_stop_loss_at = time.time()
                    last_trade_at = time.time()
                    structured_logger.log_strategy(
                        symbol=symbol,
                        side="exit",
                        stage="filled",
                        result="filled",
                        reason=f"{sell_reason}_filled",
                        actual={
                            "filled_amount": amount,
                            "realized_pnl_pct": realized_pnl_pct,
                            "realized_pnl_quote": realized_pnl_quote,
                        },
                        metrics={**common_metrics, "holding_seconds": holding_seconds},
                    )
                    structured_logger.log_trade_event(
                        symbol=symbol,
                        side="sell",
                        reason=sell_reason,
                        result="filled",
                        actual={
                            "filled_amount": amount,
                            "realized_pnl_pct": realized_pnl_pct,
                            "realized_pnl_quote": realized_pnl_quote,
                        },
                        metrics={**common_metrics, "holding_seconds": holding_seconds},
                    )
                    logger.log_trade_banner(
                        BLUE,
                        f"[{symbol}] {title}",
                        f"주문 결과: {order} | 수익률={realized_pnl_pct:.2f}%",
                    )
                    notify_fn(
                        "OKX-BTC",
                        symbol,
                        f"사유: {sell_reason}\n"
                        f"수익률: {realized_pnl_pct:.2f}%\n"
                        f"실현 손익: {realized_pnl_quote:.4f} {quote}",
                    )
                    trade_history.log_fill(
                        exchange_name="OKX",
                        program_name="okx_btc_ema_trend_bot",
                        strategy_version=settings.version,
                        symbol=symbol,
                        side="sell",
                        reason=sell_reason,
                        base_currency=base,
                        quote_currency=quote,
                        amount=amount,
                        order_value_quote=amount * last_close,
                        reference_price=last_close,
                        estimated_entry_price=entry_price,
                        realized_pnl_pct=realized_pnl_pct,
                        realized_pnl_quote=realized_pnl_quote,
                        daily_realized_pnl_quote_after=daily_realized_pnl_quote,
                        base_free_before=base_free,
                        quote_free_before=quote_free,
                        remaining_base_after_estimate=0.0,
                        timeframe=settings.timeframe,
                        ma_period=settings.slow_ema_period,
                        position_id=position_id,
                        leg_index=1,
                        is_final_exit=True,
                        holding_seconds=holding_seconds,
                        fee_rate_pct=config["fee_rate_pct"],
                        fee_quote_estimate=fee_quote_estimate,
                        net_realized_pnl_quote=net_realized_pnl_quote,
                        net_realized_pnl_pct=net_realized_pnl_pct,
                        highest_price_since_entry=highest_price_since_entry,
                        lowest_price_since_entry=lowest_price_since_entry,
                        mfe_pct=mfe_pct,
                        mae_pct=mae_pct,
                        drawdown_from_high_pct=drawdown_from_high_pct,
                        trailing_armed=trailing_armed,
                        trailing_armed_at=trailing_armed_at_iso,
                        trailing_activation_price=trailing_activation_price,
                        trailing_armed_seconds=trailing_armed_seconds,
                        activation_to_exit_seconds=activation_to_exit_seconds,
                        raw_order=order,
                        extra={
                            "strategy_version": settings.version,
                            "strategy": "btc_ema_trend",
                            "volume_ratio": volume_ratio,
                            "atr_value": atr_value,
                            "atr_pct": atr_pct,
                            "confirm_bullish": confirm_bullish,
                            "stop_price": stop_price,
                            "take_profit_price": take_profit_price,
                            "highest_price_since_entry": highest_price_since_entry,
                            "trailing_armed": trailing_armed,
                            "drawdown_from_high_pct": drawdown_from_high_pct,
                            "trend_exit_triggered": trend_exit_triggered,
                            "holding_seconds": holding_seconds,
                        },
                    )
                    log(
                        f"[{symbol}] 실현 손익: {realized_pnl_quote:.4f} {quote} | "
                        f"오늘 누적 실현 손익: {daily_realized_pnl_quote:.4f} {quote}"
                    )
                    entry_price = None
                    entry_opened_at = None
                    position_id = None
                    highest_price_since_entry = None
                    lowest_price_since_entry = None
                    trailing_armed = False
                    trailing_armed_at = None
                    trailing_activation_price = None
                else:
                    log(
                        f"[{symbol}] 추정 매도 수량({amount:.8f} {base})이 "
                        f"최소 주문 수량({settings.min_order_amount:.5f} {base})보다 작아 청산을 생략합니다."
                    )
            else:
                log(f"[{symbol}] BTC EMA 전략 조건에 해당하지 않아 대기합니다.")

        except Exception as e:
            log(f"[{symbol}] 에러 발생: {repr(e)}")
            log(traceback.format_exc().rstrip())
            structured_logger.log_system(
                level="ERROR",
                event="loop_error",
                message="BTC 전략 루프 중 예외가 발생했습니다.",
                symbol=symbol,
                context={"error": repr(e)},
            )
            notifier.notify_error_message("OKX-BTC", symbol, repr(e))

        time.sleep(settings.loop_interval_sec)


if __name__ == "__main__":
    run_bot()
