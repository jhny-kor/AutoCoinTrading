"""
수정 요약
- 2026-05-07: BTC 포지션 비중 계산과 로그 조립을 공통 allocation helper 로 옮겨 업비트/OKX 구조를 맞춤
- 2026-05-06: BTC 매수 후보를 전략/리스크/체결/포트폴리오/레짐 위원회로 shadow 검토하도록 연결
- 2026-05-05: BTC LOW_ENERGY 레짐을 고점수 소액 probe 후보로 보정하고 진입 실패 reason 을 세분화하도록 연결
- 2026-05-01: 거래량+ATR+RSI 과열 조합은 BTC 신규 진입을 막고, range 상단 추격 신호는 추가 확인을 요구하도록 보강
- 2026-04-23: 확인 타임프레임 bullish 는 slope 하한까지 충족할 때만 유효하게 보고, 거래량 보너스는 ATR 동반 시에만 반영하도록 BTC 진입 품질을 더 보수화
- 고거래량 BTC 진입에서는 심볼별 추가 ATR 하한과 추가 confirmation loop 를 적용해 급등 추격 손실을 더 줄이도록 보강
- 2026-04-12: 텔레그램 BTC 매수 체결 알림에 기본 비중, 최종 비중, 실제 실행 비중을 함께 표시하도록 보강
- 2026-04-10: BTC 손절 후 일정 시간과 높은 점수면 fresh cross 없이 재진입 가능한 예외 경로를 추가
- 2026-04-09: BTC 손절 후 재진입은 최소 시간 + confirm/fresh cross 복구 기준으로 보도록 패턴 기반 gate 를 추가
- 2026-04-08: BTC 가 레짐을 직접 if 분기하지 않고 독립 라우터에서 `skip / breakout / trend_follow` 전략 경로를 선택하도록 정리
- 2026-04-08: BTC/KRW 는 확인 루프 5회를 사용하고 심볼별 override 가 레짐별 최소 루프보다 크면 그 값을 쓰도록 보강
- 2026-04-08: BTC 8단계 보수형 레짐에 따라 진입 확인 루프, trend-follow, 피라미딩 허용 여부를 다르게 적용
- 2026-04-06: BTC Donchian Channel 모드 실시간 조건 모니터링 연동
- BTC ATR 퍼센트가 낮을 때 신규 진입 비중을 단계형으로 줄이는 보정을 추가했다.
- 업비트 BTC 5분/15분 경로도 웹소켓 1분봉 리샘플 우선, stale 시 REST fallback 으로 바꿔 REST 캔들 호출을 더 줄이도록 확장했다.
- 업비트 BTC 1분봉 경로를 웹소켓 1분 캔들 우선, stale 시 REST fallback 으로 바꿔 phase 3 전환을 시작했다.
- 업비트 BTC best bid 조회를 웹소켓 latest 스냅샷 우선, stale 시 REST fallback 으로 바꿔 phase 2 전환을 시작했다.
- BTC 포지션 평가 helper 호출을 한 번만 수행하도록 정리해 중복 분기를 줄였다.
- 노이즈 비율 기반 동적 EMA 스프레드/신호 스코어 보정을 추가해 BTC 진입 기준을 장 상태에 맞춰 자동 조정하도록 보강했다.
- 2차 강화로 진입 상태 머신과 체결률 기반 진입 차단을 추가했다.
- BTC 진입에 RSI, 볼린저 밴드 폭, EMA 기울기, 레짐별 ATR/피라미딩/트레일링 정책을 추가해 추세 확인을 강화했다.
- 업비트 잔고/호가 REST 호출을 짧게 캐시하고 최소 주문 경계 근처에서만 호가를 재조회해 지연 영향을 줄이도록 개선
- 업비트 BTC 매도도 공통 재시도 경로를 사용하고 주문 직후 캐시를 비워 다음 루프가 최신 잔고를 다시 읽도록 보강
- BTC 가 CHOPPY 레짐일 때는 심볼별 추가 거래량 기준을 적용해 약한 진입을 더 줄이도록 보수화했다.
- 저에너지 장에서는 신규 진입을 줄이기 위한 거래소별 저에너지 가드를 추가하고, BTC/KRW 전용 보수화를 위한 심볼별 최소 ATR 기준도 반영했다.
- 업비트 429 요청 제한에 걸릴 때 짧은 backoff 재시도를 적용하고, KRW 매수 주문에는 안전 버퍼를 두도록 보강했다.
- BTC/USDT 같은 특정 심볼만 더 엄격하게 보려는 심볼별 EMA 스프레드/거래량 진입 기준을 반영했다.
- 텔레그램 매수/매도 체결 알림에 실제 체결가와 체결 금액이 함께 보이도록 보강
- BTC 진입 필터를 조금 더 보수적으로 강화하고, 강한 다중 상승 추세에서는 짧은 조정에 대한 청산을 잠시 보류하도록 조정
- BTC 익절가 도달 시 1회 부분 익절 후 잔량을 트레일링/순익 보호로 관리하는 구조를 추가
- BTC 수익성 청산 직후 재진입과 추가매수를 잠시 막는 전용 쿨다운을 추가
- 거래소 전체 기준 목표 비중과 남아 있는 누적 투입 원가를 바탕으로 BTC 신규 매수 한도를 제한하는 포트폴리오 배분 로직을 추가
- 수수료를 제하고도 순익이 남는 상태에서 추세가 꺾이면 빠르게 익절하는 순익 보호 청산 규칙을 추가
- 업비트 BTC 체결 로그에 주문 ID, API 지연, 체결 비율, 슬리피지 같은 주문 실행 품질 지표를 함께 저장하도록 확장
- 업비트 BTC 순손익 계산을 매도 수수료만이 아니라 왕복 수수료 기준으로 통일해 /pnl 집계가 더 정확해지도록 보강
- BTC 는 수익 구간에서 1회만 추가매수하는 보수적 피라미딩을 지원하도록 확장
- 업비트 BTC 에서 예상 매도 금액이 최소 주문 금액 5,000 KRW 미만이면 매도 주문을 선차단하도록 추가
- 업비트 BTC 에서 최소 주문 금액 미만 잔량은 포지션으로 보지 않아 잔량 보유 중에도 재진입할 수 있게 조정
- BTC 손절 직후에는 일반 거래 간격보다 더 길게 쉬도록 전용 재진입 쿨다운을 추가
- BTC 전략 버전 이름(strategy_version)을 구조화 로그와 체결 이력에 함께 남겨 버전별 비교가 가능하도록 확장
- BTC 거래 품질 분석용으로 최저가, MFE/MAE, 트레일링 활성화 소요 시간까지 체결 로그에 함께 남기도록 확장
- 트레일링 익절이 이미 활성화된 뒤에는 trend_exit 가 먼저 포지션을 끊지 않도록 조정
- BTC 익절 활성화 가격이 왕복 수수료보다 낮아지지 않도록 수수료 하한선을 적용
- 업비트 시장가 매수는 수량이 아니라 KRW 사용 금액 기준으로 보내도록 수정
- BTC 진입 신호를 골든크로스뿐 아니라 EMA 상승 정렬 유지 구간까지 허용해 진입 기회를 늘리도록 조정
- BTC 전용 5분봉/15분봉 EMA 추세추종 실험용 업비트 봇 추가
- EMA 골든크로스 진입, 거래량 확인 유지, ATR 기반 변동성 필터 적용
- 물타기 없이 1회 포지션만 운영하고, 손절/익절은 ATR 또는 최근 스윙 기준으로 계산
- 손절/익절/추세 종료 청산을 모두 텔레그램과 체결 JSONL 에 기록하도록 연결
- 전략 판단 로그를 system / strategy / trade JSONL 로 분리 저장하도록 추가
- 진입/청산 퍼널과 차단 사유를 reason 코드 기준으로 집계 가능하게 기록하도록 추가
- 거래량 배수 계산을 형성 중인 현재 봉 대신 직전 마감 봉 기준으로 바꿔 BTC 필터 해석을 안정화하도록 조정
- 익절 구간 도달 후 최고가 대비 되돌림으로 전량 청산하는 트레일링 익절 로직을 추가
- 포지션 ID, 트레일링 활성화 시각, 최고가 대비 되돌림 같은 분석용 로그 필드를 추가

업비트 BTC 전용 EMA 추세추종 봇

- 심볼: BTC/KRW
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
from core.execution.common import log_order_failure
from core.execution.upbit import (
    apply_upbit_buy_order_buffer,
    create_upbit_market_data_provider,
    create_market_buy_order_upbit,
    create_market_sell_order_upbit,
    create_upbit_client,
    enrich_upbit_order_with_private_event,
    fetch_best_bid_upbit,
    fetch_ohlcv_upbit_with_provider,
    fetch_ohlcv_upbit,
    get_spot_balances_upbit_with_provider,
    invalidate_upbit_balance_cache,
    invalidate_upbit_orderbook_cache,
    load_upbit_config,
    safe_amount_to_precision_upbit,
    should_refresh_best_bid_upbit,
)
from core.market_data.upbit_provider import UpbitMarketDataProvider
from core.logging.metrics import build_btc_common_metrics
from core.positions.lifecycle import clear_btc_position_state
from core.positions.guards import handle_unrecoverable_position
from core.risk.allocation import (
    build_btc_allocations,
    build_btc_position_sizing,
    compute_allocation_score,
    format_allocation_score_log,
    format_btc_position_sizing_log,
    format_dynamic_bonus_log,
    format_portfolio_budget_log,
)
from core.risk.execution_guard import ExecutionQualityGuard, FillQualitySnapshot
from core.runtime.bootstrap import build_btc_runtime_state
from core.risk.shared import is_daily_loss_limit_reached, is_dynamic_bonus_eligible
from core.strategy.btc import (
    compute_btc_entry_state,
    compute_btc_exit_flags,
    compute_btc_stop_loss_reentry_gate,
)
from core.strategy.combined_filters import (
    calc_recent_range_context,
    is_overheated_entry_risk,
    requires_overheat_confirmation,
)
from core.strategy.entry_committee import (
    evaluate_entry_committee,
    load_entry_committee_settings,
    record_entry_committee_result,
)
from core.strategy.indicators import (
    calc_bollinger_band_width_pct,
    calc_donchian_channel,
    calc_ema_series as calc_ema_series_core,
    calc_noise_ratio,
    calc_percentile_rank,
    calc_pct_slope,
    calc_recent_atr_series,
    calc_recent_volume_ratio_series,
    calc_rsi,
)
from core.strategy.timing import update_entry_timing_state
from core.strategy.btc_position import (
    build_btc_exit_prices,
    evaluate_btc_open_position,
)
from core.strategy.funnels import (
    build_btc_add_on_steps,
    build_btc_entry_steps,
    build_btc_exit_steps,
)
from core.strategy.low_energy import evaluate_low_energy_probe
from core.strategy.regime_router import route_btc_strategy
from market_regime_guard import (
    build_regime_change_message,
    classify_symbol_regime,
    load_latest_symbol_record,
    load_low_energy_snapshot,
    update_regime_state,
)
from portfolio_allocator import PortfolioAllocator
from state_recovery import (
    load_program_daily_realized_pnl_quote,
    restore_program_position_states,
)
from structured_log_manager import FunnelStep, StructuredLogManager, choose_atr_reason
from strategy_settings import load_managed_symbols
from telegram_notifier import load_telegram_notifier
from trade_history_logger import (
    TradeHistoryLogger,
    estimate_round_trip_net_pnl,
    summarize_order_for_notification,
)


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
    return build_btc_exit_prices(
        entry_price=entry_price,
        atr_value=atr_value,
        recent_swing_low=recent_swing_low,
        recent_swing_high=recent_swing_high,
        min_take_profit_pct=min_take_profit_pct,
        settings=settings,
    )


def run_bot():
    """업비트 BTC 전용 EMA 추세추종 봇 메인 루프."""
    config = load_upbit_config()
    settings = load_btc_trend_settings()
    entry_committee_settings = load_entry_committee_settings()
    exchange = create_upbit_client(config)
    market_data_provider: UpbitMarketDataProvider | None = create_upbit_market_data_provider(config)
    logger = BotLogger("upbit_btc_ema_trend_bot")
    structured_logger = StructuredLogManager("upbit_btc_ema_trend_bot")
    notifier = load_telegram_notifier()
    trade_history = TradeHistoryLogger()
    execution_quality_guard = ExecutionQualityGuard()
    log = logger.log
    entry_timing_state: dict[str, dict[str, int | str]] = {}

    symbol = "BTC/KRW"
    base = "BTC"
    quote = "KRW"
    recovered_state = restore_program_position_states(
        "upbit_btc_ema_trend_bot",
        [symbol],
    ).get(symbol)
    runtime_state = build_btc_runtime_state(symbol, recovered_state)
    portfolio_allocator = PortfolioAllocator(
        exchange_name="UPBIT",
        quote_currency=quote,
        tracked_symbols=load_managed_symbols("upbit"),
    )
    entry_price = runtime_state.entry_price
    entry_opened_at = runtime_state.entry_opened_at
    position_id = runtime_state.position_id
    highest_price_since_entry = runtime_state.highest_price_since_entry
    lowest_price_since_entry = runtime_state.lowest_price_since_entry
    trailing_armed = runtime_state.trailing_armed
    trailing_armed_at = runtime_state.trailing_armed_at
    trailing_activation_price = runtime_state.trailing_activation_price
    partial_take_profit_done = runtime_state.partial_take_profit_done
    add_on_count = runtime_state.add_on_count
    last_trade_at = runtime_state.last_trade_at
    last_stop_loss_at = runtime_state.last_stop_loss_at
    last_profit_exit_at = runtime_state.last_profit_exit_at
    unrecoverable_position_warned = False
    daily_pnl_date = datetime.now().date()
    daily_realized_pnl_quote = load_program_daily_realized_pnl_quote(
        "upbit_btc_ema_trend_bot",
        daily_pnl_date,
    )
    daily_limit_notified = (
        daily_realized_pnl_quote <= -config["max_daily_loss_quote"]
    )
    min_buy_order_value = float(os.getenv("UPBIT_MIN_BUY_ORDER_VALUE", "5000"))

    min_ohlcv_limit = max(
        settings.slow_ema_period + 5,
        settings.atr_period + 5,
        settings.volume_lookback + 5,
        settings.swing_lookback + 5,
        settings.rsi_period + 5,
        settings.noise_ratio_lookback + 5,
        settings.bb_period + 5,
        settings.slow_ema_period + settings.ema_slope_lookback + 5,
    )
    confirm_limit = max(settings.confirm_ema_period + 5, settings.slow_ema_period + 5)

    log("=== 업비트 BTC EMA 추세추종 봇 시작 ===")
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
    log(f"복구된 당일 실현 손익: {daily_realized_pnl_quote:.2f} {quote}")
    if recovered_state and recovered_state.average_entry_price is not None:
        log(
            f"복구된 BTC 포지션: avg={recovered_state.average_entry_price:.0f}, "
            f"entries={recovered_state.cycle_buy_count}, "
            f"partial_tp_done={recovered_state.partial_take_profit_done}, "
            f"trailing_armed={recovered_state.trailing_armed}"
        )
    structured_logger.log_system(
        level="INFO",
        event="bot_started",
        message="업비트 BTC EMA 전략 봇을 시작합니다.",
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
            daily_realized_pnl_quote = load_program_daily_realized_pnl_quote(
                "upbit_btc_ema_trend_bot",
                daily_pnl_date,
            )
            daily_limit_notified = False
            log("일자가 변경되어 BTC 전용 봇의 일일 손익을 초기화합니다.")
            structured_logger.log_system(
                level="INFO",
                event="daily_pnl_reset",
                message="BTC 전용 봇의 일일 손익 누적값을 초기화했습니다.",
                symbol=symbol,
            )

        try:
            ohlcv = fetch_ohlcv_upbit_with_provider(
                exchange,
                symbol=symbol,
                timeframe=settings.timeframe,
                limit=min_ohlcv_limit,
                market_data_provider=market_data_provider,
            )
            confirm_ohlcv = fetch_ohlcv_upbit_with_provider(
                exchange,
                symbol=symbol,
                timeframe=settings.confirm_timeframe,
                limit=confirm_limit,
                market_data_provider=market_data_provider,
            )
            closes = [row[4] for row in ohlcv]
            confirm_closes = [row[4] for row in confirm_ohlcv]
            last_close = closes[-1]
            last_high = ohlcv[-1][2]
            last_low = ohlcv[-1][3]
            donchian_entry_upper, _ = calc_donchian_channel(ohlcv, settings.donchian_entry_lookback)
            _, donchian_exit_lower = calc_donchian_channel(ohlcv, settings.donchian_exit_lookback)
            fast_ema_series = calc_ema_series(closes, settings.fast_ema_period)
            slow_ema_series = calc_ema_series(closes, settings.slow_ema_period)

            bullish, bearish, prev_fast, prev_slow, last_fast, last_slow = detect_ema_crossover(
                closes,
                settings.fast_ema_period,
                settings.slow_ema_period,
            )
            volume_ratio = calc_volume_ratio(ohlcv, settings.volume_lookback)
            volume_ratio_series = calc_recent_volume_ratio_series(
                ohlcv,
                settings.volume_lookback,
                sample_count=20,
            )
            volume_ratio_percentile = calc_percentile_rank(
                volume_ratio_series,
                volume_ratio,
            )
            atr_value = calc_atr(ohlcv, settings.atr_period)
            atr_pct = (atr_value / last_close * 100) if last_close else 0.0
            atr_series = calc_recent_atr_series(ohlcv, settings.atr_period, sample_count=20)
            atr_percentile = calc_percentile_rank(atr_series, atr_value)
            recent_range_context = calc_recent_range_context(
                ohlcv,
                last_close=last_close,
                lookback=settings.volume_lookback,
            )
            base_min_atr_pct = settings.get_min_atr_pct(symbol)
            effective_min_atr_pct = base_min_atr_pct
            confirm_ema_series = calc_ema_series(confirm_closes, settings.confirm_ema_period)
            confirm_ema = confirm_ema_series[-1]
            confirm_close = confirm_closes[-1]
            confirm_ema_slope_pct = calc_pct_slope(
                confirm_ema_series,
                settings.ema_slope_lookback,
            )
            base_min_ema_spread_pct = settings.get_min_ema_spread_pct(symbol)
            confirm_bullish_raw = confirm_close > confirm_ema
            confirm_bullish = settings.is_confirm_trend_quality_passed(
                symbol=symbol,
                confirm_bullish=confirm_bullish_raw,
                confirm_ema_slope_pct=confirm_ema_slope_pct,
            )
            rsi_value = calc_rsi(closes, settings.rsi_period)
            noise_ratio = calc_noise_ratio(
                ohlcv,
                settings.noise_ratio_lookback,
            )
            bb_width_pct = calc_bollinger_band_width_pct(
                closes,
                period=settings.bb_period,
                stddev_multiplier=settings.bb_stddev_multiplier,
            )
            fast_ema_slope_pct = calc_pct_slope(
                fast_ema_series,
                settings.ema_slope_lookback,
            )
            slow_ema_slope_pct = calc_pct_slope(
                slow_ema_series,
                settings.ema_slope_lookback,
            )
            noise_spread_multiplier = 1.0
            effective_signal_score_min = settings.signal_score_min
            if settings.enable_noise_ratio_adaptation and noise_ratio is not None:
                noise_spread_multiplier = 1.0 + (
                    (noise_ratio - settings.noise_ratio_baseline)
                    / max(settings.noise_ratio_baseline, 1e-9)
                ) * 0.5
                noise_spread_multiplier = max(
                    settings.noise_ratio_min_multiplier,
                    min(settings.noise_ratio_max_multiplier, noise_spread_multiplier),
                )
                effective_signal_score_min = max(
                    0.0,
                    min(
                        100.0,
                        settings.signal_score_min
                        + (noise_ratio - settings.noise_ratio_baseline)
                        * settings.noise_ratio_signal_score_weight,
                    ),
                )
            # 노이즈가 큰 장은 EMA 스프레드와 신호 점수 기준을 같이 높여 가짜 돌파를 줄인다.
            effective_min_ema_spread_pct = base_min_ema_spread_pct * noise_spread_multiplier
            symbol_regime_snapshot = classify_symbol_regime(
                load_latest_symbol_record(exchange_name="upbit", symbol=symbol)
            )
            symbol_regime = symbol_regime_snapshot.regime
            btc_entry_state = compute_btc_entry_state(
                bullish=bullish,
                last_fast=last_fast,
                last_slow=last_slow,
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
                symbol_regime=symbol_regime,
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
            signal_is_strong = bool(btc_entry_state["signal_is_strong"])
            trend_follow_entry = bool(btc_entry_state["trend_follow_entry"])
            entry_signal = bool(btc_entry_state["entry_signal"])
            overheated_entry_blocked = is_overheated_entry_risk(
                volume_ratio=volume_ratio,
                atr_percentile=atr_percentile,
                rsi_value=rsi_value,
                volume_ratio_threshold=settings.overheat_guard_volume_ratio,
                atr_percentile_threshold=settings.overheat_guard_atr_percentile,
                rsi_threshold=settings.overheat_guard_rsi,
            )
            overheat_extra_confirmation_required = requires_overheat_confirmation(
                signal_is_strong=signal_is_strong,
                range_position_pct=recent_range_context["range_position_pct"],
                distance_from_recent_high_pct=recent_range_context["distance_from_recent_high_pct"],
                range_position_threshold=settings.overheat_extra_confirmation_range_position_pct,
                distance_from_high_threshold_pct=settings.overheat_extra_confirmation_distance_from_high_pct,
            )
            recent_swing_low = get_recent_swing_low(ohlcv[:-1], settings.swing_lookback)
            recent_swing_high = get_recent_swing_high(ohlcv[:-1], settings.swing_lookback)

            base_free, quote_free = get_spot_balances_upbit_with_provider(
                exchange,
                base=base,
                quote=quote,
                market_data_provider=market_data_provider,
            )
            best_bid = None
            if base_free > 0 and market_data_provider is not None:
                best_bid = market_data_provider.get_best_bid(symbol)
            if best_bid is None and should_refresh_best_bid_upbit(
                base_free=base_free,
                last_close=last_close,
                min_order_value=min_buy_order_value,
                refresh_buffer_pct=config["best_bid_refresh_buffer_pct"],
            ):
                best_bid = fetch_best_bid_upbit(exchange, symbol)
            sell_price_reference = best_bid if best_bid and best_bid > 0 else last_close
            position_quote_value = base_free * last_close
            # 업비트는 최소 주문 금액 기준으로 다시 팔 수 없는 잔량은 포지션에서 제외한다.
            has_position = position_quote_value >= min_buy_order_value
            if handle_unrecoverable_position(
                warned_symbols={symbol} if unrecoverable_position_warned else set(),
                symbol=symbol,
                has_position=has_position,
                average_entry_price=entry_price,
                log=log,
                structured_logger=structured_logger,
                context={
                    "base_free": base_free,
                    "quote_free": quote_free,
                    "position_quote_value": position_quote_value,
                },
                message="평균 진입가를 복구하지 못한 BTC 포지션을 감지해 자동 매매를 보류합니다.",
            ):
                unrecoverable_position_warned = True
                continue
            if not has_position:
                unrecoverable_position_warned = False

            now_ts = time.time()
            base_cooldown_remaining = max(0.0, settings.min_trade_interval_sec - (now_ts - last_trade_at))
            stop_loss_cooldown_remaining = max(
                0.0,
                settings.stop_loss_reentry_cooldown_sec - (now_ts - last_stop_loss_at),
            )
            profit_exit_cooldown_remaining = max(
                0.0,
                settings.profit_exit_reentry_cooldown_sec - (now_ts - last_profit_exit_at),
            )
            cooldown_remaining = max(
                base_cooldown_remaining,
                stop_loss_cooldown_remaining,
                profit_exit_cooldown_remaining,
            )
            in_cooldown = cooldown_remaining > 0
            low_energy_snapshot = load_low_energy_snapshot(
                exchange_name="upbit",
                managed_symbols=load_managed_symbols("upbit"),
            )
            low_energy_guard_active = low_energy_snapshot.active and not has_position
            regime_route = route_btc_strategy(symbol_regime)
            regime_policy = regime_route.policy
            strategy_key = regime_route.strategy_key
            symbol_regime_blocks_entry = (
                not has_position and regime_policy.pause_new_entry
            )
            symbol_regime_requires_fresh_cross = regime_policy.require_fresh_cross
            trend_follow_entry_allowed = regime_policy.allow_trend_follow_entry
            regime_confirmation_loops = max(
                regime_policy.required_confirmation_loops,
                settings.get_entry_confirmation_loops(symbol),
            )
            if overheat_extra_confirmation_required:
                regime_confirmation_loops += settings.overheat_extra_confirmation_loops
            effective_min_volume_ratio = settings.get_effective_min_volume_ratio(
                symbol,
                symbol_regime,
            )
            volume_filter_passed = (
                volume_ratio is not None
                and volume_ratio >= effective_min_volume_ratio
            )
            effective_min_atr_pct = max(
                base_min_atr_pct,
                effective_min_atr_pct * regime_policy.min_atr_multiplier,
            )
            high_volume_ratio_threshold = settings.get_high_volume_ratio_threshold(symbol)
            if (
                volume_ratio is not None
                and high_volume_ratio_threshold is not None
                and volume_ratio >= high_volume_ratio_threshold
            ):
                high_volume_min_atr_pct = settings.get_high_volume_min_atr_pct(symbol)
                if high_volume_min_atr_pct is not None:
                    effective_min_atr_pct = max(effective_min_atr_pct, high_volume_min_atr_pct)
                regime_confirmation_loops += settings.get_high_volume_extra_confirmation_loops(symbol)
            atr_filter_passed = effective_min_atr_pct <= atr_pct <= settings.max_atr_pct
            volume_bonus_allowed = settings.is_volume_bonus_allowed(
                symbol=symbol,
                volume_ratio=volume_ratio,
                atr_pct=atr_pct,
            )
            scored_volume_ratio = volume_ratio if volume_bonus_allowed else None
            scored_required_volume_ratio = effective_min_volume_ratio if volume_bonus_allowed else None
            should_alert, previous_regime = update_regime_state(
                exchange_name="upbit",
                symbol=symbol,
                new_regime=symbol_regime,
            )
            if should_alert:
                notifier.notify_attention_required(
                    "REGIME",
                    build_regime_change_message(
                        exchange_name="UPBIT",
                        symbol=symbol,
                        previous_regime=previous_regime,
                        snapshot=symbol_regime_snapshot,
                    ),
                )
            daily_loss_limit_reached = is_daily_loss_limit_reached(
                daily_realized_pnl_quote=daily_realized_pnl_quote,
                max_daily_loss_quote=config["max_daily_loss_quote"],
            )
            fill_quality_snapshot = (
                execution_quality_guard.get_fill_quality_snapshot(
                    exchange_name="UPBIT",
                    symbol=symbol,
                    since_seconds=settings.fill_quality_lookback_sec,
                    min_fill_ratio=settings.fill_quality_min_fill_ratio,
                    min_sample_count=settings.fill_quality_min_sample_count,
                )
                if settings.enable_fill_quality_guard
                else FillQualitySnapshot(
                    active=False,
                    avg_fill_ratio=None,
                    sample_count=0,
                    latest_recorded_at=None,
                    reason="disabled",
                )
            )
            # BTC 도 최근 체결비율이 낮았던 구간은 진입보다 실행 품질 회복을 우선한다.
            fill_quality_entry_blocked = (
                entry_signal and not has_position and fill_quality_snapshot.active
            )
            stop_loss_pattern_gate = compute_btc_stop_loss_reentry_gate(
                enabled=(
                    settings.enable_stop_loss_pattern_reentry
                    and last_stop_loss_at > 0
                    and not has_position
                ),
                elapsed_since_stop_loss_sec=max(0.0, now_ts - last_stop_loss_at),
                min_cooldown_sec=settings.stop_loss_pattern_min_cooldown_sec,
                entry_signal=entry_signal,
                bullish=bullish,
                signal_score=signal_score,
                min_signal_score=settings.stop_loss_pattern_min_signal_score,
                volume_filter_passed=volume_filter_passed,
                atr_filter_passed=atr_filter_passed,
                confirm_bullish=confirm_bullish,
                require_confirm_bullish=settings.stop_loss_pattern_require_confirm_bullish,
                require_fresh_cross=settings.stop_loss_pattern_require_fresh_cross,
                relaxed_no_fresh_cross_after_sec=settings.get_relaxed_fresh_cross_after_sec(symbol),
                relaxed_no_fresh_cross_min_signal_score=settings.get_relaxed_fresh_cross_min_signal_score(symbol),
            )
            stop_loss_pattern_blocked = bool(
                stop_loss_pattern_gate["enabled"]
                and not stop_loss_pattern_gate["pattern_ready"]
            )
            low_energy_probe_decision = evaluate_low_energy_probe(
                enabled=settings.enable_low_energy_probe,
                low_energy_guard_active=low_energy_guard_active,
                signal_score=signal_score,
                min_signal_score=settings.low_energy_probe_min_signal_score,
                htf_bullish=confirm_bullish,
                require_htf_bullish=settings.low_energy_probe_require_confirm_bullish,
                volume_ratio=volume_ratio,
                min_volume_ratio=settings.low_energy_probe_min_volume_ratio,
                atr_percentile=atr_percentile,
                max_atr_percentile=settings.low_energy_probe_max_atr_percentile,
                position_scale=settings.low_energy_probe_position_scale,
                extra_confirmation_loops=settings.low_energy_probe_extra_confirmation_loops,
            )
            effective_low_energy_guard_active = (
                low_energy_guard_active and not low_energy_probe_decision.allowed
            )
            effective_symbol_regime_blocks_entry = (
                symbol_regime_blocks_entry and not low_energy_probe_decision.allowed
            )
            if low_energy_probe_decision.allowed:
                log(
                    f"[{symbol}] LOW_ENERGY 이지만 BTC 고품질 소액 probe 후보로 전환합니다. "
                    f"signal={signal_score:.1f}, volume={0.0 if volume_ratio is None else volume_ratio:.3f}, "
                    f"position_scale={low_energy_probe_decision.position_scale:.2f}x"
                )
            raw_entry_candidate = False
            if strategy_key == "skip":
                raw_entry_candidate = False
            elif strategy_key == "breakout":
                raw_entry_candidate = (
                    entry_signal
                    and bullish
                    and not effective_low_energy_guard_active
                    and not effective_symbol_regime_blocks_entry
                    and not fill_quality_entry_blocked
                    and not stop_loss_pattern_blocked
                    and not overheated_entry_blocked
                    and (not symbol_regime_requires_fresh_cross or bullish)
                )
            else:
                raw_entry_candidate = (
                    entry_signal
                    and not effective_low_energy_guard_active
                    and not effective_symbol_regime_blocks_entry
                    and not fill_quality_entry_blocked
                    and not stop_loss_pattern_blocked
                    and not overheated_entry_blocked
                    and (trend_follow_entry_allowed or bullish or not trend_follow_entry)
                    and (not symbol_regime_requires_fresh_cross or bullish)
                )
            # 단발 신호에 바로 진입하지 않고 같은 방향 확인이 누적될 때만 READY 로 승격한다.
            entry_timing_snapshot = update_entry_timing_state(
                state_store=entry_timing_state,
                symbol=symbol,
                has_position=has_position,
                candidate_active=raw_entry_candidate,
                required_confirmations=regime_confirmation_loops
                + low_energy_probe_decision.extra_confirmation_loops,
            )

            log("-" * 60)
            log(f"[{symbol}] 현재 종가: {last_close:.0f}")
            donchian_upper_text = "N/A" if donchian_entry_upper is None else f"{donchian_entry_upper:.0f}"
            donchian_lower_text = "N/A" if donchian_exit_lower is None else f"{donchian_exit_lower:.0f}"
            log(
                f"[{symbol}] 진입 모드: {settings.entry_mode.upper()} "
                f"(Donchian 상단: {donchian_upper_text}, 하단: {donchian_lower_text})"
            )
            log(
                f"[{symbol}] EMA 상태 - 이전 {prev_fast:.0f}/{prev_slow:.0f}, 현재 {last_fast:.0f}/{last_slow:.0f}"
            )
            logger.log_signal(symbol, bullish, bearish)
            log(
                f"[{symbol}] 거래량 배수: {volume_ratio:.4f}배"
                if volume_ratio is not None
                else f"[{symbol}] 거래량 배수 계산 불가"
            )
            log(
                f"[{symbol}] ATR: {atr_value:.0f}, ATR 비율: {atr_pct:.4f}% "
                f"(허용 {effective_min_atr_pct:.4f}% ~ {settings.max_atr_pct:.4f}%)"
            )
            log(
                f"[{symbol}] 최근 range 위치: "
                f"{0.0 if recent_range_context['range_position_pct'] is None else recent_range_context['range_position_pct']:.2f}% | "
                f"고점 거리: {0.0 if recent_range_context['distance_from_recent_high_pct'] is None else recent_range_context['distance_from_recent_high_pct']:.4f}% | "
                f"ATR percentile: {0.0 if atr_percentile is None else atr_percentile:.1f}"
            )
            if overheated_entry_blocked:
                log(
                    f"[{symbol}] 고거래량+고ATR+RSI 과열 조합으로 신규 진입을 차단합니다 "
                    f"(volume {0.0 if volume_ratio is None else volume_ratio:.2f}, "
                    f"ATR percentile {0.0 if atr_percentile is None else atr_percentile:.1f}, "
                    f"RSI {0.0 if rsi_value is None else rsi_value:.2f})."
                )
            if overheat_extra_confirmation_required:
                log(
                    f"[{symbol}] 강한 신호지만 최근 range 상단 추격 위험이 있어 "
                    f"confirmation {settings.overheat_extra_confirmation_loops}회를 추가합니다."
                )
            if low_energy_guard_active:
                log(
                    f"[{symbol}] 저에너지 장 감지: 평균 거래량 배수 {low_energy_snapshot.avg_volume_ratio:.3f}, "
                    f"평균 절대 변화율 {low_energy_snapshot.avg_abs_change_pct:.4f}% 로 신규 진입을 보류합니다."
                )
            if symbol_regime_blocks_entry:
                log(f"[{symbol}] 심볼 레짐 {symbol_regime} 상태라 신규 진입을 보류합니다.")
            log(f"[{symbol}] 레짐 라우터 선택 전략: {strategy_key}")
            log(
                f"[{symbol}] 확인 타임프레임 종가: {confirm_close:.0f}, "
                f"확인 EMA: {confirm_ema:.0f}, raw 상승 추세={confirm_bullish_raw}, "
                f"적격 상승 추세={confirm_bullish}"
            )
            log(
                f"[{symbol}] 확인 EMA 기울기: {0.0 if confirm_ema_slope_pct is None else confirm_ema_slope_pct:.4f}% "
                f"(적격 기준 {settings.get_confirm_ema_slope_min_pct(symbol):.4f}%)"
            )
            log(
                f"[{symbol}] EMA 정렬 상태: aligned={ema_aligned}, "
                f"price_above_fast={price_above_fast}, spread={ema_spread_pct:.4f}%, "
                f"ema_slope_positive={ema_slope_positive}"
            )
            log(
                f"[{symbol}] RSI: {0.0 if rsi_value is None else rsi_value:.2f}, "
                f"BB 폭: {0.0 if bb_width_pct is None else bb_width_pct:.4f}%, "
                f"EMA 기울기: {0.0 if fast_ema_slope_pct is None else fast_ema_slope_pct:.4f}%/"
                f"{0.0 if slow_ema_slope_pct is None else slow_ema_slope_pct:.4f}%, "
                f"신호 스코어: {signal_score:.1f}"
            )
            if noise_ratio is not None:
                log(
                    f"[{symbol}] 노이즈 비율: {noise_ratio:.4f} "
                    f"(기본 EMA 스프레드 {base_min_ema_spread_pct:.4f}% -> 동적 {effective_min_ema_spread_pct:.4f}%, "
                    f"기본 점수 {settings.signal_score_min:.1f} -> 동적 {effective_signal_score_min:.1f})"
                )
            log(
                f"[{symbol}] 진입 상태 머신: {entry_timing_snapshot.phase} "
                f"({entry_timing_snapshot.confirmation_count}/"
                f"{entry_timing_snapshot.required_confirmations})"
            )
            if fill_quality_snapshot.avg_fill_ratio is not None:
                log(
                    f"[{symbol}] 최근 체결비율: {fill_quality_snapshot.avg_fill_ratio * 100:.1f}% "
                    f"(표본 {fill_quality_snapshot.sample_count}, 차단 기준 {settings.fill_quality_min_fill_ratio * 100:.1f}%)"
                )
            if trend_follow_entry and not bullish:
                log(
                    f"[{symbol}] 신규 골든크로스는 아니지만 EMA 상승 정렬 유지 조건으로 진입 후보를 허용합니다."
                )
            if entry_signal and not rsi_filter_passed:
                log(
                    f"[{symbol}] RSI 가 허용 구간 {settings.rsi_entry_min:.1f}~{settings.rsi_entry_max:.1f} 밖이라 진입을 보류합니다."
                )
            if entry_signal and not bb_width_filter_passed:
                log(
                    f"[{symbol}] 볼린저 밴드 폭 {0.0 if bb_width_pct is None else bb_width_pct:.4f}% 가 "
                    f"허용 범위 {settings.min_bb_width_pct:.4f}%~{settings.max_bb_width_pct:.4f}% 밖이라 진입을 보류합니다."
                )
            if fill_quality_entry_blocked:
                log(
                    f"[{symbol}] 최근 체결비율 {fill_quality_snapshot.avg_fill_ratio * 100:.1f}% 로 낮아 "
                    f"다음 {settings.fill_quality_lookback_sec // 60}분 동안 신규 진입을 보류합니다."
                )
            if raw_entry_candidate and not entry_timing_snapshot.ready:
                log(
                    f"[{symbol}] 진입 후보 신호를 누적 확인 중입니다. "
                    f"{entry_timing_snapshot.confirmation_count}/{entry_timing_snapshot.required_confirmations}"
                )
            if trend_follow_entry and not bullish and not trend_follow_entry_allowed:
                log(f"[{symbol}] 현재 레짐 {symbol_regime} 에서는 trend-follow 진입을 허용하지 않습니다.")
            if volume_ratio is not None and not volume_bonus_allowed:
                log(
                    f"[{symbol}] 거래량 보너스 비활성: volume {volume_ratio:.4f}배, ATR {atr_pct:.4f}% "
                    f"(보너스 ATR 기준 {0.0 if settings.get_volume_bonus_min_atr_pct(symbol) is None else settings.get_volume_bonus_min_atr_pct(symbol):.4f}%)"
                )
            # 포지션 평가 helper 는 한 번만 호출하고, 이후 보유 여부에 따라 후처리만 나눈다.
            position_state = evaluate_btc_open_position(
                has_position=has_position,
                entry_price=entry_price,
                last_close=last_close,
                base_free=base_free,
                fee_rate_pct=config["fee_rate_pct"],
                atr_value=atr_value,
                recent_swing_low=recent_swing_low,
                recent_swing_high=recent_swing_high,
                highest_price_since_entry=highest_price_since_entry,
                lowest_price_since_entry=lowest_price_since_entry,
                trailing_armed=trailing_armed,
                trailing_armed_at=trailing_armed_at,
                trailing_activation_price=trailing_activation_price,
                partial_take_profit_done=partial_take_profit_done,
                confirm_bullish=confirm_bullish,
                ema_aligned=ema_aligned,
                ema_spread_pct=ema_spread_pct,
                settings=settings,
            )
            stop_price = position_state["stop_price"]
            take_profit_price = position_state["take_profit_price"]
            pnl_pct = position_state["pnl_pct"]
            current_fee_quote_estimate = position_state["current_fee_quote_estimate"]
            current_net_realized_pnl_quote = position_state["current_net_realized_pnl_quote"]
            current_net_realized_pnl_pct = position_state["current_net_realized_pnl_pct"]
            partial_take_profit_triggered = position_state["partial_take_profit_triggered"]
            bull_pullback_hold_active = position_state["bull_pullback_hold_active"]
            drawdown_from_high_pct = position_state["drawdown_from_high_pct"]
            mfe_pct = position_state["mfe_pct"]
            mae_pct = position_state["mae_pct"]

            if has_position and entry_price is not None:
                highest_price_since_entry = position_state["highest_price_since_entry"]
                lowest_price_since_entry = position_state["lowest_price_since_entry"]
                if position_state["trailing_armed_just_now"]:
                    trailing_armed = True
                    trailing_armed_at = time.time()
                    trailing_activation_price = position_state["trailing_activation_price"]
                    log(
                        f"[{symbol}] 익절 구간에 진입해 트레일링 익절을 활성화합니다. "
                        f"현재 최고가: {highest_price_since_entry:.0f}"
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
                else:
                    trailing_armed = bool(position_state["trailing_armed"])
                    trailing_armed_at = position_state["trailing_armed_at"]
                    trailing_activation_price = position_state["trailing_activation_price"]
                log(
                    f"[{symbol}] 평균 진입가: {entry_price:.0f}, 현재 수익률: {pnl_pct:.2f}%, "
                    f"손절가: {stop_price:.0f}, 익절가: {take_profit_price:.0f}, "
                    f"최고가: {highest_price_since_entry:.0f}, "
                    f"최고가 대비 되돌림: {0.0 if drawdown_from_high_pct is None else drawdown_from_high_pct:.2f}%"
                )
                if current_net_realized_pnl_pct is not None:
                    log(
                        f"[{symbol}] 수수료 반영 예상 순익률: {current_net_realized_pnl_pct:.2f}% "
                        f"(보호 익절 기준 {settings.fee_protect_min_net_pnl_pct:.2f}%)"
                    )
                bull_pullback_hold_active = (
                    settings.enable_bull_pullback_hold
                    and confirm_bullish
                    and ema_aligned
                    and pnl_pct is not None
                    and pnl_pct > 0
                    and drawdown_from_high_pct is not None
                    and drawdown_from_high_pct <= settings.bull_pullback_tolerance_pct
                    and ema_spread_pct >= settings.bull_pullback_min_spread_pct
                )
                if bull_pullback_hold_active:
                    log(
                        f"[{symbol}] 강한 상방 정렬 구간이라 되돌림 {drawdown_from_high_pct:.2f}% 는 "
                        f"일시 조정으로 보고 보유를 유지합니다."
                    )
            else:
                if not has_position:
                    highest_price_since_entry = position_state["highest_price_since_entry"]
                    lowest_price_since_entry = position_state["lowest_price_since_entry"]
                    trailing_armed = bool(position_state["trailing_armed"])
                    trailing_armed_at = position_state["trailing_armed_at"]
                    trailing_activation_price = position_state["trailing_activation_price"]
                    partial_take_profit_done = bool(position_state["partial_take_profit_done"])
                    add_on_count = 0

            if daily_loss_limit_reached:
                log(f"[{symbol}] 일일 최대 손실 제한에 도달하여 신규 진입을 중단합니다.")
                if not daily_limit_notified:
                    notifier.notify_daily_loss_limit(
                        "UPBIT-BTC",
                        f"오늘 누적 실현 손익: {daily_realized_pnl_quote:.2f} {quote}\n"
                        f"손실 제한: -{config['max_daily_loss_quote']:.2f} {quote}",
                    )
                    daily_limit_notified = True

            btc_exit_flags = compute_btc_exit_flags(
                has_position=has_position,
                stop_price=stop_price,
                take_profit_price=take_profit_price,
                last_close=last_close,
                highest_price_since_entry=highest_price_since_entry,
                trailing_drawdown_pct=(
                    settings.trailing_drawdown_pct
                    * regime_policy.trailing_drawdown_multiplier
                ),
                trailing_armed=trailing_armed,
                enable_fee_protect_exit=settings.enable_fee_protect_exit,
                fee_protect_min_net_pnl_pct=settings.fee_protect_min_net_pnl_pct,
                enable_atr_trailing_exit=settings.enable_atr_trailing_exit,
                trailing_atr_multiple=settings.trailing_atr_multiple,
                atr_value=atr_value,
                pnl_pct=current_net_realized_pnl_pct,
                bearish=(bearish or (not ema_aligned) or (not price_above_fast)),
                confirm_bullish=confirm_bullish and not bull_pullback_hold_active,
                entry_mode=settings.entry_mode,
                donchian_exit_lower=donchian_exit_lower,
                last_low=last_low,
                enable_donchian_failure_exit=settings.enable_donchian_failure_exit,
            )
            drawdown_from_high_pct = btc_exit_flags["drawdown_from_high_pct"]
            stop_triggered = bool(btc_exit_flags["stop_triggered"])
            trailing_stop_triggered = bool(btc_exit_flags["trailing_stop_triggered"])
            profit_protect_triggered = bool(btc_exit_flags["profit_protect_triggered"])
            donchian_failure_triggered = bool(btc_exit_flags["donchian_failure_triggered"])
            trend_exit_triggered = bool(btc_exit_flags["trend_exit_triggered"])
            base_position_ratio = settings.get_position_ratio(symbol)
            allocation_score_result = compute_allocation_score(
                settings=portfolio_allocator.settings,
                signal_score=signal_score,
                volume_ratio=scored_volume_ratio,
                required_volume_ratio=scored_required_volume_ratio,
                volume_ratio_percentile=volume_ratio_percentile,
                trend_ok=confirm_bullish,
                htf_slope_pct=confirm_ema_slope_pct,
                low_energy_guard_active=effective_low_energy_guard_active,
                symbol_regime=symbol_regime,
                atr_pct=atr_pct,
                atr_percentile=atr_percentile,
                orderbook_pressure_score=None,
                fill_quality_avg_fill_ratio=fill_quality_snapshot.avg_fill_ratio,
                fill_quality_entry_blocked=fill_quality_entry_blocked,
                correlation_with_btc=None,
                max_correlation_with_btc=1.0,
            )
            position_sizing = build_btc_position_sizing(
                settings=settings,
                symbol=symbol,
                base_position_ratio=base_position_ratio,
                symbol_regime=symbol_regime,
                atr_pct=atr_pct,
                score_scale=allocation_score_result.score_scale,
                low_energy_probe_allowed=low_energy_probe_decision.allowed,
                low_energy_probe_position_scale=low_energy_probe_decision.position_scale,
            )
            regime_position_scale = position_sizing.regime_position_scale
            atr_position_scale = position_sizing.atr_position_scale
            pre_score_position_ratio = position_sizing.pre_score_position_ratio
            position_ratio = position_sizing.position_ratio
            effective_partial_take_profit_ratio = min(
                1.0,
                settings.partial_take_profit_ratio
                * regime_policy.partial_take_profit_ratio_multiplier,
            )
            dynamic_bonus_eligible = is_dynamic_bonus_eligible(
                has_position=has_position,
                base_signal=entry_signal and ema_aligned and price_above_fast,
                strong_signal=signal_score >= effective_signal_score_min,
                require_strong_signal=False,
                volume_ratio=scored_volume_ratio,
                volume_threshold=portfolio_allocator.settings.dynamic_volume_ratio_threshold,
                trend_ok=confirm_bullish,
                require_trend_ok=portfolio_allocator.settings.dynamic_require_trend_ok,
                enable_dynamic_overweight=(
                    portfolio_allocator.settings.enable_dynamic_overweight
                    and regime_policy.allow_dynamic_overweight
                ),
            )
            (
                requested_order_value,
                requested_add_on_order_value,
                allocation_decision,
                add_on_allocation_decision,
            ) = build_btc_allocations(
                portfolio_allocator=portfolio_allocator,
                exchange=exchange,
                symbol=symbol,
                quote_free=quote_free,
                risk_per_trade=config["risk_per_trade"],
                position_ratio=position_ratio,
                pyramid_position_ratio=settings.pyramid_position_ratio,
                score_scale=allocation_score_result.score_scale,
                dynamic_bonus_eligible=dynamic_bonus_eligible,
            )
            log(format_btc_position_sizing_log(symbol=symbol, sizing=position_sizing))
            log(format_allocation_score_log(symbol=symbol, score=allocation_score_result))
            order_value = allocation_decision.approved_order_value_quote
            add_on_order_value = add_on_allocation_decision.approved_order_value_quote

            common_metrics = build_btc_common_metrics(
                strategy_name="upbit_btc_ema_trend",
                strategy_version=settings.version,
                symbol=symbol,
                timeframe=settings.timeframe,
                confirm_timeframe=settings.confirm_timeframe,
                price=last_close,
                prev_fast_ema=prev_fast,
                prev_slow_ema=prev_slow,
                last_fast_ema=last_fast,
                last_slow_ema=last_slow,
                ema_aligned=ema_aligned,
                price_above_fast=price_above_fast,
                ema_slope_positive=ema_slope_positive,
                ema_spread_pct=ema_spread_pct,
                effective_min_ema_spread_pct=effective_min_ema_spread_pct,
                rsi_value=rsi_value,
                rsi_filter_passed=rsi_filter_passed,
                bb_width_pct=bb_width_pct,
                bb_width_filter_passed=bb_width_filter_passed,
                signal_score=signal_score,
                noise_ratio=noise_ratio,
                noise_spread_multiplier=noise_spread_multiplier,
                base_min_ema_spread_pct=base_min_ema_spread_pct,
                effective_signal_score_min=effective_signal_score_min,
                signal_is_strong=signal_is_strong,
                entry_timing_phase=entry_timing_snapshot.phase,
                entry_timing_confirmation_count=entry_timing_snapshot.confirmation_count,
                entry_timing_required_confirmations=entry_timing_snapshot.required_confirmations,
                fill_quality_avg_fill_ratio=fill_quality_snapshot.avg_fill_ratio,
                fill_quality_sample_count=fill_quality_snapshot.sample_count,
                fill_quality_entry_blocked=fill_quality_entry_blocked,
                trend_follow_entry=trend_follow_entry,
                entry_signal=entry_signal,
                volume_ratio=volume_ratio,
                volume_ratio_percentile=volume_ratio_percentile,
                volume_bonus_allowed=volume_bonus_allowed,
                effective_min_volume_ratio=effective_min_volume_ratio,
                atr_value=atr_value,
                atr_pct=atr_pct,
                atr_percentile=atr_percentile,
                recent_high=recent_range_context["recent_high"],
                recent_low=recent_range_context["recent_low"],
                range_position_pct=recent_range_context["range_position_pct"],
                distance_from_recent_high_pct=recent_range_context["distance_from_recent_high_pct"],
                distance_from_recent_low_pct=recent_range_context["distance_from_recent_low_pct"],
                overheated_entry_blocked=overheated_entry_blocked,
                overheat_extra_confirmation_required=overheat_extra_confirmation_required,
                effective_min_atr_pct=effective_min_atr_pct,
                confirm_bullish=confirm_bullish,
                confirm_bullish_raw=confirm_bullish_raw,
                confirm_ema_slope_pct=confirm_ema_slope_pct,
                base_free=base_free,
                quote_free=quote_free,
                position_ratio=position_ratio,
                has_position=has_position,
                daily_realized_pnl_quote=daily_realized_pnl_quote,
                portfolio_base_target_pct=allocation_decision.base_target_pct * 100,
                portfolio_effective_target_pct=allocation_decision.effective_target_pct * 100,
                portfolio_dynamic_bonus_pct=allocation_decision.dynamic_bonus_pct * 100,
                portfolio_dynamic_bonus_applied=allocation_decision.dynamic_bonus_applied,
                portfolio_total_budget_quote=allocation_decision.total_portfolio_quote,
                portfolio_current_cost_basis_quote=allocation_decision.current_cost_basis_quote,
                portfolio_remaining_budget_quote=allocation_decision.remaining_budget_quote,
                allocation_score=allocation_score_result.allocation_score,
                allocation_score_scale=allocation_score_result.score_scale,
                allocation_signal_score=allocation_score_result.signal_score_component,
                allocation_market_score=allocation_score_result.market_score_component,
                allocation_execution_score=allocation_score_result.execution_score_component,
                allocation_diversification_score=allocation_score_result.diversification_score_component,
                allocation_reason_top=allocation_score_result.reason_top,
                order_value=order_value,
                executable_order_value_quote=order_value,
                pnl_pct=pnl_pct,
                net_pnl_pct_estimate=current_net_realized_pnl_pct,
                fee_protect_min_net_pnl_pct=settings.fee_protect_min_net_pnl_pct,
                bull_pullback_hold_active=bull_pullback_hold_active,
                bull_pullback_tolerance_pct=settings.bull_pullback_tolerance_pct,
                bull_pullback_min_spread_pct=settings.bull_pullback_min_spread_pct,
                position_id=position_id,
                highest_price_since_entry=highest_price_since_entry,
                lowest_price_since_entry=lowest_price_since_entry,
                trailing_armed=trailing_armed,
                partial_take_profit_done=partial_take_profit_done,
                partial_take_profit_triggered=partial_take_profit_triggered,
                drawdown_from_high_pct=drawdown_from_high_pct,
                trailing_activation_price=trailing_activation_price,
                mfe_pct=mfe_pct,
                mae_pct=mae_pct,
                add_on_count=add_on_count,
                pyramid_add_on_enabled=settings.enable_pyramid_add_on,
                pyramid_trigger_profit_pct=settings.pyramid_trigger_profit_pct,
                pyramid_max_add_ons=max(
                    0,
                    settings.pyramid_max_add_ons + regime_policy.pyramid_max_add_ons_delta,
                ),
                profit_protect_triggered=profit_protect_triggered,
                profit_exit_cooldown_remaining_sec=profit_exit_cooldown_remaining,
                low_energy_guard_active=low_energy_guard_active,
                effective_low_energy_guard_active=effective_low_energy_guard_active,
                low_energy_probe_allowed=low_energy_probe_decision.allowed,
                low_energy_probe_reason=low_energy_probe_decision.reason,
                low_energy_probe_position_scale=low_energy_probe_decision.position_scale,
                low_energy_avg_volume_ratio=low_energy_snapshot.avg_volume_ratio,
                low_energy_avg_abs_change_pct=low_energy_snapshot.avg_abs_change_pct,
                low_energy_ready_count=low_energy_snapshot.ready_count,
                symbol_regime=symbol_regime,
                regime_strategy_key=strategy_key,
                symbol_regime_blocks_entry=symbol_regime_blocks_entry,
                symbol_regime_requires_fresh_cross=symbol_regime_requires_fresh_cross,
                regime_position_scale=regime_position_scale,
                atr_position_scale=atr_position_scale,
                base_position_ratio=base_position_ratio,
                pre_score_position_ratio=pre_score_position_ratio,
                effective_position_ratio=position_ratio,
                regime_dynamic_overweight_allowed=regime_policy.allow_dynamic_overweight,
                regime_min_atr_multiplier=regime_policy.min_atr_multiplier,
                regime_trailing_drawdown_multiplier=regime_policy.trailing_drawdown_multiplier,
                regime_partial_take_profit_ratio_multiplier=regime_policy.partial_take_profit_ratio_multiplier,
            )
            entry_committee_result = evaluate_entry_committee(
                common_metrics,
                entry_committee_settings,
            )
            common_metrics.update(entry_committee_result.to_metrics())
            log(
                format_portfolio_budget_log(
                    symbol=symbol,
                    allocation_decision=allocation_decision,
                    quote=quote,
                    quote_decimals=0,
                )
            )
            if allocation_decision.dynamic_bonus_applied:
                log(format_dynamic_bonus_log(symbol=symbol, allocation_decision=allocation_decision))
            if stop_loss_pattern_blocked:
                log(
                    f"[{symbol}] 손절 후 패턴 재진입 대기 중입니다. "
                    f"경과 {int(max(0.0, now_ts - last_stop_loss_at))}초 / 최소 {settings.stop_loss_pattern_min_cooldown_sec}초, "
                    f"신호 점수 {signal_score:.1f}/{settings.stop_loss_pattern_min_signal_score:.1f}, "
                    f"confirm={confirm_bullish}, fresh_cross={bullish}, "
                    f"relaxed_fresh_cross={stop_loss_pattern_gate['relaxed_fresh_cross_used']}"
                )

            entry_steps = build_btc_entry_steps(
                entry_signal=entry_signal,
                bullish=bullish,
                trend_follow_entry=trend_follow_entry,
                ema_aligned=ema_aligned,
                price_above_fast=price_above_fast,
                ema_slope_positive=ema_slope_positive,
                ema_spread_pct=ema_spread_pct,
                effective_min_ema_spread_pct=effective_min_ema_spread_pct,
                signal_score=signal_score,
                min_signal_score=effective_signal_score_min,
                rsi_filter_passed=rsi_filter_passed,
                bb_width_filter_passed=bb_width_filter_passed,
                bb_width_pct=bb_width_pct,
                min_bb_width_pct=settings.min_bb_width_pct,
                max_bb_width_pct=settings.max_bb_width_pct,
                has_position=has_position,
                in_cooldown=in_cooldown,
                cooldown_remaining=cooldown_remaining,
                base_cooldown_remaining=base_cooldown_remaining,
                stop_loss_cooldown_remaining=stop_loss_cooldown_remaining,
                profit_exit_cooldown_remaining=profit_exit_cooldown_remaining,
                stop_loss_pattern_blocked=stop_loss_pattern_blocked,
                stop_loss_pattern_elapsed_sec=max(0.0, now_ts - last_stop_loss_at) if last_stop_loss_at > 0 else None,
                stop_loss_pattern_min_cooldown_sec=settings.stop_loss_pattern_min_cooldown_sec,
                stop_loss_pattern_signal_score=signal_score,
                stop_loss_pattern_min_signal_score=settings.stop_loss_pattern_min_signal_score,
                low_energy_guard_active=effective_low_energy_guard_active,
                low_energy_avg_volume_ratio=low_energy_snapshot.avg_volume_ratio,
                low_energy_avg_abs_change_pct=low_energy_snapshot.avg_abs_change_pct,
                low_energy_ready_count=low_energy_snapshot.ready_count,
                low_energy_probe_allowed=low_energy_probe_decision.allowed,
                low_energy_probe_reason=low_energy_probe_decision.reason,
                low_energy_probe_min_signal_score=settings.low_energy_probe_min_signal_score,
                low_energy_probe_min_volume_ratio=settings.low_energy_probe_min_volume_ratio,
                low_energy_probe_max_atr_percentile=settings.low_energy_probe_max_atr_percentile,
                symbol_regime_blocks_entry=effective_symbol_regime_blocks_entry,
                symbol_regime=symbol_regime,
                symbol_regime_requires_fresh_cross=symbol_regime_requires_fresh_cross,
                volume_filter_passed=volume_filter_passed,
                volume_ratio=volume_ratio,
                effective_min_volume_ratio=effective_min_volume_ratio,
                atr_filter_passed=atr_filter_passed,
                atr_pct=atr_pct,
                effective_min_atr_pct=effective_min_atr_pct,
                max_atr_pct=settings.max_atr_pct,
                confirm_bullish=(not settings.enable_confirm_timeframe_filter or confirm_bullish),
                daily_loss_limit_reached=daily_loss_limit_reached,
                daily_realized_pnl_quote=daily_realized_pnl_quote,
                max_daily_loss_quote=config["max_daily_loss_quote"],
                remaining_budget_quote=allocation_decision.remaining_budget_quote,
                current_cost_basis_quote=allocation_decision.current_cost_basis_quote,
                target_budget_quote=allocation_decision.target_budget_quote,
                order_value=order_value,
                min_buy_order_value=min_buy_order_value,
                estimated_entry_amount=safe_amount_to_precision_upbit(exchange, symbol, order_value / last_close if last_close else 0.0),
                min_order_amount=0.0,
                entry_strategy_key=strategy_key,
            )
            entry_steps.extend(
                [
                    FunnelStep(
                        stage="fill_quality_guard",
                        passed=not fill_quality_entry_blocked,
                        reason="fill_quality_low",
                        actual={
                            "avg_fill_ratio": fill_quality_snapshot.avg_fill_ratio,
                            "sample_count": fill_quality_snapshot.sample_count,
                        },
                        required={"min_fill_ratio": settings.fill_quality_min_fill_ratio},
                    ),
                    FunnelStep(
                        stage="entry_timing",
                        passed=entry_timing_snapshot.ready,
                        reason="entry_confirmation_pending",
                        actual={
                            "phase": entry_timing_snapshot.phase,
                            "confirmation_count": entry_timing_snapshot.confirmation_count,
                        },
                        required={"required_confirmations": entry_timing_snapshot.required_confirmations},
                    ),
                ]
            )
            record_entry_committee_result(
                structured_logger=structured_logger,
                symbol=symbol,
                metrics=common_metrics,
                entry_steps=entry_steps,
                result=entry_committee_result,
            )
            entry_ready, _ = structured_logger.run_funnel(
                symbol=symbol,
                side="entry",
                steps=entry_steps,
                metrics=common_metrics,
                ready_stage="buy_ready",
                ready_reason="entry_conditions_met",
            )

            add_on_profit_ready = (
                has_position
                and entry_price is not None
                and pnl_pct is not None
                and pnl_pct >= settings.pyramid_trigger_profit_pct
            )
            effective_pyramid_max_add_ons = 0
            if regime_policy.allow_pyramiding:
                effective_pyramid_max_add_ons = max(
                    0,
                    settings.pyramid_max_add_ons + regime_policy.pyramid_max_add_ons_delta,
                )
            add_on_limit_available = add_on_count < effective_pyramid_max_add_ons
            add_on_ready = False
            if settings.enable_pyramid_add_on:
                add_on_ready, _ = structured_logger.run_funnel(
                    symbol=symbol,
                    side="entry",
                    steps=build_btc_add_on_steps(
                        has_position=has_position,
                        add_on_profit_ready=add_on_profit_ready,
                        pnl_pct=pnl_pct,
                        min_pnl_pct=settings.pyramid_trigger_profit_pct,
                        add_on_limit_available=add_on_limit_available,
                        add_on_count=add_on_count,
                        max_add_ons=effective_pyramid_max_add_ons,
                        trailing_armed=trailing_armed,
                        entry_signal=entry_signal,
                        bullish=bullish,
                        trend_follow_entry=trend_follow_entry,
                        in_cooldown=in_cooldown,
                        cooldown_remaining=cooldown_remaining,
                        profit_exit_cooldown_remaining=profit_exit_cooldown_remaining,
                        volume_filter_passed=volume_filter_passed,
                        volume_ratio=volume_ratio,
                        effective_min_volume_ratio=effective_min_volume_ratio,
                        atr_filter_passed=atr_filter_passed,
                        atr_pct=atr_pct,
                        min_atr_pct=effective_min_atr_pct,
                        max_atr_pct=settings.max_atr_pct,
                        confirm_bullish=(not settings.enable_confirm_timeframe_filter or confirm_bullish),
                        daily_loss_limit_reached=daily_loss_limit_reached,
                        daily_realized_pnl_quote=daily_realized_pnl_quote,
                        max_daily_loss_quote=config["max_daily_loss_quote"],
                        remaining_budget_quote=add_on_allocation_decision.remaining_budget_quote,
                        current_cost_basis_quote=add_on_allocation_decision.current_cost_basis_quote,
                        target_budget_quote=add_on_allocation_decision.target_budget_quote,
                        add_on_order_value=add_on_order_value,
                        min_buy_order_value=min_buy_order_value,
                        estimated_add_on_amount=safe_amount_to_precision_upbit(exchange, symbol, add_on_order_value / last_close if last_close else 0.0),
                        min_order_amount=0.0,
                    ),
                    metrics=common_metrics,
                    ready_stage="add_on_ready",
                    ready_reason="add_on_conditions_met",
                    ready_extra={"entry_type": "add_on_winner"},
                )

            exit_steps = build_btc_exit_steps(
                has_position=has_position,
                stop_triggered=stop_triggered,
                partial_take_profit_triggered=partial_take_profit_triggered,
                profit_protect_triggered=profit_protect_triggered,
                trailing_stop_triggered=trailing_stop_triggered,
                donchian_failure_triggered=donchian_failure_triggered,
                trend_exit_triggered=trend_exit_triggered,
                estimated_exit_amount=safe_amount_to_precision_upbit(exchange, symbol, base_free),
                min_order_amount=0.0,
                sell_order_value_quote=(safe_amount_to_precision_upbit(exchange, symbol, base_free) * last_close),
                min_sell_order_value=min_buy_order_value,
            )
            exit_ready, _ = structured_logger.run_funnel(
                symbol=symbol,
                side="exit",
                steps=exit_steps,
                metrics=common_metrics,
                ready_stage="sell_ready",
                ready_reason=(
                    "stop_loss_triggered"
                    if stop_triggered
                    else "partial_take_profit_triggered"
                    if partial_take_profit_triggered
                    else "profit_protect_triggered"
                    if profit_protect_triggered
                    else "trailing_stop_triggered"
                    if trailing_stop_triggered
                    else "donchian_failure_triggered"
                    if donchian_failure_triggered
                    else "trend_exit_triggered"
                ),
            )

            if entry_ready:
                if order_value <= min_buy_order_value:
                    log(f"[{symbol}] 주문 금액이 너무 작아 진입을 생략합니다.")
                else:
                    buffered_order_value = apply_upbit_buy_order_buffer(
                        requested_order_value_quote=order_value,
                        quote_free=quote_free,
                        fee_rate_pct=config["fee_rate_pct"],
                        buffer_pct=config["krw_order_buffer_pct"],
                        buffer_krw=config["krw_order_buffer_krw"],
                    )
                    if buffered_order_value <= min_buy_order_value:
                        log(
                            f"[{symbol}] 주문 가능 KRW 버퍼를 반영하면 금액이 "
                            f"{min_buy_order_value:.0f} {quote} 이하라 진입을 생략합니다."
                        )
                        continue
                    amount = safe_amount_to_precision_upbit(exchange, symbol, buffered_order_value / last_close)
                    cost_to_spend = buffered_order_value
                    structured_logger.log_strategy(
                        symbol=symbol,
                        side="entry",
                        stage="order_requested",
                        result="requested",
                        reason="market_buy_requested",
                        actual={
                            "order_value_quote": cost_to_spend,
                            "amount": amount,
                        },
                        metrics=common_metrics,
                    )
                    order_request_started_at = time.time()
                    try:
                        order = create_market_buy_order_upbit(exchange, symbol, cost_to_spend)
                    except Exception as order_error:
                        log_order_failure(
                            structured_logger=structured_logger,
                            symbol=symbol,
                            side="entry",
                            message="BTC 매수 주문 요청이 실패했습니다.",
                            actual={
                                "order_value_quote": cost_to_spend,
                                "amount": amount,
                            },
                            metrics=common_metrics,
                            error=order_error,
                            extra={"strategy_version": settings.version},
                        )
                        continue
                    order_response_received_at = time.time()
                    order = enrich_upbit_order_with_private_event(
                        order,
                        symbol=symbol,
                        market_data_provider=market_data_provider,
                    )
                    invalidate_upbit_balance_cache(exchange)
                    invalidate_upbit_orderbook_cache(exchange, symbol)
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
                            "filled_amount": amount,
                            "order_value_quote": cost_to_spend,
                        },
                        metrics={**common_metrics, "estimated_entry_price_after": entry_price},
                    )
                    structured_logger.log_trade_event(
                        symbol=symbol,
                        side="buy",
                        reason="entry",
                        result="filled",
                        actual={
                            "filled_amount": amount,
                            "order_value_quote": cost_to_spend,
                        },
                        metrics={**common_metrics, "estimated_entry_price_after": entry_price},
                    )
                    logger.log_trade_banner(
                        RED,
                        f"[{symbol}] BTC EMA 전략 매수 체결",
                        f"주문 결과: {order}",
                    )
                    buy_summary = summarize_order_for_notification(
                        raw_order=order,
                        side="buy",
                        requested_amount=amount,
                        requested_order_value_quote=cost_to_spend,
                        fallback_amount=amount,
                        fallback_order_value_quote=cost_to_spend,
                        fallback_price=entry_price,
                    )
                    executed_ratio_pct = 0.0
                    if quote_free > 0 and buy_summary["executed_order_value_quote"] not in (None, 0):
                        executed_ratio_pct = (
                            float(buy_summary["executed_order_value_quote"]) / float(quote_free) * 100
                        )
                    notifier.notify_buy_fill(
                        "UPBIT-BTC",
                        symbol,
                        f"현재 레짐: {symbol_regime}\n"
                        f"매수 금액: {buy_summary['executed_order_value_quote']:.0f} {quote}\n"
                        f"매수 단가: {buy_summary['executed_price']:.0f}\n"
                        f"체결 수량: {buy_summary['executed_amount']:.8f} {base}\n"
                        f"기본 비중: {base_position_ratio * 100:.2f}%\n"
                        f"최종 비중: {position_ratio * 100:.2f}%\n"
                        f"실행 비중: {executed_ratio_pct:.2f}%",
                    )
                    trade_history.log_fill(
                        exchange_name="UPBIT",
                        program_name="upbit_btc_ema_trend_bot",
                        strategy_version=settings.version,
                        symbol=symbol,
                        side="buy",
                        reason="entry",
                        base_currency=base,
                        quote_currency=quote,
                        amount=amount,
                        order_value_quote=cost_to_spend,
                        reference_price=last_close,
                        estimated_entry_price=entry_price,
                        base_free_before=base_free,
                        quote_free_before=quote_free,
                        remaining_base_after_estimate=base_free + amount,
                        timeframe=settings.timeframe,
                        ma_period=settings.slow_ema_period,
                        position_id=position_id,
                        leg_index=0,
                        is_final_exit=False,
                        request_started_at=order_request_started_at,
                        response_received_at=order_response_received_at,
                        requested_order_value_quote=cost_to_spend,
                        raw_order=order,
                        extra={
                            "strategy_version": settings.version,
                            "strategy": "btc_ema_trend",
                            "entry_type": "initial_entry",
                            "volume_ratio": volume_ratio,
                            "atr_value": atr_value,
                            "atr_pct": atr_pct,
                            "atr_percentile": atr_percentile,
                            "range_position_pct": recent_range_context["range_position_pct"],
                            "distance_from_recent_high_pct": recent_range_context["distance_from_recent_high_pct"],
                            "overheated_entry_blocked": overheated_entry_blocked,
                            "overheat_extra_confirmation_required": overheat_extra_confirmation_required,
                            "confirm_bullish": confirm_bullish,
                        },
                    )
                    add_on_count = 0

            elif add_on_ready:
                buffered_add_on_order_value = apply_upbit_buy_order_buffer(
                    requested_order_value_quote=add_on_order_value,
                    quote_free=quote_free,
                    fee_rate_pct=config["fee_rate_pct"],
                    buffer_pct=config["krw_order_buffer_pct"],
                    buffer_krw=config["krw_order_buffer_krw"],
                )
                if buffered_add_on_order_value <= min_buy_order_value:
                    log(
                        f"[{symbol}] 추가매수 가능 KRW 버퍼를 반영하면 금액이 "
                        f"{min_buy_order_value:.0f} {quote} 이하라 추가매수를 생략합니다."
                    )
                    continue
                amount = safe_amount_to_precision_upbit(exchange, symbol, buffered_add_on_order_value / last_close)
                cost_to_spend = buffered_add_on_order_value
                structured_logger.log_strategy(
                    symbol=symbol,
                    side="entry",
                    stage="order_requested",
                    result="requested",
                    reason="market_buy_requested",
                    actual={
                        "order_value_quote": cost_to_spend,
                        "amount": amount,
                    },
                    metrics={**common_metrics, "entry_type": "add_on_winner"},
                )
                order_request_started_at = time.time()
                try:
                    order = create_market_buy_order_upbit(exchange, symbol, cost_to_spend)
                except Exception as order_error:
                    log_order_failure(
                        structured_logger=structured_logger,
                        symbol=symbol,
                        side="entry",
                        message="BTC 추가매수 주문 요청이 실패했습니다.",
                        actual={
                            "order_value_quote": cost_to_spend,
                            "amount": amount,
                        },
                        metrics={**common_metrics, "entry_type": "add_on_winner"},
                        error=order_error,
                        extra={"strategy_version": settings.version},
                    )
                    continue
                order_response_received_at = time.time()
                order = enrich_upbit_order_with_private_event(
                    order,
                    symbol=symbol,
                    market_data_provider=market_data_provider,
                )
                invalidate_upbit_balance_cache(exchange)
                invalidate_upbit_orderbook_cache(exchange, symbol)

                previous_amount = base_free
                added_amount = amount
                total_amount = previous_amount + added_amount
                previous_entry_price = entry_price or last_close
                if total_amount > 0:
                    entry_price = (
                        (previous_entry_price * previous_amount) + (last_close * added_amount)
                    ) / total_amount
                else:
                    entry_price = last_close
                add_on_count += 1
                last_trade_at = time.time()
                highest_price_since_entry = max(highest_price_since_entry or last_close, last_close)
                lowest_price_since_entry = min(lowest_price_since_entry or last_close, last_close)

                structured_logger.log_strategy(
                    symbol=symbol,
                    side="entry",
                    stage="filled",
                    result="filled",
                    reason="buy_add_on_filled",
                    actual={
                        "filled_amount": added_amount,
                        "order_value_quote": cost_to_spend,
                    },
                    metrics={
                        **common_metrics,
                        "entry_type": "add_on_winner",
                        "estimated_entry_price_after": entry_price,
                        "add_on_count_after": add_on_count,
                    },
                )
                structured_logger.log_trade_event(
                    symbol=symbol,
                    side="buy",
                    reason="add_on_winner",
                    result="filled",
                    actual={
                        "filled_amount": added_amount,
                        "order_value_quote": cost_to_spend,
                    },
                    metrics={
                        **common_metrics,
                        "entry_type": "add_on_winner",
                        "estimated_entry_price_after": entry_price,
                        "add_on_count_after": add_on_count,
                    },
                )
                logger.log_trade_banner(
                    RED,
                    f"[{symbol}] BTC EMA 전략 추가매수 체결",
                    f"주문 결과: {order}",
                )
                add_on_summary = summarize_order_for_notification(
                    raw_order=order,
                    side="buy",
                    requested_amount=amount,
                    requested_order_value_quote=cost_to_spend,
                    fallback_amount=amount,
                    fallback_order_value_quote=cost_to_spend,
                    fallback_price=entry_price,
                )
                executed_ratio_pct = 0.0
                if quote_free > 0 and add_on_summary["executed_order_value_quote"] not in (None, 0):
                    executed_ratio_pct = (
                        float(add_on_summary["executed_order_value_quote"]) / float(quote_free) * 100
                    )
                add_on_ratio_pct = settings.pyramid_position_ratio * allocation_score_result.score_scale * 100
                notifier.notify_buy_fill(
                    "UPBIT-BTC",
                    symbol,
                    f"현재 레짐: {symbol_regime}\n"
                    f"사유: add_on_winner\n"
                    f"매수 금액: {add_on_summary['executed_order_value_quote']:.0f} {quote}\n"
                    f"매수 단가: {add_on_summary['executed_price']:.0f}\n"
                    f"체결 수량: {add_on_summary['executed_amount']:.8f} {base}\n"
                    f"갱신 평균 진입가: {entry_price:.0f}\n"
                    f"기본 추가매수 비중: {settings.pyramid_position_ratio * 100:.2f}%\n"
                    f"최종 추가매수 비중: {add_on_ratio_pct:.2f}%\n"
                    f"실행 비중: {executed_ratio_pct:.2f}%",
                )
                trade_history.log_fill(
                    exchange_name="UPBIT",
                    program_name="upbit_btc_ema_trend_bot",
                    strategy_version=settings.version,
                    symbol=symbol,
                    side="buy",
                    reason="add_on_winner",
                    base_currency=base,
                    quote_currency=quote,
                    amount=added_amount,
                    order_value_quote=cost_to_spend,
                    reference_price=last_close,
                    estimated_entry_price=entry_price,
                    base_free_before=base_free,
                    quote_free_before=quote_free,
                    remaining_base_after_estimate=total_amount,
                    timeframe=settings.timeframe,
                    ma_period=settings.slow_ema_period,
                    position_id=position_id,
                    leg_index=add_on_count,
                    is_final_exit=False,
                    request_started_at=order_request_started_at,
                    response_received_at=order_response_received_at,
                    requested_order_value_quote=cost_to_spend,
                    raw_order=order,
                    extra={
                        "strategy_version": settings.version,
                        "strategy": "btc_ema_trend",
                        "entry_type": "add_on_winner",
                        "previous_entry_price": previous_entry_price,
                        "updated_entry_price": entry_price,
                        "add_on_count_after": add_on_count,
                        "volume_ratio": volume_ratio,
                        "atr_value": atr_value,
                        "atr_pct": atr_pct,
                        "atr_percentile": atr_percentile,
                        "range_position_pct": recent_range_context["range_position_pct"],
                        "distance_from_recent_high_pct": recent_range_context["distance_from_recent_high_pct"],
                        "overheated_entry_blocked": overheated_entry_blocked,
                        "overheat_extra_confirmation_required": overheat_extra_confirmation_required,
                        "confirm_bullish": confirm_bullish,
                    },
                )

            elif exit_ready:
                partial_take_profit_full_exit = False
                if partial_take_profit_triggered:
                    partial_amount = safe_amount_to_precision_upbit(
                        exchange,
                        symbol,
                        base_free * effective_partial_take_profit_ratio,
                    )
                    remaining_after_partial = max(base_free - partial_amount, 0.0)
                    if (
                        partial_amount <= 0
                        or partial_amount * sell_price_reference <= min_buy_order_value
                        or remaining_after_partial * sell_price_reference <= min_buy_order_value
                    ):
                        partial_take_profit_full_exit = True
                        amount = safe_amount_to_precision_upbit(exchange, symbol, base_free)
                    else:
                        amount = partial_amount
                else:
                    amount = safe_amount_to_precision_upbit(exchange, symbol, base_free)
                sell_order_value_quote = amount * sell_price_reference
                if amount <= 0:
                    pass
                elif sell_order_value_quote <= min_buy_order_value:
                    log(
                        f"[{symbol}] 예상 매도 금액이 {min_buy_order_value:.0f} {quote} 이하라 매도 주문을 생략합니다."
                    )
                else:
                    if stop_triggered:
                        sell_reason = "stop_loss"
                        notify_fn = notifier.notify_stop_loss_fill
                        title = "BTC EMA 전략 손절 체결"
                    elif partial_take_profit_triggered:
                        sell_reason = "partial_take_profit"
                        notify_fn = notifier.notify_sell_fill
                        title = (
                            "BTC EMA 전략 부분 익절 체결"
                            if not partial_take_profit_full_exit
                            else "BTC EMA 전략 전량 익절 체결"
                        )
                    elif profit_protect_triggered:
                        sell_reason = "profit_protect_take_profit"
                        notify_fn = notifier.notify_sell_fill
                        title = "BTC EMA 전략 순익 보호 익절 체결"
                    elif trailing_stop_triggered:
                        sell_reason = "trailing_take_profit"
                        notify_fn = notifier.notify_sell_fill
                        title = "BTC EMA 전략 트레일링 익절 체결"
                    elif donchian_failure_triggered:
                        sell_reason = "donchian_failure_exit"
                        notify_fn = notifier.notify_sell_fill
                        title = "BTC EMA 전략 돌파 실패 청산"
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
                    order_request_started_at = time.time()
                    try:
                        order = create_market_sell_order_upbit(exchange, symbol, amount)
                    except Exception as order_error:
                        log_order_failure(
                            structured_logger=structured_logger,
                            symbol=symbol,
                            side="exit",
                            message="BTC 매도 주문 요청이 실패했습니다.",
                            actual={"sell_amount": amount},
                            metrics=common_metrics,
                            error=order_error,
                            extra={"strategy_version": settings.version},
                        )
                        continue
                    order_response_received_at = time.time()
                    order = enrich_upbit_order_with_private_event(
                        order,
                        symbol=symbol,
                        market_data_provider=market_data_provider,
                    )
                    invalidate_upbit_balance_cache(exchange)
                    invalidate_upbit_orderbook_cache(exchange, symbol)
                    realized_pnl_pct = 0.0
                    realized_pnl_quote = 0.0
                    holding_seconds = None
                    trailing_armed_at_iso = (
                        datetime.fromtimestamp(trailing_armed_at).astimezone().isoformat()
                        if trailing_armed_at is not None
                        else None
                    )
                    trailing_armed_seconds = None
                    activation_to_exit_seconds = None
                    fee_quote_estimate = None
                    net_realized_pnl_quote = None
                    net_realized_pnl_pct = None
                    if entry_opened_at is not None:
                        holding_seconds = max(0.0, time.time() - entry_opened_at)
                    if entry_opened_at is not None and trailing_armed_at is not None:
                        trailing_armed_seconds = max(0.0, trailing_armed_at - entry_opened_at)
                    if trailing_armed_at is not None:
                        activation_to_exit_seconds = max(0.0, time.time() - trailing_armed_at)
                    if entry_price:
                        realized_pnl_pct = (last_close - entry_price) / entry_price * 100
                        realized_pnl_quote = (last_close - entry_price) * amount
                        daily_realized_pnl_quote += realized_pnl_quote
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
                    if stop_triggered:
                        last_stop_loss_at = time.time()
                    elif sell_reason in {
                        "trailing_take_profit",
                        "profit_protect_take_profit",
                        "partial_take_profit",
                    }:
                        last_profit_exit_at = time.time()
                    last_trade_at = time.time()
                    if sell_reason == "partial_take_profit" and not partial_take_profit_full_exit:
                        partial_take_profit_done = True
                        if not trailing_armed:
                            trailing_armed = True
                            trailing_armed_at = time.time()
                            trailing_activation_price = highest_price_since_entry or last_close
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
                    sell_summary = summarize_order_for_notification(
                        raw_order=order,
                        side="sell",
                        requested_amount=amount,
                        requested_order_value_quote=amount * last_close,
                        fallback_amount=amount,
                        fallback_order_value_quote=amount * last_close,
                        fallback_price=last_close,
                    )
                    notify_fn(
                        "UPBIT-BTC",
                        symbol,
                        f"현재 레짐: {symbol_regime}\n"
                        f"사유: {sell_reason}\n"
                        f"매도 금액: {sell_summary['executed_order_value_quote']:.0f} {quote}\n"
                        f"매도 단가: {sell_summary['executed_price']:.0f}\n"
                        f"체결 수량: {sell_summary['executed_amount']:.8f} {base}\n"
                        f"수익률: {realized_pnl_pct:.2f}%\n"
                        f"실현 손익: {realized_pnl_quote:.2f} {quote}",
                    )
                    trade_history.log_fill(
                        exchange_name="UPBIT",
                        program_name="upbit_btc_ema_trend_bot",
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
                        is_final_exit=(sell_reason != "partial_take_profit" or partial_take_profit_full_exit),
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
                        request_started_at=order_request_started_at,
                        response_received_at=order_response_received_at,
                        requested_amount=amount,
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
                            "partial_take_profit_done": partial_take_profit_done,
                            "partial_take_profit_triggered": partial_take_profit_triggered,
                            "partial_take_profit_full_exit": partial_take_profit_full_exit,
                            "partial_take_profit_ratio": settings.partial_take_profit_ratio,
                            "effective_partial_take_profit_ratio": effective_partial_take_profit_ratio,
                            "current_net_pnl_pct_estimate": current_net_realized_pnl_pct,
                            "fee_protect_min_net_pnl_pct": settings.fee_protect_min_net_pnl_pct,
                            "profit_protect_triggered": profit_protect_triggered,
                            "highest_price_since_entry": highest_price_since_entry,
                            "trailing_armed": trailing_armed,
                            "drawdown_from_high_pct": drawdown_from_high_pct,
                            "trend_exit_triggered": trend_exit_triggered,
                            "holding_seconds": holding_seconds,
                        },
                    )
                    log(
                        f"[{symbol}] 실현 손익: {realized_pnl_quote:.2f} {quote} | "
                        f"오늘 누적 실현 손익: {daily_realized_pnl_quote:.2f} {quote}"
                    )
                    if sell_reason != "partial_take_profit" or partial_take_profit_full_exit:
                        cleared = clear_btc_position_state()
                        entry_price = cleared["entry_price"]
                        entry_opened_at = cleared["entry_opened_at"]
                        position_id = cleared["position_id"]
                        highest_price_since_entry = cleared["highest_price_since_entry"]
                        lowest_price_since_entry = cleared["lowest_price_since_entry"]
                        trailing_armed = bool(cleared["trailing_armed"])
                        trailing_armed_at = cleared["trailing_armed_at"]
                        trailing_activation_price = cleared["trailing_activation_price"]
                        partial_take_profit_done = bool(cleared["partial_take_profit_done"])
                        add_on_count = int(cleared["add_on_count"])
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
            notifier.notify_error_message("UPBIT-BTC", symbol, repr(e))

        time.sleep(settings.loop_interval_sec)


if __name__ == "__main__":
    run_bot()
