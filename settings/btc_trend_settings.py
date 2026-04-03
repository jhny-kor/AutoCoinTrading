"""
BTC 전용 EMA 추세추종 설정 로더

- 단일 `.env` 대신 중앙 환경 로더를 통해 `.env.settings`, `.env.secrets`, `.env.local` 까지 읽을 수 있게 정리

- 레짐별 포지션 비중 스케일 설정을 추가해 BTC도 상승장/횡보장/저에너지장에 따라 진입 크기를 다르게 조절할 수 있게 확장했다.
- 노이즈 비율 기반 동적 진입 문턱값 설정을 추가해 BTC 진입 기준을 장 상태에 맞춰 자동 보정할 수 있게 확장했다.
- 2차 강화용으로 진입 상태 머신과 체결률 품질 가드 설정을 추가했다.
- BTC 전용 전략에 RSI, 볼린저 밴드 폭, EMA 기울기 필터와 신호 스코어 기준을 추가해 진입 품질을 강화했다.
- BTC 가 CHOPPY 레짐일 때는 심볼별 추가 최소 거래량 기준을 적용하도록 설정을 확장했다.
- BTC/USDT 같은 특정 심볼만 더 엄격하게 진입시키도록 심볼별 EMA 스프레드/거래량 기준 오버라이드를 추가했다.
- BTC 진입 필터를 조금 더 보수적으로 하고, 강한 다중 상승 추세에서는 짧은 조정을 견디는 설정을 추가했다.
- BTC 익절가 도달 시 1회 부분 익절 후 잔량을 트레일링/순익 보호로 관리하는 설정을 추가했다.
- BTC 수익성 청산 직후에는 재진입과 추가매수를 잠시 막는 전용 쿨다운 설정을 추가했다.
- 수수료를 반영해도 순익이 남을 때 추세 약화가 나오면 빠르게 보호 익절하는 설정을 추가했다.
- BTC 손절 직후에는 일반 거래 간격보다 더 길게 쉬도록 전용 재진입 쿨다운 설정을 추가했다.
- BTC 는 수익 구간에서 1회만 추가매수하는 보수적 피라미딩 설정을 .env 에서 읽도록 확장했다.
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

from settings.env import load_project_env
from strategy_settings import parse_symbol_float_map


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
    trend_follow_requires_ema_slope_positive: bool
    ema_slope_lookback: int
    enable_rsi_filter: bool
    rsi_period: int
    rsi_entry_min: float
    rsi_entry_max: float
    enable_bb_width_filter: bool
    bb_period: int
    bb_stddev_multiplier: float
    min_bb_width_pct: float
    max_bb_width_pct: float
    signal_score_min: float
    enable_noise_ratio_adaptation: bool
    noise_ratio_lookback: int
    noise_ratio_baseline: float
    noise_ratio_min_multiplier: float
    noise_ratio_max_multiplier: float
    noise_ratio_signal_score_weight: float
    entry_confirmation_loops: int
    enable_fill_quality_guard: bool
    fill_quality_lookback_sec: int
    fill_quality_min_fill_ratio: float
    fill_quality_min_sample_count: int
    min_ema_spread_pct: float
    min_ema_spread_pct_map: dict[str, float]
    enable_fee_protect_exit: bool
    fee_protect_min_net_pnl_pct: float
    enable_bull_pullback_hold: bool
    bull_pullback_tolerance_pct: float
    bull_pullback_min_spread_pct: float
    atr_period: int
    min_atr_pct: float
    min_atr_pct_map: dict[str, float]
    max_atr_pct: float
    volume_lookback: int
    min_volume_ratio: float
    min_volume_ratio_map: dict[str, float]
    choppy_min_volume_ratio_map: dict[str, float]
    position_ratio: float
    position_ratio_map: dict[str, float]
    enable_regime_position_scaling: bool
    regime_position_scale_map: dict[str, float]
    min_order_amount: float
    min_trade_interval_sec: int
    stop_loss_reentry_cooldown_sec: int
    profit_exit_reentry_cooldown_sec: int
    enable_partial_take_profit: bool
    partial_take_profit_ratio: float
    enable_pyramid_add_on: bool
    pyramid_trigger_profit_pct: float
    pyramid_position_ratio: float
    pyramid_max_add_ons: int
    stop_mode: str
    take_profit_mode: str
    stop_atr_multiple: float
    take_profit_atr_multiple: float
    trailing_drawdown_pct: float
    swing_lookback: int
    exit_on_bearish_cross: bool
    loop_interval_sec: int

    def get_position_ratio(self, symbol: str) -> float:
        """심볼별 초기 진입 비중 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        return self.position_ratio_map.get(symbol, self.position_ratio)

    def get_min_ema_spread_pct(self, symbol: str) -> float:
        """심볼별 EMA 스프레드 기준 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        return self.min_ema_spread_pct_map.get(symbol, self.min_ema_spread_pct)

    def get_min_volume_ratio(self, symbol: str) -> float:
        """심볼별 거래량 기준 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        return self.min_volume_ratio_map.get(symbol, self.min_volume_ratio)

    def get_min_atr_pct(self, symbol: str) -> float:
        """심볼별 최소 ATR 기준 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        return self.min_atr_pct_map.get(symbol, self.min_atr_pct)

    def get_regime_position_scale(self, regime: str | None) -> float:
        """레짐별 포지션 비중 스케일을 반환한다."""
        if not self.enable_regime_position_scaling:
            return 1.0
        if not regime:
            return 1.0
        return self.regime_position_scale_map.get(regime, 1.0)

    def get_effective_min_volume_ratio(
        self, symbol: str, regime: str | None = None
    ) -> float:
        """심볼별 기본 거래량 기준에 레짐별 추가 기준을 반영해 반환한다."""
        base_ratio = self.get_min_volume_ratio(symbol)
        if regime == "CHOPPY":
            return max(
                base_ratio,
                self.choppy_min_volume_ratio_map.get(symbol, base_ratio),
            )
        return base_ratio


def load_btc_trend_settings() -> BtcTrendSettings:
    """BTC 전용 EMA 추세추종 설정을 불러온다."""
    load_project_env()

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
        trend_follow_requires_ema_slope_positive=parse_bool(
            os.getenv("BTC_TREND_REQUIRE_EMA_SLOPE_POSITIVE", "true"),
            default=True,
        ),
        ema_slope_lookback=int(os.getenv("BTC_TREND_EMA_SLOPE_LOOKBACK", "3")),
        enable_rsi_filter=parse_bool(
            os.getenv("BTC_TREND_ENABLE_RSI_FILTER", "true"),
            default=True,
        ),
        rsi_period=int(os.getenv("BTC_TREND_RSI_PERIOD", "14")),
        rsi_entry_min=float(os.getenv("BTC_TREND_RSI_ENTRY_MIN", "40")),
        rsi_entry_max=float(os.getenv("BTC_TREND_RSI_ENTRY_MAX", "72")),
        enable_bb_width_filter=parse_bool(
            os.getenv("BTC_TREND_ENABLE_BB_WIDTH_FILTER", "true"),
            default=True,
        ),
        bb_period=int(os.getenv("BTC_TREND_BB_PERIOD", "20")),
        bb_stddev_multiplier=float(
            os.getenv("BTC_TREND_BB_STDDEV_MULTIPLIER", "2.0")
        ),
        min_bb_width_pct=float(os.getenv("BTC_TREND_MIN_BB_WIDTH_PCT", "0.20")),
        max_bb_width_pct=float(os.getenv("BTC_TREND_MAX_BB_WIDTH_PCT", "8.00")),
        signal_score_min=float(os.getenv("BTC_TREND_SIGNAL_SCORE_MIN", "55")),
        enable_noise_ratio_adaptation=parse_bool(
            os.getenv("BTC_TREND_ENABLE_NOISE_RATIO_ADAPTATION", "true"),
            default=True,
        ),
        noise_ratio_lookback=int(os.getenv("BTC_TREND_NOISE_RATIO_LOOKBACK", "20")),
        noise_ratio_baseline=float(
            os.getenv("BTC_TREND_NOISE_RATIO_BASELINE", "0.50")
        ),
        noise_ratio_min_multiplier=float(
            os.getenv("BTC_TREND_NOISE_RATIO_MIN_MULTIPLIER", "0.70")
        ),
        noise_ratio_max_multiplier=float(
            os.getenv("BTC_TREND_NOISE_RATIO_MAX_MULTIPLIER", "1.30")
        ),
        noise_ratio_signal_score_weight=float(
            os.getenv("BTC_TREND_NOISE_RATIO_SIGNAL_SCORE_WEIGHT", "12.0")
        ),
        entry_confirmation_loops=int(
            os.getenv("BTC_TREND_ENTRY_CONFIRMATION_LOOPS", "2")
        ),
        enable_fill_quality_guard=parse_bool(
            os.getenv("BTC_TREND_ENABLE_FILL_QUALITY_GUARD", "true"),
            default=True,
        ),
        fill_quality_lookback_sec=int(
            os.getenv("BTC_TREND_FILL_QUALITY_LOOKBACK_SEC", "3600")
        ),
        fill_quality_min_fill_ratio=float(
            os.getenv("BTC_TREND_FILL_QUALITY_MIN_FILL_RATIO", "0.95")
        ),
        fill_quality_min_sample_count=int(
            os.getenv("BTC_TREND_FILL_QUALITY_MIN_SAMPLE_COUNT", "1")
        ),
        min_ema_spread_pct=float(os.getenv("BTC_TREND_MIN_EMA_SPREAD_PCT", "0.002")),
        min_ema_spread_pct_map=parse_symbol_float_map(
            os.getenv("BTC_TREND_MIN_EMA_SPREAD_PCT_MAP", "")
        ),
        enable_fee_protect_exit=parse_bool(
            os.getenv("BTC_TREND_ENABLE_FEE_PROTECT_EXIT", "true"),
            default=True,
        ),
        fee_protect_min_net_pnl_pct=float(
            os.getenv("BTC_TREND_FEE_PROTECT_MIN_NET_PNL_PCT", "0.12")
        ),
        enable_bull_pullback_hold=parse_bool(
            os.getenv("BTC_TREND_ENABLE_BULL_PULLBACK_HOLD", "true"),
            default=True,
        ),
        bull_pullback_tolerance_pct=float(
            os.getenv("BTC_TREND_BULL_PULLBACK_TOLERANCE_PCT", "0.20")
        ),
        bull_pullback_min_spread_pct=float(
            os.getenv("BTC_TREND_BULL_PULLBACK_MIN_SPREAD_PCT", "0.10")
        ),
        atr_period=int(os.getenv("BTC_TREND_ATR_PERIOD", "14")),
        min_atr_pct=float(os.getenv("BTC_TREND_MIN_ATR_PCT", "0.08")),
        min_atr_pct_map=parse_symbol_float_map(
            os.getenv("BTC_TREND_MIN_ATR_PCT_MAP", "")
        ),
        max_atr_pct=float(os.getenv("BTC_TREND_MAX_ATR_PCT", "2.50")),
        volume_lookback=int(os.getenv("BTC_TREND_VOLUME_LOOKBACK", "20")),
        min_volume_ratio=float(os.getenv("BTC_TREND_MIN_VOLUME_RATIO", "1.05")),
        min_volume_ratio_map=parse_symbol_float_map(
            os.getenv("BTC_TREND_MIN_VOLUME_RATIO_MAP", "")
        ),
        choppy_min_volume_ratio_map=parse_symbol_float_map(
            os.getenv("BTC_TREND_CHOPPY_MIN_VOLUME_RATIO_MAP", "")
        ),
        position_ratio=float(os.getenv("BTC_TREND_POSITION_RATIO", "0.25")),
        position_ratio_map=parse_symbol_float_map(
            os.getenv("BTC_TREND_POSITION_RATIO_MAP", "")
        ),
        enable_regime_position_scaling=parse_bool(
            os.getenv("BTC_TREND_ENABLE_REGIME_POSITION_SCALING", "true"),
            default=True,
        ),
        regime_position_scale_map=parse_symbol_float_map(
            os.getenv(
                "BTC_TREND_REGIME_POSITION_SCALE_MAP",
                "TRENDING:1.10,BREAKOUT_ATTEMPT:0.90,CHOPPY:0.50,LOW_ENERGY:0.00,OVERHEATED:0.30,EXHAUSTION_RISK:0.00",
            )
        ),
        min_order_amount=float(os.getenv("BTC_TREND_MIN_ORDER_AMOUNT", "0.00001")),
        min_trade_interval_sec=int(os.getenv("BTC_TREND_MIN_TRADE_INTERVAL_SEC", "300")),
        stop_loss_reentry_cooldown_sec=int(
            os.getenv("BTC_TREND_STOP_LOSS_REENTRY_COOLDOWN_SEC", "600")
        ),
        profit_exit_reentry_cooldown_sec=int(
            os.getenv("BTC_TREND_PROFIT_EXIT_REENTRY_COOLDOWN_SEC", "600")
        ),
        enable_partial_take_profit=parse_bool(
            os.getenv("BTC_TREND_ENABLE_PARTIAL_TAKE_PROFIT", "true"),
            default=True,
        ),
        partial_take_profit_ratio=float(
            os.getenv("BTC_TREND_PARTIAL_TAKE_PROFIT_RATIO", "0.5")
        ),
        enable_pyramid_add_on=parse_bool(
            os.getenv("BTC_TREND_ENABLE_PYRAMID_ADD_ON", "true"),
            default=True,
        ),
        pyramid_trigger_profit_pct=float(
            os.getenv("BTC_TREND_PYRAMID_TRIGGER_PROFIT_PCT", "0.35")
        ),
        pyramid_position_ratio=float(
            os.getenv("BTC_TREND_PYRAMID_POSITION_RATIO", "0.15")
        ),
        pyramid_max_add_ons=int(os.getenv("BTC_TREND_PYRAMID_MAX_ADD_ONS", "1")),
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
