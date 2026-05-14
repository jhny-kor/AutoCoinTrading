"""
수정 요약
- 2026-05-14: 실행모델/호가/슬리피지 helper 를 tools.backtest_execution 으로 분리했다.
- 2026-04-24: analysis_logs 호가 스냅샷을 읽어 best bid/ask 와 depth 기반 부분체결을 반영하는 체결 모델을 추가했다.
- 2026-05-11: 알트 리플레이가 live volume/gap 상한과 volume spike exit 계약을 반영하도록 보강했다.
- 2026-04-23: Sharpe ratio, profit factor, 슬리피지/부분체결/지연 실행 모델을 추가해 백테스트 요약과 실행 가정을 강화했다.
- 2026-04-13: 장시간 걸리던 주간 알트/SOL 백테스트가 배치 요약 파일 생성 전에 사실상 멈추지 않도록 반복 지표 계산 입력을 최근 필요 구간으로 제한해 성능 병목을 줄였다.
- 2026-04-10: 백테스트 실행 시 추가 override 세트를 임시 적용하고 summary 에 적용 세트 메타데이터를 남기도록 확장했다.
- 알트 리플레이에서 점수 기반 비중 계산에 필요한 최소 거래량 기준값을 일관되게 재사용하도록 회귀 버그를 수정
- 2026-04-09: score 기반 동적 자본 배분도 리플레이에 반영해 live 와 backtest 의 비중 규칙 차이를 줄이도록 확장
- 2026-04-08: 알트 리플레이에도 live 와 같은 fresh cross, HTF bearish 차단, Bollinger squeeze 입력을 반영해 parity 를 보강
- 기준 시각 이전 실거래 포지션을 초기 상태로 주입할 수 있게 position-aware 리플레이 초기 상태를 추가해 실거래 비교 정확도를 높이도록 확장
- 실거래와의 차이를 줄이기 위해 알트/BTC 리플레이도 공통 신호 계산, 레짐 정책, 노이즈 비율, 진입 상태 머신을 반영하도록 확장
- 혼합 청산 세트를 위해 알트 리플레이도 심볼별 순익 보호 익절 기준 map 을 읽도록 확장
- 로컬 OHLCV 파일과 공개 거래소 시세를 이용해 전략을 오프라인으로 재생하는 백테스트/리플레이 CLI 를 추가
- 알트 MA 전략과 BTC EMA 전략을 공통 인터페이스로 요약/거래 로그까지 저장하도록 구성
- 결과를 reports/backtests 아래에 summary.json, trades.jsonl, equity_curve.jsonl 로 남기도록 추가
- fetch 서브커맨드로 공개 OHLCV 를 저장해 리플레이 입력 데이터를 준비할 수 있도록 확장

백테스트/리플레이 도구

- 목적: 실거래 전에 전략을 로컬 데이터로 다시 재생해 기대 동작을 검증한다.
- 입력: CSV 또는 JSONL 형식의 OHLCV 파일
- 출력: 요약 JSON, 체결 JSONL, 자산곡선 JSONL
- 범위: 알트 MA 전략, BTC EMA 전략
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_right
from pathlib import Path
from typing import Any

from analysis_log_collector import (
    create_okx_public_client,
    create_upbit_public_client,
    fetch_okx_ohlcv,
    fetch_upbit_ohlcv,
)
from btc_trend_settings import load_btc_trend_settings
from core.risk.alt_exit import compute_alt_exit_decisions, compute_alt_position_metrics
from core.strategy.alt import compute_alt_signal_state, compute_can_average_down
from core.strategy.btc import compute_btc_entry_state, compute_btc_exit_flags
from core.strategy.btc_position import evaluate_btc_open_position
from core.strategy.indicators import (
    calc_adx,
    calc_bollinger_bands,
    calc_bollinger_band_width_pct,
    calc_donchian_channel,
    calc_macd_histogram,
    calc_noise_ratio,
    calc_pct_slope,
    calc_return_correlation,
    calc_rsi,
)
from core.strategy.timing import update_entry_timing_state
from market_regime_guard import classify_symbol_regime, get_alt_regime_policy, get_btc_regime_policy
from portfolio_allocator import load_portfolio_allocation_settings
from strategy_settings import load_strategy_settings
from settings.env import temporary_runtime_overrides
from tools.apply_strategy_set import resolve_set_paths
from tools.backtest_io import (
    build_output_dir,
    format_iso,
    get_active_candles_by_time,
    get_recent_active_candles_by_time,
    load_candles,
    local_date_key,
    resample_candles,
    write_json,
    write_jsonl,
)
from tools.backtest_execution import (
    apply_execution_price,
    build_execution_model,
    estimate_orderbook_fill_ratio,
    load_orderbook_snapshots,
    resolve_default_fee_rate,
    resolve_default_max_daily_loss,
    resolve_default_min_buy_order_value,
    resolve_execution_candle,
    resolve_orderbook_snapshot,
)
from tools.backtest_math import (
    calc_atr,
    calc_avg_abs_change_pct,
    calc_ema_series,
    calc_sma,
    calc_volume_ratio,
    compute_max_drawdown,
    compute_profit_factor,
    compute_sharpe_ratio,
    detect_ema_crossover,
    detect_sma_crossover,
    get_recent_swing_high,
    get_recent_swing_low,
    parse_timeframe_to_minutes,
    build_full_ema_series,
    build_macd_histogram_series,
)
from tools.backtest_models import (
    DEFAULT_RISK_PER_TRADE,
    AltReplayInitialState,
    BtcReplayInitialState,
    Candle,
    EquityPoint,
    ExecutionModel,
    OrderbookSnapshot,
    TradeRecord,
)
from tools.update_backtest_registry import REGISTRY_PATH, build_all_registry_entries, write_registry
from core.risk.allocation import compute_allocation_score


def parse_bool(raw: str | None, default: bool = False) -> bool:
    """문자열 불리언 값을 파싱한다."""
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def build_exit_prices(
    *,
    entry_price: float,
    atr_value: float,
    recent_swing_low: float,
    recent_swing_high: float,
    min_take_profit_pct: float,
    settings,
) -> tuple[float, float]:
    """BTC 전략의 손절/익절 가격을 계산한다."""
    if settings.stop_mode == "swing":
        stop_price = recent_swing_low
    else:
        stop_price = entry_price - (atr_value * settings.stop_atr_multiple)

    if settings.take_profit_mode == "swing":
        take_profit_price = recent_swing_high
        if take_profit_price <= entry_price:
            take_profit_price = entry_price + (atr_value * settings.take_profit_atr_multiple)
    else:
        take_profit_price = entry_price + (atr_value * settings.take_profit_atr_multiple)

    fee_floor = entry_price * (1 + (min_take_profit_pct / 100))
    return stop_price, max(take_profit_price, fee_floor)


def clamp_noise_multiplier(
    *,
    noise_ratio: float | None,
    baseline: float,
    min_multiplier: float,
    max_multiplier: float,
) -> float:
    """노이즈 비율을 진입 문턱값 배수로 변환한다."""
    if noise_ratio is None:
        return 1.0
    multiplier = 1.0 + ((noise_ratio - baseline) / max(baseline, 1e-9)) * 0.5
    return max(min_multiplier, min(max_multiplier, multiplier))


def build_replay_symbol_regime(
    *,
    volume_ratio: float | None,
    avg_abs_change_pct: float | None,
    gap_pct: float | None,
    rsi_value: float | None,
    adx_value: float | None,
    bullish_signal: bool,
    bearish_signal: bool,
    above_ma: bool,
    htf_bullish: bool | None,
    public_buy_ready: bool,
):
    """실시간 분석 로그 대신 현재 캔들 특징으로 레짐을 분류한다."""
    return classify_symbol_regime(
        {
            "volume_ratio": volume_ratio,
            "avg_abs_change_pct": avg_abs_change_pct,
            "gap_pct": gap_pct,
            "rsi": rsi_value,
            "adx": adx_value,
            "public_buy_ready": public_buy_ready,
            "bullish_signal": bullish_signal,
            "bearish_signal": bearish_signal,
            "above_ma": above_ma,
            "htf_bullish": htf_bullish,
            "collected_at_local": None,
        }
    )


def simulate_alt_strategy(
    *,
    candles: list[Candle],
    btc_reference_candles: list[Candle] | None,
    source_timeframe: str,
    symbol: str,
    exchange_name: str,
    initial_cash: float,
    fee_rate_pct: float,
    risk_per_trade: float,
    min_buy_order_value: float,
    max_daily_loss_quote: float,
    execution_model: ExecutionModel | None = None,
    orderbook_snapshots: list[OrderbookSnapshot] | None = None,
    initial_state: AltReplayInitialState | None = None,
    start_timestamp_ms: int | None = None,
) -> tuple[dict[str, Any], list[TradeRecord], list[EquityPoint]]:
    """공통 알트 MA 전략을 오프라인으로 재생한다."""
    strategy = load_strategy_settings(
        "UPBIT_MIN_BUY_ORDER_VALUE" if exchange_name.lower() == "upbit" else "OKX_MIN_BUY_ORDER_VALUE",
        min_buy_order_value,
    )
    execution_model = execution_model or ExecutionModel(
        slippage_bps=0.0,
        buy_fill_ratio=1.0,
        sell_fill_ratio=1.0,
        latency_ms=0,
    )
    orderbook_snapshots = orderbook_snapshots or []
    portfolio_settings = load_portfolio_allocation_settings()
    higher_timeframe_candles = resample_candles(
        candles,
        source_timeframe=source_timeframe,
        target_timeframe=strategy.higher_timeframe,
    )
    higher_timeframe_timestamps = [candle.timestamp_ms for candle in higher_timeframe_candles]
    btc_reference_timestamps = (
        [candle.timestamp_ms for candle in btc_reference_candles]
        if btc_reference_candles
        else []
    )

    cash = initial_state.cash_quote if initial_state is not None else initial_cash
    units = initial_state.units if initial_state is not None else 0.0
    avg_entry_price: float | None = (
        initial_state.average_entry_price if initial_state is not None else None
    )
    entry_count = initial_state.entry_count if initial_state is not None else 0
    highest_price_since_entry: float | None = (
        initial_state.highest_price_since_entry if initial_state is not None else None
    )
    lowest_price_since_entry: float | None = (
        initial_state.lowest_price_since_entry if initial_state is not None else None
    )
    partial_take_profit_done = (
        initial_state.partial_take_profit_done if initial_state is not None else False
    )
    partial_stop_loss_done = (
        initial_state.partial_stop_loss_done if initial_state is not None else False
    )
    last_trade_ts = initial_state.last_trade_ts if initial_state is not None else 0
    last_partial_take_profit_ts = (
        initial_state.last_partial_take_profit_ts if initial_state is not None else 0
    )
    daily_realized_pnl_quote = (
        initial_state.daily_realized_pnl_quote if initial_state is not None else 0.0
    )
    daily_pnl_date: str | None = (
        local_date_key(start_timestamp_ms) if start_timestamp_ms is not None else None
    )
    trade_records: list[TradeRecord] = []
    equity_curve: list[EquityPoint] = []
    entry_timing_state: dict[str, dict[str, int | str]] = {}
    ma_period = 20
    all_closes = [candle.close for candle in candles]
    macd_histogram_series = build_macd_histogram_series(
        all_closes,
        fast_period=strategy.macd_fast_period,
        slow_period=strategy.macd_slow_period,
        signal_period=strategy.macd_signal_period,
    )

    min_required = max(
        strategy.volume_lookback + 3,
        strategy.volatility_lookback + 3,
        strategy.rsi_period + 3,
        strategy.macd_slow_period + strategy.macd_signal_period + 3,
        strategy.noise_ratio_lookback + 3,
        25,
    )
    max_indicator_history = max(
        min_required + 2,
        ma_period + strategy.trend_slope_lookback + 5,
        strategy.bb_period + 5,
        strategy.noise_ratio_lookback + 5,
        max(29, 14 * 2 + 2),
    )
    htf_required = max(1, strategy.higher_timeframe_ma_period + 2)
    btc_reference_required = max(1, strategy.correlation_lookback + 2)
    for index in range(min_required, len(candles)):
        start_index = max(0, index + 1 - max_indicator_history)
        window = candles[start_index : index + 1]
        current = candles[index]
        if start_timestamp_ms is not None and current.timestamp_ms < start_timestamp_ms:
            continue
        current_date = local_date_key(current.timestamp_ms)
        if current_date != daily_pnl_date:
            daily_pnl_date = current_date
            daily_realized_pnl_quote = 0.0

        closes = all_closes[start_index : index + 1]
        bullish, bearish, prev_close, prev_ma, last_close, last_ma = detect_sma_crossover(closes, ma_period)
        ma_series = [
            calc_sma(closes[: idx + 1], ma_period)
            for idx in range(ma_period - 1, len(closes))
        ]
        volume_ratio = calc_volume_ratio(window, strategy.volume_lookback)
        avg_abs_change_pct = calc_avg_abs_change_pct(closes, strategy.volatility_lookback)
        noise_ratio = calc_noise_ratio(
            [[c.timestamp_ms, c.open, c.high, c.low, c.close, c.volume] for c in window],
            strategy.noise_ratio_lookback,
        )
        rsi_value = calc_rsi(closes, strategy.rsi_period)
        macd_histogram = macd_histogram_series[index]
        bb_upper, _bb_mid, _bb_lower = calc_bollinger_bands(
            closes,
            period=strategy.bb_period,
            stddev_multiplier=strategy.bb_stddev,
        )
        bb_width_pct = calc_bollinger_band_width_pct(
            closes,
            period=strategy.bb_period,
            stddev_multiplier=strategy.bb_stddev,
        )
        ma_slope_pct = calc_pct_slope(ma_series, strategy.trend_slope_lookback)
        price_slope_pct = calc_pct_slope(closes, strategy.trend_slope_lookback)
        adx_value = calc_adx(
            [[c.timestamp_ms, c.open, c.high, c.low, c.close, c.volume] for c in window],
            14,
        )

        active_higher_timeframe = get_recent_active_candles_by_time(
            higher_timeframe_candles,
            higher_timeframe_timestamps,
            current.timestamp_ms,
            htf_required,
        )
        htf_bullish = True
        htf_bearish = True
        if strategy.enable_higher_timeframe_filter:
            htf_bullish = False
            htf_bearish = False
            if len(active_higher_timeframe) >= strategy.higher_timeframe_ma_period:
                htf_closes = [candle.close for candle in active_higher_timeframe]
                htf_last_close = htf_closes[-1]
                htf_last_ma = calc_sma(htf_closes, strategy.higher_timeframe_ma_period)
                htf_bullish = htf_last_close > htf_last_ma
                htf_bearish = htf_last_close < htf_last_ma

        base_min_gap_pct = strategy.get_crossover_gap_pct(symbol)
        noise_gap_multiplier = clamp_noise_multiplier(
            noise_ratio=noise_ratio,
            baseline=strategy.noise_ratio_baseline,
            min_multiplier=strategy.noise_ratio_min_multiplier,
            max_multiplier=strategy.noise_ratio_max_multiplier,
        ) if strategy.enable_noise_ratio_adaptation else 1.0
        min_gap_pct = base_min_gap_pct * noise_gap_multiplier

        effective_min_volume_ratio = strategy.get_min_volume_ratio(symbol)
        effective_max_volume_ratio = strategy.get_max_volume_ratio(symbol)
        max_entry_gap_pct = strategy.get_max_entry_gap_pct(symbol)

        alt_signal_state = compute_alt_signal_state(
            prev_close=prev_close,
            prev_ma=prev_ma,
            last_close=last_close,
            last_ma=last_ma,
            min_gap_pct=min_gap_pct,
            enable_trend_follow_entry=strategy.enable_trend_follow_entry,
            require_prev_above_ma=strategy.trend_follow_requires_prev_above_ma,
            require_price_rising=strategy.trend_follow_requires_price_rising,
            require_ma_slope_positive=strategy.trend_follow_requires_ma_slope_positive,
            volume_ratio=volume_ratio,
            min_volume_ratio=effective_min_volume_ratio,
            rsi_value=rsi_value,
            enable_rsi_filter=strategy.enable_rsi_filter,
            rsi_entry_min=strategy.rsi_entry_min,
            rsi_entry_max=strategy.rsi_entry_max,
            macd_histogram=macd_histogram,
            enable_macd_filter=strategy.enable_macd_filter,
            ma_slope_pct=ma_slope_pct,
            price_slope_pct=price_slope_pct,
            signal_score_min=strategy.signal_score_min,
            entry_mode=strategy.entry_mode,
            bb_width_pct=bb_width_pct,
            squeeze_max_bandwidth_pct=strategy.squeeze_max_bandwidth_pct,
            bb_upper=bb_upper,
            squeeze_min_volume_ratio=strategy.squeeze_min_volume_ratio,
        )
        bullish = bool(alt_signal_state["bullish"])
        bearish = bool(alt_signal_state["bearish"])
        gap_pct = float(alt_signal_state["gap_pct"])
        gap_within_upper_bound = gap_pct <= max_entry_gap_pct
        signal_is_strong = bool(alt_signal_state["signal_is_strong"])
        signal_score = float(alt_signal_state["signal_score"])
        rsi_filter_passed = bool(alt_signal_state["rsi_filter_passed"])
        macd_filter_passed = bool(alt_signal_state["macd_filter_passed"])
        trend_follow_entry = bool(alt_signal_state["trend_follow_entry"])
        entry_signal = bool(alt_signal_state["entry_signal"])

        volume_filter_passed = (
            True
            if not strategy.enable_volume_filter
            else volume_ratio is not None and volume_ratio >= effective_min_volume_ratio
        )
        volume_within_upper_bound = (
            True
            if not strategy.enable_volume_filter or volume_ratio is None
            else volume_ratio <= effective_max_volume_ratio
        )
        volatility_filter_passed = (
            True
            if not strategy.enable_volatility_filter
            else (
                avg_abs_change_pct is not None
                and strategy.min_volatility_pct <= avg_abs_change_pct <= strategy.max_volatility_pct
            )
        )
        higher_timeframe_entry_passed = (
            True if not strategy.enable_higher_timeframe_filter else bool(htf_bullish)
        )
        higher_timeframe_exit_passed = (
            True if not strategy.enable_higher_timeframe_filter else bool(htf_bearish)
        )
        htf_bearish_entry_blocked = (
            entry_signal
            and strategy.blocks_entry_when_htf_bearish(symbol)
            and htf_bearish
        )

        public_buy_ready = (
            bullish
            and signal_is_strong
            and rsi_filter_passed
            and macd_filter_passed
            and volume_filter_passed
            and volatility_filter_passed
            and higher_timeframe_entry_passed
            and not htf_bearish_entry_blocked
        )
        regime_snapshot = build_replay_symbol_regime(
            volume_ratio=volume_ratio,
            avg_abs_change_pct=avg_abs_change_pct,
            gap_pct=gap_pct,
            rsi_value=rsi_value,
            adx_value=adx_value,
            bullish_signal=bullish,
            bearish_signal=bearish,
            above_ma=last_close > last_ma,
            htf_bullish=htf_bullish,
            public_buy_ready=public_buy_ready,
        )
        regime_policy = get_alt_regime_policy(regime_snapshot.regime)

        btc_reference_closes: list[float] = []
        if btc_reference_candles:
            active_btc_reference = get_recent_active_candles_by_time(
                btc_reference_candles,
                btc_reference_timestamps,
                current.timestamp_ms,
                btc_reference_required,
            )
            btc_reference_closes = [candle.close for candle in active_btc_reference]
        correlation_with_btc = (
            calc_return_correlation(
                closes,
                btc_reference_closes,
                lookback=strategy.correlation_lookback,
            )
            if strategy.enable_correlation_filter and btc_reference_closes
            else None
        )

        position_quote_value = units * last_close
        has_position = units > 0 and position_quote_value >= min_buy_order_value * 0.5
        in_partial_tp_cooldown = (
            strategy.partial_take_profit_reentry_cooldown_sec > 0
            and (current.timestamp_ms - last_partial_take_profit_ts) / 1000
            < strategy.partial_take_profit_reentry_cooldown_sec
        )
        in_trade_cooldown = (
            strategy.min_trade_interval_sec > 0
            and (current.timestamp_ms - last_trade_ts) / 1000 < strategy.min_trade_interval_sec
        )
        daily_loss_limit_reached = daily_realized_pnl_quote <= -max_daily_loss_quote

        correlation_entry_blocked = (
            entry_signal
            and strategy.enable_correlation_filter
            and correlation_with_btc is not None
            and correlation_with_btc >= strategy.max_correlation_with_btc
        )
        fill_quality_entry_blocked = False
        raw_entry_candidate = (
            entry_signal
            and not regime_policy.pause_new_entry
            and not correlation_entry_blocked
            and (not regime_policy.require_fresh_cross or bullish)
            and not htf_bearish_entry_blocked
        )
        entry_timing_snapshot = update_entry_timing_state(
            state_store=entry_timing_state,
            symbol=symbol,
            has_position=has_position,
            candidate_active=raw_entry_candidate,
            required_confirmations=strategy.entry_confirmation_loops,
        )

        realized_on_this_bar = False
        pnl_pct = None
        current_net_realized_pnl_pct = None
        mfe_pct = None
        mae_pct = None
        if has_position and avg_entry_price is not None:
            position_metrics = compute_alt_position_metrics(
                has_position=has_position,
                average_entry_price=avg_entry_price,
                last_close=last_close,
                base_free=units,
                fee_rate_pct=fee_rate_pct,
                highest_price_since_entry=highest_price_since_entry,
                lowest_price_since_entry=lowest_price_since_entry,
            )
            highest_price_since_entry = position_metrics["highest_price_since_entry"]
            lowest_price_since_entry = position_metrics["lowest_price_since_entry"]
            pnl_pct = position_metrics["pnl_pct"]
            mfe_pct = position_metrics["mfe_pct"]
            mae_pct = position_metrics["mae_pct"]
            current_net_realized_pnl_pct = position_metrics["net_pnl_pct"]
        elif not has_position:
            highest_price_since_entry = None
            lowest_price_since_entry = None

        take_profit_pct = strategy.get_take_profit_pct(symbol) + regime_policy.take_profit_bonus_pct
        stop_loss_pct = strategy.get_stop_loss_pct(symbol) * regime_policy.stop_loss_multiplier
        fee_protect_min_net_pnl_pct = strategy.get_fee_protect_min_net_pnl_pct(symbol)
        break_even_guard_min_mfe_pct = strategy.get_break_even_guard_min_mfe_pct(symbol)
        break_even_guard_floor_net_pnl_pct = strategy.get_break_even_guard_floor_net_pnl_pct(symbol)
        alt_exit_state = compute_alt_exit_decisions(
            has_position=has_position,
            pnl_pct=pnl_pct,
            mfe_pct=mfe_pct,
            current_net_realized_pnl_pct=current_net_realized_pnl_pct,
            take_profit_pct=take_profit_pct,
            stop_loss_pct=stop_loss_pct,
            fee_rate_pct=fee_rate_pct,
            enable_fee_protect_exit=strategy.enable_fee_protect_exit,
            fee_protect_min_net_pnl_pct=fee_protect_min_net_pnl_pct,
            enable_break_even_guard=strategy.enable_break_even_guard,
            break_even_guard_min_mfe_pct=break_even_guard_min_mfe_pct,
            break_even_guard_floor_net_pnl_pct=break_even_guard_floor_net_pnl_pct,
            break_even_guard_max_profit_retrace_pct=strategy.break_even_guard_max_profit_retrace_pct,
            enable_volume_spike_exit=strategy.enable_volume_spike_exit,
            volume_spike_exit_min_profit_pct=strategy.volume_spike_exit_min_profit_pct,
            volume_spike_exit_max_volume_ratio=strategy.volume_spike_exit_max_volume_ratio,
            volume_ratio=volume_ratio,
            bearish=bearish,
            sell_split_ratio=strategy.sell_split_ratio,
        )
        take_profit_ready = bool(alt_exit_state["take_profit_ready"])
        stop_loss_triggered = bool(alt_exit_state["stop_loss_triggered"])
        profit_protect_triggered = bool(alt_exit_state["profit_protect_triggered"])
        break_even_guard_triggered = bool(alt_exit_state["break_even_guard_triggered"])
        volume_spike_exit_triggered = bool(alt_exit_state["volume_spike_exit_triggered"])

        if has_position and avg_entry_price is not None:
            normal_exit_triggered = bearish and take_profit_ready and higher_timeframe_exit_passed
            exit_ratio = 0.0
            exit_reason = ""
            is_final_exit = True
            if stop_loss_triggered:
                if strategy.uses_partial_stop_loss(symbol) and not partial_stop_loss_done:
                    exit_ratio = strategy.partial_stop_loss_ratio
                    exit_reason = "partial_stop_loss"
                    is_final_exit = False
                else:
                    exit_ratio = 1.0
                    exit_reason = "stop_loss"
            elif profit_protect_triggered:
                exit_ratio = 1.0
                exit_reason = "profit_protect_take_profit"
            elif break_even_guard_triggered:
                exit_ratio = 1.0
                exit_reason = "break_even_guard_exit"
            elif volume_spike_exit_triggered:
                exit_ratio = 1.0
                exit_reason = "volume_spike_take_profit"
            elif normal_exit_triggered:
                if strategy.uses_partial_take_profit(symbol) and not partial_take_profit_done:
                    exit_ratio = strategy.partial_take_profit_ratio
                    exit_reason = "partial_take_profit"
                    is_final_exit = False
                else:
                    exit_ratio = 1.0
                    exit_reason = "take_profit"

            if exit_ratio > 0:
                requested_amount = units * min(max(exit_ratio, 0.0), 1.0)
                amount = requested_amount * execution_model.sell_fill_ratio
                if amount > 0:
                    execution_candle, _, execution_timing = resolve_execution_candle(
                        candles,
                        current_index=index,
                        execution_model=execution_model,
                    )
                    orderbook_snapshot = resolve_orderbook_snapshot(
                        orderbook_snapshots,
                        target_timestamp_ms=execution_candle.timestamp_ms,
                    )
                    execution_price = apply_execution_price(
                        reference_price=(
                            orderbook_snapshot.best_bid
                            if orderbook_snapshot is not None and orderbook_snapshot.best_bid is not None
                            else execution_candle.open if execution_timing == "next_open" else last_close
                        ),
                        side="sell",
                        slippage_bps=execution_model.slippage_bps,
                    )
                    proceeds = amount * execution_price
                    sell_fee_quote = proceeds * (fee_rate_pct / 100.0)
                    realized_pnl_quote = (execution_price - avg_entry_price) * amount
                    entry_fee_quote = (avg_entry_price * amount) * (fee_rate_pct / 100.0)
                    net_realized_pnl_quote = realized_pnl_quote - entry_fee_quote - sell_fee_quote
                    net_realized_pnl_pct = (
                        (net_realized_pnl_quote / (avg_entry_price * amount)) * 100
                        if avg_entry_price * amount > 0
                        else None
                    )
                    cash += proceeds - sell_fee_quote
                    units = max(0.0, units - amount)
                    daily_realized_pnl_quote += net_realized_pnl_quote
                    if units <= 1e-12:
                        units = 0.0
                        avg_entry_price = None
                        entry_count = 0
                        partial_take_profit_done = False
                        partial_stop_loss_done = False
                        highest_price_since_entry = None
                        lowest_price_since_entry = None
                        is_final_exit = True
                    if exit_reason == "partial_take_profit" and units > 0:
                        partial_take_profit_done = True
                        last_partial_take_profit_ts = current.timestamp_ms
                    if exit_reason == "partial_stop_loss" and units > 0:
                        partial_stop_loss_done = True
                    last_trade_ts = current.timestamp_ms
                    trade_records.append(
                        TradeRecord(
                            strategy_type="alt",
                            symbol=symbol,
                            side="sell",
                            reason=exit_reason,
                            timestamp_ms=execution_candle.timestamp_ms,
                            recorded_at=format_iso(execution_candle.timestamp_ms),
                            price=execution_price,
                            amount=amount,
                            order_value_quote=proceeds,
                            fee_quote=sell_fee_quote + entry_fee_quote,
                            realized_pnl_quote=realized_pnl_quote,
                            realized_pnl_pct=pnl_pct,
                            net_realized_pnl_quote=net_realized_pnl_quote,
                            net_realized_pnl_pct=net_realized_pnl_pct,
                            cash_after=cash,
                            position_amount_after=units,
                            average_entry_price_after=avg_entry_price,
                            entry_count_after=entry_count,
                            extra={
                                "is_final_exit": is_final_exit,
                                "daily_realized_pnl_quote_after": daily_realized_pnl_quote,
                                "mfe_pct": mfe_pct,
                                "mae_pct": mae_pct,
                                "current_net_realized_pnl_pct": current_net_realized_pnl_pct,
                                "signal_score": signal_score,
                                "symbol_regime": regime_snapshot.regime,
                                "requested_amount": requested_amount,
                                "fill_ratio": execution_model.sell_fill_ratio,
                                "slippage_bps": execution_model.slippage_bps,
                                "execution_timing": execution_timing,
                                "latency_ms": execution_model.latency_ms,
                                "orderbook_snapshot_used": orderbook_snapshot is not None,
                                "orderbook_spread_pct": None if orderbook_snapshot is None else orderbook_snapshot.spread_pct,
                            },
                        )
                    )
                    realized_on_this_bar = True

        pre_score_position_ratio = strategy.get_position_ratio(symbol, risk_per_trade)
        allocation_score_result = compute_allocation_score(
            settings=portfolio_settings,
            signal_score=signal_score,
            volume_ratio=volume_ratio,
            required_volume_ratio=effective_min_volume_ratio,
            trend_ok=htf_bullish,
            low_energy_guard_active=(regime_snapshot.regime == "LOW_ENERGY" and not has_position),
            symbol_regime=regime_snapshot.regime,
            fill_quality_avg_fill_ratio=None,
            fill_quality_entry_blocked=False,
            correlation_with_btc=correlation_with_btc,
            max_correlation_with_btc=strategy.max_correlation_with_btc,
        )
        position_ratio = pre_score_position_ratio * allocation_score_result.score_scale
        requested_order_value = cash * position_ratio * strategy.buy_split_ratio
        can_average_down = compute_can_average_down(
            has_position=has_position,
            average_entry_price=avg_entry_price,
            last_close=last_close,
            averaging_down_gap_pct=strategy.averaging_down_gap_pct,
        )
        effective_max_entry_count = max(0, strategy.max_entry_count + regime_policy.max_entry_count_delta)
        entry_allowed = (
            entry_signal
            and signal_is_strong
            and (not regime_policy.require_strong_signal or signal_is_strong)
            and volume_filter_passed
            and volume_within_upper_bound
            and volatility_filter_passed
            and higher_timeframe_entry_passed
            and gap_within_upper_bound
            and not htf_bearish_entry_blocked
            and not correlation_entry_blocked
            and not fill_quality_entry_blocked
            and entry_timing_snapshot.ready
            and not in_trade_cooldown
            and not in_partial_tp_cooldown
            and not daily_loss_limit_reached
            and requested_order_value >= min_buy_order_value
            and (
                not has_position
                or (
                    can_average_down
                    and entry_count < effective_max_entry_count
                )
            )
            and not realized_on_this_bar
        )

        if entry_allowed:
            order_value = min(cash, requested_order_value)
            orderbook_snapshot = resolve_orderbook_snapshot(
                orderbook_snapshots,
                target_timestamp_ms=current.timestamp_ms,
            )
            orderbook_fill_ratio = estimate_orderbook_fill_ratio(
                side="buy",
                snapshot=orderbook_snapshot,
                requested_order_value_quote=order_value,
            )
            executed_order_value = order_value * min(execution_model.buy_fill_ratio, orderbook_fill_ratio)
            fee_quote = executed_order_value * (fee_rate_pct / 100.0)
            net_order_value = executed_order_value - fee_quote
            if net_order_value >= min_buy_order_value and last_close > 0:
                execution_candle, _, execution_timing = resolve_execution_candle(
                    candles,
                    current_index=index,
                    execution_model=execution_model,
                )
                if execution_timing == "next_open":
                    orderbook_snapshot = resolve_orderbook_snapshot(
                        orderbook_snapshots,
                        target_timestamp_ms=execution_candle.timestamp_ms,
                    )
                execution_price = apply_execution_price(
                    reference_price=(
                        orderbook_snapshot.best_ask
                        if orderbook_snapshot is not None and orderbook_snapshot.best_ask is not None
                        else execution_candle.open if execution_timing == "next_open" else last_close
                    ),
                    side="buy",
                    slippage_bps=execution_model.slippage_bps,
                )
                amount = net_order_value / execution_price
                previous_cost = (avg_entry_price or 0.0) * units
                units += amount
                avg_entry_price = ((previous_cost + net_order_value) / units) if units > 0 else last_close
                cash -= executed_order_value
                entry_count += 1
                highest_price_since_entry = execution_price
                lowest_price_since_entry = execution_price
                last_trade_ts = execution_candle.timestamp_ms
                trade_records.append(
                    TradeRecord(
                        strategy_type="alt",
                        symbol=symbol,
                        side="buy",
                        reason="entry" if not has_position else "average_down",
                        timestamp_ms=execution_candle.timestamp_ms,
                        recorded_at=format_iso(execution_candle.timestamp_ms),
                        price=execution_price,
                        amount=amount,
                        order_value_quote=net_order_value,
                        fee_quote=fee_quote,
                        realized_pnl_quote=None,
                        realized_pnl_pct=None,
                        net_realized_pnl_quote=None,
                        net_realized_pnl_pct=None,
                        cash_after=cash,
                        position_amount_after=units,
                        average_entry_price_after=avg_entry_price,
                        entry_count_after=entry_count,
                        extra={
                            "signal_is_strong": signal_is_strong,
                            "signal_score": signal_score,
                            "allocation_score": allocation_score_result.allocation_score,
                            "allocation_score_scale": allocation_score_result.score_scale,
                            "gap_pct": gap_pct,
                            "max_entry_gap_pct": max_entry_gap_pct,
                            "noise_ratio": noise_ratio,
                            "noise_gap_multiplier": noise_gap_multiplier,
                            "volume_ratio": volume_ratio,
                            "max_volume_ratio": effective_max_volume_ratio,
                            "avg_abs_change_pct": avg_abs_change_pct,
                            "correlation_with_btc": correlation_with_btc,
                            "symbol_regime": regime_snapshot.regime,
                            "entry_timing_phase": entry_timing_snapshot.phase,
                            "requested_order_value_quote": order_value,
                            "executed_order_value_quote": executed_order_value,
                            "fill_ratio": execution_model.buy_fill_ratio,
                            "slippage_bps": execution_model.slippage_bps,
                            "execution_timing": execution_timing,
                            "latency_ms": execution_model.latency_ms,
                            "orderbook_snapshot_used": orderbook_snapshot is not None,
                            "orderbook_fill_ratio": orderbook_fill_ratio,
                            "orderbook_spread_pct": None if orderbook_snapshot is None else orderbook_snapshot.spread_pct,
                        },
                    )
                )

        equity_curve.append(
            EquityPoint(
                timestamp_ms=current.timestamp_ms,
                equity_quote=cash + (units * last_close),
                cash_quote=cash,
                position_amount=units,
                close=last_close,
            )
        )

    sell_records = [record for record in trade_records if record.side == "sell"]
    winning_trades = [
        record
        for record in sell_records
        if (record.net_realized_pnl_quote or 0.0) > 0
    ]
    summary = {
        "strategy_type": "alt",
        "symbol": symbol,
        "exchange_name": exchange_name,
        "source_timeframe": source_timeframe,
        "strategy_version": strategy.version,
        "initial_cash_quote": initial_cash,
        "final_cash_quote": cash,
        "final_position_amount": units,
        "final_equity_quote": equity_curve[-1].equity_quote if equity_curve else initial_cash,
        "net_return_pct": (
            (((equity_curve[-1].equity_quote if equity_curve else initial_cash) - initial_cash) / initial_cash) * 100
            if initial_cash > 0
            else 0.0
        ),
        "trade_count": len(trade_records),
        "buy_count": len([record for record in trade_records if record.side == "buy"]),
        "sell_count": len(sell_records),
        "win_count": len(winning_trades),
        "win_rate_pct": (len(winning_trades) / len(sell_records) * 100) if sell_records else 0.0,
        "total_net_realized_pnl_quote": sum((record.net_realized_pnl_quote or 0.0) for record in sell_records),
        "profit_factor": compute_profit_factor(sell_records),
        "sharpe_ratio": compute_sharpe_ratio(equity_curve, timeframe=source_timeframe),
        "max_drawdown_pct": compute_max_drawdown(equity_curve),
        "backtest_assumes_full_fill": (
            execution_model.buy_fill_ratio >= 0.999
            and execution_model.sell_fill_ratio >= 0.999
        ),
        "execution_model": asdict(execution_model),
        "orderbook_snapshot_count": len(orderbook_snapshots),
    }
    return summary, trade_records, equity_curve


def simulate_btc_strategy(
    *,
    candles: list[Candle],
    source_timeframe: str,
    symbol: str,
    exchange_name: str,
    initial_cash: float,
    fee_rate_pct: float,
    risk_per_trade: float,
    min_buy_order_value: float,
    max_daily_loss_quote: float,
    execution_model: ExecutionModel | None = None,
    orderbook_snapshots: list[OrderbookSnapshot] | None = None,
    initial_state: BtcReplayInitialState | None = None,
    start_timestamp_ms: int | None = None,
) -> tuple[dict[str, Any], list[TradeRecord], list[EquityPoint]]:
    """BTC EMA 전략을 오프라인으로 재생한다."""
    settings = load_btc_trend_settings()
    portfolio_settings = load_portfolio_allocation_settings()
    execution_model = execution_model or ExecutionModel(
        slippage_bps=0.0,
        buy_fill_ratio=1.0,
        sell_fill_ratio=1.0,
        latency_ms=0,
    )
    orderbook_snapshots = orderbook_snapshots or []
    base_candles = resample_candles(candles, source_timeframe=source_timeframe, target_timeframe=settings.timeframe)
    confirm_candles = resample_candles(
        candles,
        source_timeframe=source_timeframe,
        target_timeframe=settings.confirm_timeframe,
    )
    confirm_timestamps = [candle.timestamp_ms for candle in confirm_candles]
    base_closes = [candle.close for candle in base_candles]
    confirm_closes = [candle.close for candle in confirm_candles]
    fast_ema_full = build_full_ema_series(base_closes, settings.fast_ema_period)
    slow_ema_full = build_full_ema_series(base_closes, settings.slow_ema_period)
    confirm_ema_full = build_full_ema_series(confirm_closes, settings.confirm_ema_period)

    cash = initial_state.cash_quote if initial_state is not None else initial_cash
    units = initial_state.units if initial_state is not None else 0.0
    entry_price: float | None = initial_state.entry_price if initial_state is not None else None
    partial_take_profit_done = (
        initial_state.partial_take_profit_done if initial_state is not None else False
    )
    add_on_count = initial_state.add_on_count if initial_state is not None else 0
    highest_price_since_entry: float | None = (
        initial_state.highest_price_since_entry if initial_state is not None else None
    )
    lowest_price_since_entry: float | None = (
        initial_state.lowest_price_since_entry if initial_state is not None else None
    )
    trailing_armed = initial_state.trailing_armed if initial_state is not None else False
    trailing_armed_at = (
        initial_state.trailing_armed_at_ts if initial_state is not None else None
    )
    trailing_activation_price = (
        initial_state.trailing_activation_price if initial_state is not None else None
    )
    last_trade_ts = initial_state.last_trade_ts if initial_state is not None else 0
    last_stop_loss_ts = initial_state.last_stop_loss_ts if initial_state is not None else 0
    last_profit_exit_ts = initial_state.last_profit_exit_ts if initial_state is not None else 0
    daily_realized_pnl_quote = (
        initial_state.daily_realized_pnl_quote if initial_state is not None else 0.0
    )
    daily_pnl_date: str | None = (
        local_date_key(start_timestamp_ms) if start_timestamp_ms is not None else None
    )
    trade_records: list[TradeRecord] = []
    equity_curve: list[EquityPoint] = []
    entry_timing_state: dict[str, dict[str, int | str]] = {}

    min_required = max(
        settings.slow_ema_period + 5,
        settings.atr_period + 5,
        settings.volume_lookback + 5,
        settings.swing_lookback + 5,
        settings.rsi_period + 5,
        settings.bb_period + 5,
        settings.noise_ratio_lookback + 5,
    )
    max_indicator_history = max(
        min_required + 2,
        settings.atr_period + 5,
        settings.volume_lookback + 5,
        settings.swing_lookback + 5,
        settings.rsi_period + 5,
        settings.bb_period + 5,
        settings.noise_ratio_lookback + 5,
        max(29, 14 * 2 + 2),
    )
    for index in range(min_required, len(base_candles)):
        start_index = max(0, index + 1 - max_indicator_history)
        window = base_candles[start_index : index + 1]
        current = base_candles[index]
        if start_timestamp_ms is not None and current.timestamp_ms < start_timestamp_ms:
            continue
        current_date = local_date_key(current.timestamp_ms)
        if current_date != daily_pnl_date:
            daily_pnl_date = current_date
            daily_realized_pnl_quote = 0.0

        closes = base_closes[start_index : index + 1]
        prev_fast = fast_ema_full[index - 1]
        prev_slow = slow_ema_full[index - 1]
        fast_ema = fast_ema_full[index]
        slow_ema = slow_ema_full[index]
        if None in {prev_fast, prev_slow, fast_ema, slow_ema}:
            continue
        bullish = prev_fast <= prev_slow and fast_ema > slow_ema
        bearish = prev_fast >= prev_slow and fast_ema < slow_ema
        last_close = base_closes[index]
        last_high = current.high
        last_low = current.low
        base_ohlcv_window = [
            [c.timestamp_ms, c.open, c.high, c.low, c.close, c.volume]
            for c in window
        ]
        donchian_entry_upper, _ = calc_donchian_channel(
            base_ohlcv_window,
            settings.donchian_entry_lookback,
        )
        _, donchian_exit_lower = calc_donchian_channel(
            base_ohlcv_window,
            settings.donchian_exit_lookback,
        )
        volume_ratio = calc_volume_ratio(window, settings.volume_lookback)
        atr_value = calc_atr(window, settings.atr_period)
        atr_pct = (atr_value / last_close) * 100 if last_close > 0 else 0.0
        rsi_value = calc_rsi(closes, settings.rsi_period)
        noise_ratio = calc_noise_ratio(
            base_ohlcv_window,
            settings.noise_ratio_lookback,
        )
        bb_width_pct = calc_bollinger_band_width_pct(
            closes,
            period=settings.bb_period,
            stddev_multiplier=settings.bb_stddev_multiplier,
        )
        fast_ema_series = [value for value in fast_ema_full[max(0, index - settings.ema_slope_lookback - 1) : index + 1] if value is not None]
        slow_ema_series = [value for value in slow_ema_full[max(0, index - settings.ema_slope_lookback - 1) : index + 1] if value is not None]
        fast_ema_slope_pct = calc_pct_slope(fast_ema_series, settings.ema_slope_lookback)
        slow_ema_slope_pct = calc_pct_slope(slow_ema_series, settings.ema_slope_lookback)
        confirm_end = bisect_right(confirm_timestamps, current.timestamp_ms)
        confirm_filter_passed = True
        confirm_bullish = True
        if settings.enable_confirm_timeframe_filter:
            confirm_filter_passed = False
            confirm_bullish = False
            if confirm_end >= settings.confirm_ema_period:
                confirm_last_close = confirm_closes[confirm_end - 1]
                confirm_last_ema = confirm_ema_full[confirm_end - 1]
                if confirm_last_ema is None:
                    continue
                confirm_bullish = confirm_last_close > confirm_last_ema
                confirm_filter_passed = confirm_bullish

        base_min_ema_spread_pct = settings.get_min_ema_spread_pct(symbol)
        noise_spread_multiplier = clamp_noise_multiplier(
            noise_ratio=noise_ratio,
            baseline=settings.noise_ratio_baseline,
            min_multiplier=settings.noise_ratio_min_multiplier,
            max_multiplier=settings.noise_ratio_max_multiplier,
        ) if settings.enable_noise_ratio_adaptation else 1.0
        effective_signal_score_min = settings.signal_score_min
        if settings.enable_noise_ratio_adaptation and noise_ratio is not None:
            effective_signal_score_min = max(
                0.0,
                min(
                    100.0,
                    settings.signal_score_min
                    + (noise_ratio - settings.noise_ratio_baseline)
                    * settings.noise_ratio_signal_score_weight,
                ),
            )
        effective_min_ema_spread_pct = base_min_ema_spread_pct * noise_spread_multiplier
        btc_entry_state = compute_btc_entry_state(
            bullish=bullish,
            last_fast=fast_ema,
            last_slow=slow_ema,
            last_close=last_close,
            min_ema_spread_pct=effective_min_ema_spread_pct,
            enable_trend_follow_entry=settings.enable_trend_follow_entry,
            require_price_above_fast=settings.trend_follow_requires_price_above_fast,
            require_ema_slope_positive=settings.trend_follow_requires_ema_slope_positive,
            fast_ema_slope_pct=fast_ema_slope_pct,
            slow_ema_slope_pct=slow_ema_slope_pct,
            rsi_value=rsi_value,
            enable_rsi_filter=settings.enable_rsi_filter,
            rsi_entry_min=settings.rsi_entry_min,
            rsi_entry_max=settings.rsi_entry_max,
            bb_width_pct=bb_width_pct,
            enable_bb_width_filter=settings.enable_bb_width_filter,
            min_bb_width_pct=settings.min_bb_width_pct,
            max_bb_width_pct=settings.max_bb_width_pct,
            signal_score_min=effective_signal_score_min,
            symbol_regime=None,
            entry_mode=settings.entry_mode,
            donchian_entry_upper=donchian_entry_upper,
            donchian_confirm_breakout_close=settings.donchian_confirm_breakout_close,
            last_high=last_high,
        )
        ema_aligned = bool(btc_entry_state["ema_aligned"])
        price_above_fast = bool(btc_entry_state["price_above_fast"])
        ema_slope_positive = bool(btc_entry_state["ema_slope_positive"])
        ema_spread_pct = float(btc_entry_state["ema_spread_pct"])
        rsi_filter_passed = bool(btc_entry_state["rsi_filter_passed"])
        bb_width_filter_passed = bool(btc_entry_state["bb_width_filter_passed"])
        signal_score = float(btc_entry_state["signal_score"])
        trend_follow_entry = bool(btc_entry_state["trend_follow_entry"])
        entry_signal = bool(btc_entry_state["entry_signal"])
        volume_filter_passed = volume_ratio is not None and volume_ratio >= settings.get_min_volume_ratio(symbol)
        atr_filter_passed = settings.get_min_atr_pct(symbol) <= atr_pct <= settings.max_atr_pct

        has_position = units > 0
        if has_position and entry_price is not None:
            highest_price_since_entry = max(highest_price_since_entry or last_close, last_close)
            lowest_price_since_entry = min(lowest_price_since_entry or last_close, last_close)
        elif not has_position:
            highest_price_since_entry = None
            lowest_price_since_entry = None
            trailing_armed = False
            trailing_armed_at = None
            trailing_activation_price = None
            partial_take_profit_done = False
            add_on_count = 0

        base_cooldown_remaining = settings.min_trade_interval_sec - ((current.timestamp_ms - last_trade_ts) / 1000)
        stop_loss_cooldown_remaining = settings.stop_loss_reentry_cooldown_sec - ((current.timestamp_ms - last_stop_loss_ts) / 1000)
        profit_exit_cooldown_remaining = settings.profit_exit_reentry_cooldown_sec - ((current.timestamp_ms - last_profit_exit_ts) / 1000)
        in_cooldown = max(base_cooldown_remaining, stop_loss_cooldown_remaining, profit_exit_cooldown_remaining) > 0
        daily_loss_limit_reached = daily_realized_pnl_quote <= -max_daily_loss_quote

        regime_snapshot = build_replay_symbol_regime(
            volume_ratio=volume_ratio,
            avg_abs_change_pct=calc_avg_abs_change_pct(closes, settings.volume_lookback),
            gap_pct=ema_spread_pct,
            rsi_value=rsi_value,
            adx_value=calc_adx(
                base_ohlcv_window,
                14,
            ),
            bullish_signal=bullish,
            bearish_signal=bearish,
            above_ma=last_close > slow_ema,
            htf_bullish=confirm_bullish,
            public_buy_ready=(
                bullish and volume_filter_passed and atr_filter_passed and confirm_filter_passed
                and rsi_filter_passed and bb_width_filter_passed
            ),
        )
        regime_policy = get_btc_regime_policy(regime_snapshot.regime)
        effective_min_volume_ratio = settings.get_effective_min_volume_ratio(symbol, regime_snapshot.regime)
        volume_filter_passed = volume_ratio is not None and volume_ratio >= effective_min_volume_ratio
        effective_min_atr_pct = settings.get_min_atr_pct(symbol) * regime_policy.min_atr_multiplier
        atr_filter_passed = effective_min_atr_pct <= atr_pct <= settings.max_atr_pct
        fill_quality_entry_blocked = False
        raw_entry_candidate = (
            entry_signal
            and not regime_policy.pause_new_entry
            and not fill_quality_entry_blocked
        )
        entry_timing_snapshot = update_entry_timing_state(
            state_store=entry_timing_state,
            symbol=symbol,
            has_position=has_position,
            candidate_active=raw_entry_candidate,
            required_confirmations=settings.entry_confirmation_loops,
        )

        recent_swing_low = get_recent_swing_low(window[:-1], settings.swing_lookback)
        recent_swing_high = get_recent_swing_high(window[:-1], settings.swing_lookback)
        position_state = evaluate_btc_open_position(
            has_position=has_position,
            entry_price=entry_price,
            last_close=last_close,
            base_free=units,
            fee_rate_pct=fee_rate_pct,
            atr_value=atr_value,
            recent_swing_low=recent_swing_low,
            recent_swing_high=recent_swing_high,
            highest_price_since_entry=highest_price_since_entry,
            lowest_price_since_entry=lowest_price_since_entry,
            trailing_armed=trailing_armed,
            trailing_armed_at=None,
            trailing_activation_price=None,
            partial_take_profit_done=partial_take_profit_done,
            confirm_bullish=confirm_bullish,
            ema_aligned=ema_aligned,
            ema_spread_pct=ema_spread_pct,
            settings=settings,
        )
        highest_price_since_entry = position_state["highest_price_since_entry"]
        lowest_price_since_entry = position_state["lowest_price_since_entry"]
        trailing_armed = bool(position_state["trailing_armed"])
        stop_price = position_state["stop_price"]
        take_profit_price = position_state["take_profit_price"]
        pnl_pct = position_state["pnl_pct"]
        current_net_pnl_pct = position_state["current_net_realized_pnl_pct"]
        partial_take_profit_triggered = bool(position_state["partial_take_profit_triggered"])
        bull_pullback_hold_active = bool(position_state["bull_pullback_hold_active"])
        drawdown_from_high_pct = position_state["drawdown_from_high_pct"]
        mfe_pct = position_state["mfe_pct"]
        mae_pct = position_state["mae_pct"]

        btc_exit_flags = compute_btc_exit_flags(
            has_position=has_position,
            stop_price=stop_price,
            take_profit_price=take_profit_price,
            last_close=last_close,
            highest_price_since_entry=highest_price_since_entry,
            trailing_drawdown_pct=settings.trailing_drawdown_pct * regime_policy.trailing_drawdown_multiplier,
            trailing_armed=trailing_armed,
            enable_fee_protect_exit=settings.enable_fee_protect_exit,
            fee_protect_min_net_pnl_pct=settings.fee_protect_min_net_pnl_pct,
            enable_atr_trailing_exit=settings.enable_atr_trailing_exit,
            trailing_atr_multiple=settings.trailing_atr_multiple,
            atr_value=atr_value,
            pnl_pct=current_net_pnl_pct,
            bearish=(bearish or (not ema_aligned) or (not price_above_fast)),
            confirm_bullish=confirm_bullish and not bull_pullback_hold_active,
            entry_mode=settings.entry_mode,
            donchian_exit_lower=donchian_exit_lower,
            last_low=last_low,
            enable_donchian_failure_exit=settings.enable_donchian_failure_exit,
        )
        stop_triggered = bool(btc_exit_flags["stop_triggered"])
        trailing_triggered = bool(btc_exit_flags["trailing_stop_triggered"])
        profit_protect_triggered = bool(btc_exit_flags["profit_protect_triggered"])
        trend_exit_triggered = bool(btc_exit_flags["trend_exit_triggered"])

        if has_position and entry_price is not None:
            sell_ratio = 0.0
            exit_reason = ""
            if stop_triggered:
                sell_ratio = 1.0
                exit_reason = "stop_loss"
            elif profit_protect_triggered:
                sell_ratio = 1.0
                exit_reason = "profit_protect_take_profit"
            elif trailing_triggered:
                sell_ratio = 1.0
                exit_reason = "trailing_take_profit"
            elif partial_take_profit_triggered:
                sell_ratio = settings.partial_take_profit_ratio
                exit_reason = "partial_take_profit"
            elif trend_exit_triggered:
                sell_ratio = 1.0
                exit_reason = "trend_exit"

            if sell_ratio > 0:
                requested_amount = units * min(max(sell_ratio, 0.0), 1.0)
                amount = requested_amount * execution_model.sell_fill_ratio
                execution_candle, _, execution_timing = resolve_execution_candle(
                    candles,
                    current_index=index,
                    execution_model=execution_model,
                )
                orderbook_snapshot = resolve_orderbook_snapshot(
                    orderbook_snapshots,
                    target_timestamp_ms=execution_candle.timestamp_ms,
                )
                execution_price = apply_execution_price(
                    reference_price=(
                        orderbook_snapshot.best_bid
                        if orderbook_snapshot is not None and orderbook_snapshot.best_bid is not None
                        else execution_candle.open if execution_timing == "next_open" else last_close
                    ),
                    side="sell",
                    slippage_bps=execution_model.slippage_bps,
                )
                proceeds = amount * execution_price
                sell_fee_quote = proceeds * (fee_rate_pct / 100.0)
                realized_pnl_quote = (execution_price - entry_price) * amount
                entry_fee_quote = (entry_price * amount) * (fee_rate_pct / 100.0)
                net_realized_pnl_quote = realized_pnl_quote - entry_fee_quote - sell_fee_quote
                net_realized_pnl_pct = (
                    (net_realized_pnl_quote / (entry_price * amount)) * 100
                    if entry_price * amount > 0
                    else None
                )
                cash += proceeds - sell_fee_quote
                units = max(0.0, units - amount)
                daily_realized_pnl_quote += net_realized_pnl_quote
                if exit_reason == "stop_loss":
                    last_stop_loss_ts = current.timestamp_ms
                if exit_reason in {"profit_protect_take_profit", "trailing_take_profit", "trend_exit"}:
                    last_profit_exit_ts = current.timestamp_ms
                if exit_reason == "partial_take_profit" and units > 0:
                    partial_take_profit_done = True
                if units <= 1e-12:
                    units = 0.0
                    entry_price = None
                    trailing_armed = False
                    partial_take_profit_done = False
                    add_on_count = 0
                trade_records.append(
                    TradeRecord(
                        strategy_type="btc",
                        symbol=symbol,
                        side="sell",
                        reason=exit_reason,
                        timestamp_ms=execution_candle.timestamp_ms,
                        recorded_at=format_iso(execution_candle.timestamp_ms),
                        price=execution_price,
                        amount=amount,
                        order_value_quote=proceeds,
                        fee_quote=sell_fee_quote + entry_fee_quote,
                        realized_pnl_quote=realized_pnl_quote,
                        realized_pnl_pct=pnl_pct,
                        net_realized_pnl_quote=net_realized_pnl_quote,
                        net_realized_pnl_pct=net_realized_pnl_pct,
                        cash_after=cash,
                        position_amount_after=units,
                        average_entry_price_after=entry_price,
                        entry_count_after=1 + add_on_count,
                        extra={
                            "trailing_armed": trailing_armed,
                            "atr_pct": atr_pct,
                            "ema_spread_pct": ema_spread_pct,
                            "signal_score": signal_score,
                            "noise_ratio": noise_ratio,
                            "symbol_regime": regime_snapshot.regime,
                            "drawdown_from_high_pct": drawdown_from_high_pct,
                            "mfe_pct": mfe_pct,
                            "mae_pct": mae_pct,
                            "requested_amount": requested_amount,
                            "fill_ratio": execution_model.sell_fill_ratio,
                            "slippage_bps": execution_model.slippage_bps,
                            "execution_timing": execution_timing,
                            "latency_ms": execution_model.latency_ms,
                            "orderbook_snapshot_used": orderbook_snapshot is not None,
                            "orderbook_spread_pct": None if orderbook_snapshot is None else orderbook_snapshot.spread_pct,
                        },
                    )
                )
                last_trade_ts = execution_candle.timestamp_ms

        pre_score_position_ratio = settings.get_position_ratio(symbol)
        allocation_score_result = compute_allocation_score(
            settings=portfolio_settings,
            signal_score=signal_score,
            volume_ratio=volume_ratio,
            required_volume_ratio=effective_min_volume_ratio,
            trend_ok=confirm_bullish,
            low_energy_guard_active=(regime_snapshot.regime == "LOW_ENERGY" and not has_position),
            symbol_regime=regime_snapshot.regime,
            fill_quality_avg_fill_ratio=None,
            fill_quality_entry_blocked=False,
            correlation_with_btc=None,
            max_correlation_with_btc=1.0,
        )
        position_ratio = pre_score_position_ratio * allocation_score_result.score_scale
        requested_order_value = cash * risk_per_trade * position_ratio
        requested_add_on_order_value = cash * risk_per_trade * settings.pyramid_position_ratio * allocation_score_result.score_scale
        entry_allowed = (
            entry_signal
            and signal_score >= effective_signal_score_min
            and volume_filter_passed
            and atr_filter_passed
            and confirm_filter_passed
            and not regime_policy.pause_new_entry
            and (not regime_policy.require_fresh_cross or bullish)
            and entry_timing_snapshot.ready
            and not in_cooldown
            and not daily_loss_limit_reached
            and requested_order_value >= min_buy_order_value
            and not has_position
        )
        add_on_allowed = (
            has_position
            and entry_price is not None
            and settings.enable_pyramid_add_on
            and add_on_count < max(0, settings.pyramid_max_add_ons + regime_policy.pyramid_max_add_ons_delta)
            and ((last_close - entry_price) / entry_price) * 100 >= settings.pyramid_trigger_profit_pct
            and entry_signal
            and signal_score >= effective_signal_score_min
            and requested_add_on_order_value >= min_buy_order_value
        )

        if entry_allowed or add_on_allowed:
            reason = "entry" if entry_allowed else "pyramid_add_on"
            order_value = requested_order_value if entry_allowed else requested_add_on_order_value
            order_value = min(cash, order_value)
            orderbook_snapshot = resolve_orderbook_snapshot(
                orderbook_snapshots,
                target_timestamp_ms=current.timestamp_ms,
            )
            orderbook_fill_ratio = estimate_orderbook_fill_ratio(
                side="buy",
                snapshot=orderbook_snapshot,
                requested_order_value_quote=order_value,
            )
            executed_order_value = order_value * min(execution_model.buy_fill_ratio, orderbook_fill_ratio)
            fee_quote = executed_order_value * (fee_rate_pct / 100.0)
            net_order_value = executed_order_value - fee_quote
            if net_order_value >= min_buy_order_value and last_close > 0:
                execution_candle, _, execution_timing = resolve_execution_candle(
                    candles,
                    current_index=index,
                    execution_model=execution_model,
                )
                if execution_timing == "next_open":
                    orderbook_snapshot = resolve_orderbook_snapshot(
                        orderbook_snapshots,
                        target_timestamp_ms=execution_candle.timestamp_ms,
                    )
                execution_price = apply_execution_price(
                    reference_price=(
                        orderbook_snapshot.best_ask
                        if orderbook_snapshot is not None and orderbook_snapshot.best_ask is not None
                        else execution_candle.open if execution_timing == "next_open" else last_close
                    ),
                    side="buy",
                    slippage_bps=execution_model.slippage_bps,
                )
                amount = net_order_value / execution_price
                previous_cost = (entry_price or 0.0) * units
                units += amount
                entry_price = ((previous_cost + net_order_value) / units) if units > 0 else execution_price
                cash -= executed_order_value
                last_trade_ts = execution_candle.timestamp_ms
                highest_price_since_entry = execution_price
                lowest_price_since_entry = execution_price
                if reason == "pyramid_add_on":
                    add_on_count += 1
                trade_records.append(
                    TradeRecord(
                        strategy_type="btc",
                        symbol=symbol,
                        side="buy",
                        reason=reason,
                        timestamp_ms=execution_candle.timestamp_ms,
                        recorded_at=format_iso(execution_candle.timestamp_ms),
                        price=execution_price,
                        amount=amount,
                        order_value_quote=net_order_value,
                        fee_quote=fee_quote,
                        realized_pnl_quote=None,
                        realized_pnl_pct=None,
                        net_realized_pnl_quote=None,
                        net_realized_pnl_pct=None,
                        cash_after=cash,
                        position_amount_after=units,
                        average_entry_price_after=entry_price,
                        entry_count_after=1 + add_on_count,
                        extra={
                            "ema_spread_pct": ema_spread_pct,
                            "atr_pct": atr_pct,
                            "volume_ratio": volume_ratio,
                            "signal_score": signal_score,
                            "allocation_score": allocation_score_result.allocation_score,
                            "allocation_score_scale": allocation_score_result.score_scale,
                            "noise_ratio": noise_ratio,
                            "noise_spread_multiplier": noise_spread_multiplier,
                            "symbol_regime": regime_snapshot.regime,
                            "entry_timing_phase": entry_timing_snapshot.phase,
                            "requested_order_value_quote": order_value,
                            "executed_order_value_quote": executed_order_value,
                            "fill_ratio": execution_model.buy_fill_ratio,
                            "slippage_bps": execution_model.slippage_bps,
                            "execution_timing": execution_timing,
                            "latency_ms": execution_model.latency_ms,
                            "orderbook_snapshot_used": orderbook_snapshot is not None,
                            "orderbook_fill_ratio": orderbook_fill_ratio,
                            "orderbook_spread_pct": None if orderbook_snapshot is None else orderbook_snapshot.spread_pct,
                        },
                    )
                )

        equity_curve.append(
            EquityPoint(
                timestamp_ms=current.timestamp_ms,
                equity_quote=cash + (units * last_close),
                cash_quote=cash,
                position_amount=units,
                close=last_close,
            )
        )

    sell_records = [record for record in trade_records if record.side == "sell"]
    winning_trades = [
        record for record in sell_records if (record.net_realized_pnl_quote or 0.0) > 0
    ]
    summary = {
        "strategy_type": "btc",
        "symbol": symbol,
        "exchange_name": exchange_name,
        "source_timeframe": source_timeframe,
        "strategy_version": settings.version,
        "initial_cash_quote": initial_cash,
        "final_cash_quote": cash,
        "final_position_amount": units,
        "final_equity_quote": equity_curve[-1].equity_quote if equity_curve else initial_cash,
        "net_return_pct": (
            (((equity_curve[-1].equity_quote if equity_curve else initial_cash) - initial_cash) / initial_cash) * 100
            if initial_cash > 0
            else 0.0
        ),
        "trade_count": len(trade_records),
        "buy_count": len([record for record in trade_records if record.side == "buy"]),
        "sell_count": len(sell_records),
        "win_count": len(winning_trades),
        "win_rate_pct": (len(winning_trades) / len(sell_records) * 100) if sell_records else 0.0,
        "total_net_realized_pnl_quote": sum((record.net_realized_pnl_quote or 0.0) for record in sell_records),
        "profit_factor": compute_profit_factor(sell_records),
        "sharpe_ratio": compute_sharpe_ratio(equity_curve, timeframe=source_timeframe),
        "max_drawdown_pct": compute_max_drawdown(equity_curve),
        "backtest_assumes_full_fill": (
            execution_model.buy_fill_ratio >= 0.999
            and execution_model.sell_fill_ratio >= 0.999
        ),
        "execution_model": asdict(execution_model),
        "orderbook_snapshot_count": len(orderbook_snapshots),
    }
    return summary, trade_records, equity_curve


def save_fetch_output(path: Path, candles: list[list[float]]) -> None:
    """공개 OHLCV 조회 결과를 파일로 저장한다."""
    suffix = path.suffix.lower()
    path.parent.mkdir(parents=True, exist_ok=True)
    if suffix == ".csv":
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_ms", "open", "high", "low", "close", "volume"])
            for row in candles:
                writer.writerow(row)
        return
    with path.open("w", encoding="utf-8") as f:
        for row in candles:
            payload = {
                "timestamp_ms": row[0],
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5],
            }
            f.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def run_fetch_command(args: argparse.Namespace) -> int:
    """공개 거래소에서 OHLCV 를 가져와 파일로 저장한다."""
    exchange_name = args.exchange.lower()
    if exchange_name == "okx":
        exchange = create_okx_public_client()
        rows = fetch_okx_ohlcv(exchange, args.symbol, timeframe=args.timeframe, limit=args.limit)
    elif exchange_name == "upbit":
        exchange = create_upbit_public_client()
        rows = fetch_upbit_ohlcv(exchange, args.symbol, timeframe=args.timeframe, limit=args.limit)
    else:
        raise ValueError(f"지원하지 않는 거래소입니다: {args.exchange}")
    save_fetch_output(Path(args.output), rows)
    print(f"저장 완료: {args.output} ({len(rows)}개 캔들)")
    return 0


def run_backtest_command(args: argparse.Namespace) -> int:
    """리플레이/백테스트를 실행하고 결과 파일을 저장한다."""
    input_path = Path(args.input)
    candles = load_candles(input_path)
    btc_reference_candles = None
    if getattr(args, "btc_reference_input", None):
        btc_reference_candles = load_candles(Path(args.btc_reference_input))
    if len(candles) < 50:
        raise ValueError("백테스트에 필요한 캔들이 너무 적습니다. 최소 50개 이상 준비하세요.")

    fee_rate_pct = args.fee_rate_pct
    if fee_rate_pct is None:
        fee_rate_pct = resolve_default_fee_rate(args.exchange)
    min_buy_order_value = args.min_buy_order_value
    if min_buy_order_value is None:
        min_buy_order_value = resolve_default_min_buy_order_value(args.exchange)
    max_daily_loss_quote = args.max_daily_loss_quote
    if max_daily_loss_quote is None:
        max_daily_loss_quote = resolve_default_max_daily_loss(args.exchange)
    execution_model = build_execution_model(args)

    override_set_names = list(args.override_set or [])
    override_paths = resolve_set_paths(override_set_names)
    override_paths.extend(Path(path) for path in (args.override_toml or []))
    orderbook_snapshots = load_orderbook_snapshots(
        Path(args.orderbook_input) if getattr(args, "orderbook_input", None) else None
    )

    with temporary_runtime_overrides(override_paths):
        if args.strategy == "alt":
            summary, trades, equity_curve = simulate_alt_strategy(
                candles=candles,
                btc_reference_candles=btc_reference_candles,
                source_timeframe=args.timeframe,
                symbol=args.symbol,
                exchange_name=args.exchange,
                initial_cash=args.initial_cash,
                fee_rate_pct=fee_rate_pct,
                risk_per_trade=args.risk_per_trade,
                min_buy_order_value=min_buy_order_value,
                max_daily_loss_quote=max_daily_loss_quote,
                execution_model=execution_model,
                orderbook_snapshots=orderbook_snapshots,
            )
        else:
            summary, trades, equity_curve = simulate_btc_strategy(
                candles=candles,
                source_timeframe=args.timeframe,
                symbol=args.symbol,
                exchange_name=args.exchange,
                initial_cash=args.initial_cash,
                fee_rate_pct=fee_rate_pct,
                risk_per_trade=args.risk_per_trade,
                min_buy_order_value=min_buy_order_value,
                max_daily_loss_quote=max_daily_loss_quote,
                execution_model=execution_model,
                orderbook_snapshots=orderbook_snapshots,
            )

    summary["override_set_names"] = override_set_names
    summary["override_paths"] = [str(path) for path in override_paths]
    summary["orderbook_input"] = str(args.orderbook_input) if getattr(args, "orderbook_input", None) else None

    output_dir = build_output_dir(Path(args.output_dir), args.strategy, args.symbol)
    write_json(output_dir / "summary.json", summary)
    write_jsonl(output_dir / "trades.jsonl", trades)
    write_jsonl(output_dir / "equity_curve.jsonl", equity_curve)
    write_registry(REGISTRY_PATH, build_all_registry_entries())

    print(f"리플레이 완료: {output_dir}")
    print(
        f"전략={summary['strategy_type']} "
        f"수익률={summary['net_return_pct']:.2f}% "
        f"거래수={summary['trade_count']} "
        f"Sharpe={float(summary.get('sharpe_ratio', 0.0) or 0.0):.3f} "
        f"PF={float(summary.get('profit_factor', 0.0) or 0.0):.3f} "
        f"최대낙폭={summary['max_drawdown_pct']:.2f}%"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 만든다."""
    parser = argparse.ArgumentParser(description="전략 백테스트/리플레이 도구")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="공개 OHLCV 를 파일로 저장")
    fetch_parser.add_argument("--exchange", required=True, choices=["okx", "upbit"])
    fetch_parser.add_argument("--symbol", required=True)
    fetch_parser.add_argument("--timeframe", required=True)
    fetch_parser.add_argument("--limit", type=int, default=1000)
    fetch_parser.add_argument("--output", required=True)

    run_parser = subparsers.add_parser("run", help="로컬 OHLCV 파일로 전략을 재생")
    run_parser.add_argument("--strategy", required=True, choices=["alt", "btc"])
    run_parser.add_argument("--exchange", required=True, choices=["okx", "upbit"])
    run_parser.add_argument("--symbol", required=True)
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument(
        "--btc-reference-input",
        help="알트 전략에서 BTC 상관관계 필터를 같이 재생할 때 사용할 BTC 기준 OHLCV 파일",
    )
    run_parser.add_argument("--timeframe", required=True, help="입력 파일 캔들 주기")
    run_parser.add_argument("--initial-cash", type=float, default=1_000_000.0)
    run_parser.add_argument("--fee-rate-pct", type=float, default=None)
    run_parser.add_argument("--risk-per-trade", type=float, default=DEFAULT_RISK_PER_TRADE)
    run_parser.add_argument("--min-buy-order-value", type=float, default=None)
    run_parser.add_argument("--max-daily-loss-quote", type=float, default=None)
    run_parser.add_argument("--slippage-bps", type=float, default=0.0, help="매수/매도에 불리하게 적용할 슬리피지 bps")
    run_parser.add_argument("--buy-fill-ratio", type=float, default=1.0, help="매수 체결 비율 0~1")
    run_parser.add_argument("--sell-fill-ratio", type=float, default=1.0, help="매도 체결 비율 0~1")
    run_parser.add_argument("--latency-ms", type=int, default=0, help="0보다 크면 다음 캔들 시가 체결로 근사")
    run_parser.add_argument("--orderbook-input", help="analysis_logs 형식 호가 스냅샷 JSONL 경로")
    run_parser.add_argument("--override-set", action="append", default=[], help="config/sets 아래 실험 세트 이름 또는 경로")
    run_parser.add_argument("--override-toml", action="append", default=[], help="추가 TOML override 경로")
    run_parser.add_argument("--output-dir", default="reports/backtests")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "fetch":
        return run_fetch_command(args)
    if args.command == "run":
        return run_backtest_command(args)
    parser.error("지원하지 않는 명령입니다.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
