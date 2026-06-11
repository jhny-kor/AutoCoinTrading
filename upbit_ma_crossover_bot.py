"""
수정 요약
- 2026-06-12: 알트 순익 trailing exit 정책을 업비트 알트 루프에 연결했다.
- 2026-06-03: BTC LOW_ENERGY 저ATR 구간에서 알트가 고점권이면 추격 진입을 차단하도록 연결
- 2026-05-15: XRP/KRW 고점수 반등 probe 를 mean_reversion 하단 reclaim 미확인 예외로 제한 연결
- 2026-05-14: 알트 공통 SMA/거래량/등락률 helper 를 core.strategy.indicators 로 분리함
- 2026-05-14: 알트 진입/청산 퍼널 실행 단계를 공통 alt_loop helper 로 옮김
- 2026-05-14: 업비트 시장가 주문 제출, private 이벤트 보강, 캐시 무효화를 공통 order adapter 로 옮김
- 2026-05-14: 청산 퍼널 ready reason 결정을 공통 exit helper 로 옮겨 run_bot 단계 분기를 줄임
- 2026-05-14: 최소 주문 금액 기준 매도 fallback 정책을 공통 alt_exit helper 로 옮김
- 2026-05-14: 주문 요청/체결 구조화 로그 입력을 공통 helper 로 옮김
- 2026-05-14: 텔레그램 체결 알림 본문을 공통 formatter 로 옮김
- 2026-05-14: 매도 체결 후 내부 포지션 상태 갱신을 공통 lifecycle helper 로 옮김
- 2026-05-14: 매수 체결 후 내부 포지션 상태 갱신을 공통 lifecycle helper 로 옮김
- 2026-05-13: 매도 주문 직전 청산 비율/reason 결정 로직을 공통 alt_exit helper 로 옮김
- 2026-05-13: 알트 진입 후반부 가드 퍼널 단계를 공통 helper 로 옮겨 OKX 봇과 중복을 줄임
- 2026-05-13: 무포지션 기본 지표와 부분청산 pending 계산을 공통 alt_exit helper 로 옮김
- 2026-05-13: SOL probe 청산 기준 계산도 공통 helper 로 옮겨 거래소별 중복을 줄임
- 2026-05-13: SOL probe 진입 승격과 레짐/LOW_ENERGY 우회 보정을 공통 helper 로 옮겨 OKX 알트 봇과 구조를 맞춤
- 2026-05-12: 하단 근접 mean_reversion probe 전용 낮은 점수 기준과 소액 비중 우회 계산을 업비트 알트 진입 경로에 연결
- 2026-05-07: SOL 제한형 probe 전략을 연결해 점수 70 이상 소액 진입과 180분 시간 청산을 적용
- 2026-05-06: 매수 후보를 전략/리스크/체결/포트폴리오/레짐 위원회로 shadow 검토하도록 연결
- 2026-05-06: mean_reversion 하단 근접 후보는 소액 비중과 추가 confirmation 으로만 진입 후보화
- 2026-05-05: 업비트 알트 고품질 후보가 최소주문금액에만 걸릴 때 예산과 손절방지 조건 확인 후 최소 주문 floor 를 적용
- 2026-05-05: LOW_ENERGY 레짐을 고점수 소액 probe 후보로 보정하고 업비트 주문 버퍼 후 최소금액 차단을 퍼널에 반영
- 2026-05-05: mean_reversion 음수 slope + 고거래량 + 중고 ATR + 저점 근접 조합을 신규 진입 차단 조건으로 연결
- 2026-05-02: 업비트 ETH/XRP 거래량 급등 신호가 손절방지 조건을 만족하면 소액/추가확인 후보로 낮추도록 반영
- 2026-05-02: BTC 상관계수 단독 차단은 결합 손절방지 가드가 꺼진 fallback 으로 낮춰 좋은 거래 차단을 줄임
- 2026-05-02: 손절 방지를 위해 BTC 위험 레짐+고상관+알트 고ATR, 거래량+ATR+체결 약세, 손절 후 유사 조건 재진입 가드를 추가
- 2026-05-01: 거래량+ATR+RSI 과열 조합은 신규 진입을 막고, range 상단 추격 신호는 추가 확인을 요구하도록 보강
- CHOPPY 레짐에서는 Bollinger 하단 복귀 기반 mean_reversion 전략 경로를 사용하도록 확장
- 알트 자체 ATR 퍼센트를 포지션 비중 계산에 직접 반영하도록 연결
- ETH/KRW 같은 약한 알트는 심볼별 signal_score 최소 기준 오버라이드를 적용해 저품질 진입을 더 줄이도록 보강
- 2026-05-07: 알트 포지션 비중 계산과 로그 조립을 공통 allocation helper 로 옮겨 업비트/OKX 구조를 맞춤
- 2026-04-12: 텔레그램 매수 체결 알림에 기본 비중, 최종 비중, 실제 실행 비중을 함께 표시하도록 보강
- 2026-04-10: 알트 보수형 조정으로 최대 진입 이격도와 최대 거래량 배수 상한을 추가하고 과열 추격 진입을 더 줄이도록 보강
- 2026-04-09: 알트 손절 후 재진입을 최소 시간 + 패턴 복구 기준으로 보도록 패턴 기반 재진입 gate 를 추가
- 2026-04-08: 알트도 독립 레짐 라우터에서 `skip / breakout / trend_follow` 전략 경로를 선택하도록 정리
- 2026-04-06: 알트 Bollinger Squeeze + 거래량 확장 진입 지표 연산 연동
- BTC ATR 퍼센트가 낮을 때 알트 신규 진입 비중을 단계형으로 줄이는 보정을 추가했다.
- BTC LOW_ENERGY 축소 스케일에 심볼별 override 를 적용해 ETH/KRW 는 더 보수적으로, XRP/KRW 는 덜 보수적으로 진입 비중을 줄이도록 조정했다.
- BTC 레짐 기반 알트 신규 진입 비중 스케일을 추가해 BTC 가 LOW_ENERGY 일 때는 알트 포지션을 먼저 축소하도록 보강했다.
- 무포지션 경로에서도 순손익 관련 지역변수가 항상 초기화되도록 helper 를 추가해 UnboundLocalError 재발을 막고 회귀 테스트 기준을 맞췄다.
- 업비트 알트 상위 타임프레임 5분봉도 웹소켓 1분봉 리샘플 우선, stale 시 REST fallback 으로 바꿔 REST 캔들 호출을 더 줄이도록 확장했다.
- 업비트 1분봉 조회를 웹소켓 1분 캔들 우선, stale 시 REST fallback 으로 바꿔 phase 3 전환을 시작했다.
- 업비트 best bid 조회를 웹소켓 latest 스냅샷 우선, stale 시 REST fallback 으로 바꿔 phase 2 전환을 시작했다.
- 노이즈 비율 기반 동적 이격도 보정을 추가해 알트 진입 기준을 장 상태에 맞춰 자동 조정하도록 보강
- 2차 강화로 진입 상태 머신, BTC 상관관계 가드, 체결률 기반 진입 차단을 추가했다.
- 알트 진입에 RSI, MACD, MA 기울기, 신호 스코어를 추가하고 레짐별 손절/익절/분할진입 정책을 반영하도록 강화
- 업비트 잔고/호가 REST 호출을 짧게 캐시하고 최소 주문 경계 근처에서만 호가를 재조회해 지연과 요청 수를 줄이도록 개선
- 업비트 시장가 매도도 공통 재시도 경로를 사용하고 주문 직후 캐시를 비워 다음 루프가 최신 잔고를 다시 읽도록 보강
- 혼합 청산 세트를 위해 심볼별 순익 보호 익절 기준을 읽어 ETH/KRW, XRP/KRW, ETH/USDT 같은 심볼별 청산 성격을 분리할 수 있게 확장
- XRP/KRW 같은 특정 심볼은 상위 타임프레임 하락 추세일 때 신규 진입을 차단하도록 보수화했다.
- 저에너지 장에서는 신규 진입을 줄이기 위한 거래소별 저에너지 가드를 추가했다.
- 업비트 429 요청 제한에 걸릴 때 짧은 backoff 재시도를 적용하고, KRW 매수 주문에는 안전 버퍼를 두도록 보강했다.
- ETH/KRW 같은 특정 심볼에서 수익을 줬다가 다시 크게 깨지는 흐름을 막기 위한 브레이크이븐 가드를 추가했다.
- 텔레그램 매수/매도 체결 알림에 실제 체결가와 체결 금액이 함께 보이도록 보강
- 부분 익절 직후 같은 코인 재진입과 추가 매수를 잠시 막는 전용 쿨다운을 추가
- 거래소 전체 기준 목표 비중과 남아 있는 누적 투입 원가를 바탕으로 알트 신규 매수 한도를 제한하는 포트폴리오 배분 로직을 추가
- 알트가 수수료를 제하고도 순익인 상태에서 메인 추세가 꺾이면 즉시 전량 익절하는 순익 보호 청산 규칙을 추가
- 업비트 알트 체결 로그에 주문 ID, API 지연, 체결 비율, 슬리피지 같은 주문 실행 품질 지표를 함께 저장하도록 확장
- 심볼별 부분익절/부분손절 설정을 지원하고 ETH/XRP 같은 선택 알트에만 1회 부분청산을 적용하도록 확장
- 업비트 알트 매도 체결 로그도 왕복 수수료 기준 순손익을 함께 남겨 /pnl 집계가 모두 net 기준으로 가능하도록 보강
- 업비트 알트에서 예상 매도 금액이 최소 주문 금액 5,000 KRW 미만이면 매도 주문을 선차단하도록 추가
- 업비트 알트에서 최소 주문 금액 미만 잔량은 내부 포지션 상태도 함께 초기화해 재진입이 막히지 않도록 조정
- 공통 전략 버전 이름(strategy_version)을 구조화 로그와 체결 이력에 함께 남겨 버전별 비교가 가능하도록 확장
- 알트 포지션의 최고가/최저가, MFE/MAE, 보유시간을 체결 로그에 함께 남겨 거래 품질 분석이 가능하도록 확장
- 알트 보수형 trend_follow_entry 를 추가해 연속 MA 상단 유지와 상승 확인 시 제한적으로 신규 진입을 허용
- 심볼별 거래량 기준을 읽어 DOGE 같은 고변동 코인만 더 엄격한 진입 품질 필터를 적용할 수 있게 개선
- 업비트 알트 익절은 왕복 수수료보다 낮지 않도록 소폭 안전마진을 포함한 하한선을 적용
- 업비트 시장가 매수는 수량이 아니라 KRW 사용 금액 기준으로 보내도록 수정
- 업비트 알트 보유 여부를 최소 주문 금액 기준으로 판정해 먼지잔고는 포지션에서 제외하도록 조정
- 업비트 알트 감시 심볼 목록을 .env 기반 공통 로더로 읽도록 재구조화
- 공통 전략 값을 .env 에서 읽도록 구조 정리
- 업비트 전용 값은 API 정보와 최소 주문 금액만 유지하도록 정리
- 낮은 시드머니 테스트 시 두 파일이 같은 전략 기준으로 동작하도록 맞춤
- 매수 신호는 빨간색, 매도 신호는 파란색으로 로그에 표시되도록 개선
- 실제 거래 발생 시 굵은 강조 배너 로그가 나오도록 개선
- 업비트 거래 수수료를 .env 로 관리하고 최소 익절 조건에 반영
- 프로그램별 로그 파일이 자동으로 저장되도록 공통 로거 연결
- 심볼별 이격도 기준을 .env 에서 다르게 읽도록 개선
- 심볼별 익절률/손절률을 .env 에서 다르게 읽도록 개선
- 손실 한도 초과 시 데드크로스 없이도 즉시 청산하는 손절 규칙 추가
- 상위 타임프레임 추세와 같은 방향일 때만 신규 진입하는 필터 추가
- 일일 최대 손실 한도 도달 시 신규 매수를 중단하는 제한 추가
- 거래량 필터와 변동성 필터를 신규 진입 조건에 추가
- 텔레그램 알림 모듈 연결
- 매수/익절/손절/에러/일일 손실 제한 도달 시 텔레그램 메시지 전송 추가
- 체결 결과를 trade_logs/trade_history.jsonl 에 구조화해서 저장하도록 추가
- BTC 는 전용 EMA 봇으로 분리하고 기존 업비트 봇은 알트(XRP) 전용으로 정리
- 전략 판단 로그를 system / strategy / trade JSONL 로 분리 저장하도록 추가
- 매수/매도 판단을 퍼널 단계와 reason 코드 기준으로 집계 가능하게 기록하도록 추가
- 거래량 배수 계산을 형성 중인 현재 봉 대신 직전 마감 봉 기준으로 바꿔 더 안정적으로 해석하도록 조정
"""

import os
import time
import traceback
from datetime import datetime
from typing import Tuple

import ccxt
from dotenv import load_dotenv

from bot_logger import BLUE, RED, BotLogger
from core.execution.common import log_order_failure
from core.execution.order_logging import log_order_filled, log_order_requested
from core.execution.upbit import (
    apply_upbit_buy_order_buffer as apply_upbit_buy_order_buffer_core,
    create_upbit_market_data_provider as create_upbit_market_data_provider_core,
    create_upbit_client as create_upbit_client_core,
    fetch_best_bid_upbit as fetch_best_bid_upbit_core,
    fetch_ohlcv_upbit_with_provider as fetch_ohlcv_upbit_with_provider_core,
    fetch_ohlcv_upbit as fetch_ohlcv_upbit_core,
    get_spot_balances_upbit_with_provider as get_spot_balances_upbit_with_provider_core,
    load_upbit_config as load_upbit_config_core,
    safe_amount_to_precision_upbit as safe_amount_to_precision_upbit_core,
    should_refresh_best_bid_upbit as should_refresh_best_bid_upbit_core,
)
from core.execution.order_adapters import (
    submit_upbit_market_buy,
    submit_upbit_market_sell,
)
from core.market_data.upbit_provider import UpbitMarketDataProvider
from core.logging.metrics import build_alt_common_metrics
from core.notifications.trade_messages import (
    UPBIT_TRADE_MESSAGE_FORMAT,
    format_buy_fill_message,
    format_sell_fill_message,
)
from core.positions.lifecycle import (
    apply_alt_buy_fill_state,
    apply_alt_sell_fill_state,
    clear_alt_position_state,
)
from core.positions.guards import handle_unrecoverable_position
from core.risk.allocation import (
    build_alt_allocation,
    build_alt_position_sizing,
    compute_allocation_score,
    format_allocation_score_log,
    format_alt_position_sizing_log,
    format_dynamic_bonus_log,
    format_portfolio_budget_log,
)
from core.risk.execution_guard import ExecutionQualityGuard, FillQualitySnapshot
from core.risk.shared import is_daily_loss_limit_reached, is_dynamic_bonus_eligible
from core.risk.alt_exit import (
    build_empty_position_runtime_metrics,
    compute_alt_exit_decisions,
    compute_alt_position_metrics,
    resolve_alt_partial_exit_policy,
    resolve_alt_sell_order_by_min_value,
    resolve_alt_sell_intent,
)
from core.risk.alt_profit_trailing import resolve_alt_profit_trailing_exit
from core.runtime.bootstrap import build_alt_runtime_state
from core.strategy.alt import (
    compute_alt_signal_state,
    compute_can_average_down,
    compute_alt_stop_loss_reentry_gate,
)
from core.strategy.entry_committee import (
    evaluate_entry_committee,
    load_entry_committee_settings,
    record_entry_committee_result,
)
from core.strategy.alt_loop import run_alt_entry_funnel, run_alt_exit_funnel
from core.strategy.combined_filters import (
    calc_recent_range_context,
    is_btc_regime_correlation_volatility_risk,
    is_low_energy_top_chase_entry_risk,
    is_overheated_entry_risk,
    is_stop_loss_context_reentry_risk,
    is_volume_atr_execution_weak_risk,
    requires_overheat_confirmation,
    safe_optional_float,
)
from core.strategy.funnels import (
    build_alt_entry_guard_steps,
    build_alt_entry_steps,
    build_alt_exit_steps,
)
from core.strategy.low_energy import evaluate_low_energy_probe
from core.strategy.mean_reversion import compute_bollinger_mean_reversion_state
from core.strategy.regime_router import route_alt_strategy
from core.strategy.sol_probe import (
    format_sol_probe_entry_log,
    resolve_sol_probe_exit_state,
    resolve_sol_probe_entry_state,
)
from core.strategy.volume_spike_entry import evaluate_volume_spike_entry_downgrade
from core.strategy.xrp_rebound_probe import resolve_xrp_rebound_probe_state
from core.strategy.indicators import (
    calc_avg_abs_change_pct,
    calc_atr,
    calc_bollinger_bands,
    calc_bollinger_band_width_pct,
    calc_completed_volume_ratio as calc_volume_ratio,
    calc_macd_histogram,
    calc_noise_ratio,
    calc_percentile_rank,
    calc_pct_slope,
    calc_recent_atr_series,
    calc_recent_volume_ratio_series,
    calc_return_correlation,
    calc_rsi,
    calc_sma,
    detect_sma_crossover as detect_crossover,
)
from core.strategy.timing import update_entry_timing_state
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
from structured_log_manager import FunnelStep, StructuredLogManager, choose_volatility_reason
from strategy_settings import (
    DEFAULT_UPBIT_BTC_SYMBOL,
    load_alt_markets,
    load_managed_symbols,
    load_strategy_settings,
)
from telegram_notifier import load_telegram_notifier
from trade_history_logger import (
    TradeHistoryLogger,
    estimate_round_trip_net_pnl,
    summarize_order_for_notification,
)

def load_config() -> dict:
    """환경 변수와 기본 설정 로드 (업비트용)."""
    return load_upbit_config_core()


def create_upbit_client(config: dict) -> ccxt.upbit:
    """업비트 클라이언트 생성."""
    return create_upbit_client_core(config)


def create_upbit_market_data_provider(config: dict) -> UpbitMarketDataProvider | None:
    """업비트 웹소켓 latest 스냅샷 provider 를 생성한다."""
    return create_upbit_market_data_provider_core(config)


def is_upbit_rate_limit_error(exc: Exception) -> bool:
    """업비트 요청 제한(429) 계열 예외인지 확인한다."""
    lowered = str(exc).lower()
    return isinstance(exc, ccxt.RateLimitExceeded) or "too_many_requests" in lowered or "429" in lowered


def call_upbit_with_retry(exchange: ccxt.upbit, func, *args, **kwargs):
    """업비트 공통 호출에 짧은 backoff 재시도를 적용한다."""
    retry_count = int(exchange.options.get("upbit_request_retry_count", 3) or 3)
    retry_delay_sec = float(exchange.options.get("upbit_request_retry_delay_sec", 1.2) or 1.2)
    last_error: Exception | None = None
    for attempt in range(retry_count + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_error = exc
            if not is_upbit_rate_limit_error(exc) or attempt >= retry_count:
                raise
            time.sleep(retry_delay_sec * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise RuntimeError("업비트 재시도 호출이 비정상 종료되었습니다.")


def apply_upbit_buy_order_buffer(
    *,
    requested_order_value_quote: float,
    quote_free: float,
    fee_rate_pct: float,
    buffer_pct: float,
    buffer_krw: float,
) -> float:
    return apply_upbit_buy_order_buffer_core(
        requested_order_value_quote=requested_order_value_quote,
        quote_free=quote_free,
        fee_rate_pct=fee_rate_pct,
        buffer_pct=buffer_pct,
        buffer_krw=buffer_krw,
    )


def fetch_ohlcv(
    exchange: ccxt.upbit,
    symbol: str,
    timeframe: str = "1m",
    limit: int = 200,
    market_data_provider: UpbitMarketDataProvider | None = None,
):
    return fetch_ohlcv_upbit_with_provider_core(
        exchange,
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        market_data_provider=market_data_provider,
    )


def get_spot_balances(
    exchange: ccxt.upbit,
    base: str,
    quote: str,
    *,
    market_data_provider: UpbitMarketDataProvider | None = None,
) -> Tuple[float, float]:
    return get_spot_balances_upbit_with_provider_core(
        exchange,
        base=base,
        quote=quote,
        market_data_provider=market_data_provider,
    )


def safe_amount_to_precision(exchange: ccxt.upbit, symbol: str, amount: float) -> float:
    return safe_amount_to_precision_upbit_core(exchange, symbol, amount)


def fetch_best_bid(exchange: ccxt.upbit, symbol: str) -> float | None:
    return fetch_best_bid_upbit_core(exchange, symbol)


def should_refresh_best_bid(
    *,
    base_free: float,
    last_close: float,
    min_order_value: float,
    refresh_buffer_pct: float,
) -> bool:
    """최소 주문 경계 근처일 때만 최신 매수호가를 다시 조회한다."""
    return should_refresh_best_bid_upbit_core(
        base_free=base_free,
        last_close=last_close,
        min_order_value=min_order_value,
        refresh_buffer_pct=refresh_buffer_pct,
    )


def run_bot():
    """
    업비트 원화 마켓 알트 1분봉 단순 이동평균 돌파 전략 봇.

    - 심볼: .env 의 UPBIT_ALT_SYMBOLS 에 등록한 업비트 알트 현물
    - 타임프레임: 1분봉
    - 전략:
        - 이전 캔들에서는 가격 < MA, 현재 캔들에서 가격 > MA  -> 골든 크로스 -> 매수
        - 이전 캔들에서는 가격 > MA, 현재 캔들에서 가격 < MA  -> 데드 크로스 -> 매도
    """
    config = load_config()
    strategy = load_strategy_settings("UPBIT_MIN_BUY_ORDER_VALUE", 5000)
    entry_committee_settings = load_entry_committee_settings()
    exchange = create_upbit_client(config)
    market_data_provider = create_upbit_market_data_provider(config)

    # BTC 는 전용 EMA 봇으로 분리했으므로 기존 업비트 봇은 알트만 담당한다.
    markets = load_alt_markets("upbit")
    recovered_states = restore_program_position_states(
        "upbit_ma_crossover_bot",
        [market["symbol"] for market in markets],
    )
    runtime_state = build_alt_runtime_state(recovered_states)

    timeframe = "1m"
    ma_period = 20
    min_ohlcv_limit = max(
        ma_period + 5,
        strategy.rsi_period + 5,
        strategy.noise_ratio_lookback + 5,
        strategy.macd_slow_period + strategy.macd_signal_period + 5,
        ma_period + strategy.trend_slope_lookback + 5,
    )

    entry_price = runtime_state.entry_price
    entry_opened_at = runtime_state.entry_opened_at
    highest_price_since_entry = runtime_state.highest_price_since_entry
    lowest_price_since_entry = runtime_state.lowest_price_since_entry
    partial_take_profit_done = runtime_state.partial_take_profit_done
    partial_stop_loss_done = runtime_state.partial_stop_loss_done
    alt_profit_trailing_armed = runtime_state.trailing_armed
    unrecoverable_position_warned: set[str] = set()
    partial_take_profit_last_at = runtime_state.partial_take_profit_last_at
    entry_count = runtime_state.entry_count
    last_trade_at = runtime_state.last_trade_at
    last_stop_loss_at = runtime_state.last_stop_loss_at
    # 일일 누적 실현 손익(KRW 기준)
    daily_pnl_date = datetime.now().date()
    daily_realized_pnl_quote = load_program_daily_realized_pnl_quote(
        "upbit_ma_crossover_bot",
        daily_pnl_date,
    )
    logger = BotLogger("upbit_ma_crossover_bot")
    structured_logger = StructuredLogManager("upbit_ma_crossover_bot")
    notifier = load_telegram_notifier()
    trade_history = TradeHistoryLogger()
    execution_quality_guard = ExecutionQualityGuard()
    portfolio_allocator = PortfolioAllocator(
        exchange_name="UPBIT",
        quote_currency="KRW",
        tracked_symbols=load_managed_symbols("upbit"),
    )
    daily_limit_notified = (
        daily_realized_pnl_quote <= -config["max_daily_loss_quote"]
    )
    entry_timing_state: dict[str, dict[str, int | str]] = {}
    last_stop_loss_context: dict[str, dict[str, object]] = {}
    log = logger.log

    log("=== 업비트 단순 이동평균 돌파 봇 시작 ===")
    log(f"타임프레임: {timeframe}, MA 기간: {ma_period}")
    log(f"한 번에 사용하는 계좌 비율: {config['risk_per_trade']}")
    log(f"업비트 편도 수수료: {config['fee_rate_pct']}%")
    log(f"일일 최대 손실 제한: {config['max_daily_loss_quote']} KRW")
    log(f"복구된 당일 실현 손익: {daily_realized_pnl_quote:.2f} KRW")
    if recovered_states:
        recovered_summary = ", ".join(
            f"{symbol}(avg={state.average_entry_price:.2f}, entries={state.cycle_buy_count})"
            for symbol, state in recovered_states.items()
            if state.average_entry_price is not None
        )
        if recovered_summary:
            log(f"복구된 포지션 상태: {recovered_summary}")
    structured_logger.log_system(
        level="INFO",
        event="bot_started",
        message="업비트 알트 전략 봇을 시작합니다.",
        context={
            "timeframe": timeframe,
            "ma_period": ma_period,
            "risk_per_trade": config["risk_per_trade"],
            "fee_rate_pct": config["fee_rate_pct"],
            "max_daily_loss_quote": config["max_daily_loss_quote"],
        },
    )

    while True:
        today = datetime.now().date()
        if today != daily_pnl_date:
            daily_pnl_date = today
            daily_realized_pnl_quote = load_program_daily_realized_pnl_quote(
                "upbit_ma_crossover_bot",
                daily_pnl_date,
            )
            daily_limit_notified = False
            log("일자가 변경되어 일일 손익 누적값을 초기화합니다.")
            structured_logger.log_system(
                level="INFO",
                event="daily_pnl_reset",
                message="일일 손익 누적값을 초기화했습니다.",
            )

        btc_reference_closes: list[float] = []
        btc_reference_above_ma = False
        btc_reference_regime = "UNKNOWN"
        btc_reference_atr_pct = None
        if (
            strategy.enable_correlation_filter
            or strategy.enable_btc_atr_position_scaling
        ):
            try:
                btc_ohlcv = fetch_ohlcv(
                    exchange,
                    DEFAULT_UPBIT_BTC_SYMBOL,
                    timeframe=timeframe,
                    limit=max(min_ohlcv_limit, strategy.correlation_lookback + ma_period + 5),
                    market_data_provider=market_data_provider,
                )
                btc_reference_closes = [row[4] for row in btc_ohlcv]
                if len(btc_reference_closes) >= ma_period:
                    btc_reference_ma = calc_sma(btc_reference_closes, ma_period)
                    btc_reference_above_ma = btc_reference_closes[-1] > btc_reference_ma
                btc_reference_atr_value = calc_atr(
                    btc_ohlcv,
                    strategy.btc_atr_position_scale_lookback,
                )
                if btc_reference_atr_value is not None and btc_reference_closes:
                    last_btc_close = btc_reference_closes[-1]
                    if last_btc_close > 0:
                        btc_reference_atr_pct = (
                            btc_reference_atr_value / last_btc_close * 100
                        )
            except Exception as exc:
                log(f"[BTC/KRW] 상관관계 기준 시세 조회 실패: {exc}")
        btc_reference_regime_snapshot = classify_symbol_regime(
            load_latest_symbol_record(
                exchange_name="upbit",
                symbol=DEFAULT_UPBIT_BTC_SYMBOL,
            )
        )
        btc_reference_regime = btc_reference_regime_snapshot.regime

        for m in markets:
            symbol = m["symbol"]
            base = m["base"]
            quote = m["quote"]

            log(f"=== {symbol} 체크 시작 ===")

            try:
                log("캔들 데이터 조회 시도 중...")
                ohlcv = fetch_ohlcv(
                    exchange,
                    symbol,
                    timeframe=timeframe,
                    limit=min_ohlcv_limit,
                    market_data_provider=market_data_provider,
                )
                closes = [c[4] for c in ohlcv]  # 종가 리스트
                ma_series = [
                    calc_sma(closes[: idx + 1], ma_period)
                    for idx in range(ma_period - 1, len(closes))
                ]

                log("이동평균 및 크로스 계산 중...")
                (
                    bullish,
                    bearish,
                    prev_close,
                    prev_ma,
                    last_close,
                    last_ma,
                ) = detect_crossover(closes, ma_period)

                log("-" * 60)
                log(f"[{symbol}] 이전 종가: {prev_close:.0f}, 이전 MA: {prev_ma:.0f}")
                log(f"[{symbol}] 현재 종가: {last_close:.0f}, 현재 MA: {last_ma:.0f}")
                logger.log_signal(symbol, bullish, bearish)
                log(f"[{symbol}] 신호 상태: bullish={bullish}, bearish={bearish}")
                gap_pct = abs(last_close - last_ma) / last_ma * 100 if last_ma else 0.0
                log(f"[{symbol}] 현재 종가와 MA 이격도: {gap_pct:.4f}%")
                rsi_value = calc_rsi(closes, strategy.rsi_period)
                noise_ratio = calc_noise_ratio(
                    ohlcv,
                    strategy.noise_ratio_lookback,
                )
                _macd_value, _macd_signal, macd_histogram = calc_macd_histogram(
                    closes,
                    fast_period=strategy.macd_fast_period,
                    slow_period=strategy.macd_slow_period,
                    signal_period=strategy.macd_signal_period,
                )
                _prev_macd_value, _prev_macd_signal, prev_macd_histogram = calc_macd_histogram(
                    closes[:-1],
                    fast_period=strategy.macd_fast_period,
                    slow_period=strategy.macd_slow_period,
                    signal_period=strategy.macd_signal_period,
                )
                ma_slope_pct = calc_pct_slope(
                    ma_series,
                    strategy.trend_slope_lookback,
                )
                price_slope_pct = calc_pct_slope(
                    closes,
                    strategy.trend_slope_lookback,
                )

                volume_ratio = calc_volume_ratio(ohlcv, strategy.volume_lookback)
                volume_ratio_series = calc_recent_volume_ratio_series(
                    ohlcv,
                    strategy.volume_lookback,
                    sample_count=20,
                )
                volume_ratio_percentile = calc_percentile_rank(
                    volume_ratio_series,
                    volume_ratio,
                )
                base_min_volume_ratio = strategy.get_min_volume_ratio(symbol)
                effective_min_volume_ratio = base_min_volume_ratio
                effective_max_volume_ratio = strategy.get_max_volume_ratio(symbol)
                volume_filter_passed = True
                volume_within_upper_bound = True
                if strategy.enable_volume_filter and volume_ratio is not None:
                    volume_filter_passed = (
                        volume_ratio >= effective_min_volume_ratio
                    )
                    volume_within_upper_bound = (
                        volume_ratio <= effective_max_volume_ratio
                    )
                    log(
                        f"[{symbol}] 거래량 배수: {volume_ratio:.4f}배 "
                        f"(허용 {effective_min_volume_ratio:.4f}배 ~ {effective_max_volume_ratio:.4f}배)"
                    )

                avg_abs_change_pct = calc_avg_abs_change_pct(
                    closes, strategy.volatility_lookback
                )
                atr_value = calc_atr(ohlcv, 14)
                atr_pct = (atr_value / last_close * 100) if atr_value is not None and last_close else None
                atr_series = calc_recent_atr_series(ohlcv, 14, sample_count=20)
                atr_percentile = calc_percentile_rank(atr_series, atr_value)
                recent_range_context = calc_recent_range_context(
                    ohlcv,
                    last_close=last_close,
                    lookback=strategy.volatility_lookback,
                )
                volatility_filter_passed = True
                if strategy.enable_volatility_filter and avg_abs_change_pct is not None:
                    volatility_filter_passed = (
                        strategy.min_volatility_pct
                        <= avg_abs_change_pct
                        <= strategy.max_volatility_pct
                    )
                    log(
                        f"[{symbol}] 최근 평균 절대 변화율: {avg_abs_change_pct:.4f}% "
                        f"(허용 {strategy.min_volatility_pct:.4f}% ~ "
                        f"{strategy.max_volatility_pct:.4f}%)"
                    )
                htf_bullish = True
                htf_bearish = True
                htf_ma_slope_pct = None
                if strategy.enable_higher_timeframe_filter:
                    log(
                        f"[{symbol}] 상위 타임프레임({strategy.higher_timeframe}) 추세 확인 중..."
                    )
                    htf_ohlcv = fetch_ohlcv(
                        exchange,
                        symbol,
                        timeframe=strategy.higher_timeframe,
                        limit=strategy.higher_timeframe_ma_period + 5,
                        market_data_provider=market_data_provider,
                    )
                    htf_closes = [c[4] for c in htf_ohlcv]
                    htf_last_close = htf_closes[-1]
                    htf_last_ma = calc_sma(
                        htf_closes, strategy.higher_timeframe_ma_period
                    )
                    htf_ma_series = [
                        calc_sma(
                            htf_closes[: idx + 1],
                            strategy.higher_timeframe_ma_period,
                        )
                        for idx in range(strategy.higher_timeframe_ma_period - 1, len(htf_closes))
                    ]
                    htf_bullish = htf_last_close > htf_last_ma
                    htf_bearish = htf_last_close < htf_last_ma
                    htf_ma_slope_pct = calc_pct_slope(
                        htf_ma_series,
                        strategy.trend_slope_lookback,
                    )
                    log(
                        f"[{symbol}] 상위 타임프레임 종가: {htf_last_close:.0f}, "
                        f"상위 MA: {htf_last_ma:.0f}, "
                        f"상승추세={htf_bullish}, 하락추세={htf_bearish}"
                    )

                log("잔고 조회 중...")
                base_free, quote_free = get_spot_balances(
                    exchange,
                    base,
                    quote,
                    market_data_provider=market_data_provider,
                )
                log(f"현물 잔고 - {base}: {base_free}, {quote}: {quote_free}")
                best_bid = None
                if base_free > 0 and market_data_provider is not None:
                    best_bid = market_data_provider.get_best_bid(symbol)
                if best_bid is None and should_refresh_best_bid(
                    base_free=base_free,
                    last_close=last_close,
                    min_order_value=strategy.min_buy_order_value,
                    refresh_buffer_pct=config["best_bid_refresh_buffer_pct"],
                ):
                    best_bid = fetch_best_bid(exchange, symbol)
                sell_price_reference = best_bid if best_bid and best_bid > 0 else last_close

                position_quote_value = base_free * last_close
                # 업비트는 최소 주문 금액 기준이므로 현재 평가금액이 기준보다 작으면 먼지잔고로 본다.
                has_position = position_quote_value >= strategy.min_buy_order_value
                low_energy_snapshot = load_low_energy_snapshot(
                    exchange_name="upbit",
                    managed_symbols=load_managed_symbols("upbit"),
                )
                low_energy_guard_active = low_energy_snapshot.active and not has_position
                latest_symbol_record = load_latest_symbol_record(exchange_name="upbit", symbol=symbol)
                symbol_regime_snapshot = classify_symbol_regime(latest_symbol_record)
                orderbook_pressure_score = safe_optional_float(
                    latest_symbol_record.get("orderbook_pressure_score")
                    if latest_symbol_record
                    else None
                )
                symbol_regime = symbol_regime_snapshot.regime
                regime_route = route_alt_strategy(symbol_regime)
                regime_policy = regime_route.policy
                strategy_key = regime_route.strategy_key
                symbol_regime_blocks_entry = (
                    not has_position and regime_policy.pause_new_entry
                )
                symbol_regime_requires_strong_signal = regime_policy.require_strong_signal
                symbol_regime_requires_fresh_cross = regime_policy.require_fresh_cross
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
                if low_energy_guard_active:
                    log(
                        f"[{symbol}] 저에너지 장 감지: 평균 거래량 배수 {low_energy_snapshot.avg_volume_ratio:.3f}, "
                        f"평균 절대 변화율 {low_energy_snapshot.avg_abs_change_pct:.4f}% 로 신규 진입을 보류합니다."
                    )
                if symbol_regime_blocks_entry:
                    log(f"[{symbol}] 심볼 레짐 {symbol_regime} 상태라 신규 진입을 보류합니다.")
                avg_entry_price = entry_price.get(symbol)
                if handle_unrecoverable_position(
                    warned_symbols=unrecoverable_position_warned,
                    symbol=symbol,
                    has_position=has_position,
                    average_entry_price=avg_entry_price,
                    log=log,
                    structured_logger=structured_logger,
                    context={
                        "base_free": base_free,
                        "quote_free": quote_free,
                        "position_quote_value": position_quote_value,
                    },
                    message="평균 진입가를 복구하지 못한 포지션을 감지해 자동 매매를 보류합니다.",
                ):
                    continue
                elif not has_position:
                    # 최소 주문 금액 미만 잔량은 신규 포지션으로 다시 진입할 수 있도록 내부 상태를 비운다.
                    if (
                        symbol in entry_price
                        or symbol in entry_count
                        or symbol in entry_opened_at
                    ):
                        entry_price.pop(symbol, None)
                        entry_count.pop(symbol, None)
                        entry_opened_at.pop(symbol, None)
                        highest_price_since_entry.pop(symbol, None)
                        lowest_price_since_entry.pop(symbol, None)
                        partial_take_profit_done.pop(symbol, None)
                        partial_stop_loss_done.pop(symbol, None)
                        unrecoverable_position_warned.discard(symbol)
                        log(
                            f"[{symbol}] 최소 주문 금액 미만 잔량은 포지션에서 제외하고 재진입 가능 상태로 초기화합니다."
                        )

                current_entry_count = entry_count.get(symbol, 0)
                last_trade_ts = last_trade_at.get(symbol, 0.0)
                seconds_since_last_trade = time.time() - last_trade_ts
                in_cooldown = (
                    seconds_since_last_trade < strategy.min_trade_interval_sec
                )
                last_stop_loss_ts = last_stop_loss_at.get(symbol, 0.0)
                seconds_since_last_stop_loss = (
                    time.time() - last_stop_loss_ts if last_stop_loss_ts > 0 else float("inf")
                )
                partial_take_profit_last_ts = partial_take_profit_last_at.get(symbol, 0.0)
                partial_take_profit_cooldown_remaining = max(
                    0.0,
                    strategy.partial_take_profit_reentry_cooldown_sec
                    - (time.time() - partial_take_profit_last_ts),
                ) if partial_take_profit_last_ts > 0 else 0.0
                partial_take_profit_cooldown_active = (
                    partial_take_profit_cooldown_remaining > 0
                )

                if in_cooldown:
                    remain_sec = int(
                        strategy.min_trade_interval_sec - seconds_since_last_trade
                    )
                    log(
                        f"[{symbol}] 최근 거래 후 쿨다운 중입니다. 남은 시간: {remain_sec}초"
                    )
                if partial_take_profit_cooldown_active:
                    log(
                        f"[{symbol}] 부분 익절 후 재진입/추가매수 쿨다운 중입니다. "
                        f"남은 시간: {int(partial_take_profit_cooldown_remaining)}초"
                    )

                base_min_gap_pct = strategy.get_crossover_gap_pct(symbol)
                effective_signal_score_min = strategy.get_signal_score_min(symbol)
                noise_gap_multiplier = 1.0
                if strategy.enable_noise_ratio_adaptation and noise_ratio is not None:
                    noise_gap_multiplier = 1.0 + (
                        (noise_ratio - strategy.noise_ratio_baseline)
                        / max(strategy.noise_ratio_baseline, 1e-9)
                    ) * 0.5
                    noise_gap_multiplier = max(
                        strategy.noise_ratio_min_multiplier,
                        min(strategy.noise_ratio_max_multiplier, noise_gap_multiplier),
                    )
                # 노이즈가 큰 장은 진입 문턱을 높이고, 깔끔한 장은 문턱을 낮춰 진입 속도를 높인다.
                min_gap_pct = base_min_gap_pct * noise_gap_multiplier
                max_entry_gap_pct = strategy.get_max_entry_gap_pct(symbol)
                effective_max_entry_count = max(
                    0,
                    strategy.max_entry_count + regime_policy.max_entry_count_delta,
                )
                bb_upper, bb_mid, bb_lower = calc_bollinger_bands(
                    closes, period=strategy.bb_period, stddev_multiplier=strategy.bb_stddev
                )
                bb_width_pct = calc_bollinger_band_width_pct(
                    closes, period=strategy.bb_period, stddev_multiplier=strategy.bb_stddev
                )
                signal_state = compute_alt_signal_state(
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
                    signal_score_min=effective_signal_score_min,
                    symbol_regime=symbol_regime,
                    entry_mode=strategy.entry_mode,
                    bb_width_pct=bb_width_pct,
                    squeeze_max_bandwidth_pct=strategy.squeeze_max_bandwidth_pct,
                    bb_upper=bb_upper,
                    squeeze_min_volume_ratio=strategy.squeeze_min_volume_ratio,
                )
                if strategy_key in {"mean_reversion", "low_energy_probe"}:
                    signal_state = compute_bollinger_mean_reversion_state(
                        prev_close=prev_close,
                        last_close=last_close,
                        bb_lower=bb_lower,
                        bb_mid=bb_mid,
                        bb_upper=bb_upper,
                        bb_width_pct=bb_width_pct,
                        squeeze_max_bandwidth_pct=strategy.squeeze_max_bandwidth_pct,
                        rsi_value=rsi_value,
                        signal_score_min=effective_signal_score_min,
                        rsi_min=strategy.mean_reversion_rsi_min,
                        rsi_max=strategy.mean_reversion_rsi_max,
                        macd_histogram=macd_histogram,
                        prev_macd_histogram=prev_macd_histogram,
                        allow_negative_macd=strategy.mean_reversion_allow_negative_macd,
                        require_macd_recovering=strategy.mean_reversion_require_macd_recovering,
                        macd_recovery_epsilon=strategy.mean_reversion_macd_recovery_epsilon,
                        atr_percentile=atr_percentile,
                        max_atr_percentile=strategy.mean_reversion_max_atr_percentile,
                        range_position_pct=recent_range_context["range_position_pct"],
                        max_range_position_pct=strategy.mean_reversion_max_range_position_pct,
                        ma_slope_pct=ma_slope_pct,
                        price_slope_pct=price_slope_pct,
                        volume_ratio=volume_ratio,
                        distance_from_recent_low_pct=recent_range_context["distance_from_recent_low_pct"],
                        block_negative_slope_high_volume_atr=strategy.mean_reversion_block_negative_slope_high_volume_atr,
                        negative_slope_threshold_pct=strategy.mean_reversion_negative_slope_threshold_pct,
                        high_volume_ratio=strategy.mean_reversion_high_volume_ratio,
                        mid_atr_percentile=strategy.mean_reversion_mid_atr_percentile,
                        min_distance_from_low_pct=strategy.mean_reversion_min_distance_from_low_pct,
                        allow_lower_near_probe=strategy.enable_mean_reversion_lower_near_probe,
                        lower_near_max_distance_pct=strategy.mean_reversion_lower_near_max_distance_pct,
                        lower_near_min_headroom_pct=strategy.mean_reversion_lower_near_min_headroom_pct,
                        lower_near_min_signal_score=strategy.mean_reversion_lower_near_min_signal_score,
                        lower_near_position_scale=strategy.mean_reversion_lower_near_position_scale,
                        lower_near_extra_confirmation_loops=strategy.mean_reversion_lower_near_extra_confirmation_loops,
                    )
                bullish = bool(signal_state["bullish"])
                bearish = bool(signal_state["bearish"])
                gap_pct = float(signal_state["gap_pct"])
                gap_within_upper_bound = gap_pct <= max_entry_gap_pct
                signal_is_strong = bool(signal_state["signal_is_strong"])
                signal_score = float(signal_state["signal_score"])
                rsi_filter_passed = bool(signal_state["rsi_filter_passed"])
                macd_filter_passed = bool(signal_state["macd_filter_passed"])
                trend_follow_entry = bool(signal_state["trend_follow_entry"])
                entry_signal = bool(signal_state["entry_signal"])
                mean_reversion_falling_knife_blocked = bool(
                    signal_state.get("falling_knife_blocked", False)
                )
                mean_reversion_lower_reclaim_confirmed = bool(
                    signal_state.get("lower_reclaim_confirmed", bullish)
                )
                mean_reversion_lower_near_probe_allowed = bool(
                    signal_state.get("lower_near_probe_allowed", False)
                )
                mean_reversion_lower_near_extra_confirmation_loops = int(
                    signal_state.get("lower_near_extra_confirmation_loops", 0)
                )
                xrp_rebound_probe_state = resolve_xrp_rebound_probe_state(
                    enabled=strategy.enable_xrp_rebound_probe,
                    symbol=symbol,
                    eligible_symbols=strategy.xrp_rebound_probe_symbols,
                    strategy_key=strategy_key,
                    signal_score=signal_score,
                    min_signal_score=strategy.xrp_rebound_probe_min_signal_score,
                    htf_bearish=htf_bearish,
                    rsi_filter_passed=rsi_filter_passed,
                    macd_filter_passed=macd_filter_passed,
                    lower_reclaim_confirmed=mean_reversion_lower_reclaim_confirmed,
                    falling_knife_blocked=mean_reversion_falling_knife_blocked,
                    position_scale=strategy.xrp_rebound_probe_position_scale,
                    extra_confirmation_loops=strategy.xrp_rebound_probe_extra_confirmation_loops,
                    entry_signal=entry_signal,
                    signal_is_strong=signal_is_strong,
                    bullish=bullish,
                    mean_reversion_lower_near_probe_allowed=mean_reversion_lower_near_probe_allowed,
                    mean_reversion_lower_near_extra_confirmation_loops=mean_reversion_lower_near_extra_confirmation_loops,
                )
                xrp_rebound_probe_decision = xrp_rebound_probe_state.decision
                xrp_rebound_probe_allowed = xrp_rebound_probe_decision.allowed
                entry_signal = xrp_rebound_probe_state.entry_signal
                signal_is_strong = xrp_rebound_probe_state.signal_is_strong
                bullish = xrp_rebound_probe_state.bullish
                mean_reversion_lower_near_probe_allowed = (
                    xrp_rebound_probe_state.mean_reversion_lower_near_probe_allowed
                )
                mean_reversion_lower_near_extra_confirmation_loops = (
                    xrp_rebound_probe_state.mean_reversion_lower_near_extra_confirmation_loops
                )
                if xrp_rebound_probe_state.lower_near_suppressed:
                    signal_state["lower_near_probe_allowed"] = False
                    signal_state["lower_near_extra_confirmation_loops"] = 0
                    signal_state["lower_near_probe_reason"] = (
                        xrp_rebound_probe_decision.reason
                    )
                low_energy_probe_decision = evaluate_low_energy_probe(
                    enabled=strategy.enable_low_energy_probe,
                    low_energy_guard_active=low_energy_guard_active,
                    signal_score=signal_score,
                    min_signal_score=strategy.low_energy_probe_min_signal_score,
                    htf_bullish=htf_bullish,
                    require_htf_bullish=strategy.low_energy_probe_require_htf_bullish,
                    volume_ratio=volume_ratio,
                    min_volume_ratio=strategy.low_energy_probe_min_volume_ratio,
                    orderbook_pressure_score=orderbook_pressure_score,
                    min_orderbook_pressure_score=strategy.low_energy_probe_min_orderbook_pressure_score,
                    atr_percentile=atr_percentile,
                    max_atr_percentile=strategy.low_energy_probe_max_atr_percentile,
                    falling_knife_blocked=mean_reversion_falling_knife_blocked,
                    position_scale=strategy.low_energy_probe_position_scale,
                    extra_confirmation_loops=strategy.low_energy_probe_extra_confirmation_loops,
                )
                sol_probe_entry_state = resolve_sol_probe_entry_state(
                    enabled=strategy.enable_sol_probe,
                    symbol=symbol,
                    eligible_symbols=strategy.sol_probe_symbols,
                    signal_score=signal_score,
                    min_signal_score=strategy.sol_probe_min_signal_score,
                    has_position=has_position,
                    current_entry_count=current_entry_count,
                    position_scale=strategy.sol_probe_position_scale,
                    entry_signal=entry_signal,
                    signal_is_strong=signal_is_strong,
                    max_entry_count=effective_max_entry_count,
                    low_energy_guard_active=low_energy_guard_active,
                    low_energy_probe_allowed=low_energy_probe_decision.allowed,
                    symbol_regime_blocks_entry=symbol_regime_blocks_entry,
                    mean_reversion_lower_near_probe_allowed=mean_reversion_lower_near_probe_allowed,
                )
                sol_probe_entry_decision = sol_probe_entry_state.decision
                sol_probe_entry_allowed = sol_probe_entry_decision.allowed
                entry_signal = sol_probe_entry_state.entry_signal
                signal_is_strong = sol_probe_entry_state.signal_is_strong
                effective_max_entry_count = sol_probe_entry_state.max_entry_count
                effective_low_energy_guard_active = sol_probe_entry_state.low_energy_guard_active
                effective_symbol_regime_blocks_entry = (
                    sol_probe_entry_state.symbol_regime_blocks_entry
                )
                if sol_probe_entry_allowed:
                    log(
                        format_sol_probe_entry_log(
                            symbol=symbol,
                            signal_score=signal_score,
                            position_scale=sol_probe_entry_decision.position_scale,
                        )
                    )
                if low_energy_probe_decision.allowed:
                    log(
                        f"[{symbol}] LOW_ENERGY 이지만 고품질 소액 probe 후보로 전환합니다. "
                        f"signal={signal_score:.1f}, volume={0.0 if volume_ratio is None else volume_ratio:.3f}, "
                        f"position_scale={low_energy_probe_decision.position_scale:.2f}x"
                    )
                if xrp_rebound_probe_allowed:
                    log(
                        f"[{symbol}] XRP 고점수 반등 probe 후보로 전환합니다. "
                        f"signal={signal_score:.1f}, htf_bearish={htf_bearish}, "
                        f"position_scale={xrp_rebound_probe_decision.position_scale:.2f}x"
                    )
                entry_probe_score_override_allowed = (
                    mean_reversion_lower_near_probe_allowed
                    or low_energy_probe_decision.allowed
                    or sol_probe_entry_allowed
                    or xrp_rebound_probe_allowed
                )
                overheated_entry_blocked = is_overheated_entry_risk(
                    volume_ratio=volume_ratio,
                    atr_percentile=atr_percentile,
                    rsi_value=rsi_value,
                    volume_ratio_threshold=strategy.overheat_guard_volume_ratio,
                    atr_percentile_threshold=strategy.overheat_guard_atr_percentile,
                    rsi_threshold=strategy.overheat_guard_rsi,
                )
                overheat_extra_confirmation_required = requires_overheat_confirmation(
                    signal_is_strong=signal_is_strong,
                    range_position_pct=recent_range_context["range_position_pct"],
                    distance_from_recent_high_pct=recent_range_context["distance_from_recent_high_pct"],
                    range_position_threshold=strategy.overheat_extra_confirmation_range_position_pct,
                    distance_from_high_threshold_pct=strategy.overheat_extra_confirmation_distance_from_high_pct,
                )
                # 알트가 BTC와 너무 같은 방향으로 움직이는 구간은 포트폴리오 중복 노출을 줄이기 위해 진입을 막는다.
                correlation_with_btc = (
                    calc_return_correlation(
                        closes,
                        btc_reference_closes,
                        lookback=strategy.correlation_lookback,
                    )
                    if strategy.enable_correlation_filter and btc_reference_closes
                    else None
                )
                correlation_entry_blocked = (
                    entry_signal
                    and strategy.enable_correlation_filter
                    and not strategy.enable_combined_stop_loss_guards
                    and not has_position
                    and btc_reference_above_ma
                    and correlation_with_btc is not None
                    and correlation_with_btc >= strategy.max_correlation_with_btc
                )
                # 최근 체결비율이 낮았던 심볼은 주문 품질이 회복될 때까지 잠시 쉬게 만든다.
                fill_quality_snapshot = (
                    execution_quality_guard.get_fill_quality_snapshot(
                        exchange_name="UPBIT",
                        symbol=symbol,
                        since_seconds=strategy.fill_quality_lookback_sec,
                        min_fill_ratio=strategy.fill_quality_min_fill_ratio,
                        min_sample_count=strategy.fill_quality_min_sample_count,
                    )
                    if strategy.enable_fill_quality_guard
                    else FillQualitySnapshot(
                        active=False,
                        avg_fill_ratio=None,
                        sample_count=0,
                        latest_recorded_at=None,
                        reason="disabled",
                    )
                )
                fill_quality_entry_blocked = (
                    entry_signal and not has_position and fill_quality_snapshot.active
                )
                btc_correlation_volatility_blocked = (
                    entry_signal
                    and not has_position
                    and strategy.enable_combined_stop_loss_guards
                    and is_btc_regime_correlation_volatility_risk(
                        btc_regime=btc_reference_regime,
                        correlation_with_btc=correlation_with_btc,
                        alt_atr_percentile=atr_percentile,
                        risky_btc_regimes=strategy.btc_correlation_volatility_risky_regimes,
                        min_correlation=strategy.btc_correlation_volatility_min_corr,
                        min_alt_atr_percentile=strategy.btc_correlation_volatility_min_atr_percentile,
                    )
                )
                volume_atr_execution_blocked = (
                    entry_signal
                    and not has_position
                    and strategy.enable_combined_stop_loss_guards
                    and is_volume_atr_execution_weak_risk(
                        volume_ratio=volume_ratio,
                        atr_percentile=atr_percentile,
                        fill_quality_avg_fill_ratio=fill_quality_snapshot.avg_fill_ratio,
                        fill_quality_sample_count=fill_quality_snapshot.sample_count,
                        orderbook_pressure_score=orderbook_pressure_score,
                        volume_ratio_threshold=strategy.volume_atr_execution_guard_volume_ratio,
                        atr_percentile_threshold=strategy.volume_atr_execution_guard_atr_percentile,
                        min_fill_ratio=strategy.volume_atr_execution_min_fill_ratio,
                        min_fill_sample_count=strategy.volume_atr_execution_min_fill_samples,
                        min_orderbook_pressure_score=strategy.volume_atr_execution_min_orderbook_pressure_score,
                    )
                )
                low_energy_top_chase_actual = {
                    "btc_reference_regime": btc_reference_regime,
                    "btc_reference_atr_pct": btc_reference_atr_pct,
                    "range_position_pct": recent_range_context["range_position_pct"],
                    "distance_from_recent_high_pct": recent_range_context["distance_from_recent_high_pct"],
                }
                low_energy_top_chase_required = {
                    "risky_btc_regimes": strategy.low_energy_top_chase_risky_btc_regimes,
                    "max_btc_atr_pct": strategy.low_energy_top_chase_max_btc_atr_pct,
                    "range_position_pct": strategy.low_energy_top_chase_range_position_pct,
                    "distance_from_high_pct": strategy.low_energy_top_chase_distance_from_high_pct,
                }
                low_energy_top_chase_entry_blocked = (
                    entry_signal
                    and not has_position
                    and is_low_energy_top_chase_entry_risk(
                        enabled=strategy.enable_low_energy_top_chase_guard,
                        btc_regime=btc_reference_regime,
                        btc_atr_pct=btc_reference_atr_pct,
                        range_position_pct=recent_range_context["range_position_pct"],
                        distance_from_recent_high_pct=recent_range_context["distance_from_recent_high_pct"],
                        risky_btc_regimes=strategy.low_energy_top_chase_risky_btc_regimes,
                        max_btc_atr_pct=strategy.low_energy_top_chase_max_btc_atr_pct,
                        range_position_threshold=strategy.low_energy_top_chase_range_position_pct,
                        distance_from_high_threshold_pct=strategy.low_energy_top_chase_distance_from_high_pct,
                    )
                )
                if low_energy_top_chase_entry_blocked:
                    log(
                        f"[{symbol}] BTC 저에너지/저ATR 구간에서 최근 고점권 추격 위험이 커 신규 진입을 차단합니다 "
                        f"(BTC regime {btc_reference_regime}, BTC ATR {0.0 if btc_reference_atr_pct is None else btc_reference_atr_pct:.4f}%, "
                        f"range {0.0 if recent_range_context['range_position_pct'] is None else recent_range_context['range_position_pct']:.2f}%, "
                        f"고점 거리 {0.0 if recent_range_context['distance_from_recent_high_pct'] is None else recent_range_context['distance_from_recent_high_pct']:.4f}%)."
                    )
                current_entry_risk_context = {
                    "strategy_key": strategy_key,
                    "symbol_regime": symbol_regime,
                    "btc_reference_regime": btc_reference_regime,
                    "low_energy_top_chase": low_energy_top_chase_entry_blocked,
                    "high_atr": (
                        atr_percentile is not None
                        and atr_percentile >= strategy.volume_atr_execution_guard_atr_percentile
                    ),
                    "high_volume": (
                        volume_ratio is not None
                        and volume_ratio >= strategy.volume_atr_execution_guard_volume_ratio
                    ),
                    "range_top_risk": overheat_extra_confirmation_required,
                    "high_btc_correlation": (
                        correlation_with_btc is not None
                        and correlation_with_btc >= strategy.btc_correlation_volatility_min_corr
                    ),
                }
                stop_loss_pattern_gate = compute_alt_stop_loss_reentry_gate(
                    enabled=(
                        strategy.enable_stop_loss_pattern_reentry
                        and last_stop_loss_ts > 0
                        and not has_position
                    ),
                    elapsed_since_stop_loss_sec=seconds_since_last_stop_loss,
                    min_cooldown_sec=strategy.stop_loss_pattern_min_cooldown_sec,
                    entry_signal=entry_signal,
                    bullish=bullish,
                    signal_score=signal_score,
                    min_signal_score=strategy.stop_loss_pattern_min_signal_score,
                    volume_ratio=volume_ratio,
                    min_volume_ratio=effective_min_volume_ratio,
                    min_volume_ratio_multiplier=strategy.stop_loss_pattern_min_volume_ratio_multiplier,
                    htf_bullish=htf_bullish,
                    require_htf_bullish=strategy.stop_loss_pattern_require_htf_bullish,
                    require_fresh_cross=strategy.stop_loss_pattern_require_fresh_cross,
                )
                stop_loss_pattern_blocked = bool(
                    stop_loss_pattern_gate["enabled"]
                    and not stop_loss_pattern_gate["pattern_ready"]
                )
                stop_loss_context_reentry_blocked = (
                    entry_signal
                    and not has_position
                    and strategy.enable_combined_stop_loss_guards
                    and is_stop_loss_context_reentry_risk(
                        elapsed_since_stop_loss_sec=seconds_since_last_stop_loss,
                        cooldown_sec=strategy.stop_loss_context_reentry_cooldown_sec,
                        current_context=current_entry_risk_context,
                        previous_context=last_stop_loss_context.get(symbol),
                        min_similarity_count=strategy.stop_loss_context_min_similarity_count,
                    )
                )
                volume_spike_entry_downgrade = evaluate_volume_spike_entry_downgrade(
                    enabled=strategy.enable_volume_spike_entry_downgrade,
                    symbol=symbol,
                    eligible_symbols=strategy.volume_spike_entry_downgrade_symbols,
                    volume_ratio=volume_ratio,
                    max_volume_ratio=effective_max_volume_ratio,
                    hard_max_volume_ratio=strategy.volume_spike_entry_hard_max_volume_ratio,
                    signal_score=signal_score,
                    min_signal_score=strategy.volume_spike_entry_min_signal_score,
                    htf_bullish=htf_bullish,
                    require_htf_bullish=strategy.volume_spike_entry_require_htf_bullish,
                    orderbook_pressure_score=orderbook_pressure_score,
                    min_orderbook_pressure_score=strategy.volume_spike_entry_min_orderbook_pressure_score,
                    atr_percentile=atr_percentile,
                    max_atr_percentile=strategy.volume_spike_entry_max_atr_percentile,
                    position_scale=strategy.volume_spike_entry_position_scale,
                    extra_confirmation_loops=strategy.volume_spike_entry_extra_confirmation_loops,
                )
                volume_cap_allows_entry = (
                    volume_within_upper_bound or volume_spike_entry_downgrade.allowed
                )
                raw_entry_candidate = False
                if strategy_key == "skip":
                    raw_entry_candidate = False
                elif strategy_key == "breakout":
                    raw_entry_candidate = (
                        entry_signal
                        and (bullish or sol_probe_entry_allowed or xrp_rebound_probe_allowed)
                        and not effective_symbol_regime_blocks_entry
                        and not effective_low_energy_guard_active
                        and not correlation_entry_blocked
                        and not fill_quality_entry_blocked
                        and not stop_loss_pattern_blocked
                        and not stop_loss_context_reentry_blocked
                        and not overheated_entry_blocked
                        and not btc_correlation_volatility_blocked
                        and not volume_atr_execution_blocked
                        and not low_energy_top_chase_entry_blocked
                        and gap_within_upper_bound
                        and volume_cap_allows_entry
                        and (
                            not symbol_regime_requires_fresh_cross
                            or bullish
                            or sol_probe_entry_allowed
                            or xrp_rebound_probe_allowed
                        )
                    )
                else:
                    raw_entry_candidate = (
                        entry_signal
                        and not effective_symbol_regime_blocks_entry
                        and not effective_low_energy_guard_active
                        and not correlation_entry_blocked
                        and not fill_quality_entry_blocked
                        and not stop_loss_pattern_blocked
                        and not stop_loss_context_reentry_blocked
                        and not overheated_entry_blocked
                        and not btc_correlation_volatility_blocked
                        and not volume_atr_execution_blocked
                        and not low_energy_top_chase_entry_blocked
                        and gap_within_upper_bound
                        and volume_cap_allows_entry
                        and (
                            not symbol_regime_requires_fresh_cross
                            or bullish
                            or sol_probe_entry_allowed
                            or xrp_rebound_probe_allowed
                        )
                    )
                # 단발 신호에 바로 진입하지 않고 같은 방향 확인이 누적될 때만 READY 로 승격한다.
                if mean_reversion_lower_near_probe_allowed:
                    log(
                        f"[{symbol}] mean_reversion 하단 reclaim 전이지만 하단 근접 소액 probe 후보로 전환합니다. "
                        f"bb_lower_distance={float(signal_state.get('bb_lower_distance_pct', 0.0)):.4f}%, "
                        f"headroom={gap_pct:.4f}%, position_scale={strategy.mean_reversion_lower_near_position_scale:.2f}x"
                    )
                entry_timing_snapshot = update_entry_timing_state(
                    state_store=entry_timing_state,
                    symbol=symbol,
                    has_position=has_position,
                    candidate_active=raw_entry_candidate,
                    required_confirmations=(
                        strategy.entry_confirmation_loops
                        + (
                            strategy.overheat_extra_confirmation_loops
                            if overheat_extra_confirmation_required
                            else 0
                        )
                        + (
                            strategy.stop_loss_context_extra_confirmation_loops
                            if stop_loss_context_reentry_blocked
                            else 0
                        )
                        + volume_spike_entry_downgrade.extra_confirmation_loops
                        + low_energy_probe_decision.extra_confirmation_loops
                        + mean_reversion_lower_near_extra_confirmation_loops
                        + xrp_rebound_probe_decision.extra_confirmation_loops
                    ),
                )
                log(f"[{symbol}] 적용 이격도 기준: {min_gap_pct:.4f}%")
                log(f"[{symbol}] 적용 최대 이격도 상한: {max_entry_gap_pct:.4f}%")
                if noise_ratio is not None:
                    log(
                        f"[{symbol}] 노이즈 비율: {noise_ratio:.4f} "
                        f"(기본 이격도 {base_min_gap_pct:.4f}% -> 동적 이격도 {min_gap_pct:.4f}%)"
                    )
                log(
                    f"[{symbol}] RSI: {rsi_value:.2f} | MACD 히스토그램: "
                    f"{0.0 if macd_histogram is None else macd_histogram:.6f} | "
                    f"MA 기울기: {0.0 if ma_slope_pct is None else ma_slope_pct:.4f}% | "
                    f"가격 기울기: {0.0 if price_slope_pct is None else price_slope_pct:.4f}% | "
                    f"신호 스코어: {signal_score:.1f}"
                )
                log(
                    f"[{symbol}] 최근 range 위치: "
                    f"{0.0 if recent_range_context['range_position_pct'] is None else recent_range_context['range_position_pct']:.2f}% | "
                    f"고점 거리: {0.0 if recent_range_context['distance_from_recent_high_pct'] is None else recent_range_context['distance_from_recent_high_pct']:.4f}% | "
                    f"ATR percentile: {0.0 if atr_percentile is None else atr_percentile:.1f}"
                )
                if mean_reversion_falling_knife_blocked:
                    log(
                        f"[{symbol}] mean_reversion 하단 복귀가 나왔지만 음수 slope+고거래량+중고ATR+저점 근접 조합이라 신규 진입을 차단합니다 "
                        f"(MA slope {0.0 if ma_slope_pct is None else ma_slope_pct:.4f}%, "
                        f"price slope {0.0 if price_slope_pct is None else price_slope_pct:.4f}%, "
                        f"volume {0.0 if volume_ratio is None else volume_ratio:.2f}, "
                        f"ATR percentile {0.0 if atr_percentile is None else atr_percentile:.1f}, "
                        f"저점 거리 {0.0 if recent_range_context['distance_from_recent_low_pct'] is None else recent_range_context['distance_from_recent_low_pct']:.4f}%)."
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
                        f"confirmation {strategy.overheat_extra_confirmation_loops}회를 추가합니다."
                    )
                if volume_spike_entry_downgrade.allowed:
                    log(
                        f"[{symbol}] 거래량 상한 초과지만 손절방지 조건을 충족해 소액 진입 후보로 낮춥니다 "
                        f"(volume {0.0 if volume_ratio is None else volume_ratio:.2f}, "
                        f"score {signal_score:.1f}, ATR percentile {0.0 if atr_percentile is None else atr_percentile:.1f}, "
                        f"orderbook pressure {0.0 if orderbook_pressure_score is None else orderbook_pressure_score:.1f}, "
                        f"비중 {volume_spike_entry_downgrade.position_scale:.2f}x, "
                        f"추가 confirmation {volume_spike_entry_downgrade.extra_confirmation_loops}회)."
                    )
                if btc_correlation_volatility_blocked:
                    log(
                        f"[{symbol}] BTC 위험 레짐({btc_reference_regime})에서 BTC 상관계수 "
                        f"{0.0 if correlation_with_btc is None else correlation_with_btc:.3f}, "
                        f"ALT ATR percentile {0.0 if atr_percentile is None else atr_percentile:.1f} 조합으로 신규 진입을 차단합니다."
                    )
                if volume_atr_execution_blocked:
                    log(
                        f"[{symbol}] 거래량+ATR 확장 중 체결/호가 우위가 약해 신규 진입을 차단합니다 "
                        f"(volume {0.0 if volume_ratio is None else volume_ratio:.2f}, "
                        f"ATR percentile {0.0 if atr_percentile is None else atr_percentile:.1f}, "
                        f"fill {0.0 if fill_quality_snapshot.avg_fill_ratio is None else fill_quality_snapshot.avg_fill_ratio * 100:.1f}%, "
                        f"orderbook pressure {0.0 if orderbook_pressure_score is None else orderbook_pressure_score:.1f})."
                    )
                if stop_loss_context_reentry_blocked:
                    log(
                        f"[{symbol}] 최근 손절과 유사한 조건이 {strategy.stop_loss_context_reentry_cooldown_sec}초 "
                        f"쿨다운 안에 반복되어 재진입을 차단합니다."
                    )
                bb_width_text = "N/A" if bb_width_pct is None else f"{bb_width_pct:.2f}%"
                log(
                    f"[{symbol}] 진입 모드: {strategy.entry_mode.upper()} "
                    f"(BB Width: {bb_width_text}, 기준 {strategy.squeeze_max_bandwidth_pct:.2f}%)"
                )
                log(f"[{symbol}] 레짐 라우터 선택 전략: {strategy_key}")
                log(
                    f"[{symbol}] 진입 상태 머신: {entry_timing_snapshot.phase} "
                    f"({entry_timing_snapshot.confirmation_count}/"
                    f"{entry_timing_snapshot.required_confirmations})"
                )
                if correlation_with_btc is not None:
                    log(
                        f"[{symbol}] BTC 상관계수: {correlation_with_btc:.3f} "
                        f"(차단 기준 {strategy.max_correlation_with_btc:.3f}, BTC 상단추세={btc_reference_above_ma})"
                    )
                if fill_quality_snapshot.avg_fill_ratio is not None:
                    log(
                        f"[{symbol}] 최근 체결비율: {fill_quality_snapshot.avg_fill_ratio * 100:.1f}% "
                        f"(표본 {fill_quality_snapshot.sample_count}, 차단 기준 {strategy.fill_quality_min_fill_ratio * 100:.1f}%)"
                    )
                if (
                    (entry_signal or bearish)
                    and not signal_is_strong
                    and not entry_probe_score_override_allowed
                ):
                    log(
                        f"[{symbol}] 신호 점수 {signal_score:.1f} 가 기준 {effective_signal_score_min:.1f} 미만이라 이번 신호는 건너뜁니다."
                    )
                if entry_signal and not rsi_filter_passed:
                    log(
                        f"[{symbol}] RSI {0.0 if rsi_value is None else rsi_value:.2f} 가 "
                        f"허용 구간 {strategy.rsi_entry_min:.1f}~{strategy.rsi_entry_max:.1f} 밖이라 매수를 보류합니다."
                    )
                if entry_signal and not macd_filter_passed:
                    log(
                        f"[{symbol}] MACD 히스토그램이 양수가 아니어서 매수를 보류합니다."
                    )
                if correlation_entry_blocked:
                    log(
                        f"[{symbol}] BTC 와 상관계수 {correlation_with_btc:.3f} 가 높고 BTC 도 상단 추세라 신규 매수를 보류합니다."
                    )
                if fill_quality_entry_blocked:
                    log(
                        f"[{symbol}] 최근 체결비율 {fill_quality_snapshot.avg_fill_ratio * 100:.1f}% 로 낮아 "
                        f"다음 {strategy.fill_quality_lookback_sec // 60}분 동안 신규 매수를 보류합니다."
                    )
                if stop_loss_pattern_blocked:
                    log(
                        f"[{symbol}] 손절 후 패턴 재진입 대기 중입니다. "
                        f"경과 {int(seconds_since_last_stop_loss)}초 / 최소 {strategy.stop_loss_pattern_min_cooldown_sec}초, "
                        f"신호 점수 {signal_score:.1f}/{strategy.stop_loss_pattern_min_signal_score:.1f}, "
                        f"거래량 {0.0 if volume_ratio is None else volume_ratio:.4f}/"
                        f"{float(stop_loss_pattern_gate['required_min_volume_ratio']):.4f}, "
                        f"HTF 상승={htf_bullish}, fresh_cross={bullish}"
                    )
                if raw_entry_candidate and not entry_timing_snapshot.ready:
                    log(
                        f"[{symbol}] 진입 후보 신호를 누적 확인 중입니다. "
                        f"{entry_timing_snapshot.confirmation_count}/{entry_timing_snapshot.required_confirmations}"
                    )
                if trend_follow_entry and not bullish:
                    log(
                        f"[{symbol}] 신규 골든크로스는 아니지만 MA 상단 유지 추세 조건으로 진입 후보를 허용합니다."
                    )

                if (
                    strategy.enable_higher_timeframe_filter
                    and entry_signal
                    and not htf_bullish
                ):
                    log(
                        f"[{symbol}] 상위 타임프레임 상승 추세가 아니어서 매수를 보류합니다."
                    )
                if (
                    strategy.enable_higher_timeframe_filter
                    and bearish
                    and not htf_bearish
                ):
                    log(
                        f"[{symbol}] 상위 타임프레임 하락 추세가 아니어서 일반 매도를 보류합니다."
                    )
                if entry_signal and strategy.enable_volume_filter and not volume_filter_passed:
                    log(
                        f"[{symbol}] 거래량이 부족하여 신규 매수를 보류합니다."
                    )
                if (
                    entry_signal
                    and strategy.enable_volume_filter
                    and not volume_within_upper_bound
                    and not volume_spike_entry_downgrade.allowed
                ):
                    log(
                        f"[{symbol}] 거래량이 과도하게 급증해 추격 위험이 커 신규 매수를 보류합니다."
                    )
                if entry_signal and not gap_within_upper_bound:
                    log(
                        f"[{symbol}] 이격도가 너무 커 과열 돌파로 판단해 신규 매수를 보류합니다."
                    )
                htf_bearish_entry_blocked = (
                    entry_signal
                    and strategy.blocks_entry_when_htf_bearish(symbol)
                    and htf_bearish
                )
                if htf_bearish_entry_blocked:
                    log(
                        f"[{symbol}] 상위 타임프레임 하락 추세가 유지 중이라 신규 매수를 보류합니다."
                    )
                if entry_signal and strategy.enable_volatility_filter and not volatility_filter_passed:
                    log(
                        f"[{symbol}] 변동성이 기준 범위를 벗어나 신규 매수를 보류합니다."
                    )

                can_average_down = compute_can_average_down(
                    has_position=has_position,
                    average_entry_price=avg_entry_price,
                    last_close=last_close,
                    averaging_down_gap_pct=strategy.averaging_down_gap_pct,
                )
                if entry_signal and has_position and not can_average_down:
                    log(
                        f"[{symbol}] 추가 매수 조건 미충족: 현재가가 평균 진입가보다 "
                        f"{strategy.averaging_down_gap_pct}% 이상 낮지 않습니다."
                    )

                position_runtime_metrics = build_empty_position_runtime_metrics()
                pnl_pct = position_runtime_metrics["pnl_pct"]
                mfe_pct = position_runtime_metrics["mfe_pct"]
                mae_pct = position_runtime_metrics["mae_pct"]
                current_net_realized_pnl_quote = position_runtime_metrics["current_net_realized_pnl_quote"]
                current_net_realized_pnl_pct = position_runtime_metrics["current_net_realized_pnl_pct"]
                if has_position and avg_entry_price:
                    position_metrics = compute_alt_position_metrics(
                        has_position=has_position,
                        average_entry_price=avg_entry_price,
                        last_close=last_close,
                        base_free=base_free,
                        fee_rate_pct=config["fee_rate_pct"],
                        highest_price_since_entry=highest_price_since_entry.get(symbol),
                        lowest_price_since_entry=lowest_price_since_entry.get(symbol),
                    )
                    highest_price_since_entry[symbol] = position_metrics["highest_price_since_entry"]
                    lowest_price_since_entry[symbol] = position_metrics["lowest_price_since_entry"]
                    pnl_pct = position_metrics["pnl_pct"]
                    mfe_pct = position_metrics["mfe_pct"]
                    mae_pct = position_metrics["mae_pct"]
                    current_net_realized_pnl_quote = position_metrics["net_pnl_quote"]
                    current_net_realized_pnl_pct = position_metrics["net_pnl_pct"]
                    log(f"[{symbol}] 평균 진입가 대비 현재 수익률: {pnl_pct:.2f}%")
                elif not has_position:
                    highest_price_since_entry.pop(symbol, None)
                    lowest_price_since_entry.pop(symbol, None)
                    alt_profit_trailing_armed.pop(symbol, None)

                fee_round_trip_pct = config["fee_rate_pct"] * 2
                sol_probe_exit_state = resolve_sol_probe_exit_state(
                    enabled=strategy.enable_sol_probe,
                    symbol=symbol,
                    eligible_symbols=strategy.sol_probe_symbols,
                    has_position=has_position,
                    opened_at=entry_opened_at.get(symbol),
                    now_ts=time.time(),
                    max_hold_minutes=strategy.sol_probe_max_hold_minutes,
                    base_take_profit_pct=strategy.get_take_profit_pct(symbol),
                    base_stop_loss_pct=strategy.get_stop_loss_pct(symbol),
                    stop_loss_multiplier=regime_policy.stop_loss_multiplier,
                    take_profit_bonus_pct=regime_policy.take_profit_bonus_pct,
                    fee_round_trip_pct=fee_round_trip_pct,
                    sol_probe_take_profit_pct=strategy.sol_probe_take_profit_pct,
                    sol_probe_stop_loss_pct=strategy.sol_probe_stop_loss_pct,
                )
                take_profit_pct = sol_probe_exit_state.take_profit_pct
                stop_loss_pct = sol_probe_exit_state.stop_loss_pct
                fee_protect_min_net_pnl_pct = strategy.get_fee_protect_min_net_pnl_pct(symbol)
                break_even_guard_min_mfe_pct = strategy.get_break_even_guard_min_mfe_pct(symbol)
                break_even_guard_floor_net_pnl_pct = (
                    strategy.get_break_even_guard_floor_net_pnl_pct(symbol)
                )
                break_even_guard_max_profit_retrace_pct = (
                    strategy.break_even_guard_max_profit_retrace_pct
                )
                partial_exit_policy = resolve_alt_partial_exit_policy(
                    symbol=symbol,
                    partial_take_profit_enabled=strategy.uses_partial_take_profit(symbol),
                    partial_stop_loss_enabled=strategy.uses_partial_stop_loss(symbol),
                    partial_take_profit_done=partial_take_profit_done,
                    partial_stop_loss_done=partial_stop_loss_done,
                    partial_take_profit_ratio=strategy.partial_take_profit_ratio,
                    partial_take_profit_ratio_multiplier=(
                        regime_policy.partial_take_profit_ratio_multiplier
                    ),
                )
                partial_take_profit_pending = partial_exit_policy.partial_take_profit_pending
                partial_stop_loss_pending = partial_exit_policy.partial_stop_loss_pending
                effective_partial_take_profit_ratio = (
                    partial_exit_policy.effective_partial_take_profit_ratio
                )
                effective_min_take_profit_pct = (
                    sol_probe_exit_state.effective_take_profit_pct
                )
                sol_probe_time_exit_triggered = sol_probe_exit_state.time_exit_triggered
                if has_position:
                    log(
                        f"[{symbol}] 적용 익절률: {effective_min_take_profit_pct:.2f}% "
                        f"(전략값 {take_profit_pct:.2f}%, 레짐 보정 {regime_policy.take_profit_bonus_pct:.2f}%, "
                        f"왕복 수수료 {fee_round_trip_pct:.2f}%), "
                        f"적용 손절률: {stop_loss_pct:.2f}%"
                    )
                daily_loss_limit_reached = is_daily_loss_limit_reached(
                    daily_realized_pnl_quote=daily_realized_pnl_quote,
                    max_daily_loss_quote=config["max_daily_loss_quote"],
                )
                log(
                    f"[{symbol}] 오늘 누적 실현 손익: {daily_realized_pnl_quote:.2f} {quote}"
                )
                if daily_loss_limit_reached:
                    log(
                        f"[{symbol}] 일일 최대 손실 제한에 도달하여 신규 매수를 중단합니다."
                    )
                    if not daily_limit_notified:
                        notifier.notify_daily_loss_limit(
                            "UPBIT",
                            f"오늘 누적 실현 손익: {daily_realized_pnl_quote:.2f} {quote}\n"
                            f"손실 제한: -{config['max_daily_loss_quote']:.2f} {quote}",
                        )
                        daily_limit_notified = True
                if current_net_realized_pnl_pct is not None:
                    log(
                        f"[{symbol}] 수수료 반영 예상 순익률: {current_net_realized_pnl_pct:.2f}% "
                        f"(보호 익절 기준 {fee_protect_min_net_pnl_pct:.2f}%)"
                    )
                alt_exit_state = compute_alt_exit_decisions(
                    has_position=has_position,
                    pnl_pct=pnl_pct,
                    mfe_pct=mfe_pct,
                    current_net_realized_pnl_pct=current_net_realized_pnl_pct,
                    take_profit_pct=take_profit_pct,
                    stop_loss_pct=stop_loss_pct,
                    fee_rate_pct=config["fee_rate_pct"],
                    enable_fee_protect_exit=(
                        strategy.enable_fee_protect_exit
                        and not strategy.enable_alt_profit_trailing_exit
                    ),
                    fee_protect_min_net_pnl_pct=fee_protect_min_net_pnl_pct,
                    enable_break_even_guard=strategy.enable_break_even_guard,
                    break_even_guard_min_mfe_pct=break_even_guard_min_mfe_pct,
                    break_even_guard_floor_net_pnl_pct=break_even_guard_floor_net_pnl_pct,
                    break_even_guard_max_profit_retrace_pct=break_even_guard_max_profit_retrace_pct,
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
                profit_retrace_from_mfe_pct = alt_exit_state["profit_retrace_from_mfe_pct"]
                alt_profit_trailing_decision = resolve_alt_profit_trailing_exit(
                    has_position=has_position,
                    enabled=strategy.enable_alt_profit_trailing_exit,
                    trailing_armed=alt_profit_trailing_armed.get(symbol, False),
                    pnl_pct=pnl_pct,
                    mfe_pct=mfe_pct,
                    current_net_realized_pnl_pct=current_net_realized_pnl_pct,
                    arm_net_pnl_pct=strategy.alt_profit_trailing_arm_net_pnl_pct,
                    drawdown_pct=strategy.alt_profit_trailing_drawdown_pct,
                    floor_net_pnl_pct=strategy.alt_profit_trailing_floor_net_pnl_pct,
                    bearish=bearish,
                    stop_loss_triggered=stop_loss_triggered,
                )
                if alt_profit_trailing_decision.trailing_armed:
                    alt_profit_trailing_armed[symbol] = True
                else:
                    alt_profit_trailing_armed.pop(symbol, None)
                alt_profit_trailing_exit_triggered = (
                    alt_profit_trailing_decision.trailing_exit_triggered
                )
                if (
                    bearish
                    and has_position
                    and pnl_pct is not None
                    and not take_profit_ready
                    and not alt_profit_trailing_exit_triggered
                    and not profit_protect_triggered
                    and not break_even_guard_triggered
                    and not volume_spike_exit_triggered
                    and not stop_loss_triggered
                ):
                    log(
                        f"[{symbol}] 최소 익절률({effective_min_take_profit_pct}%) "
                        f"(전략값 {take_profit_pct}%, 왕복 수수료 {fee_round_trip_pct}%) "
                        f"미달로 매도를 보류합니다."
                    )
                if has_position and profit_protect_triggered:
                    log(
                        f"[{symbol}] 순익 보호 익절 조건 충족: 수수료 반영 순익률 "
                        f"{current_net_realized_pnl_pct:.2f}% >= {fee_protect_min_net_pnl_pct:.2f}%"
                    )
                if has_position and alt_profit_trailing_decision.trailing_armed_just_now:
                    log(
                        f"[{symbol}] 순익 trailing 모드 전환: 순익률 "
                        f"{0.0 if current_net_realized_pnl_pct is None else current_net_realized_pnl_pct:.2f}% >= "
                        f"{strategy.alt_profit_trailing_arm_net_pnl_pct:.2f}%"
                    )
                if has_position and alt_profit_trailing_exit_triggered:
                    log(
                        f"[{symbol}] 순익 trailing 청산 조건 충족: reason="
                        f"{alt_profit_trailing_decision.trigger_reason}, "
                        f"이익 반납폭 "
                        f"{0.0 if alt_profit_trailing_decision.profit_retrace_from_mfe_pct is None else alt_profit_trailing_decision.profit_retrace_from_mfe_pct:.2f}% / "
                        f"{strategy.alt_profit_trailing_drawdown_pct:.2f}%, 순익률 "
                        f"{0.0 if current_net_realized_pnl_pct is None else current_net_realized_pnl_pct:.2f}%"
                    )
                if has_position and break_even_guard_triggered:
                    log(
                        f"[{symbol}] 브레이크이븐 가드 조건 충족: 최대 유리 구간 {mfe_pct:.2f}% 이후 "
                        f"수수료 반영 순익률이 {current_net_realized_pnl_pct:.2f}% 까지 되돌고 "
                        f"이익 반납폭이 {0.0 if profit_retrace_from_mfe_pct is None else profit_retrace_from_mfe_pct:.2f}% 에 도달해 청산합니다."
                    )
                if has_position and stop_loss_triggered:
                    log(
                        f"[{symbol}] 손절 조건 충족: 현재 수익률 {pnl_pct:.2f}% <= -{stop_loss_pct:.2f}%"
                    )
                if has_position and volume_spike_exit_triggered:
                    log(
                        f"[{symbol}] Volume Spike Exit 조건 충족: 순익률 "
                        f"{0.0 if current_net_realized_pnl_pct is None else current_net_realized_pnl_pct:.2f}% "
                        f"상태에서 거래량 배수 {0.0 if volume_ratio is None else volume_ratio:.4f} 가 "
                        f"{strategy.volume_spike_exit_max_volume_ratio:.4f} 이하로 급감해 조기 청산합니다."
                    )
                if has_position and sol_probe_time_exit_triggered:
                    log(
                        f"[{symbol}] SOL probe 최대 보유 시간 "
                        f"{strategy.sol_probe_max_hold_minutes}분을 초과해 시간 청산합니다."
                    )

                base_position_ratio = strategy.get_position_ratio(
                    symbol,
                    config["risk_per_trade"],
                )
                allocation_score_result = compute_allocation_score(
                    settings=portfolio_allocator.settings,
                    signal_score=signal_score,
                    volume_ratio=volume_ratio,
                    required_volume_ratio=effective_min_volume_ratio,
                    volume_ratio_percentile=volume_ratio_percentile,
                    trend_ok=htf_bullish,
                    htf_slope_pct=htf_ma_slope_pct,
                    low_energy_guard_active=low_energy_guard_active,
                    symbol_regime=symbol_regime,
                    atr_pct=atr_pct,
                    atr_percentile=atr_percentile,
                    orderbook_pressure_score=orderbook_pressure_score,
                    fill_quality_avg_fill_ratio=fill_quality_snapshot.avg_fill_ratio,
                    fill_quality_entry_blocked=fill_quality_entry_blocked,
                    correlation_with_btc=correlation_with_btc,
                    max_correlation_with_btc=strategy.max_correlation_with_btc,
                )
                position_sizing = build_alt_position_sizing(
                    strategy=strategy,
                    symbol=symbol,
                    base_position_ratio=base_position_ratio,
                    symbol_regime=symbol_regime,
                    btc_reference_regime=btc_reference_regime,
                    btc_reference_atr_pct=btc_reference_atr_pct,
                    alt_atr_pct=atr_pct,
                    score_scale=allocation_score_result.score_scale,
                    volume_spike_position_scale=(
                        volume_spike_entry_downgrade.position_scale
                        if volume_spike_entry_downgrade.allowed
                        else None
                    ),
                    mean_reversion_lower_near_position_scale=(
                        strategy.mean_reversion_lower_near_position_scale
                        if mean_reversion_lower_near_probe_allowed
                        else None
                    ),
                    low_energy_probe_allowed=low_energy_probe_decision.allowed,
                    low_energy_probe_position_scale=low_energy_probe_decision.position_scale,
                    xrp_rebound_probe_allowed=xrp_rebound_probe_allowed,
                    xrp_rebound_probe_position_scale=xrp_rebound_probe_decision.position_scale,
                    sol_probe_allowed=sol_probe_entry_allowed,
                    sol_probe_position_scale=sol_probe_entry_decision.position_scale,
                )
                regime_position_scale = position_sizing.regime_position_scale
                btc_regime_position_scale = position_sizing.btc_regime_position_scale
                btc_atr_position_scale = position_sizing.btc_atr_position_scale
                combined_position_scale = position_sizing.combined_regime_position_scale
                alt_atr_position_scale = position_sizing.alt_atr_position_scale
                pre_score_position_ratio = position_sizing.pre_score_position_ratio
                position_ratio = position_sizing.position_ratio
                log(
                    format_alt_position_sizing_log(
                        symbol=symbol,
                        sizing=position_sizing,
                        btc_reference_regime=btc_reference_regime,
                        btc_reference_atr_pct=btc_reference_atr_pct,
                        alt_atr_pct=atr_pct,
                    )
                )
                log(format_allocation_score_log(symbol=symbol, score=allocation_score_result))
                dynamic_bonus_eligible = is_dynamic_bonus_eligible(
                    has_position=has_position,
                    base_signal=bullish,
                    strong_signal=signal_score >= strategy.dynamic_signal_score_min,
                    require_strong_signal=portfolio_allocator.settings.dynamic_require_strong_signal,
                    volume_ratio=volume_ratio,
                    volume_threshold=portfolio_allocator.settings.dynamic_volume_ratio_threshold,
                    trend_ok=htf_bullish,
                    require_trend_ok=portfolio_allocator.settings.dynamic_require_trend_ok,
                    enable_dynamic_overweight=(
                        portfolio_allocator.settings.enable_dynamic_overweight
                        and regime_policy.allow_dynamic_overweight
                        and not volume_spike_entry_downgrade.allowed
                        and not sol_probe_entry_allowed
                        and not xrp_rebound_probe_allowed
                    ),
                )
                requested_order_value, allocation_decision = build_alt_allocation(
                    portfolio_allocator=portfolio_allocator,
                    exchange=exchange,
                    symbol=symbol,
                    quote_free=quote_free,
                    position_ratio=position_ratio,
                    buy_split_ratio=strategy.buy_split_ratio,
                    dynamic_bonus_eligible=dynamic_bonus_eligible,
                )
                krw_to_use = allocation_decision.approved_order_value_quote
                executable_krw_to_use = apply_upbit_buy_order_buffer(
                    requested_order_value_quote=krw_to_use,
                    quote_free=quote_free,
                    fee_rate_pct=config["fee_rate_pct"],
                    buffer_pct=config["krw_order_buffer_pct"],
                    buffer_krw=config["krw_order_buffer_krw"],
                )
                upbit_min_order_floor_applied = False
                upbit_min_order_floor_reason = (
                    "sol_probe_floor_disabled"
                    if sol_probe_entry_allowed
                    else "not_needed"
                )
                if executable_krw_to_use <= strategy.min_buy_order_value and not sol_probe_entry_allowed:
                    floor_min_signal_score = max(
                        effective_signal_score_min,
                        strategy.upbit_min_order_floor_min_signal_score,
                    )
                    floor_requested_krw = strategy.min_buy_order_value * (
                        1.0 + max(0.0, strategy.upbit_min_order_floor_buffer_pct)
                    )
                    floor_quality_ok = (
                        strategy.enable_upbit_min_order_floor
                        and signal_score >= floor_min_signal_score
                        and (not strategy.upbit_min_order_floor_require_htf_bullish or htf_bullish)
                        and not htf_bearish_entry_blocked
                        and not mean_reversion_falling_knife_blocked
                        and not overheated_entry_blocked
                        and not btc_correlation_volatility_blocked
                        and not volume_atr_execution_blocked
                        and not stop_loss_context_reentry_blocked
                    )
                    budget_ok = (
                        allocation_decision.remaining_budget_quote >= floor_requested_krw
                        and quote_free >= floor_requested_krw
                    )
                    if not strategy.enable_upbit_min_order_floor:
                        upbit_min_order_floor_reason = "disabled"
                    elif not floor_quality_ok:
                        upbit_min_order_floor_reason = "quality_gate_blocked"
                    elif not budget_ok:
                        upbit_min_order_floor_reason = "budget_or_quote_free_insufficient"
                    else:
                        floored_krw_to_use = apply_upbit_buy_order_buffer(
                            requested_order_value_quote=floor_requested_krw,
                            quote_free=quote_free,
                            fee_rate_pct=config["fee_rate_pct"],
                            buffer_pct=config["krw_order_buffer_pct"],
                            buffer_krw=config["krw_order_buffer_krw"],
                        )
                        if floored_krw_to_use > strategy.min_buy_order_value:
                            executable_krw_to_use = floored_krw_to_use
                            upbit_min_order_floor_applied = True
                            upbit_min_order_floor_reason = "applied"
                        else:
                            upbit_min_order_floor_reason = "buffered_floor_still_too_small"
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
                estimated_sell_ratio = (
                    1.0
                    if sol_probe_time_exit_triggered
                    else float(alt_exit_state["estimated_sell_ratio"])
                )
                estimated_sell_amount = base_free * estimated_sell_ratio
                estimated_sell_amount = safe_amount_to_precision(
                    exchange, symbol, estimated_sell_amount
                )
                estimated_sell_order_value_quote = estimated_sell_amount * sell_price_reference

                common_metrics = build_alt_common_metrics(
                    strategy_name="upbit_alt_ma_crossover",
                    strategy_version=strategy.version,
                    symbol=symbol,
                    timeframe=timeframe,
                    ma_period=ma_period,
                    price=last_close,
                    ma=last_ma,
                    gap_pct=gap_pct,
                    noise_ratio=noise_ratio,
                    noise_gap_multiplier=noise_gap_multiplier,
                    base_min_gap_pct=base_min_gap_pct,
                    signal_score=signal_score,
                    signal_is_strong=signal_is_strong,
                    entry_signal=entry_signal,
                    bullish_signal=bullish,
                    rsi_value=rsi_value,
                    rsi_filter_passed=rsi_filter_passed,
                    macd_histogram=macd_histogram,
                    macd_filter_passed=macd_filter_passed,
                    ma_slope_pct=ma_slope_pct,
                    price_slope_pct=price_slope_pct,
                    entry_timing_phase=entry_timing_snapshot.phase,
                    entry_timing_confirmation_count=entry_timing_snapshot.confirmation_count,
                    entry_timing_required_confirmations=entry_timing_snapshot.required_confirmations,
                    correlation_with_btc=correlation_with_btc,
                    correlation_entry_blocked=correlation_entry_blocked,
                    fill_quality_avg_fill_ratio=fill_quality_snapshot.avg_fill_ratio,
                    fill_quality_sample_count=fill_quality_snapshot.sample_count,
                    fill_quality_entry_blocked=fill_quality_entry_blocked,
                    trend_follow_entry=trend_follow_entry,
                    volume_ratio=volume_ratio,
                    volume_ratio_percentile=volume_ratio_percentile,
                    volume_cap_allows_entry=volume_cap_allows_entry,
                    volume_spike_entry_downgrade_allowed=volume_spike_entry_downgrade.allowed,
                    volume_spike_entry_downgrade_reason=volume_spike_entry_downgrade.reason,
                    volume_spike_entry_position_scale=volume_spike_entry_downgrade.position_scale,
                    volume_spike_entry_extra_confirmation_loops=(
                        volume_spike_entry_downgrade.extra_confirmation_loops
                    ),
                    avg_abs_change_pct=avg_abs_change_pct,
                    atr_percentile=atr_percentile,
                    recent_high=recent_range_context["recent_high"],
                    recent_low=recent_range_context["recent_low"],
                    range_position_pct=recent_range_context["range_position_pct"],
                    distance_from_recent_high_pct=recent_range_context["distance_from_recent_high_pct"],
                    distance_from_recent_low_pct=recent_range_context["distance_from_recent_low_pct"],
                    overheated_entry_blocked=overheated_entry_blocked,
                    overheat_extra_confirmation_required=overheat_extra_confirmation_required,
                    btc_correlation_volatility_blocked=btc_correlation_volatility_blocked,
                    volume_atr_execution_blocked=volume_atr_execution_blocked,
                    stop_loss_context_reentry_blocked=stop_loss_context_reentry_blocked,
                    orderbook_pressure_score=orderbook_pressure_score,
                    htf_bullish=htf_bullish,
                    htf_bearish=htf_bearish,
                    htf_bearish_entry_blocked=htf_bearish_entry_blocked,
                    base_free=base_free,
                    quote_free=quote_free,
                    requested_order_value_quote=krw_to_use,
                    executable_order_value_quote=executable_krw_to_use,
                    upbit_min_order_floor_applied=upbit_min_order_floor_applied,
                    upbit_min_order_floor_reason=upbit_min_order_floor_reason,
                    position_ratio=position_ratio,
                    has_position=has_position,
                    position_quote_value=position_quote_value,
                    best_bid=best_bid,
                    entry_count=current_entry_count,
                    pnl_pct=pnl_pct,
                    portfolio_base_target_pct=allocation_decision.base_target_pct * 100,
                    portfolio_effective_target_pct=allocation_decision.effective_target_pct * 100,
                    portfolio_dynamic_bonus_pct=allocation_decision.dynamic_bonus_pct * 100,
                    portfolio_dynamic_bonus_applied=allocation_decision.dynamic_bonus_applied,
                    portfolio_total_budget_quote=allocation_decision.total_portfolio_quote,
                    portfolio_current_cost_basis_quote=allocation_decision.current_cost_basis_quote,
                    portfolio_remaining_budget_quote=allocation_decision.remaining_budget_quote,
                    net_pnl_pct_estimate=current_net_realized_pnl_pct,
                    daily_realized_pnl_quote=daily_realized_pnl_quote,
                    fee_round_trip_pct=fee_round_trip_pct,
                    fee_protect_min_net_pnl_pct=fee_protect_min_net_pnl_pct,
                    profit_protect_triggered=profit_protect_triggered,
                    alt_profit_trailing_armed=alt_profit_trailing_armed.get(symbol, False),
                    alt_profit_trailing_exit_triggered=alt_profit_trailing_exit_triggered,
                    alt_profit_trailing_trigger_reason=alt_profit_trailing_decision.trigger_reason,
                    break_even_guard_min_mfe_pct=break_even_guard_min_mfe_pct,
                    break_even_guard_floor_net_pnl_pct=break_even_guard_floor_net_pnl_pct,
                    break_even_guard_max_profit_retrace_pct=break_even_guard_max_profit_retrace_pct,
                    break_even_guard_triggered=break_even_guard_triggered,
                    profit_retrace_from_mfe_pct=profit_retrace_from_mfe_pct,
                    low_energy_guard_active=low_energy_guard_active,
                    effective_low_energy_guard_active=effective_low_energy_guard_active,
                    low_energy_probe_allowed=low_energy_probe_decision.allowed,
                    low_energy_probe_reason=low_energy_probe_decision.reason,
                    low_energy_probe_position_scale=low_energy_probe_decision.position_scale,
                    sol_probe_entry_allowed=sol_probe_entry_allowed,
                    sol_probe_entry_reason=sol_probe_entry_decision.reason,
                    sol_probe_position_scale=sol_probe_entry_decision.position_scale,
                    xrp_rebound_probe_allowed=xrp_rebound_probe_allowed,
                    xrp_rebound_probe_reason=xrp_rebound_probe_decision.reason,
                    xrp_rebound_probe_min_signal_score=strategy.xrp_rebound_probe_min_signal_score,
                    xrp_rebound_probe_position_scale=xrp_rebound_probe_decision.position_scale,
                    xrp_rebound_probe_extra_confirmation_loops=(
                        xrp_rebound_probe_decision.extra_confirmation_loops
                    ),
                    sol_probe_take_profit_pct=strategy.sol_probe_take_profit_pct,
                    sol_probe_stop_loss_pct=strategy.sol_probe_stop_loss_pct,
                    sol_probe_max_hold_minutes=strategy.sol_probe_max_hold_minutes,
                    sol_probe_time_exit_triggered=sol_probe_time_exit_triggered,
                    mean_reversion_lower_reclaim_confirmed=mean_reversion_lower_reclaim_confirmed,
                    mean_reversion_lower_near_probe_allowed=mean_reversion_lower_near_probe_allowed,
                    mean_reversion_lower_near_probe_reason=str(
                        signal_state.get("lower_near_probe_reason", "")
                    ),
                    mean_reversion_bb_lower_distance_pct=float(
                        signal_state.get("bb_lower_distance_pct", 0.0)
                    ),
                    mean_reversion_lower_near_max_distance_pct=(
                        strategy.mean_reversion_lower_near_max_distance_pct
                    ),
                    mean_reversion_lower_near_position_scale=(
                        strategy.mean_reversion_lower_near_position_scale
                    ),
                    mean_reversion_lower_near_extra_confirmation_loops=(
                        mean_reversion_lower_near_extra_confirmation_loops
                    ),
                    low_energy_avg_volume_ratio=low_energy_snapshot.avg_volume_ratio,
                    low_energy_avg_abs_change_pct=low_energy_snapshot.avg_abs_change_pct,
                    low_energy_ready_count=low_energy_snapshot.ready_count,
                    btc_reference_regime=btc_reference_regime,
                    btc_regime_position_scale=btc_regime_position_scale,
                    btc_reference_atr_pct=btc_reference_atr_pct,
                    btc_atr_position_scale=btc_atr_position_scale,
                    symbol_regime=symbol_regime,
                    regime_strategy_key=strategy_key,
                    symbol_regime_blocks_entry=symbol_regime_blocks_entry,
                    symbol_regime_requires_strong_signal=symbol_regime_requires_strong_signal,
                    symbol_regime_requires_fresh_cross=symbol_regime_requires_fresh_cross,
                    regime_position_scale=regime_position_scale,
                    combined_regime_position_scale=combined_position_scale,
                    base_position_ratio=base_position_ratio,
                    pre_score_position_ratio=pre_score_position_ratio,
                    allocation_score=allocation_score_result.allocation_score,
                    allocation_score_scale=allocation_score_result.score_scale,
                    allocation_signal_score=allocation_score_result.signal_score_component,
                    allocation_market_score=allocation_score_result.market_score_component,
                    allocation_execution_score=allocation_score_result.execution_score_component,
                    allocation_diversification_score=allocation_score_result.diversification_score_component,
                    allocation_reason_top=allocation_score_result.reason_top,
                    effective_position_ratio=position_ratio,
                    order_value=executable_krw_to_use,
                    regime_dynamic_overweight_allowed=regime_policy.allow_dynamic_overweight,
                    regime_stop_loss_multiplier=regime_policy.stop_loss_multiplier,
                    regime_take_profit_bonus_pct=regime_policy.take_profit_bonus_pct,
                    regime_partial_take_profit_ratio_multiplier=regime_policy.partial_take_profit_ratio_multiplier,
                    partial_take_profit_cooldown_active=partial_take_profit_cooldown_active,
                    partial_take_profit_cooldown_remaining_sec=partial_take_profit_cooldown_remaining,
                    partial_take_profit_pending=partial_take_profit_pending,
                    partial_stop_loss_pending=partial_stop_loss_pending,
                )
                entry_committee_result = evaluate_entry_committee(
                    common_metrics,
                    entry_committee_settings,
                )
                common_metrics.update(entry_committee_result.to_metrics())

                entry_cooldown_active = (
                    in_cooldown
                    or partial_take_profit_cooldown_active
                    or stop_loss_pattern_blocked
                    or stop_loss_context_reentry_blocked
                )

                entry_steps = build_alt_entry_steps(
                    entry_signal=entry_signal,
                    bullish=bullish,
                    trend_follow_entry=trend_follow_entry,
                    signal_is_strong=signal_is_strong,
                    signal_score=signal_score,
                    min_signal_score=effective_signal_score_min,
                    gap_pct=gap_pct,
                    min_gap_pct=min_gap_pct,
                    max_gap_pct=max_entry_gap_pct,
                    gap_within_upper_bound=gap_within_upper_bound,
                    rsi_filter_passed=rsi_filter_passed,
                    macd_filter_passed=macd_filter_passed,
                    htf_bullish=(
                        not strategy.enable_higher_timeframe_filter
                        or htf_bullish
                        or xrp_rebound_probe_allowed
                    ),
                    volume_filter_passed=(not strategy.enable_volume_filter or volume_filter_passed),
                    volume_ratio=volume_ratio,
                    effective_min_volume_ratio=effective_min_volume_ratio,
                    max_volume_ratio=effective_max_volume_ratio,
                    volume_within_upper_bound=volume_within_upper_bound,
                    volume_cap_downgrade_allowed=volume_spike_entry_downgrade.allowed,
                    volume_cap_downgrade_reason=volume_spike_entry_downgrade.reason,
                    volume_cap_hard_max_ratio=strategy.volume_spike_entry_hard_max_volume_ratio,
                    volatility_filter_passed=(not strategy.enable_volatility_filter or volatility_filter_passed),
                    avg_abs_change_pct=avg_abs_change_pct,
                    min_volatility_pct=strategy.min_volatility_pct,
                    max_volatility_pct=strategy.max_volatility_pct,
                    in_cooldown=entry_cooldown_active,
                    seconds_since_last_trade=seconds_since_last_trade,
                    stop_loss_pattern_blocked=stop_loss_pattern_blocked,
                    stop_loss_pattern_elapsed_sec=seconds_since_last_stop_loss if last_stop_loss_ts > 0 else None,
                    stop_loss_pattern_min_cooldown_sec=strategy.stop_loss_pattern_min_cooldown_sec,
                    stop_loss_pattern_signal_score=signal_score,
                    stop_loss_pattern_min_signal_score=strategy.stop_loss_pattern_min_signal_score,
                    stop_loss_pattern_volume_ratio=volume_ratio,
                    stop_loss_pattern_required_volume_ratio=float(stop_loss_pattern_gate["required_min_volume_ratio"]),
                    can_average_down=can_average_down,
                    last_close=last_close,
                    avg_entry_price=avg_entry_price,
                    current_entry_count=current_entry_count,
                    max_entry_count=effective_max_entry_count,
                    daily_loss_limit_reached=daily_loss_limit_reached,
                    daily_realized_pnl_quote=daily_realized_pnl_quote,
                    max_daily_loss_quote=config["max_daily_loss_quote"],
                    order_value_quote=executable_krw_to_use,
                    min_buy_order_value=strategy.min_buy_order_value,
                    entry_strategy_key=strategy_key,
                    order_value_block_reason="order_value_too_small_after_upbit_buffer",
                    squeeze_band_passed=bool(signal_state.get("squeeze_band_passed", True)),
                    squeeze_volume_passed=bool(signal_state.get("squeeze_volume_passed", True)),
                    squeeze_breakout_passed=bool(signal_state.get("squeeze_breakout_passed", True)),
                    mean_reversion_lower_reclaim_confirmed=mean_reversion_lower_reclaim_confirmed,
                    mean_reversion_lower_near_probe_allowed=mean_reversion_lower_near_probe_allowed,
                    mean_reversion_bb_lower_distance_pct=float(
                        signal_state.get("bb_lower_distance_pct", 0.0)
                    ),
                    mean_reversion_lower_near_max_distance_pct=(
                        strategy.mean_reversion_lower_near_max_distance_pct
                    ),
                    mean_reversion_lower_near_min_signal_score=float(
                        signal_state.get(
                            "lower_near_min_signal_score",
                            strategy.mean_reversion_lower_near_min_signal_score,
                        )
                    ),
                    mean_reversion_lower_near_signal_passed=bool(
                        signal_state.get("lower_near_signal_passed", False)
                    ),
                    entry_probe_signal=(
                        sol_probe_entry_allowed or xrp_rebound_probe_allowed
                    ),
                    entry_probe_reason=(
                        xrp_rebound_probe_decision.reason
                        if xrp_rebound_probe_allowed
                        else sol_probe_entry_decision.reason
                    ),
                    atr_context_passed=bool(signal_state.get("atr_context_passed", True)),
                    range_context_passed=bool(signal_state.get("range_context_passed", True)),
                    falling_knife_blocked=mean_reversion_falling_knife_blocked,
                )
                entry_steps.extend(
                    build_alt_entry_guard_steps(
                        strategy=strategy,
                        symbol=symbol,
                        sol_probe_entry_allowed=sol_probe_entry_allowed,
                        sol_probe_entry_decision=sol_probe_entry_decision,
                        has_position=has_position,
                        current_entry_count=current_entry_count,
                        signal_score=signal_score,
                        htf_bearish_entry_blocked=htf_bearish_entry_blocked,
                        htf_bearish=htf_bearish,
                        effective_low_energy_guard_active=effective_low_energy_guard_active,
                        low_energy_guard_active=low_energy_guard_active,
                        low_energy_probe_decision=low_energy_probe_decision,
                        low_energy_snapshot=low_energy_snapshot,
                        volume_ratio=volume_ratio,
                        orderbook_pressure_score=orderbook_pressure_score,
                        atr_percentile=atr_percentile,
                        effective_symbol_regime_blocks_entry=effective_symbol_regime_blocks_entry,
                        symbol_regime=symbol_regime,
                        symbol_regime_requires_strong_signal=symbol_regime_requires_strong_signal,
                        signal_is_strong=signal_is_strong,
                        entry_probe_score_override_allowed=entry_probe_score_override_allowed,
                        effective_signal_score_min=effective_signal_score_min,
                        correlation_entry_blocked=correlation_entry_blocked,
                        correlation_with_btc=correlation_with_btc,
                        btc_reference_above_ma=btc_reference_above_ma,
                        btc_correlation_volatility_blocked=btc_correlation_volatility_blocked,
                        btc_reference_regime=btc_reference_regime,
                        volume_atr_execution_blocked=volume_atr_execution_blocked,
                        low_energy_top_chase_entry_blocked=low_energy_top_chase_entry_blocked,
                        low_energy_top_chase_actual=low_energy_top_chase_actual,
                        low_energy_top_chase_required=low_energy_top_chase_required,
                        fill_quality_snapshot=fill_quality_snapshot,
                        stop_loss_context_reentry_blocked=stop_loss_context_reentry_blocked,
                        seconds_since_last_stop_loss=seconds_since_last_stop_loss,
                        last_stop_loss_ts=last_stop_loss_ts,
                        current_entry_risk_context=current_entry_risk_context,
                        last_stop_loss_context=last_stop_loss_context,
                        fill_quality_entry_blocked=fill_quality_entry_blocked,
                        entry_timing_snapshot=entry_timing_snapshot,
                    )
                )
                entry_steps.extend(
                    [
                        FunnelStep(
                            stage="upbit_min_order_floor",
                            passed=(
                                executable_krw_to_use > strategy.min_buy_order_value
                                or upbit_min_order_floor_reason in {"not_needed", "applied"}
                            ),
                            reason=f"upbit_min_order_floor_{upbit_min_order_floor_reason}",
                            actual={
                                "floor_applied": upbit_min_order_floor_applied,
                                "floor_reason": upbit_min_order_floor_reason,
                                "requested_order_value_quote": krw_to_use,
                                "executable_order_value_quote": executable_krw_to_use,
                            },
                            required={
                                "min_order_value": strategy.min_buy_order_value,
                                "min_signal_score": max(
                                    effective_signal_score_min,
                                    strategy.upbit_min_order_floor_min_signal_score,
                                ),
                            },
                        ),
                        FunnelStep(
                            stage="portfolio_budget",
                            passed=allocation_decision.remaining_budget_quote > 0,
                            reason="portfolio_budget_exhausted",
                            actual={
                                "current_cost_basis_quote": allocation_decision.current_cost_basis_quote,
                                "remaining_budget_quote": allocation_decision.remaining_budget_quote,
                            },
                            required={"portfolio_target_budget_quote": allocation_decision.target_budget_quote},
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
                entry_ready = run_alt_entry_funnel(
                    structured_logger=structured_logger,
                    symbol=symbol,
                    entry_steps=entry_steps,
                    metrics=common_metrics,
                )

                exit_steps = build_alt_exit_steps(
                    has_position=has_position,
                    stop_loss_triggered=stop_loss_triggered,
                    profit_protect_triggered=profit_protect_triggered,
                    break_even_guard_triggered=break_even_guard_triggered,
                    volume_spike_exit_triggered=volume_spike_exit_triggered,
                    bearish=bearish,
                    in_cooldown=in_cooldown,
                    seconds_since_last_trade=seconds_since_last_trade,
                    signal_is_strong=signal_is_strong,
                    gap_pct=gap_pct,
                    min_gap_pct=min_gap_pct,
                    htf_bearish=(not strategy.enable_higher_timeframe_filter or htf_bearish),
                    take_profit_ready=take_profit_ready,
                    pnl_pct=pnl_pct,
                    current_net_realized_pnl_pct=current_net_realized_pnl_pct,
                    mfe_pct=mfe_pct,
                    min_take_profit_pct=effective_min_take_profit_pct,
                    fee_protect_min_net_pnl_pct=fee_protect_min_net_pnl_pct,
                    break_even_guard_min_mfe_pct=break_even_guard_min_mfe_pct,
                    break_even_guard_floor_net_pnl_pct=break_even_guard_floor_net_pnl_pct,
                    alt_profit_trailing_exit_triggered=alt_profit_trailing_exit_triggered,
                    sol_probe_time_exit_triggered=sol_probe_time_exit_triggered,
                )
                exit_steps.extend(
                    [
                        FunnelStep(
                            stage="amount",
                            passed=estimated_sell_amount > 0,
                            reason="sell_amount_too_small",
                            actual={"sell_amount": estimated_sell_amount},
                            required={"sell_amount_gt": 0},
                        ),
                        FunnelStep(
                            stage="order_value",
                            passed=estimated_sell_order_value_quote > strategy.min_buy_order_value,
                            reason="sell_order_value_too_small",
                            actual={"sell_order_value_quote": estimated_sell_order_value_quote},
                            required={"min_sell_order_value": strategy.min_buy_order_value},
                        ),
                    ]
                )
                exit_ready = run_alt_exit_funnel(
                    structured_logger=structured_logger,
                    symbol=symbol,
                    exit_steps=exit_steps,
                    metrics=common_metrics,
                    stop_loss_triggered=stop_loss_triggered,
                    profit_protect_triggered=profit_protect_triggered,
                    break_even_guard_triggered=break_even_guard_triggered,
                    volume_spike_exit_triggered=volume_spike_exit_triggered,
                    sol_probe_time_exit_triggered=sol_probe_time_exit_triggered,
                    alt_profit_trailing_exit_triggered=alt_profit_trailing_exit_triggered,
                )

                # 매수 신호 발생 시, 분할 횟수/쿨다운/추가 매수 가격 조건을 만족하면 진입
                if entry_ready:
                    if executable_krw_to_use <= strategy.min_buy_order_value:
                        log(
                            f"[{symbol}] 주문 가능 KRW 버퍼 반영 후 금액이 "
                            f"{strategy.min_buy_order_value:.0f} {quote} 이하라 매수 주문을 생략합니다."
                        )
                    else:
                        amount = executable_krw_to_use / last_close
                        amount = safe_amount_to_precision(exchange, symbol, amount)
                        cost_to_spend = executable_krw_to_use
                        log_order_requested(
                            structured_logger=structured_logger,
                            symbol=symbol,
                            side="entry",
                            reason="market_buy_requested",
                            actual={
                                "order_value_quote": cost_to_spend,
                                "amount": amount,
                            },
                            metrics=common_metrics,
                        )
                        log(f"[매수] 시장가 매수 시도: {symbol}, 사용 금액={cost_to_spend:.0f} {quote}, 수량={amount}")
                        try:
                            order_submission = submit_upbit_market_buy(
                                exchange=exchange,
                                symbol=symbol,
                                order_value_quote=cost_to_spend,
                                market_data_provider=market_data_provider,
                            )
                        except Exception as order_error:
                            log_order_failure(
                                structured_logger=structured_logger,
                                symbol=symbol,
                                side="entry",
                                message="매수 주문 요청이 실패했습니다.",
                                actual={
                                    "order_value_quote": cost_to_spend,
                                    "amount": amount,
                                },
                                metrics=common_metrics,
                                error=order_error,
                                extra={"strategy_version": strategy.version},
                            )
                            continue
                        order = order_submission.order
                        order_request_started_at = order_submission.request_started_at
                        order_response_received_at = order_submission.response_received_at
                        buy_fill_state = apply_alt_buy_fill_state(
                            symbol=symbol,
                            bought_amount=amount,
                            last_close=last_close,
                            has_position=has_position,
                            avg_entry_price=avg_entry_price,
                            base_free=base_free,
                            current_entry_count=current_entry_count,
                            now_ts=time.time(),
                            entry_price=entry_price,
                            entry_count=entry_count,
                            entry_opened_at=entry_opened_at,
                            highest_price_since_entry=highest_price_since_entry,
                            lowest_price_since_entry=lowest_price_since_entry,
                        )
                        if not has_position:
                            alt_profit_trailing_armed.pop(symbol, None)
                        last_trade_at[symbol] = time.time()
                        log_order_filled(
                            structured_logger=structured_logger,
                            symbol=symbol,
                            strategy_side="entry",
                            trade_side="buy",
                            strategy_reason="buy_filled",
                            trade_reason="entry",
                            actual={
                                "filled_amount": amount,
                                "order_value_quote": cost_to_spend,
                            },
                            metrics={
                                **common_metrics,
                                "estimated_entry_price_after": buy_fill_state.entry_price_after,
                            },
                        )
                        logger.log_trade_banner(
                            RED,
                            f"[{symbol}] 매수 주문 체결",
                            f"주문 결과: {order}",
                        )
                        buy_summary = summarize_order_for_notification(
                            raw_order=order,
                            side="buy",
                            requested_amount=amount,
                            requested_order_value_quote=cost_to_spend,
                            fallback_amount=amount,
                            fallback_order_value_quote=cost_to_spend,
                            fallback_price=buy_fill_state.entry_price_after,
                        )
                        executed_ratio_pct = 0.0
                        if quote_free > 0 and buy_summary["executed_order_value_quote"] not in (None, 0):
                            executed_ratio_pct = (
                                float(buy_summary["executed_order_value_quote"]) / float(quote_free) * 100
                            )
                        notifier.notify_buy_fill(
                            "UPBIT",
                            symbol,
                            format_buy_fill_message(
                                symbol_regime=symbol_regime,
                                quote=quote,
                                base=base,
                                buy_summary=buy_summary,
                                base_position_ratio=base_position_ratio,
                                position_ratio=position_ratio,
                                executed_ratio_pct=executed_ratio_pct,
                                fmt=UPBIT_TRADE_MESSAGE_FORMAT,
                            ),
                        )
                        trade_history.log_fill(
                            exchange_name="UPBIT",
                            program_name="upbit_ma_crossover_bot",
                            strategy_version=strategy.version,
                            symbol=symbol,
                            side="buy",
                            reason="entry",
                            base_currency=base,
                            quote_currency=quote,
                            amount=amount,
                            order_value_quote=cost_to_spend,
                            reference_price=last_close,
                            estimated_entry_price=buy_fill_state.entry_price_after,
                            entry_count_after=buy_fill_state.entry_count_after,
                            base_free_before=base_free,
                            quote_free_before=quote_free,
                            remaining_base_after_estimate=buy_fill_state.remaining_base_after_estimate,
                            timeframe=timeframe,
                            ma_period=ma_period,
                            request_started_at=order_request_started_at,
                            response_received_at=order_response_received_at,
                            requested_order_value_quote=cost_to_spend,
                            raw_order=order,
                            extra={
                                "strategy_version": strategy.version,
                                "bullish_signal": bullish,
                                "signal_is_strong": signal_is_strong,
                                "signal_score": signal_score,
                                "gap_pct": gap_pct,
                                "take_profit_pct": effective_min_take_profit_pct,
                                "configured_take_profit_pct": take_profit_pct,
                                "stop_loss_pct": stop_loss_pct,
                                "sol_probe_entry_allowed": sol_probe_entry_allowed,
                                "sol_probe_entry_reason": sol_probe_entry_decision.reason,
                                "sol_probe_position_scale": sol_probe_entry_decision.position_scale,
                                "xrp_rebound_probe_allowed": xrp_rebound_probe_allowed,
                                "xrp_rebound_probe_reason": xrp_rebound_probe_decision.reason,
                                "xrp_rebound_probe_position_scale": xrp_rebound_probe_decision.position_scale,
                                "fee_round_trip_pct": fee_round_trip_pct,
                                "min_volume_ratio": effective_min_volume_ratio,
                                "volume_filter_passed": volume_filter_passed,
                                "volatility_filter_passed": volatility_filter_passed,
                                "atr_percentile": atr_percentile,
                                "range_position_pct": recent_range_context["range_position_pct"],
                                "distance_from_recent_high_pct": recent_range_context["distance_from_recent_high_pct"],
                                "overheated_entry_blocked": overheated_entry_blocked,
                                "overheat_extra_confirmation_required": overheat_extra_confirmation_required,
                                "btc_correlation_volatility_blocked": btc_correlation_volatility_blocked,
                                "volume_atr_execution_blocked": volume_atr_execution_blocked,
                                "stop_loss_context_reentry_blocked": stop_loss_context_reentry_blocked,
                                "orderbook_pressure_score": orderbook_pressure_score,
                                "htf_bullish": htf_bullish,
                            },
                        )
                        log(
                            f"[{symbol}] 분할 매수 진행: {buy_fill_state.entry_count_after}/{effective_max_entry_count}회"
                        )
                        log(
                            f"[{symbol}] 갱신된 평균 진입가: {buy_fill_state.entry_price_after:.0f}"
                        )

                # 매도 신호 발생 시, 분할 청산 + 최소 익절률 조건을 만족하면 청산
                elif exit_ready:
                    sell_intent = resolve_alt_sell_intent(
                        sell_split_ratio=strategy.sell_split_ratio,
                        stop_loss_triggered=stop_loss_triggered,
                        partial_stop_loss_pending=partial_stop_loss_pending,
                        partial_stop_loss_ratio=strategy.partial_stop_loss_ratio,
                        profit_protect_triggered=profit_protect_triggered,
                        break_even_guard_triggered=break_even_guard_triggered,
                        volume_spike_exit_triggered=volume_spike_exit_triggered,
                        sol_probe_time_exit_triggered=sol_probe_time_exit_triggered,
                        partial_take_profit_pending=partial_take_profit_pending,
                        effective_partial_take_profit_ratio=effective_partial_take_profit_ratio,
                        alt_profit_trailing_exit_triggered=alt_profit_trailing_exit_triggered,
                    )
                    sell_ratio = sell_intent.sell_ratio
                    exit_reason_key = sell_intent.exit_reason_key
                    sell_reason = sell_intent.sell_reason

                    sell_amount = base_free * sell_ratio
                    amount = safe_amount_to_precision(
                        exchange, symbol, sell_amount
                    )
                    sell_order_value_quote = amount * sell_price_reference
                    full_sell_amount = safe_amount_to_precision(exchange, symbol, base_free)
                    full_sell_order_value_quote = full_sell_amount * sell_price_reference
                    sell_order_plan = resolve_alt_sell_order_by_min_value(
                        symbol=symbol,
                        base=base,
                        quote=quote,
                        amount=amount,
                        full_sell_amount=full_sell_amount,
                        sell_order_value_quote=sell_order_value_quote,
                        full_sell_order_value_quote=full_sell_order_value_quote,
                        sell_ratio=sell_ratio,
                        exit_reason_key=exit_reason_key,
                        sell_reason=sell_reason,
                        min_sell_order_value=strategy.min_buy_order_value,
                    )
                    amount = sell_order_plan.amount
                    sell_order_value_quote = sell_order_plan.order_value_quote or sell_order_value_quote
                    sell_ratio = sell_order_plan.sell_ratio
                    exit_reason_key = sell_order_plan.exit_reason_key
                    sell_reason = sell_order_plan.sell_reason
                    if sell_order_plan.log_message:
                        log(sell_order_plan.log_message)
                    if not sell_order_plan.should_order:
                        pass
                    else:
                        log_order_requested(
                            structured_logger=structured_logger,
                            symbol=symbol,
                            side="exit",
                            reason="market_sell_requested",
                            actual={"sell_amount": amount},
                            metrics=common_metrics,
                        )
                        log(f"[매도] 시장가 매도 시도: {symbol}, 수량={amount}")
                        try:
                            order_submission = submit_upbit_market_sell(
                                exchange=exchange,
                                symbol=symbol,
                                amount=amount,
                                market_data_provider=market_data_provider,
                            )
                        except Exception as order_error:
                            log_order_failure(
                                structured_logger=structured_logger,
                                symbol=symbol,
                                side="exit",
                                message="매도 주문 요청이 실패했습니다.",
                                actual={"sell_amount": amount},
                                metrics=common_metrics,
                                error=order_error,
                                extra={"strategy_version": strategy.version},
                            )
                            continue
                        order = order_submission.order
                        order_request_started_at = order_submission.request_started_at
                        order_response_received_at = order_submission.response_received_at
                        sell_fill_state = apply_alt_sell_fill_state(
                            symbol=symbol,
                            sold_amount=amount,
                            base_free=base_free,
                            current_entry_count=current_entry_count,
                            exit_reason_key=exit_reason_key,
                            full_clear_threshold=0.00000001,
                            now_ts=time.time(),
                            entry_count=entry_count,
                            entry_opened_at=entry_opened_at,
                            last_trade_at=last_trade_at,
                            last_stop_loss_at=last_stop_loss_at,
                            last_stop_loss_context=last_stop_loss_context,
                            current_entry_risk_context=current_entry_risk_context,
                            partial_take_profit_done=partial_take_profit_done,
                            partial_take_profit_last_at=partial_take_profit_last_at,
                            partial_stop_loss_done=partial_stop_loss_done,
                        )
                        remaining_base = sell_fill_state.remaining_base
                        # 손익 계산
                        entry = entry_price.get(symbol)
                        if entry:
                            realized_pnl_pct = (last_close - entry) / entry * 100
                            realized_pnl_quote = (last_close - entry) * amount
                            (
                                fee_quote_estimate,
                                net_realized_pnl_quote,
                                net_realized_pnl_pct,
                            ) = estimate_round_trip_net_pnl(
                                entry_price=entry,
                                exit_price=last_close,
                                amount=amount,
                                fee_rate_pct=config["fee_rate_pct"],
                                realized_pnl_quote=realized_pnl_quote,
                            )
                            daily_realized_pnl_quote += realized_pnl_quote
                            holding_seconds = sell_fill_state.holding_seconds
                            log_order_filled(
                                structured_logger=structured_logger,
                                symbol=symbol,
                                strategy_side="exit",
                                trade_side="sell",
                                strategy_reason=f"{exit_reason_key}_filled",
                                trade_reason=exit_reason_key,
                                actual={
                                    "filled_amount": amount,
                                    "realized_pnl_pct": realized_pnl_pct,
                                    "realized_pnl_quote": realized_pnl_quote,
                                },
                                metrics={
                                    **common_metrics,
                                    "holding_seconds": holding_seconds,
                                },
                            )
                            logger.log_trade_banner(
                                BLUE,
                                f"[{symbol}] {sell_reason} 매도 주문 체결",
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
                            if stop_loss_triggered:
                                notifier.notify_stop_loss_fill(
                                    "UPBIT",
                                    symbol,
                                    format_sell_fill_message(
                                        symbol_regime=symbol_regime,
                                        quote=quote,
                                        base=base,
                                        sell_summary=sell_summary,
                                        realized_pnl_pct=realized_pnl_pct,
                                        realized_pnl_quote=realized_pnl_quote,
                                        fmt=UPBIT_TRADE_MESSAGE_FORMAT,
                                    ),
                                )
                            else:
                                notifier.notify_sell_fill(
                                    "UPBIT",
                                    symbol,
                                    format_sell_fill_message(
                                        symbol_regime=symbol_regime,
                                        quote=quote,
                                        base=base,
                                        sell_summary=sell_summary,
                                        realized_pnl_pct=realized_pnl_pct,
                                        realized_pnl_quote=realized_pnl_quote,
                                        fmt=UPBIT_TRADE_MESSAGE_FORMAT,
                                    ),
                                )
                            log(
                                f"[{symbol}] 실현 손익: {realized_pnl_quote:.2f} {quote} | "
                                f"오늘 누적 실현 손익: {daily_realized_pnl_quote:.2f} {quote}"
                            )
                            trade_history.log_fill(
                                exchange_name="UPBIT",
                                program_name="upbit_ma_crossover_bot",
                                strategy_version=strategy.version,
                                symbol=symbol,
                                side="sell",
                                reason=exit_reason_key,
                                base_currency=base,
                                quote_currency=quote,
                                amount=amount,
                                order_value_quote=amount * last_close,
                                reference_price=last_close,
                                estimated_entry_price=entry,
                                realized_pnl_pct=realized_pnl_pct,
                                realized_pnl_quote=realized_pnl_quote,
                                daily_realized_pnl_quote_after=daily_realized_pnl_quote,
                                entry_count_after=sell_fill_state.entry_count_after,
                                base_free_before=base_free,
                                quote_free_before=quote_free,
                                remaining_base_after_estimate=remaining_base,
                                timeframe=timeframe,
                                ma_period=ma_period,
                                fee_rate_pct=config["fee_rate_pct"],
                                fee_quote_estimate=fee_quote_estimate,
                                net_realized_pnl_quote=net_realized_pnl_quote,
                                net_realized_pnl_pct=net_realized_pnl_pct,
                                highest_price_since_entry=highest_price_since_entry.get(symbol),
                                lowest_price_since_entry=lowest_price_since_entry.get(symbol),
                                mfe_pct=mfe_pct,
                                mae_pct=mae_pct,
                                trailing_armed=alt_profit_trailing_armed.get(symbol, False),
                                request_started_at=order_request_started_at,
                                response_received_at=order_response_received_at,
                                requested_amount=amount,
                                raw_order=order,
                                extra={
                                    "strategy_version": strategy.version,
                                    "sell_ratio": sell_ratio,
                                    "bearish_signal": bearish,
                                    "signal_is_strong": signal_is_strong,
                                    "gap_pct": gap_pct,
                                    "take_profit_pct": effective_min_take_profit_pct,
                                    "configured_take_profit_pct": take_profit_pct,
                                    "stop_loss_pct": stop_loss_pct,
                                    "fee_round_trip_pct": fee_round_trip_pct,
                                    "current_net_pnl_pct_estimate": current_net_realized_pnl_pct,
                                    "fee_protect_min_net_pnl_pct": fee_protect_min_net_pnl_pct,
                                    "profit_protect_triggered": profit_protect_triggered,
                                    "alt_profit_trailing_exit_triggered": alt_profit_trailing_exit_triggered,
                                    "alt_profit_trailing_trigger_reason": alt_profit_trailing_decision.trigger_reason,
                                    "alt_profit_trailing_retrace_from_mfe_pct": (
                                        alt_profit_trailing_decision.profit_retrace_from_mfe_pct
                                    ),
                                    "sol_probe_time_exit_triggered": sol_probe_time_exit_triggered,
                                    "sol_probe_max_hold_minutes": strategy.sol_probe_max_hold_minutes,
                                    "pnl_pct_at_decision": pnl_pct,
                                    "htf_bearish": htf_bearish,
                                    "holding_seconds": holding_seconds,
                                },
                            )
                            # 포지션 청산 후 진입가 제거
                            if sell_fill_state.should_clear_position:
                                clear_alt_position_state(
                                    symbol=symbol,
                                    entry_price=entry_price,
                                    entry_count=entry_count,
                                    entry_opened_at=entry_opened_at,
                                    highest_price_since_entry=highest_price_since_entry,
                                    lowest_price_since_entry=lowest_price_since_entry,
                                    partial_take_profit_done=partial_take_profit_done,
                                    partial_stop_loss_done=partial_stop_loss_done,
                                    unrecoverable_position_warned=unrecoverable_position_warned,
                                )
                                alt_profit_trailing_armed.pop(symbol, None)
                        else:
                            log_order_filled(
                                structured_logger=structured_logger,
                                symbol=symbol,
                                strategy_side="exit",
                                trade_side="sell",
                                strategy_reason="sell_filled_entry_unknown",
                                trade_reason="unknown_entry_sell",
                                actual={"filled_amount": amount},
                                metrics=common_metrics,
                            )
                            logger.log_trade_banner(
                                BLUE,
                                f"[{symbol}] {sell_reason} 매도 주문 체결",
                                f"주문 결과: {order}",
                            )
                            trade_history.log_fill(
                                exchange_name="UPBIT",
                                program_name="upbit_ma_crossover_bot",
                                strategy_version=strategy.version,
                                symbol=symbol,
                                side="sell",
                                reason=exit_reason_key,
                                base_currency=base,
                                quote_currency=quote,
                                amount=amount,
                                order_value_quote=amount * last_close,
                                reference_price=last_close,
                                daily_realized_pnl_quote_after=daily_realized_pnl_quote,
                                entry_count_after=sell_fill_state.entry_count_after,
                                base_free_before=base_free,
                                quote_free_before=quote_free,
                                remaining_base_after_estimate=remaining_base,
                                timeframe=timeframe,
                                ma_period=ma_period,
                                highest_price_since_entry=highest_price_since_entry.get(symbol),
                                lowest_price_since_entry=lowest_price_since_entry.get(symbol),
                                mfe_pct=mfe_pct,
                                mae_pct=mae_pct,
                                trailing_armed=alt_profit_trailing_armed.get(symbol, False),
                                request_started_at=order_request_started_at,
                                response_received_at=order_response_received_at,
                                requested_amount=amount,
                                raw_order=order,
                                extra={
                                    "strategy_version": strategy.version,
                                    "sell_ratio": sell_ratio,
                                    "bearish_signal": bearish,
                                    "signal_is_strong": signal_is_strong,
                                    "gap_pct": gap_pct,
                                    "current_net_pnl_pct_estimate": current_net_realized_pnl_pct,
                                    "fee_protect_min_net_pnl_pct": fee_protect_min_net_pnl_pct,
                                    "profit_protect_triggered": profit_protect_triggered,
                                    "alt_profit_trailing_exit_triggered": alt_profit_trailing_exit_triggered,
                                    "alt_profit_trailing_trigger_reason": alt_profit_trailing_decision.trigger_reason,
                                    "alt_profit_trailing_retrace_from_mfe_pct": (
                                        alt_profit_trailing_decision.profit_retrace_from_mfe_pct
                                    ),
                                    "sol_probe_time_exit_triggered": sol_probe_time_exit_triggered,
                                    "sol_probe_max_hold_minutes": strategy.sol_probe_max_hold_minutes,
                                    "entry_price_unknown": True,
                                    "htf_bearish": htf_bearish,
                                },
                            )
                            if sell_fill_state.should_clear_position:
                                entry_opened_at.pop(symbol, None)
                                partial_take_profit_done.pop(symbol, None)
                                partial_stop_loss_done.pop(symbol, None)
                                alt_profit_trailing_armed.pop(symbol, None)
                        log(
                            f"[{symbol}] 분할 매도 후 남은 진입 카운트: {entry_count.get(symbol, 0)}"
                        )
                else:
                    log(f"[{symbol}] 주문 조건에 해당하지 않아 대기합니다.")

            except Exception as e:
                log(f"[{symbol}] 에러 발생: {repr(e)}")
                log(traceback.format_exc().rstrip())
                structured_logger.log_system(
                    level="ERROR",
                    event="loop_error",
                    message="심볼 처리 중 예외가 발생했습니다.",
                    symbol=symbol,
                    context={"error": repr(e)},
                )
                notifier.notify_error_message("UPBIT", symbol, repr(e))

        # 사용자 설정에 따라 반복
        time.sleep(strategy.loop_interval_sec)


if __name__ == "__main__":
    run_bot()
