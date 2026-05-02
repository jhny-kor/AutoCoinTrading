"""
수정 요약
- 2026-05-02: 손절 방지를 위해 BTC 레짐+상관+ATR, 거래량+ATR+체결 약세, 손절 후 유사 조건 재진입 가드 설정을 추가
- 2026-05-01: 단독 지표 오탐을 줄이기 위해 거래량+ATR+RSI 과열 가드와 과열거리 추가확인 설정을 추가
- mean_reversion 전용 RSI 범위와 MACD 회복 조건 설정을 추가
- 알트 자체 ATR 퍼센트 기반 포지션 사이징 설정을 추가
- OKX 현물 알트 진입 전에 perpetual swap funding rate 과열을 차단할 수 있는 공통 설정을 추가
- 심볼별 signal_score 최소 기준 오버라이드를 추가해 ETH/KRW 같은 알트를 개별적으로 더 보수화할 수 있게 확장
- 2026-04-10: 알트 보수형 튜닝을 위해 최대 진입 이격도와 최대 거래량 배수 상한 설정을 추가했다.
- 2026-04-09: 알트 손절 후 재진입은 최소 시간과 신호/거래량/HTF 복구를 함께 보는 패턴 기반 설정을 추가
- 2026-04-08: 심볼별 정수 override 공통 파서를 추가해 BTC 확인 루프처럼 map 기반 int 설정을 재사용할 수 있게 확장
- 2026-04-03: 공통 전략 설정을 canonical runtime TOML 과 typed access helper 기준으로 읽도록 정리
- 2026-04-06: 알트코인 Bollinger Squeeze + 거래량 폭발 돌파 진입 모드 파라미터 추가
- BTC ATR 퍼센트가 낮을 때 알트 신규 진입 비중을 단계형으로 줄일 수 있게 공통 설정을 추가했다.
- BTC 레짐 기반 알트 신규 진입 비중을 심볼별 override map 으로 세분화해 ETH 는 더 보수적으로, XRP 는 완만하게 축소할 수 있게 확장
- 알트 신규 진입 비중에 BTC 레짐 기반 추가 스케일을 곱할 수 있게 확장해 BTC 가 LOW_ENERGY 일 때 먼저 포지션을 축소할 수 있게 보강
- 알트 전략에 레짐별 포지션 비중 스케일 설정을 추가해 상승장/횡보장/저에너지장에 따라 진입 크기를 다르게 조절할 수 있게 확장
- 노이즈 비율 기반 동적 진입 문턱값 설정을 추가해 알트 진입 기준을 장 상태에 맞춰 자동 보정할 수 있게 확장
- 2차 강화용으로 진입 상태 머신, BTC 상관관계 가드, 체결률 품질 가드 설정을 추가했다.
- 알트 공통 전략에 RSI, MACD, 기울기, 신호 스코어 설정을 추가해 진입 품질을 더 세밀하게 조정할 수 있게 확장
- 브레이크이븐 가드에 MFE 대비 최대 이익 반납폭 기준을 추가해 수익 구간 회귀 청산을 더 빠르게 제어할 수 있게 보강
- 혼합 청산 세트를 위해 수수료 반영 순익 보호 익절 기준도 심볼별 map 으로 읽도록 확장
- 특정 심볼은 상위 타임프레임 하락 추세일 때 신규 진입을 차단하도록 공통 알트 전략 설정을 추가
- ETH/KRW 같은 특정 심볼만 별도로 수익을 지키도록 브레이크이븐 가드 설정을 공통 알트 전략에 추가
- 부분 익절 직후 같은 코인 재진입과 추가 매수를 잠시 막는 전용 쿨다운 설정을 공통 알트 전략에 추가
- 수수료를 제하고도 순익이 남는 상태에서 메인 추세가 꺾이면 빠르게 전량 익절하는 공통 알트 청산 설정을 추가
- 알트 전략에서 심볼별 부분익절/부분손절 대상과 비율을 canonical config 에서 읽도록 확장
- 공통 전략 버전 이름을 canonical config 에서 읽어 로그와 체결 이력에 함께 남길 수 있도록 확장
- 알트 봇에 보수형 trend_follow_entry 설정을 추가해 골든크로스가 아니어도 제한적으로 추세 유지 진입을 허용할 수 있게 개선
- 연속 MA 상단 유지와 직전 대비 상승 조건을 canonical config 에서 제어할 수 있도록 확장
- 심볼별 거래량 기준 오버라이드를 canonical config 에서 읽어 DOGE 같은 고변동 알트의 진입 품질을 코인별로 분리 조정할 수 있게 개선
- 알트 심볼 목록과 운영/분석 대상 심볼 목록도 공통으로 canonical config 에서 읽도록 확장
- 빈 문자열로 설정한 알트 심볼 목록은 기본값으로 되돌리지 않고 비활성화로 처리하도록 보정

공통 전략 설정 로더

- 두 거래소 봇이 같은 전략 값을 canonical config 에서 읽도록 돕는 모듈
- 공통 전략 값은 STRATEGY_ 접두사로 관리
- 최소 주문 금액은 거래소별로 달라서 별도 키를 사용
- 심볼별 이격도 기준 오버라이드를 canonical config 에서 읽을 수 있도록 지원
- 심볼별 익절률/손절률 오버라이드를 canonical config 에서 읽을 수 있도록 지원
- 상위 타임프레임 추세 필터 설정을 canonical config 에서 읽을 수 있도록 지원
- 거래량 필터와 변동성 필터 설정을 canonical config 에서 읽을 수 있도록 지원
- 심볼별 최소 주문 수량 오버라이드를 canonical config 에서 읽을 수 있도록 지원
- 알트 봇 감시 심볼과 텔레그램/분석 수집 대상 심볼도 공통 규칙으로 재사용할 수 있도록 지원
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from settings.config_access import (
    config_bool,
    config_float,
    config_int,
    config_section_float,
    config_str,
    config_value,
)
from settings.env import load_project_env

DEFAULT_OKX_ALT_SYMBOLS = ["PI/USDT"]
DEFAULT_UPBIT_ALT_SYMBOLS = ["XRP/KRW"]
DEFAULT_OKX_BTC_SYMBOL = "BTC/USDT"
DEFAULT_UPBIT_BTC_SYMBOL = "BTC/KRW"


@dataclass(frozen=True)
class StrategySettings:
    """두 봇이 공통으로 사용하는 전략 설정 묶음."""

    version: str
    entry_mode: str
    bb_period: int
    bb_stddev: float
    squeeze_max_bandwidth_pct: float
    squeeze_min_volume_ratio: float
    buy_split_ratio: float
    sell_split_ratio: float
    max_entry_count: int
    min_trade_interval_sec: int
    enable_stop_loss_pattern_reentry: bool
    stop_loss_pattern_min_cooldown_sec: int
    stop_loss_pattern_min_signal_score: float
    stop_loss_pattern_min_volume_ratio_multiplier: float
    stop_loss_pattern_require_htf_bullish: bool
    stop_loss_pattern_require_fresh_cross: bool
    enable_trend_follow_entry: bool
    trend_follow_requires_prev_above_ma: bool
    trend_follow_requires_price_rising: bool
    trend_follow_requires_ma_slope_positive: bool
    trend_slope_lookback: int
    enable_higher_timeframe_filter: bool
    block_entry_when_htf_bearish_symbols: tuple[str, ...]
    higher_timeframe: str
    higher_timeframe_ma_period: int
    enable_rsi_filter: bool
    rsi_period: int
    rsi_entry_min: float
    rsi_entry_max: float
    enable_macd_filter: bool
    macd_fast_period: int
    macd_slow_period: int
    macd_signal_period: int
    mean_reversion_rsi_min: float
    mean_reversion_rsi_max: float
    mean_reversion_allow_negative_macd: bool
    mean_reversion_require_macd_recovering: bool
    mean_reversion_macd_recovery_epsilon: float
    mean_reversion_max_atr_percentile: float
    mean_reversion_max_range_position_pct: float
    overheat_guard_volume_ratio: float
    overheat_guard_atr_percentile: float
    overheat_guard_rsi: float
    overheat_extra_confirmation_range_position_pct: float
    overheat_extra_confirmation_distance_from_high_pct: float
    overheat_extra_confirmation_loops: int
    enable_combined_stop_loss_guards: bool
    btc_correlation_volatility_risky_regimes: tuple[str, ...]
    btc_correlation_volatility_min_corr: float
    btc_correlation_volatility_min_atr_percentile: float
    volume_atr_execution_guard_volume_ratio: float
    volume_atr_execution_guard_atr_percentile: float
    volume_atr_execution_min_fill_ratio: float
    volume_atr_execution_min_fill_samples: int
    volume_atr_execution_min_orderbook_pressure_score: float
    stop_loss_context_reentry_cooldown_sec: int
    stop_loss_context_min_similarity_count: int
    stop_loss_context_extra_confirmation_loops: int
    enable_noise_ratio_adaptation: bool
    noise_ratio_lookback: int
    noise_ratio_baseline: float
    noise_ratio_min_multiplier: float
    noise_ratio_max_multiplier: float
    enable_volume_filter: bool
    volume_lookback: int
    min_volume_ratio: float
    min_volume_ratio_map: dict[str, float]
    max_volume_ratio: float
    max_volume_ratio_map: dict[str, float]
    enable_okx_funding_rate_guard: bool
    okx_funding_rate_max_long_bias: float
    okx_funding_rate_cache_ttl_sec: float
    position_ratio_map: dict[str, float]
    enable_regime_position_scaling: bool
    regime_position_scale_map: dict[str, float]
    enable_btc_regime_position_scaling: bool
    btc_regime_position_scale_map: dict[str, float]
    btc_regime_position_scale_override_map: dict[str, dict[str, float]]
    enable_btc_atr_position_scaling: bool
    btc_atr_position_scale_lookback: int
    btc_atr_position_scale_threshold_map: dict[float, float]
    enable_alt_atr_position_sizing: bool
    alt_atr_position_scale_threshold_map: dict[float, float]
    enable_volatility_filter: bool
    volatility_lookback: int
    min_volatility_pct: float
    max_volatility_pct: float
    min_crossover_gap_pct: float
    max_entry_gap_pct: float
    averaging_down_gap_pct: float
    min_take_profit_pct: float
    stop_loss_pct: float
    enable_fee_protect_exit: bool
    fee_protect_min_net_pnl_pct: float
    fee_protect_min_net_pnl_pct_map: dict[str, float]
    enable_break_even_guard: bool
    break_even_guard_min_mfe_pct: float
    break_even_guard_min_mfe_pct_map: dict[str, float]
    break_even_guard_floor_net_pnl_pct: float
    break_even_guard_floor_net_pnl_pct_map: dict[str, float]
    break_even_guard_max_profit_retrace_pct: float
    enable_volume_spike_exit: bool
    volume_spike_exit_min_profit_pct: float
    volume_spike_exit_max_volume_ratio: float
    enable_auto_tune: bool
    auto_tune_window_days: int
    auto_tune_min_trades: int
    auto_tune_positive_win_rate: float
    auto_tune_positive_profit_factor: float
    auto_tune_negative_win_rate: float
    auto_tune_negative_profit_factor: float
    auto_tune_adjustment_limit_pct: float
    auto_tune_adjustment_map: dict[str, float]
    signal_score_min: float
    signal_score_min_map: dict[str, float]
    dynamic_signal_score_min: float
    entry_confirmation_loops: int
    enable_correlation_filter: bool
    correlation_lookback: int
    max_correlation_with_btc: float
    enable_fill_quality_guard: bool
    fill_quality_lookback_sec: int
    fill_quality_min_fill_ratio: float
    fill_quality_min_sample_count: int
    min_buy_order_value: float
    loop_interval_sec: int
    min_crossover_gap_pct_map: dict[str, float]
    max_entry_gap_pct_map: dict[str, float]
    min_take_profit_pct_map: dict[str, float]
    stop_loss_pct_map: dict[str, float]
    min_order_amount_map: dict[str, float]
    partial_take_profit_symbols: tuple[str, ...]
    partial_stop_loss_symbols: tuple[str, ...]
    partial_take_profit_ratio: float
    partial_stop_loss_ratio: float
    partial_take_profit_reentry_cooldown_sec: int

    def get_crossover_gap_pct(self, symbol: str) -> float:
        """심볼별 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        base_value = self.min_crossover_gap_pct_map.get(symbol, self.min_crossover_gap_pct)
        adjustment = self.auto_tune_adjustment_map.get(symbol, 0.0)
        return max(0.0, base_value * (1.0 - adjustment))

    def get_take_profit_pct(self, symbol: str) -> float:
        """심볼별 익절률 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        base_value = self.min_take_profit_pct_map.get(symbol, self.min_take_profit_pct)
        adjustment = self.auto_tune_adjustment_map.get(symbol, 0.0)
        return max(0.0, base_value * (1.0 + adjustment))

    def get_stop_loss_pct(self, symbol: str) -> float:
        """심볼별 손절률 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        base_value = self.stop_loss_pct_map.get(symbol, self.stop_loss_pct)
        adjustment = self.auto_tune_adjustment_map.get(symbol, 0.0)
        return max(0.0, base_value * (1.0 + adjustment))

    def get_min_volume_ratio(self, symbol: str) -> float:
        """심볼별 거래량 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        return self.min_volume_ratio_map.get(symbol, self.min_volume_ratio)

    def get_max_volume_ratio(self, symbol: str) -> float:
        """심볼별 최대 거래량 상한 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        return self.max_volume_ratio_map.get(symbol, self.max_volume_ratio)

    def get_min_order_amount(self, symbol: str) -> float:
        """심볼별 최소 주문 수량 오버라이드가 있으면 그 값을, 없으면 0을 반환한다."""
        return self.min_order_amount_map.get(symbol, 0.0)

    def get_max_entry_gap_pct(self, symbol: str) -> float:
        """심볼별 최대 진입 이격도 상한 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        return self.max_entry_gap_pct_map.get(symbol, self.max_entry_gap_pct)

    def get_signal_score_min(self, symbol: str) -> float:
        """심볼별 최소 신호 점수 오버라이드가 있으면 그 값을, 없으면 기본값을 반환한다."""
        return self.signal_score_min_map.get(symbol, self.signal_score_min)

    def get_auto_tune_adjustment(self, symbol: str) -> float:
        """심볼별 자동 튜닝 조정 배율을 반환한다."""
        return self.auto_tune_adjustment_map.get(symbol, 0.0)

    def get_regime_position_scale(self, regime: str | None) -> float:
        """레짐별 포지션 비중 스케일을 반환한다."""
        if not self.enable_regime_position_scaling:
            return 1.0
        if not regime:
            return 1.0
        return self.regime_position_scale_map.get(regime, 1.0)

    def get_btc_regime_position_scale(self, regime: str | None) -> float:
        """BTC 레짐 기준 알트 포지션 비중 스케일을 반환한다."""
        if not self.enable_btc_regime_position_scaling:
            return 1.0
        if not regime:
            return 1.0
        return self.btc_regime_position_scale_map.get(regime, 1.0)

    def get_btc_regime_position_scale_for_symbol(
        self,
        symbol: str,
        regime: str | None,
    ) -> float:
        """BTC 레짐 기준 알트 포지션 비중 스케일을 심볼별 override 포함으로 반환한다."""
        if not self.enable_btc_regime_position_scaling:
            return 1.0
        if not regime:
            return 1.0
        symbol_map = self.btc_regime_position_scale_override_map.get(symbol, {})
        if regime in symbol_map:
            return symbol_map[regime]
        return self.get_btc_regime_position_scale(regime)

    def get_btc_atr_position_scale(self, atr_pct: float | None) -> float:
        """BTC ATR 퍼센트 기준 알트 포지션 비중 스케일을 반환한다."""
        if not self.enable_btc_atr_position_scaling:
            return 1.0
        if atr_pct is None:
            return 1.0

        matched_scales = [
            scale
            for threshold, scale in self.btc_atr_position_scale_threshold_map.items()
            if atr_pct < threshold
        ]
        if not matched_scales:
            return 1.0
        return min(matched_scales)

    def get_alt_atr_position_scale(self, atr_pct: float | None) -> float:
        """알트 자체 ATR 퍼센트 기준 포지션 비중 스케일을 반환한다."""
        if not self.enable_alt_atr_position_sizing:
            return 1.0
        if atr_pct is None:
            return 1.0
        for threshold, scale in sorted(self.alt_atr_position_scale_threshold_map.items(), key=lambda item: item[0]):
            if atr_pct < threshold:
                return scale
        return 1.0

    def get_break_even_guard_min_mfe_pct(self, symbol: str) -> float:
        """심볼별 브레이크이븐 가드 최소 MFE 기준을 반환한다."""
        return self.break_even_guard_min_mfe_pct_map.get(
            symbol,
            self.break_even_guard_min_mfe_pct,
        )

    def get_fee_protect_min_net_pnl_pct(self, symbol: str) -> float:
        """심볼별 순익 보호 최소 순익률 기준을 반환한다."""
        return self.fee_protect_min_net_pnl_pct_map.get(
            symbol,
            self.fee_protect_min_net_pnl_pct,
        )

    def get_break_even_guard_floor_net_pnl_pct(self, symbol: str) -> float:
        """심볼별 브레이크이븐 가드 순익 바닥 기준을 반환한다."""
        return self.break_even_guard_floor_net_pnl_pct_map.get(
            symbol,
            self.break_even_guard_floor_net_pnl_pct,
        )

    def get_position_ratio(self, symbol: str, default_ratio: float) -> float:
        """심볼별 매수 비중 오버라이드가 있으면 그 값을, 없으면 기본 비중을 반환한다."""
        return self.position_ratio_map.get(symbol, default_ratio)

    def uses_partial_take_profit(self, symbol: str) -> bool:
        """심볼이 부분익절 대상인지 반환한다."""
        return symbol in self.partial_take_profit_symbols

    def uses_partial_stop_loss(self, symbol: str) -> bool:
        """심볼이 부분손절 대상인지 반환한다."""
        return symbol in self.partial_stop_loss_symbols

    def blocks_entry_when_htf_bearish(self, symbol: str) -> bool:
        """심볼이 상위 하락 추세일 때 신규 진입 차단 대상인지 반환한다."""
        return symbol in self.block_entry_when_htf_bearish_symbols


def parse_symbol_list(raw: str | None, default: list[str] | None = None) -> list[str]:
    """쉼표 구분 심볼 문자열을 중복 없이 정리한다."""
    if raw is None:
        source = default or []
    else:
        source = raw.split(",")

    result: list[str] = []
    seen: set[str] = set()
    for item in source:
        symbol = str(item).strip()
        if not symbol or symbol in seen:
            continue
        result.append(symbol)
        seen.add(symbol)
    return result


def parse_symbol_float_map(raw: str | dict[str, object]) -> dict[str, float]:
    """문자열 또는 dict 형태의 심볼 float map 을 사전으로 바꾼다."""
    if isinstance(raw, dict):
        result: dict[str, float] = {}
        for key, value in raw.items():
            try:
                result[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
        return result
    result: dict[str, float] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        symbol, value = item.split(":", 1)
        symbol = symbol.strip()
        value = value.strip()
        if not symbol or not value:
            continue
        result[symbol] = float(value)
    return result


def parse_symbol_int_map(raw: str | dict[str, object]) -> dict[str, int]:
    """문자열 또는 dict 형태의 심볼별 정수 사전을 만든다."""
    result: dict[str, int] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            try:
                result[str(key)] = int(value)
            except (TypeError, ValueError):
                continue
        return result

    if not raw:
        return result

    for item in str(raw).split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        symbol, value = item.split(":", 1)
        symbol = symbol.strip()
        value = value.strip()
        if not symbol or not value:
            continue
        try:
            result[symbol] = int(value)
        except ValueError:
            continue
    return result


def parse_symbol_regime_float_map(raw: str | dict[str, object]) -> dict[str, dict[str, float]]:
    """문자열 또는 dict 형태의 심볼별 레짐 스케일 사전을 만든다."""
    if isinstance(raw, dict):
        result: dict[str, dict[str, float]] = {}
        for symbol, inner in raw.items():
            if not isinstance(inner, dict):
                continue
            symbol_key = str(symbol)
            for regime, value in inner.items():
                try:
                    result.setdefault(symbol_key, {})[str(regime)] = float(value)
                except (TypeError, ValueError):
                    continue
        return result
    result: dict[str, dict[str, float]] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item or ":" not in item or "|" not in item:
            continue
        symbol_regime, value = item.split(":", 1)
        symbol_regime = symbol_regime.strip()
        value = value.strip()
        if not symbol_regime or not value or "|" not in symbol_regime:
            continue
        symbol, regime = symbol_regime.split("|", 1)
        symbol = symbol.strip()
        regime = regime.strip()
        if not symbol or not regime:
            continue
        result.setdefault(symbol, {})[regime] = float(value)
    return result


def parse_float_float_map(raw: str | dict[object, object]) -> dict[float, float]:
    """문자열 또는 dict 형태의 float map 을 만든다."""
    if isinstance(raw, dict):
        result: dict[float, float] = {}
        for key, value in raw.items():
            try:
                result[float(key)] = float(value)
            except (TypeError, ValueError):
                continue
        return result
    result: dict[float, float] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        key, value = item.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            continue
        result[float(key)] = float(value)
    return result


def parse_bool(raw: str, default: bool = False) -> bool:
    """문자열 불리언 값을 파싱한다."""
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def resolve_exchange_section_from_env_key(env_key: str) -> str | None:
    """거래소 접두사 env key 를 canonical section 이름으로 바꾼다."""
    normalized = env_key.strip().upper()
    if normalized.startswith("OKX_"):
        return "okx"
    if normalized.startswith("UPBIT_"):
        return "upbit"
    return None


def build_market_entry(symbol: str) -> dict[str, str]:
    """BASE/QUOTE 심볼을 봇에서 쓰는 마켓 사전으로 바꾼다."""
    if "/" not in symbol:
        raise ValueError(f"심볼 형식이 잘못되었습니다: {symbol}")

    base, quote = symbol.split("/", 1)
    base = base.strip()
    quote = quote.strip()
    normalized_symbol = f"{base}/{quote}"
    return {
        "name": base,
        "symbol": normalized_symbol,
        "base": base,
        "quote": quote,
    }


def load_alt_symbols(exchange_name: str) -> list[str]:
    """거래소별 알트 봇 감시 심볼 목록을 읽는다."""
    load_project_env()

    exchange_key = exchange_name.strip().lower()
    if exchange_key == "okx":
        return parse_symbol_list(
            config_str("okx", "alt_symbols", "", env_key="OKX_ALT_SYMBOLS") or None,
            DEFAULT_OKX_ALT_SYMBOLS,
        )
    if exchange_key == "upbit":
        return parse_symbol_list(
            config_str("upbit", "alt_symbols", "", env_key="UPBIT_ALT_SYMBOLS") or None,
            DEFAULT_UPBIT_ALT_SYMBOLS,
        )
    raise ValueError(f"지원하지 않는 거래소입니다: {exchange_name}")


def load_alt_markets(exchange_name: str) -> list[dict[str, str]]:
    """거래소별 알트 봇 감시 심볼을 마켓 사전 목록으로 반환한다."""
    return [build_market_entry(symbol) for symbol in load_alt_symbols(exchange_name)]


def load_managed_symbols(exchange_name: str) -> list[str]:
    """거래소별 운영/분석 대상 심볼 목록을 읽는다."""
    load_project_env()

    exchange_key = exchange_name.strip().lower()
    if exchange_key == "okx":
        default_symbols = [DEFAULT_OKX_BTC_SYMBOL, *load_alt_symbols("okx")]
        extra_symbols = parse_symbol_list(
            config_str("analysis", "okx_symbols", "", env_key="ANALYSIS_OKX_SYMBOLS") or None
        )
        return parse_symbol_list(None, [*default_symbols, *extra_symbols])
    if exchange_key == "upbit":
        default_symbols = [DEFAULT_UPBIT_BTC_SYMBOL, *load_alt_symbols("upbit")]
        extra_symbols = parse_symbol_list(
            config_str("analysis", "upbit_symbols", "", env_key="ANALYSIS_UPBIT_SYMBOLS") or None
        )
        return parse_symbol_list(None, [*default_symbols, *extra_symbols])
    raise ValueError(f"지원하지 않는 거래소입니다: {exchange_name}")


def _parse_trade_local_timestamp(raw: str) -> datetime | None:
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _build_symbol_auto_tune_adjustment_map(
    *,
    window_days: int,
    min_trades: int,
    positive_win_rate: float,
    positive_profit_factor: float,
    negative_win_rate: float,
    negative_profit_factor: float,
    adjustment_limit_pct: float,
) -> dict[str, float]:
    """최근 실거래 성과를 기준으로 심볼별 자동 튜닝 배율을 계산한다."""
    if window_days <= 0 or adjustment_limit_pct <= 0:
        return {}

    cutoff = datetime.now().astimezone() - timedelta(days=window_days)
    stats: dict[str, dict[str, float]] = {}

    for path in sorted(Path("trade_logs").rglob("trade_history.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if not record.get("is_final_exit"):
                continue
            recorded_local = _parse_trade_local_timestamp(str(record.get("recorded_at_local", "")))
            if recorded_local is None or recorded_local < cutoff:
                continue

            symbol = str(record.get("symbol", "")).strip()
            if not symbol:
                continue
            pnl_quote = record.get("net_realized_pnl_quote")
            if pnl_quote in (None, ""):
                pnl_quote = record.get("realized_pnl_quote")
            try:
                pnl_quote_value = float(pnl_quote)
            except (TypeError, ValueError):
                continue

            bucket = stats.setdefault(
                symbol,
                {"trades": 0.0, "wins": 0.0, "gross_profit": 0.0, "gross_loss": 0.0},
            )
            bucket["trades"] += 1
            if pnl_quote_value > 0:
                bucket["wins"] += 1
                bucket["gross_profit"] += pnl_quote_value
            elif pnl_quote_value < 0:
                bucket["gross_loss"] += abs(pnl_quote_value)

    adjustments: dict[str, float] = {}
    capped_adjustment = min(abs(adjustment_limit_pct), 0.10)
    for symbol, bucket in stats.items():
        trade_count = int(bucket["trades"])
        if trade_count < min_trades:
            continue
        win_rate = bucket["wins"] / bucket["trades"] if bucket["trades"] > 0 else 0.0
        gross_profit = bucket["gross_profit"]
        gross_loss = bucket["gross_loss"]
        profit_factor = float("inf") if gross_loss == 0 and gross_profit > 0 else (
            (gross_profit / gross_loss) if gross_loss > 0 else 0.0
        )

        adjustment = 0.0
        if win_rate >= positive_win_rate and profit_factor >= positive_profit_factor:
            adjustment = capped_adjustment
        elif win_rate <= negative_win_rate or profit_factor <= negative_profit_factor:
            adjustment = -capped_adjustment

        if adjustment != 0.0:
            adjustments[symbol] = adjustment

    return adjustments


def load_strategy_settings(
    min_buy_order_env_key: str, default_min_buy_order_value: float
) -> StrategySettings:
    """공통 전략 설정과 거래소별 최소 주문 금액 설정을 함께 읽는다."""
    load_project_env()

    enable_auto_tune = config_bool("strategy", "enable_auto_tune", True, env_key="STRATEGY_ENABLE_AUTO_TUNE")
    auto_tune_window_days = config_int("strategy", "auto_tune_window_days", 7, env_key="STRATEGY_AUTO_TUNE_WINDOW_DAYS")
    auto_tune_min_trades = config_int("strategy", "auto_tune_min_trades", 2, env_key="STRATEGY_AUTO_TUNE_MIN_TRADES")
    auto_tune_positive_win_rate = config_float("strategy", "auto_tune_positive_win_rate", 0.60, env_key="STRATEGY_AUTO_TUNE_POSITIVE_WIN_RATE")
    auto_tune_positive_profit_factor = config_float("strategy", "auto_tune_positive_profit_factor", 1.30, env_key="STRATEGY_AUTO_TUNE_POSITIVE_PROFIT_FACTOR")
    auto_tune_negative_win_rate = config_float("strategy", "auto_tune_negative_win_rate", 0.40, env_key="STRATEGY_AUTO_TUNE_NEGATIVE_WIN_RATE")
    auto_tune_negative_profit_factor = config_float("strategy", "auto_tune_negative_profit_factor", 0.90, env_key="STRATEGY_AUTO_TUNE_NEGATIVE_PROFIT_FACTOR")
    auto_tune_adjustment_limit_pct = config_float("strategy", "auto_tune_adjustment_limit_pct", 0.10, env_key="STRATEGY_AUTO_TUNE_ADJUSTMENT_LIMIT_PCT")
    auto_tune_adjustment_map = (
        _build_symbol_auto_tune_adjustment_map(
            window_days=auto_tune_window_days,
            min_trades=auto_tune_min_trades,
            positive_win_rate=auto_tune_positive_win_rate,
            positive_profit_factor=auto_tune_positive_profit_factor,
            negative_win_rate=auto_tune_negative_win_rate,
            negative_profit_factor=auto_tune_negative_profit_factor,
            adjustment_limit_pct=auto_tune_adjustment_limit_pct,
        )
        if enable_auto_tune
        else {}
    )

    return StrategySettings(
        version=config_str("strategy", "version", "alt_v1", env_key="STRATEGY_VERSION").strip(),
        entry_mode=config_str("strategy", "entry_mode", "ma", env_key="STRATEGY_ENTRY_MODE").strip().lower(),
        bb_period=config_int("strategy", "bb_period", 20, env_key="STRATEGY_BB_PERIOD"),
        bb_stddev=config_float("strategy", "bb_stddev", 2.0, env_key="STRATEGY_BB_STDDEV"),
        squeeze_max_bandwidth_pct=config_float("strategy", "squeeze_max_bandwidth_pct", 3.0, env_key="STRATEGY_SQUEEZE_MAX_BANDWIDTH_PCT"),
        squeeze_min_volume_ratio=config_float("strategy", "squeeze_min_volume_ratio", 2.5, env_key="STRATEGY_SQUEEZE_MIN_VOLUME_RATIO"),
        buy_split_ratio=config_float("strategy", "buy_split_ratio", 0.10, env_key="STRATEGY_BUY_SPLIT_RATIO"),
        sell_split_ratio=config_float("strategy", "sell_split_ratio", 0.10, env_key="STRATEGY_SELL_SPLIT_RATIO"),
        max_entry_count=config_int("strategy", "max_entry_count", 3, env_key="STRATEGY_MAX_ENTRY_COUNT"),
        min_trade_interval_sec=config_int("strategy", "min_trade_interval_sec", 300, env_key="STRATEGY_MIN_TRADE_INTERVAL_SEC"),
        enable_stop_loss_pattern_reentry=config_bool("strategy", "enable_stop_loss_pattern_reentry", True, env_key="STRATEGY_ENABLE_STOP_LOSS_PATTERN_REENTRY"),
        stop_loss_pattern_min_cooldown_sec=config_int("strategy", "stop_loss_pattern_min_cooldown_sec", 180, env_key="STRATEGY_STOP_LOSS_PATTERN_MIN_COOLDOWN_SEC"),
        stop_loss_pattern_min_signal_score=config_float("strategy", "stop_loss_pattern_min_signal_score", 70.0, env_key="STRATEGY_STOP_LOSS_PATTERN_MIN_SIGNAL_SCORE"),
        stop_loss_pattern_min_volume_ratio_multiplier=config_float("strategy", "stop_loss_pattern_min_volume_ratio_multiplier", 1.2, env_key="STRATEGY_STOP_LOSS_PATTERN_MIN_VOLUME_RATIO_MULTIPLIER"),
        stop_loss_pattern_require_htf_bullish=config_bool("strategy", "stop_loss_pattern_require_htf_bullish", True, env_key="STRATEGY_STOP_LOSS_PATTERN_REQUIRE_HTF_BULLISH"),
        stop_loss_pattern_require_fresh_cross=config_bool("strategy", "stop_loss_pattern_require_fresh_cross", True, env_key="STRATEGY_STOP_LOSS_PATTERN_REQUIRE_FRESH_CROSS"),
        enable_trend_follow_entry=config_bool("strategy", "enable_trend_follow_entry", False, env_key="STRATEGY_ENABLE_TREND_FOLLOW_ENTRY"),
        trend_follow_requires_prev_above_ma=config_bool("strategy", "trend_follow_require_prev_above_ma", True, env_key="STRATEGY_TREND_FOLLOW_REQUIRE_PREV_ABOVE_MA"),
        trend_follow_requires_price_rising=config_bool("strategy", "trend_follow_require_price_rising", True, env_key="STRATEGY_TREND_FOLLOW_REQUIRE_PRICE_RISING"),
        trend_follow_requires_ma_slope_positive=config_bool("strategy", "trend_follow_require_ma_slope_positive", True, env_key="STRATEGY_TREND_FOLLOW_REQUIRE_MA_SLOPE_POSITIVE"),
        trend_slope_lookback=config_int("strategy", "trend_slope_lookback", 3, env_key="STRATEGY_TREND_SLOPE_LOOKBACK"),
        enable_higher_timeframe_filter=config_bool("strategy", "enable_higher_timeframe_filter", True, env_key="STRATEGY_ENABLE_HIGHER_TIMEFRAME_FILTER"),
        block_entry_when_htf_bearish_symbols=tuple(
            parse_symbol_list(
                config_str("strategy", "block_entry_when_htf_bearish_symbols", "", env_key="STRATEGY_BLOCK_ENTRY_WHEN_HTF_BEARISH_SYMBOLS")
            )
        ),
        higher_timeframe=config_str("strategy", "higher_timeframe", "5m", env_key="STRATEGY_HIGHER_TIMEFRAME"),
        higher_timeframe_ma_period=config_int("strategy", "higher_timeframe_ma_period", 20, env_key="STRATEGY_HIGHER_TIMEFRAME_MA_PERIOD"),
        enable_rsi_filter=config_bool("strategy", "enable_rsi_filter", True, env_key="STRATEGY_ENABLE_RSI_FILTER"),
        rsi_period=config_int("strategy", "rsi_period", 14, env_key="STRATEGY_RSI_PERIOD"),
        rsi_entry_min=config_float("strategy", "rsi_entry_min", 40, env_key="STRATEGY_RSI_ENTRY_MIN"),
        rsi_entry_max=config_float("strategy", "rsi_entry_max", 70, env_key="STRATEGY_RSI_ENTRY_MAX"),
        enable_macd_filter=config_bool("strategy", "enable_macd_filter", True, env_key="STRATEGY_ENABLE_MACD_FILTER"),
        macd_fast_period=config_int("strategy", "macd_fast_period", 12, env_key="STRATEGY_MACD_FAST_PERIOD"),
        macd_slow_period=config_int("strategy", "macd_slow_period", 26, env_key="STRATEGY_MACD_SLOW_PERIOD"),
        macd_signal_period=config_int("strategy", "macd_signal_period", 9, env_key="STRATEGY_MACD_SIGNAL_PERIOD"),
        mean_reversion_rsi_min=config_float("strategy", "mean_reversion_rsi_min", 25.0, env_key="STRATEGY_MEAN_REVERSION_RSI_MIN"),
        mean_reversion_rsi_max=config_float("strategy", "mean_reversion_rsi_max", 58.0, env_key="STRATEGY_MEAN_REVERSION_RSI_MAX"),
        mean_reversion_allow_negative_macd=config_bool("strategy", "mean_reversion_allow_negative_macd", True, env_key="STRATEGY_MEAN_REVERSION_ALLOW_NEGATIVE_MACD"),
        mean_reversion_require_macd_recovering=config_bool("strategy", "mean_reversion_require_macd_recovering", True, env_key="STRATEGY_MEAN_REVERSION_REQUIRE_MACD_RECOVERING"),
        mean_reversion_macd_recovery_epsilon=config_float("strategy", "mean_reversion_macd_recovery_epsilon", 0.0, env_key="STRATEGY_MEAN_REVERSION_MACD_RECOVERY_EPSILON"),
        mean_reversion_max_atr_percentile=config_float("strategy", "mean_reversion_max_atr_percentile", 80.0, env_key="STRATEGY_MEAN_REVERSION_MAX_ATR_PERCENTILE"),
        mean_reversion_max_range_position_pct=config_float("strategy", "mean_reversion_max_range_position_pct", 35.0, env_key="STRATEGY_MEAN_REVERSION_MAX_RANGE_POSITION_PCT"),
        overheat_guard_volume_ratio=config_float("strategy", "overheat_guard_volume_ratio", 2.0, env_key="STRATEGY_OVERHEAT_GUARD_VOLUME_RATIO"),
        overheat_guard_atr_percentile=config_float("strategy", "overheat_guard_atr_percentile", 85.0, env_key="STRATEGY_OVERHEAT_GUARD_ATR_PERCENTILE"),
        overheat_guard_rsi=config_float("strategy", "overheat_guard_rsi", 68.0, env_key="STRATEGY_OVERHEAT_GUARD_RSI"),
        overheat_extra_confirmation_range_position_pct=config_float("strategy", "overheat_extra_confirmation_range_position_pct", 70.0, env_key="STRATEGY_OVERHEAT_EXTRA_CONFIRMATION_RANGE_POSITION_PCT"),
        overheat_extra_confirmation_distance_from_high_pct=config_float("strategy", "overheat_extra_confirmation_distance_from_high_pct", 0.20, env_key="STRATEGY_OVERHEAT_EXTRA_CONFIRMATION_DISTANCE_FROM_HIGH_PCT"),
        overheat_extra_confirmation_loops=config_int("strategy", "overheat_extra_confirmation_loops", 1, env_key="STRATEGY_OVERHEAT_EXTRA_CONFIRMATION_LOOPS"),
        enable_combined_stop_loss_guards=config_bool("strategy", "enable_combined_stop_loss_guards", True, env_key="STRATEGY_ENABLE_COMBINED_STOP_LOSS_GUARDS"),
        btc_correlation_volatility_risky_regimes=tuple(
            parse_symbol_list(
                config_str(
                    "strategy",
                    "btc_correlation_volatility_risky_regimes",
                    "LOW_ENERGY,OVERHEATED,EXHAUSTION_RISK,CHOPPY_HIGH_VOL",
                    env_key="STRATEGY_BTC_CORRELATION_VOLATILITY_RISKY_REGIMES",
                )
            )
        ),
        btc_correlation_volatility_min_corr=config_float("strategy", "btc_correlation_volatility_min_corr", 0.75, env_key="STRATEGY_BTC_CORRELATION_VOLATILITY_MIN_CORR"),
        btc_correlation_volatility_min_atr_percentile=config_float("strategy", "btc_correlation_volatility_min_atr_percentile", 70.0, env_key="STRATEGY_BTC_CORRELATION_VOLATILITY_MIN_ATR_PERCENTILE"),
        volume_atr_execution_guard_volume_ratio=config_float("strategy", "volume_atr_execution_guard_volume_ratio", 2.0, env_key="STRATEGY_VOLUME_ATR_EXECUTION_GUARD_VOLUME_RATIO"),
        volume_atr_execution_guard_atr_percentile=config_float("strategy", "volume_atr_execution_guard_atr_percentile", 80.0, env_key="STRATEGY_VOLUME_ATR_EXECUTION_GUARD_ATR_PERCENTILE"),
        volume_atr_execution_min_fill_ratio=config_float("strategy", "volume_atr_execution_min_fill_ratio", 0.98, env_key="STRATEGY_VOLUME_ATR_EXECUTION_MIN_FILL_RATIO"),
        volume_atr_execution_min_fill_samples=config_int("strategy", "volume_atr_execution_min_fill_samples", 1, env_key="STRATEGY_VOLUME_ATR_EXECUTION_MIN_FILL_SAMPLES"),
        volume_atr_execution_min_orderbook_pressure_score=config_float("strategy", "volume_atr_execution_min_orderbook_pressure_score", 45.0, env_key="STRATEGY_VOLUME_ATR_EXECUTION_MIN_ORDERBOOK_PRESSURE_SCORE"),
        stop_loss_context_reentry_cooldown_sec=config_int("strategy", "stop_loss_context_reentry_cooldown_sec", 3600, env_key="STRATEGY_STOP_LOSS_CONTEXT_REENTRY_COOLDOWN_SEC"),
        stop_loss_context_min_similarity_count=config_int("strategy", "stop_loss_context_min_similarity_count", 3, env_key="STRATEGY_STOP_LOSS_CONTEXT_MIN_SIMILARITY_COUNT"),
        stop_loss_context_extra_confirmation_loops=config_int("strategy", "stop_loss_context_extra_confirmation_loops", 2, env_key="STRATEGY_STOP_LOSS_CONTEXT_EXTRA_CONFIRMATION_LOOPS"),
        enable_noise_ratio_adaptation=config_bool("strategy", "enable_noise_ratio_adaptation", True, env_key="STRATEGY_ENABLE_NOISE_RATIO_ADAPTATION"),
        noise_ratio_lookback=config_int("strategy", "noise_ratio_lookback", 20, env_key="STRATEGY_NOISE_RATIO_LOOKBACK"),
        noise_ratio_baseline=config_float("strategy", "noise_ratio_baseline", 0.50, env_key="STRATEGY_NOISE_RATIO_BASELINE"),
        noise_ratio_min_multiplier=config_float("strategy", "noise_ratio_min_multiplier", 0.70, env_key="STRATEGY_NOISE_RATIO_MIN_MULTIPLIER"),
        noise_ratio_max_multiplier=config_float("strategy", "noise_ratio_max_multiplier", 1.30, env_key="STRATEGY_NOISE_RATIO_MAX_MULTIPLIER"),
        enable_volume_filter=config_bool("strategy", "enable_volume_filter", True, env_key="STRATEGY_ENABLE_VOLUME_FILTER"),
        volume_lookback=config_int("strategy", "volume_lookback", 20, env_key="STRATEGY_VOLUME_LOOKBACK"),
        min_volume_ratio=config_float("strategy", "min_volume_ratio", 1.2, env_key="STRATEGY_MIN_VOLUME_RATIO"),
        min_volume_ratio_map=parse_symbol_float_map(config_value("strategy", "min_volume_ratio_map", {}, env_key="STRATEGY_MIN_VOLUME_RATIO_MAP")),
        max_volume_ratio=config_float("strategy", "max_volume_ratio", 2.5, env_key="STRATEGY_MAX_VOLUME_RATIO"),
        max_volume_ratio_map=parse_symbol_float_map(config_value("strategy", "max_volume_ratio_map", {}, env_key="STRATEGY_MAX_VOLUME_RATIO_MAP")),
        enable_okx_funding_rate_guard=config_bool("strategy", "enable_okx_funding_rate_guard", True, env_key="STRATEGY_ENABLE_OKX_FUNDING_RATE_GUARD"),
        okx_funding_rate_max_long_bias=config_float("strategy", "okx_funding_rate_max_long_bias", 0.0005, env_key="STRATEGY_OKX_FUNDING_RATE_MAX_LONG_BIAS"),
        okx_funding_rate_cache_ttl_sec=config_float("strategy", "okx_funding_rate_cache_ttl_sec", 300.0, env_key="STRATEGY_OKX_FUNDING_RATE_CACHE_TTL_SEC"),
        position_ratio_map=parse_symbol_float_map(config_value("strategy", "position_ratio_map", {}, env_key="STRATEGY_POSITION_RATIO_MAP")),
        enable_regime_position_scaling=config_bool("strategy", "enable_regime_position_scaling", True, env_key="STRATEGY_ENABLE_REGIME_POSITION_SCALING"),
        regime_position_scale_map=parse_symbol_float_map(config_value("strategy", "regime_position_scale_map", {}, env_key="STRATEGY_REGIME_POSITION_SCALE_MAP")),
        enable_btc_regime_position_scaling=config_bool("strategy", "enable_btc_regime_position_scaling", True, env_key="STRATEGY_ENABLE_BTC_REGIME_POSITION_SCALING"),
        btc_regime_position_scale_map=parse_symbol_float_map(config_value("strategy", "btc_regime_position_scale_map", {}, env_key="STRATEGY_BTC_REGIME_POSITION_SCALE_MAP")),
        btc_regime_position_scale_override_map=parse_symbol_regime_float_map(config_value("strategy", "btc_regime_position_scale_override_map", {}, env_key="STRATEGY_BTC_REGIME_POSITION_SCALE_OVERRIDE_MAP")),
        enable_btc_atr_position_scaling=config_bool("strategy", "enable_btc_atr_position_scaling", True, env_key="STRATEGY_ENABLE_BTC_ATR_POSITION_SCALING"),
        btc_atr_position_scale_lookback=config_int("strategy", "btc_atr_position_scale_lookback", 14, env_key="STRATEGY_BTC_ATR_POSITION_SCALE_LOOKBACK"),
        btc_atr_position_scale_threshold_map=parse_float_float_map(config_value("strategy", "btc_atr_position_scale_threshold_map", {}, env_key="STRATEGY_BTC_ATR_POSITION_SCALE_THRESHOLD_MAP")),
        enable_alt_atr_position_sizing=config_bool("strategy", "enable_alt_atr_position_sizing", True, env_key="STRATEGY_ENABLE_ALT_ATR_POSITION_SIZING"),
        alt_atr_position_scale_threshold_map=parse_float_float_map(config_value("strategy", "alt_atr_position_scale_threshold_map", {}, env_key="STRATEGY_ALT_ATR_POSITION_SCALE_THRESHOLD_MAP")),
        enable_volatility_filter=config_bool("strategy", "enable_volatility_filter", True, env_key="STRATEGY_ENABLE_VOLATILITY_FILTER"),
        volatility_lookback=config_int("strategy", "volatility_lookback", 20, env_key="STRATEGY_VOLATILITY_LOOKBACK"),
        min_volatility_pct=config_float("strategy", "min_volatility_pct", 0.05, env_key="STRATEGY_MIN_VOLATILITY_PCT"),
        max_volatility_pct=config_float("strategy", "max_volatility_pct", 5.0, env_key="STRATEGY_MAX_VOLATILITY_PCT"),
        min_crossover_gap_pct=config_float("strategy", "min_crossover_gap_pct", 1.2, env_key="STRATEGY_MIN_CROSSOVER_GAP_PCT"),
        max_entry_gap_pct=config_float("strategy", "max_entry_gap_pct", 0.25, env_key="STRATEGY_MAX_ENTRY_GAP_PCT"),
        averaging_down_gap_pct=config_float("strategy", "averaging_down_gap_pct", 2.0, env_key="STRATEGY_AVERAGING_DOWN_GAP_PCT"),
        min_take_profit_pct=config_float("strategy", "min_take_profit_pct", 1.0, env_key="STRATEGY_MIN_TAKE_PROFIT_PCT"),
        stop_loss_pct=config_float("strategy", "stop_loss_pct", 1.5, env_key="STRATEGY_STOP_LOSS_PCT"),
        enable_fee_protect_exit=config_bool("strategy", "enable_fee_protect_exit", True, env_key="STRATEGY_ENABLE_FEE_PROTECT_EXIT"),
        fee_protect_min_net_pnl_pct=config_float("strategy", "fee_protect_min_net_pnl_pct", 0.20, env_key="STRATEGY_FEE_PROTECT_MIN_NET_PNL_PCT"),
        fee_protect_min_net_pnl_pct_map=parse_symbol_float_map(config_value("strategy", "fee_protect_min_net_pnl_pct_map", {}, env_key="STRATEGY_FEE_PROTECT_MIN_NET_PNL_PCT_MAP")),
        enable_break_even_guard=config_bool("strategy", "enable_break_even_guard", True, env_key="STRATEGY_ENABLE_BREAK_EVEN_GUARD"),
        break_even_guard_min_mfe_pct=config_float("strategy", "break_even_guard_min_mfe_pct", 0.0, env_key="STRATEGY_BREAK_EVEN_GUARD_MIN_MFE_PCT"),
        break_even_guard_min_mfe_pct_map=parse_symbol_float_map(config_value("strategy", "break_even_guard_min_mfe_pct_map", {}, env_key="STRATEGY_BREAK_EVEN_GUARD_MIN_MFE_PCT_MAP")),
        break_even_guard_floor_net_pnl_pct=config_float("strategy", "break_even_guard_floor_net_pnl_pct", 0.0, env_key="STRATEGY_BREAK_EVEN_GUARD_FLOOR_NET_PNL_PCT"),
        break_even_guard_floor_net_pnl_pct_map=parse_symbol_float_map(config_value("strategy", "break_even_guard_floor_net_pnl_pct_map", {}, env_key="STRATEGY_BREAK_EVEN_GUARD_FLOOR_NET_PNL_PCT_MAP")),
        break_even_guard_max_profit_retrace_pct=config_float("strategy", "break_even_guard_max_profit_retrace_pct", 0.6, env_key="STRATEGY_BREAK_EVEN_GUARD_MAX_PROFIT_RETRACE_PCT"),
        enable_volume_spike_exit=config_bool("strategy", "enable_volume_spike_exit", True, env_key="STRATEGY_ENABLE_VOLUME_SPIKE_EXIT"),
        volume_spike_exit_min_profit_pct=config_float("strategy", "volume_spike_exit_min_profit_pct", 0.2, env_key="STRATEGY_VOLUME_SPIKE_EXIT_MIN_PROFIT_PCT"),
        volume_spike_exit_max_volume_ratio=config_float("strategy", "volume_spike_exit_max_volume_ratio", 0.8, env_key="STRATEGY_VOLUME_SPIKE_EXIT_MAX_VOLUME_RATIO"),
        enable_auto_tune=enable_auto_tune,
        auto_tune_window_days=auto_tune_window_days,
        auto_tune_min_trades=auto_tune_min_trades,
        auto_tune_positive_win_rate=auto_tune_positive_win_rate,
        auto_tune_positive_profit_factor=auto_tune_positive_profit_factor,
        auto_tune_negative_win_rate=auto_tune_negative_win_rate,
        auto_tune_negative_profit_factor=auto_tune_negative_profit_factor,
        auto_tune_adjustment_limit_pct=auto_tune_adjustment_limit_pct,
        auto_tune_adjustment_map=auto_tune_adjustment_map,
        signal_score_min=config_float("strategy", "signal_score_min", 55, env_key="STRATEGY_SIGNAL_SCORE_MIN"),
        signal_score_min_map=parse_symbol_float_map(config_value("strategy", "signal_score_min_map", {}, env_key="STRATEGY_SIGNAL_SCORE_MIN_MAP")),
        dynamic_signal_score_min=config_float("strategy", "dynamic_signal_score_min", 70, env_key="STRATEGY_DYNAMIC_SIGNAL_SCORE_MIN"),
        entry_confirmation_loops=config_int("strategy", "entry_confirmation_loops", 2, env_key="STRATEGY_ENTRY_CONFIRMATION_LOOPS"),
        enable_correlation_filter=config_bool("strategy", "enable_correlation_filter", True, env_key="STRATEGY_ENABLE_CORRELATION_FILTER"),
        correlation_lookback=config_int("strategy", "correlation_lookback", 20, env_key="STRATEGY_CORRELATION_LOOKBACK"),
        max_correlation_with_btc=config_float("strategy", "max_correlation_with_btc", 0.70, env_key="STRATEGY_MAX_CORRELATION_WITH_BTC"),
        enable_fill_quality_guard=config_bool("strategy", "enable_fill_quality_guard", True, env_key="STRATEGY_ENABLE_FILL_QUALITY_GUARD"),
        fill_quality_lookback_sec=config_int("strategy", "fill_quality_lookback_sec", 3600, env_key="STRATEGY_FILL_QUALITY_LOOKBACK_SEC"),
        fill_quality_min_fill_ratio=config_float("strategy", "fill_quality_min_fill_ratio", 0.95, env_key="STRATEGY_FILL_QUALITY_MIN_FILL_RATIO"),
        fill_quality_min_sample_count=config_int("strategy", "fill_quality_min_sample_count", 1, env_key="STRATEGY_FILL_QUALITY_MIN_SAMPLE_COUNT"),
        min_buy_order_value=(
            config_section_float(
                resolve_exchange_section_from_env_key(min_buy_order_env_key) or "strategy",
                "min_buy_order_value",
                default_min_buy_order_value,
                env_key=min_buy_order_env_key,
            )
        ),
        loop_interval_sec=config_int("strategy", "loop_interval_sec", 10, env_key="STRATEGY_LOOP_INTERVAL_SEC"),
        min_crossover_gap_pct_map=parse_symbol_float_map(config_value("strategy", "min_crossover_gap_pct_map", {}, env_key="STRATEGY_MIN_CROSSOVER_GAP_PCT_MAP")),
        max_entry_gap_pct_map=parse_symbol_float_map(config_value("strategy", "max_entry_gap_pct_map", {}, env_key="STRATEGY_MAX_ENTRY_GAP_PCT_MAP")),
        min_take_profit_pct_map=parse_symbol_float_map(config_value("strategy", "min_take_profit_pct_map", {}, env_key="STRATEGY_MIN_TAKE_PROFIT_PCT_MAP")),
        stop_loss_pct_map=parse_symbol_float_map(config_value("strategy", "stop_loss_pct_map", {}, env_key="STRATEGY_STOP_LOSS_PCT_MAP")),
        min_order_amount_map=parse_symbol_float_map(config_value("strategy", "min_order_amount_map", {}, env_key="STRATEGY_MIN_ORDER_AMOUNT_MAP")),
        partial_take_profit_symbols=tuple(
            parse_symbol_list(config_str("strategy", "partial_take_profit_symbols", "", env_key="STRATEGY_PARTIAL_TAKE_PROFIT_SYMBOLS"), [])
        ),
        partial_stop_loss_symbols=tuple(
            parse_symbol_list(config_str("strategy", "partial_stop_loss_symbols", "", env_key="STRATEGY_PARTIAL_STOP_LOSS_SYMBOLS"), [])
        ),
        partial_take_profit_ratio=config_float("strategy", "partial_tp_ratio", 0.5, env_key="STRATEGY_PARTIAL_TP_RATIO"),
        partial_stop_loss_ratio=config_float("strategy", "partial_sl_ratio", 0.5, env_key="STRATEGY_PARTIAL_SL_RATIO"),
        partial_take_profit_reentry_cooldown_sec=config_int("strategy", "partial_tp_reentry_cooldown_sec", 900, env_key="STRATEGY_PARTIAL_TP_REENTRY_COOLDOWN_SEC"),
    )
