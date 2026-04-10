"""
수정 요약
- 2026-04-10: BTC 손절 후 일정 시간 경과와 높은 점수 조건이면 fresh cross 없이 재진입 가능한 완화 설정을 추가
- 2026-04-09: 손절 후 재진입은 최소 시간과 signal/confirm/fresh cross 복구를 함께 보는 패턴 기반 설정을 추가
- 2026-04-08: BTC 심볼별 진입 확인 루프 override map 을 추가해 BTC/USDT 와 BTC/KRW 를 다르게 운용할 수 있게 확장
- 2026-04-06: Donchian Channel 돌파 진입 파라미터 추가
- 심볼별 CHOPPY 진입 거래량 최소 기준을 설정하는 MAP 을 추가해 BTC/KRW 의 기준을 2.5 로 보수화했다.
- 2026-04-03: BTC 설정을 canonical runtime TOML 과 typed access helper 기준으로 읽도록 정리
BTC 전용 EMA 추세추종 설정 로더

- `config/runtime.toml`, `config/runtime.local.toml`, env override/secrets 레이어를 중앙 로더로 함께 읽는다.

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
- BTC 는 수익 구간에서 1회만 추가매수하는 보수적 피라미딩 설정을 canonical config 에서 읽도록 확장했다.
- BTC 전략 버전 이름을 canonical config 에서 읽어 로그와 체결 이력에 함께 남길 수 있도록 확장
- BTC 진입 신호를 골든크로스뿐 아니라 EMA 상승 정렬 유지 구간까지 허용하는 설정을 추가했다.
- BTC 전용 최소 거래 간격 기본값을 300초로 낮춰 현재 canonical config 와 기본 동작을 맞췄다.
- BTC 전용 전략에서 사용할 타임프레임, EMA, ATR, 거래량 기준을 canonical config 에서 읽는다.
- 5분봉 또는 15분봉 기반 추세추종을 실험할 수 있도록 공통 설정을 제공한다.
- 손절/익절은 ATR 또는 최근 스윙 기준 중 선택할 수 있도록 지원한다.
- OKX BTC 최소 주문수량 같은 거래소별 주문 기준도 canonical config 에서 읽어 선제 차단할 수 있도록 지원한다.
- 익절 구간 진입 후 최고가 대비 되돌림으로 전량 청산하는 트레일링 설정도 함께 읽도록 지원한다.
"""

from __future__ import annotations

from dataclasses import dataclass

from settings.config_access import config_bool, config_float, config_int, config_str, config_value
from settings.env import load_project_env
from strategy_settings import parse_float_float_map, parse_symbol_float_map, parse_symbol_int_map


@dataclass(frozen=True)
class BtcTrendSettings:
    """BTC 전용 EMA 추세추종 설정."""

    version: str
    entry_mode: str
    donchian_entry_lookback: int
    donchian_exit_lookback: int
    donchian_confirm_breakout_close: bool
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
    entry_confirmation_loops_map: dict[str, int]
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
    enable_atr_position_scaling: bool
    atr_position_scale_threshold_map: dict[float, float]
    min_order_amount: float
    min_trade_interval_sec: int
    stop_loss_reentry_cooldown_sec: int
    enable_stop_loss_pattern_reentry: bool
    stop_loss_pattern_min_cooldown_sec: int
    stop_loss_pattern_min_signal_score: float
    stop_loss_pattern_require_confirm_bullish: bool
    stop_loss_pattern_require_fresh_cross: bool
    stop_loss_pattern_relaxed_fresh_cross_after_sec_map: dict[str, int]
    stop_loss_pattern_relaxed_fresh_cross_min_signal_score_map: dict[str, float]
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

    def get_atr_position_scale(self, atr_pct: float | None) -> float:
        """ATR 퍼센트 기준 포지션 비중 스케일을 반환한다."""
        if not self.enable_atr_position_scaling:
            return 1.0
        if atr_pct is None:
            return 1.0

        matched_scales = [
            scale
            for threshold, scale in self.atr_position_scale_threshold_map.items()
            if atr_pct < threshold
        ]
        if not matched_scales:
            return 1.0
        return min(matched_scales)

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

    def get_entry_confirmation_loops(self, symbol: str) -> int:
        """심볼별 진입 확인 루프 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        return max(1, self.entry_confirmation_loops_map.get(symbol, self.entry_confirmation_loops))

    def get_relaxed_fresh_cross_after_sec(self, symbol: str) -> int:
        """심볼별 fresh cross 완화 대기 시간을 반환한다."""
        return max(0, self.stop_loss_pattern_relaxed_fresh_cross_after_sec_map.get(symbol, 0))

    def get_relaxed_fresh_cross_min_signal_score(self, symbol: str) -> float:
        """심볼별 fresh cross 완화 최소 점수를 반환한다."""
        return self.stop_loss_pattern_relaxed_fresh_cross_min_signal_score_map.get(symbol, 999.0)


def load_btc_trend_settings() -> BtcTrendSettings:
    """BTC 전용 EMA 추세추종 설정을 불러온다."""
    load_project_env()

    return BtcTrendSettings(
        version=config_str("btc_trend", "version", "btc_mid_v1", env_key="BTC_TREND_VERSION").strip(),
        entry_mode=config_str("btc_trend", "entry_mode", "ema", env_key="BTC_TREND_ENTRY_MODE").strip().lower(),
        donchian_entry_lookback=config_int("btc_trend", "donchian_entry_lookback", 20, env_key="BTC_TREND_DONCHIAN_ENTRY_LOOKBACK"),
        donchian_exit_lookback=config_int("btc_trend", "donchian_exit_lookback", 10, env_key="BTC_TREND_DONCHIAN_EXIT_LOOKBACK"),
        donchian_confirm_breakout_close=config_bool("btc_trend", "donchian_confirm_breakout_close", True, env_key="BTC_TREND_DONCHIAN_CONFIRM_BREAKOUT_CLOSE"),
        timeframe=config_str("btc_trend", "timeframe", "5m", env_key="BTC_TREND_TIMEFRAME"),
        confirm_timeframe=config_str("btc_trend", "confirm_timeframe", "15m", env_key="BTC_TREND_CONFIRM_TIMEFRAME"),
        enable_confirm_timeframe_filter=config_bool("btc_trend", "enable_confirm_filter", True, env_key="BTC_TREND_ENABLE_CONFIRM_FILTER"),
        fast_ema_period=config_int("btc_trend", "fast_ema_period", 9, env_key="BTC_TREND_FAST_EMA_PERIOD"),
        slow_ema_period=config_int("btc_trend", "slow_ema_period", 21, env_key="BTC_TREND_SLOW_EMA_PERIOD"),
        confirm_ema_period=config_int("btc_trend", "confirm_ema_period", 21, env_key="BTC_TREND_CONFIRM_EMA_PERIOD"),
        enable_trend_follow_entry=config_bool("btc_trend", "enable_trend_follow_entry", True, env_key="BTC_TREND_ENABLE_TREND_FOLLOW_ENTRY"),
        trend_follow_requires_price_above_fast=config_bool("btc_trend", "require_price_above_fast", True, env_key="BTC_TREND_REQUIRE_PRICE_ABOVE_FAST"),
        trend_follow_requires_ema_slope_positive=config_bool("btc_trend", "require_ema_slope_positive", True, env_key="BTC_TREND_REQUIRE_EMA_SLOPE_POSITIVE"),
        ema_slope_lookback=config_int("btc_trend", "ema_slope_lookback", 3, env_key="BTC_TREND_EMA_SLOPE_LOOKBACK"),
        enable_rsi_filter=config_bool("btc_trend", "enable_rsi_filter", True, env_key="BTC_TREND_ENABLE_RSI_FILTER"),
        rsi_period=config_int("btc_trend", "rsi_period", 14, env_key="BTC_TREND_RSI_PERIOD"),
        rsi_entry_min=config_float("btc_trend", "rsi_entry_min", 40, env_key="BTC_TREND_RSI_ENTRY_MIN"),
        rsi_entry_max=config_float("btc_trend", "rsi_entry_max", 72, env_key="BTC_TREND_RSI_ENTRY_MAX"),
        enable_bb_width_filter=config_bool("btc_trend", "enable_bb_width_filter", True, env_key="BTC_TREND_ENABLE_BB_WIDTH_FILTER"),
        bb_period=config_int("btc_trend", "bb_period", 20, env_key="BTC_TREND_BB_PERIOD"),
        bb_stddev_multiplier=config_float("btc_trend", "bb_stddev_multiplier", 2.0, env_key="BTC_TREND_BB_STDDEV_MULTIPLIER"),
        min_bb_width_pct=config_float("btc_trend", "min_bb_width_pct", 0.20, env_key="BTC_TREND_MIN_BB_WIDTH_PCT"),
        max_bb_width_pct=config_float("btc_trend", "max_bb_width_pct", 8.00, env_key="BTC_TREND_MAX_BB_WIDTH_PCT"),
        signal_score_min=config_float("btc_trend", "signal_score_min", 55, env_key="BTC_TREND_SIGNAL_SCORE_MIN"),
        enable_noise_ratio_adaptation=config_bool("btc_trend", "enable_noise_ratio_adaptation", True, env_key="BTC_TREND_ENABLE_NOISE_RATIO_ADAPTATION"),
        noise_ratio_lookback=config_int("btc_trend", "noise_ratio_lookback", 20, env_key="BTC_TREND_NOISE_RATIO_LOOKBACK"),
        noise_ratio_baseline=config_float("btc_trend", "noise_ratio_baseline", 0.50, env_key="BTC_TREND_NOISE_RATIO_BASELINE"),
        noise_ratio_min_multiplier=config_float("btc_trend", "noise_ratio_min_multiplier", 0.70, env_key="BTC_TREND_NOISE_RATIO_MIN_MULTIPLIER"),
        noise_ratio_max_multiplier=config_float("btc_trend", "noise_ratio_max_multiplier", 1.30, env_key="BTC_TREND_NOISE_RATIO_MAX_MULTIPLIER"),
        noise_ratio_signal_score_weight=config_float("btc_trend", "noise_ratio_signal_score_weight", 12.0, env_key="BTC_TREND_NOISE_RATIO_SIGNAL_SCORE_WEIGHT"),
        entry_confirmation_loops=config_int("btc_trend", "entry_confirmation_loops", 2, env_key="BTC_TREND_ENTRY_CONFIRMATION_LOOPS"),
        entry_confirmation_loops_map=parse_symbol_int_map(config_value("btc_trend", "entry_confirmation_loops_map", {}, env_key="BTC_TREND_ENTRY_CONFIRMATION_LOOPS_MAP")),
        enable_fill_quality_guard=config_bool("btc_trend", "enable_fill_quality_guard", True, env_key="BTC_TREND_ENABLE_FILL_QUALITY_GUARD"),
        fill_quality_lookback_sec=config_int("btc_trend", "fill_quality_lookback_sec", 3600, env_key="BTC_TREND_FILL_QUALITY_LOOKBACK_SEC"),
        fill_quality_min_fill_ratio=config_float("btc_trend", "fill_quality_min_fill_ratio", 0.95, env_key="BTC_TREND_FILL_QUALITY_MIN_FILL_RATIO"),
        fill_quality_min_sample_count=config_int("btc_trend", "fill_quality_min_sample_count", 1, env_key="BTC_TREND_FILL_QUALITY_MIN_SAMPLE_COUNT"),
        min_ema_spread_pct=config_float("btc_trend", "min_ema_spread_pct", 0.002, env_key="BTC_TREND_MIN_EMA_SPREAD_PCT"),
        min_ema_spread_pct_map=parse_symbol_float_map(config_value("btc_trend", "min_ema_spread_pct_map", {}, env_key="BTC_TREND_MIN_EMA_SPREAD_PCT_MAP")),
        enable_fee_protect_exit=config_bool("btc_trend", "enable_fee_protect_exit", True, env_key="BTC_TREND_ENABLE_FEE_PROTECT_EXIT"),
        fee_protect_min_net_pnl_pct=config_float("btc_trend", "fee_protect_min_net_pnl_pct", 0.12, env_key="BTC_TREND_FEE_PROTECT_MIN_NET_PNL_PCT"),
        enable_bull_pullback_hold=config_bool("btc_trend", "enable_bull_pullback_hold", True, env_key="BTC_TREND_ENABLE_BULL_PULLBACK_HOLD"),
        bull_pullback_tolerance_pct=config_float("btc_trend", "bull_pullback_tolerance_pct", 0.20, env_key="BTC_TREND_BULL_PULLBACK_TOLERANCE_PCT"),
        bull_pullback_min_spread_pct=config_float("btc_trend", "bull_pullback_min_spread_pct", 0.10, env_key="BTC_TREND_BULL_PULLBACK_MIN_SPREAD_PCT"),
        atr_period=config_int("btc_trend", "atr_period", 14, env_key="BTC_TREND_ATR_PERIOD"),
        min_atr_pct=config_float("btc_trend", "min_atr_pct", 0.08, env_key="BTC_TREND_MIN_ATR_PCT"),
        min_atr_pct_map=parse_symbol_float_map(config_value("btc_trend", "min_atr_pct_map", {}, env_key="BTC_TREND_MIN_ATR_PCT_MAP")),
        max_atr_pct=config_float("btc_trend", "max_atr_pct", 2.50, env_key="BTC_TREND_MAX_ATR_PCT"),
        volume_lookback=config_int("btc_trend", "volume_lookback", 20, env_key="BTC_TREND_VOLUME_LOOKBACK"),
        min_volume_ratio=config_float("btc_trend", "min_volume_ratio", 1.05, env_key="BTC_TREND_MIN_VOLUME_RATIO"),
        min_volume_ratio_map=parse_symbol_float_map(config_value("btc_trend", "min_volume_ratio_map", {}, env_key="BTC_TREND_MIN_VOLUME_RATIO_MAP")),
        choppy_min_volume_ratio_map=parse_symbol_float_map(config_value("btc_trend", "choppy_min_volume_ratio_map", {}, env_key="BTC_TREND_CHOPPY_MIN_VOLUME_RATIO_MAP")),
        position_ratio=config_float("btc_trend", "position_ratio", 0.25, env_key="BTC_TREND_POSITION_RATIO"),
        position_ratio_map=parse_symbol_float_map(config_value("btc_trend", "position_ratio_map", {}, env_key="BTC_TREND_POSITION_RATIO_MAP")),
        enable_regime_position_scaling=config_bool("btc_trend", "enable_regime_position_scaling", True, env_key="BTC_TREND_ENABLE_REGIME_POSITION_SCALING"),
        regime_position_scale_map=parse_symbol_float_map(config_value("btc_trend", "regime_position_scale_map", {}, env_key="BTC_TREND_REGIME_POSITION_SCALE_MAP")),
        enable_atr_position_scaling=config_bool("btc_trend", "enable_atr_position_scaling", True, env_key="BTC_TREND_ENABLE_ATR_POSITION_SCALING"),
        atr_position_scale_threshold_map=parse_float_float_map(config_value("btc_trend", "atr_position_scale_threshold_map", {}, env_key="BTC_TREND_ATR_POSITION_SCALE_THRESHOLD_MAP")),
        min_order_amount=config_float("btc_trend", "min_order_amount", 0.00001, env_key="BTC_TREND_MIN_ORDER_AMOUNT"),
        min_trade_interval_sec=config_int("btc_trend", "min_trade_interval_sec", 300, env_key="BTC_TREND_MIN_TRADE_INTERVAL_SEC"),
        stop_loss_reentry_cooldown_sec=config_int("btc_trend", "stop_loss_reentry_cooldown_sec", 600, env_key="BTC_TREND_STOP_LOSS_REENTRY_COOLDOWN_SEC"),
        enable_stop_loss_pattern_reentry=config_bool("btc_trend", "enable_stop_loss_pattern_reentry", True, env_key="BTC_TREND_ENABLE_STOP_LOSS_PATTERN_REENTRY"),
        stop_loss_pattern_min_cooldown_sec=config_int("btc_trend", "stop_loss_pattern_min_cooldown_sec", 180, env_key="BTC_TREND_STOP_LOSS_PATTERN_MIN_COOLDOWN_SEC"),
        stop_loss_pattern_min_signal_score=config_float("btc_trend", "stop_loss_pattern_min_signal_score", 72.0, env_key="BTC_TREND_STOP_LOSS_PATTERN_MIN_SIGNAL_SCORE"),
        stop_loss_pattern_require_confirm_bullish=config_bool("btc_trend", "stop_loss_pattern_require_confirm_bullish", True, env_key="BTC_TREND_STOP_LOSS_PATTERN_REQUIRE_CONFIRM_BULLISH"),
        stop_loss_pattern_require_fresh_cross=config_bool("btc_trend", "stop_loss_pattern_require_fresh_cross", True, env_key="BTC_TREND_STOP_LOSS_PATTERN_REQUIRE_FRESH_CROSS"),
        stop_loss_pattern_relaxed_fresh_cross_after_sec_map=parse_symbol_int_map(config_value("btc_trend", "stop_loss_pattern_relaxed_fresh_cross_after_sec_map", {}, env_key="BTC_TREND_STOP_LOSS_PATTERN_RELAXED_FRESH_CROSS_AFTER_SEC_MAP")),
        stop_loss_pattern_relaxed_fresh_cross_min_signal_score_map=parse_symbol_float_map(config_value("btc_trend", "stop_loss_pattern_relaxed_fresh_cross_min_signal_score_map", {}, env_key="BTC_TREND_STOP_LOSS_PATTERN_RELAXED_FRESH_CROSS_MIN_SIGNAL_SCORE_MAP")),
        profit_exit_reentry_cooldown_sec=config_int("btc_trend", "profit_exit_reentry_cooldown_sec", 600, env_key="BTC_TREND_PROFIT_EXIT_REENTRY_COOLDOWN_SEC"),
        enable_partial_take_profit=config_bool("btc_trend", "enable_partial_take_profit", True, env_key="BTC_TREND_ENABLE_PARTIAL_TAKE_PROFIT"),
        partial_take_profit_ratio=config_float("btc_trend", "partial_take_profit_ratio", 0.5, env_key="BTC_TREND_PARTIAL_TAKE_PROFIT_RATIO"),
        enable_pyramid_add_on=config_bool("btc_trend", "enable_pyramid_add_on", True, env_key="BTC_TREND_ENABLE_PYRAMID_ADD_ON"),
        pyramid_trigger_profit_pct=config_float("btc_trend", "pyramid_trigger_profit_pct", 0.35, env_key="BTC_TREND_PYRAMID_TRIGGER_PROFIT_PCT"),
        pyramid_position_ratio=config_float("btc_trend", "pyramid_position_ratio", 0.15, env_key="BTC_TREND_PYRAMID_POSITION_RATIO"),
        pyramid_max_add_ons=config_int("btc_trend", "pyramid_max_add_ons", 1, env_key="BTC_TREND_PYRAMID_MAX_ADD_ONS"),
        stop_mode=config_str("btc_trend", "stop_mode", "atr", env_key="BTC_TREND_STOP_MODE").strip().lower(),
        take_profit_mode=config_str("btc_trend", "take_profit_mode", "atr", env_key="BTC_TREND_TAKE_PROFIT_MODE").strip().lower(),
        stop_atr_multiple=config_float("btc_trend", "stop_atr_multiple", 1.5, env_key="BTC_TREND_STOP_ATR_MULTIPLE"),
        take_profit_atr_multiple=config_float("btc_trend", "take_profit_atr_multiple", 2.5, env_key="BTC_TREND_TAKE_PROFIT_ATR_MULTIPLE"),
        trailing_drawdown_pct=config_float("btc_trend", "trailing_drawdown_pct", 0.8, env_key="BTC_TREND_TRAILING_DRAWDOWN_PCT"),
        swing_lookback=config_int("btc_trend", "swing_lookback", 10, env_key="BTC_TREND_SWING_LOOKBACK"),
        exit_on_bearish_cross=config_bool("btc_trend", "exit_on_bearish_cross", True, env_key="BTC_TREND_EXIT_ON_BEARISH_CROSS"),
        loop_interval_sec=config_int("btc_trend", "loop_interval_sec", 20, env_key="BTC_TREND_LOOP_INTERVAL_SEC"),
    )
