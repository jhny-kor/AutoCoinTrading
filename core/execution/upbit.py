"""
수정 요약
- 업비트 심볼용 최소 market metadata 를 로컬에서 채워 `market/all` 네트워크 조회 없이 OHLCV/호가/수량 정밀도 경로가 동작하도록 보강
- 업비트 RequestTimeout, 네트워크 단절, 거래소 일시 장애를 공통 재시도 대상으로 포함해 반복 loop_error 를 줄이도록 보강
- 업비트 기본 요청 타임아웃을 10초에서 20초로 늘려 느린 캔들 응답에도 즉시 실패하지 않도록 조정
- `config/runtime.toml` + env override 레이어를 중앙 환경 로더로 읽도록 정리
- typed config access helper 를 사용해 업비트 설정 로딩의 문자열 파싱을 일관되게 정리
- 업비트 myAsset latest 를 잔고 조회 우선 경로로 읽고 myOrder 최근 이벤트를 주문 응답 보강에 쓸 helper 를 추가했다.
- 업비트 5분/15분 OHLCV 도 웹소켓 1분 캔들 리샘플 우선, stale 시 REST fallback 으로 읽게 확장했다.
- 업비트 1분봉 OHLCV 를 웹소켓 1분 캔들 우선, stale 시 REST fallback 으로 읽는 helper 를 추가해 phase 3 전환을 시작했다.
- 업비트 웹소켓 latest 스냅샷을 읽는 market data provider 설정과 생성 helper 를 추가해 best bid 를 웹소켓 우선으로 읽을 준비를 맞췄다.
- 업비트 잔고/호가 조회를 짧은 TTL 캐시로 재사용하고 최소 주문 경계 근처에서만 호가를 재조회하도록 지연 완화 경로를 추가했다.
- 업비트 시장가 매도도 공통 재시도 경로와 캐시 무효화 helper 를 쓰도록 확장했다.
- 업비트 설정 로드, 429 재시도, 주문 버퍼, 잔고/호가 조회, 시장가 주문 유틸을 공통 모듈로 분리했다.
- 알트/BTC 봇이 같은 업비트 실행 경로를 재사용하도록 정리했다.
- 업비트 REST 호출을 공식 Rate Limit 그룹별 limiter 로 분리해 현재가 조회 직후 주문 지연을 줄였다.
- 업비트 REST 그룹별 limiter 가 Oracle 호스트 전체에서 상태를 공유하도록 설정 값을 전달한다.
"""

from __future__ import annotations

import ccxt

from core.execution.upbit_markets import (
    apply_upbit_buy_order_buffer,
    ensure_upbit_market_cached,
    invalidate_upbit_balance_cache,
    invalidate_upbit_orderbook_cache,
    safe_amount_to_precision_upbit,
    should_refresh_best_bid_upbit,
)
from core.execution.upbit_rate_limits import (
    call_upbit_with_retry,
    is_upbit_retryable_error,
)
from core.execution.upbit_rest import (
    create_market_buy_order_upbit,
    create_market_sell_order_upbit,
    enrich_upbit_order_with_private_event,
    fetch_best_bid_upbit,
    fetch_ohlcv_upbit,
    fetch_ohlcv_upbit_with_provider,
    get_spot_balances_upbit,
    get_spot_balances_upbit_with_provider,
)
from core.market_data.upbit_provider import UpbitMarketDataProvider
from settings.config_access import env_bool, env_float, env_int, env_str
from settings.env import load_project_env


def load_upbit_config() -> dict:
    load_project_env()

    api_key = env_str("UPBIT_API_KEY", required=True)
    api_secret = env_str("UPBIT_API_SECRET", required=True)

    if not api_key or not api_secret:
        raise RuntimeError(
            "UPBIT_API_KEY / UPBIT_API_SECRET 가 secrets 레이어에 설정되어 있지 않습니다."
        )

    risk_per_trade = env_float("UPBIT_TRADE_RISK_PER_TRADE", 0.05)
    fee_rate_pct = env_float("UPBIT_FEE_RATE_PCT", 0.05)
    max_daily_loss_quote = env_float("UPBIT_MAX_DAILY_LOSS_QUOTE", 5000)
    request_retry_count = env_int("UPBIT_REQUEST_RETRY_COUNT", 3)
    request_retry_delay_sec = env_float("UPBIT_REQUEST_RETRY_DELAY_SEC", 1.2)
    krw_order_buffer_pct = env_float("UPBIT_KRW_ORDER_BUFFER_PCT", 0.002)
    krw_order_buffer_krw = env_float("UPBIT_KRW_ORDER_BUFFER_KRW", 1000)
    request_timeout_ms = env_int("UPBIT_REQUEST_TIMEOUT_MS", 20000)
    balance_cache_ttl_sec = env_float("UPBIT_BALANCE_CACHE_TTL_SEC", 1.0)
    orderbook_cache_ttl_sec = env_float("UPBIT_ORDERBOOK_CACHE_TTL_SEC", 0.8)
    best_bid_refresh_buffer_pct = env_float("UPBIT_BEST_BID_REFRESH_BUFFER_PCT", 0.30)
    ws_provider_enabled = env_bool("UPBIT_WS_PROVIDER_ENABLED", True)
    ws_provider_root_dir = env_str("UPBIT_WS_PROVIDER_ROOT_DIR", "logs/runtime/upbit_ws").strip()
    ws_provider_cache_ttl_sec = env_float("UPBIT_WS_PROVIDER_CACHE_TTL_SEC", 0.25)
    ws_provider_stale_sec = env_float("UPBIT_WS_PROVIDER_STALE_SEC", 5.0)
    group_rate_limit_enabled = env_bool("UPBIT_GROUP_RATE_LIMIT_ENABLED", True)
    shared_rate_limit_enabled = env_bool("UPBIT_RATE_LIMIT_SHARED_ENABLED", True)
    shared_rate_limit_state_dir = env_str(
        "UPBIT_RATE_LIMIT_SHARED_STATE_DIR",
        "logs/runtime/upbit_rate_limits",
    ).strip()

    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "risk_per_trade": risk_per_trade,
        "fee_rate_pct": fee_rate_pct,
        "max_daily_loss_quote": max_daily_loss_quote,
        "request_retry_count": request_retry_count,
        "request_retry_delay_sec": request_retry_delay_sec,
        "krw_order_buffer_pct": krw_order_buffer_pct,
        "krw_order_buffer_krw": krw_order_buffer_krw,
        "request_timeout_ms": request_timeout_ms,
        "balance_cache_ttl_sec": balance_cache_ttl_sec,
        "orderbook_cache_ttl_sec": orderbook_cache_ttl_sec,
        "best_bid_refresh_buffer_pct": best_bid_refresh_buffer_pct,
        "ws_provider_enabled": ws_provider_enabled,
        "ws_provider_root_dir": ws_provider_root_dir,
        "ws_provider_cache_ttl_sec": ws_provider_cache_ttl_sec,
        "ws_provider_stale_sec": ws_provider_stale_sec,
        "group_rate_limit_enabled": group_rate_limit_enabled,
        "shared_rate_limit_enabled": shared_rate_limit_enabled,
        "shared_rate_limit_state_dir": shared_rate_limit_state_dir,
    }


def create_upbit_client(config: dict) -> ccxt.upbit:
    return ccxt.upbit(
        {
            "apiKey": config["api_key"],
            "secret": config["api_secret"],
            "enableRateLimit": False,
            "timeout": config["request_timeout_ms"],
            "options": {
                "adjustForTimeDifference": True,
                "upbit_request_retry_count": config["request_retry_count"],
                "upbit_request_retry_delay_sec": config["request_retry_delay_sec"],
                "upbit_balance_cache_ttl_sec": config["balance_cache_ttl_sec"],
                "upbit_orderbook_cache_ttl_sec": config["orderbook_cache_ttl_sec"],
                "upbit_best_bid_refresh_buffer_pct": config["best_bid_refresh_buffer_pct"],
                "upbit_group_rate_limit_enabled": config["group_rate_limit_enabled"],
                "upbit_rate_limit_shared_enabled": config["shared_rate_limit_enabled"],
                "upbit_rate_limit_shared_state_dir": config["shared_rate_limit_state_dir"],
            },
        }
    )


def parse_bool(raw: str | None, default: bool = False) -> bool:
    """문자열 불리언 값을 파싱한다."""
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def create_upbit_market_data_provider(config: dict) -> UpbitMarketDataProvider | None:
    """업비트 웹소켓 latest 스냅샷 provider 를 생성한다."""
    if not config.get("ws_provider_enabled", True):
        return None
    return UpbitMarketDataProvider(
        root_dir=str(config.get("ws_provider_root_dir", "logs/runtime/upbit_ws")),
        cache_ttl_sec=float(config.get("ws_provider_cache_ttl_sec", 0.25) or 0.25),
        stale_sec=float(config.get("ws_provider_stale_sec", 5.0) or 5.0),
    )
