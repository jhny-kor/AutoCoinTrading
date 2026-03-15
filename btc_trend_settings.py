"""
BTC 전용 EMA 추세추종 설정 로더

- BTC 손절 직후에는 일반 거래 간격보다 더 길게 쉬도록 전용 재진입 쿨다운 설정을 추가했다.
- BTC 전략 버전 이름을 .env 에서 읽어 로그와 체결 이력에 함께 남길 수 있도록 확장
- BTC 진입 신호를 골든크로스뿐 아니라 EMA 상승 정렬 유지 구간까지 허용하는 설정을 추가했다.
- BTC 전용 최소 거래 간격 기본값을 300초로 낮춰 실환경 .env 와 기본 동작을 맞췄다.
- BTC 전용 전략에서 사용할 타임프레임, EMA, ATR, 거래량 기준을 .env 에서 읽는다.
- 5분봉 또는 15분봉 기반 추세추종을 실험할 수 있도록 공통 설정을 제공한다.
- 손절/익절은 ATR 또는 최근 스윙 기준 중 선택할 수 있도록 지원한다.
- OKX BTC 최소 주문수량 같은 거래소별 주문 기준도 .env 에서 읽어 선제 차단할 수 있도록 지원한다.
- 익절 구간 진입 후 최고가 대비 되돌림으로 전량 청산하는 트레일링 설정도 함께 읽도록 지원한다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def parse_bool(raw: str | None, default: bool = False) -> bool:
    """문자열 불리언 값을 파싱한다."""
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class BtcTrendSettings:
    """BTC 전용 EMA 추세추종 설정."""

    version: str
    timeframe: str
    confirm_timeframe: str
    enable_confirm_timeframe_filter: bool
    fast_ema_period: int
    slow_ema_period: int
    confirm_ema_period: int
    enable_trend_follow_entry: bool
    trend_follow_requires_price_above_fast: bool
    min_ema_spread_pct: float
    atr_period: int
    min_atr_pct: float
    max_atr_pct: float
    volume_lookback: int
    min_volume_ratio: float
    position_ratio: float
    min_order_amount: float
    min_trade_interval_sec: int
    stop_loss_reentry_cooldown_sec: int
    stop_mode: str
    take_profit_mode: str
    stop_atr_multiple: float
    take_profit_atr_multiple: float
    trailing_drawdown_pct: float
    swing_lookback: int
    exit_on_bearish_cross: bool
    loop_interval_sec: int


def load_btc_trend_settings() -> BtcTrendSettings:
    """BTC 전용 EMA 추세추종 설정을 불러온다."""
    load_dotenv()

    return BtcTrendSettings(
        version=os.getenv("BTC_TREND_VERSION", "btc_mid_v1").strip(),
        timeframe=os.getenv("BTC_TREND_TIMEFRAME", "5m"),
        confirm_timeframe=os.getenv("BTC_TREND_CONFIRM_TIMEFRAME", "15m"),
        enable_confirm_timeframe_filter=parse_bool(
            os.getenv("BTC_TREND_ENABLE_CONFIRM_FILTER", "true"),
            default=True,
        ),
        fast_ema_period=int(os.getenv("BTC_TREND_FAST_EMA_PERIOD", "9")),
        slow_ema_period=int(os.getenv("BTC_TREND_SLOW_EMA_PERIOD", "21")),
        confirm_ema_period=int(os.getenv("BTC_TREND_CONFIRM_EMA_PERIOD", "21")),
        enable_trend_follow_entry=parse_bool(
            os.getenv("BTC_TREND_ENABLE_TREND_FOLLOW_ENTRY", "true"),
            default=True,
        ),
        trend_follow_requires_price_above_fast=parse_bool(
            os.getenv("BTC_TREND_REQUIRE_PRICE_ABOVE_FAST", "true"),
            default=True,
        ),
        min_ema_spread_pct=float(os.getenv("BTC_TREND_MIN_EMA_SPREAD_PCT", "0.002")),
        atr_period=int(os.getenv("BTC_TREND_ATR_PERIOD", "14")),
        min_atr_pct=float(os.getenv("BTC_TREND_MIN_ATR_PCT", "0.08")),
        max_atr_pct=float(os.getenv("BTC_TREND_MAX_ATR_PCT", "2.50")),
        volume_lookback=int(os.getenv("BTC_TREND_VOLUME_LOOKBACK", "20")),
        min_volume_ratio=float(os.getenv("BTC_TREND_MIN_VOLUME_RATIO", "1.05")),
        position_ratio=float(os.getenv("BTC_TREND_POSITION_RATIO", "0.25")),
        min_order_amount=float(os.getenv("BTC_TREND_MIN_ORDER_AMOUNT", "0.00001")),
        min_trade_interval_sec=int(os.getenv("BTC_TREND_MIN_TRADE_INTERVAL_SEC", "300")),
        stop_loss_reentry_cooldown_sec=int(
            os.getenv("BTC_TREND_STOP_LOSS_REENTRY_COOLDOWN_SEC", "600")
        ),
        stop_mode=os.getenv("BTC_TREND_STOP_MODE", "atr").strip().lower(),
        take_profit_mode=os.getenv("BTC_TREND_TAKE_PROFIT_MODE", "atr").strip().lower(),
        stop_atr_multiple=float(os.getenv("BTC_TREND_STOP_ATR_MULTIPLE", "1.5")),
        take_profit_atr_multiple=float(
            os.getenv("BTC_TREND_TAKE_PROFIT_ATR_MULTIPLE", "2.5")
        ),
        trailing_drawdown_pct=float(
            os.getenv("BTC_TREND_TRAILING_DRAWDOWN_PCT", "0.8")
        ),
        swing_lookback=int(os.getenv("BTC_TREND_SWING_LOOKBACK", "10")),
        exit_on_bearish_cross=parse_bool(
            os.getenv("BTC_TREND_EXIT_ON_BEARISH_CROSS", "true"),
            default=True,
        ),
        loop_interval_sec=int(os.getenv("BTC_TREND_LOOP_INTERVAL_SEC", "20")),
    )
