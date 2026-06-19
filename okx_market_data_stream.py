"""OKX 시장데이터 웹소켓 수집기.

- 관리 대상 OKX 알트 심볼의 1m/5m 캔들과 BTC/USDT 1m 캔들을 단일 웹소켓 연결로 구독해
  로컬 스냅샷(`logs/runtime/okx_ws/candles/<SYMBOL>__<tf>.json`)으로 저장한다.
- ma_crossover_bot 이 이 스냅샷을 REST 대신 우선 읽어 결정 루프 지연을 줄인다.
  (수집기가 끊기거나 데이터가 오래되면 봇은 자동으로 REST fallback 한다.)
- ccxt.pro 가 현재 aiohttp 버전과 비호환이라 업비트와 동일한 websocket-client 기반으로 구현한다.
"""

from __future__ import annotations

import os
import signal
import sys
import threading
import time
from datetime import datetime

import ccxt

from bot_logger import BotLogger
from core.execution.okx import fetch_ohlcv_okx as fetch_ohlcv_okx_core
from core.market_data.okx_candle_store import OkxCandleStore, merge_okx_candle_rows, okx_channel_to_timeframe
from core.market_data.okx_ws_client import DEFAULT_OKX_BUSINESS_WS_URL, OkxWebSocketClient
from settings.env import load_project_env
from strategy_settings import load_managed_symbols


DEFAULT_OKX_BTC_SYMBOL = "BTC/USDT"
SEED_LIMIT = 100


def symbol_to_inst_id(symbol: str) -> str:
    return symbol.replace("/", "-")


def inst_id_to_symbol(inst_id: str) -> str:
    return inst_id.replace("-", "/")


def build_runtime_settings() -> dict[str, object]:
    """환경 변수에서 OKX 웹소켓 수집기 설정을 읽는다."""
    load_project_env()
    return {
        "url": os.getenv("OKX_WEBSOCKET_BUSINESS_URL", DEFAULT_OKX_BUSINESS_WS_URL).strip(),
        "reconnect_delay_sec": float(os.getenv("OKX_WS_RECONNECT_DELAY_SEC", "3.0")),
        "ping_interval_sec": float(os.getenv("OKX_WS_PING_INTERVAL_SEC", "20.0")),
        "heartbeat_interval_sec": float(os.getenv("OKX_WS_HEARTBEAT_INTERVAL_SEC", "60.0")),
        "max_idle_sec": float(os.getenv("OKX_WS_MAX_IDLE_SEC", "120.0")),
        "write_interval_sec": float(os.getenv("OKX_WS_WRITE_INTERVAL_SEC", "0.4")),
    }


def build_subscriptions(alt_symbols: list[str]) -> list[tuple[str, str]]:
    """알트 심볼은 1m+5m, BTC 레퍼런스는 1m 을 구독한다."""
    subscriptions: list[tuple[str, str]] = []
    for symbol in alt_symbols:
        inst_id = symbol_to_inst_id(symbol)
        subscriptions.append((inst_id, "candle1m"))
        subscriptions.append((inst_id, "candle5m"))
    btc_inst = symbol_to_inst_id(DEFAULT_OKX_BTC_SYMBOL)
    if (btc_inst, "candle1m") not in subscriptions:
        subscriptions.append((btc_inst, "candle1m"))
    return subscriptions


def distinct_symbol_timeframes(subscriptions: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """구독 목록에서 (심볼, timeframe) 고유 조합을 만든다."""
    keys: list[tuple[str, str]] = []
    for inst_id, channel in subscriptions:
        tf = okx_channel_to_timeframe(channel)
        if tf is None:
            continue
        key = (inst_id_to_symbol(inst_id), tf)
        if key not in keys:
            keys.append(key)
    return keys


def seed_buffers(
    rest_client,
    seed_keys: list[tuple[str, str]],
    buffers: dict[tuple[str, str], list[list[float]]],
    store: OkxCandleStore,
    log,
) -> int:
    """REST 로 최근 캔들을 받아 버퍼를 채운다(웹소켓은 과거 캔들을 backfill 하지 않으므로 필수)."""
    seeded = 0
    for symbol, tf in seed_keys:
        try:
            rows = fetch_ohlcv_okx_core(rest_client, symbol, timeframe=tf, limit=SEED_LIMIT)
        except Exception as error:
            log(f"OKX 캔들 seed 실패: {symbol} {tf} {error!r}")
            continue
        if not rows:
            continue
        merged = merge_okx_candle_rows(buffers.get((symbol, tf), []), rows)
        buffers[(symbol, tf)] = merged
        try:
            store.write_candles(symbol, tf, merged, force=True)
            seeded += 1
        except OSError as error:
            log(f"OKX 캔들 seed 저장 오류: {symbol} {tf} {error!r}")
    return seeded


def main() -> int:
    settings = build_runtime_settings()
    logger = BotLogger("okx_market_data_stream")
    log = logger.log

    alt_symbols = [s for s in load_managed_symbols("okx") if s != DEFAULT_OKX_BTC_SYMBOL]
    subscriptions = build_subscriptions(alt_symbols)
    seed_keys = distinct_symbol_timeframes(subscriptions)
    store = OkxCandleStore(write_interval_sec=float(settings["write_interval_sec"]))
    buffers: dict[tuple[str, str], list[list[float]]] = {}
    rest_client = ccxt.okx({"enableRateLimit": True})
    health_state: dict[str, object] = {
        "captured_at_local": datetime.now().astimezone().isoformat(),
        "managed_symbols": alt_symbols,
        "subscription_count": len(subscriptions),
    }

    def handle_candle(inst_id: str, channel: str, data: list[list[str]]) -> None:
        timeframe = okx_channel_to_timeframe(channel)
        if timeframe is None:
            return
        symbol = inst_id_to_symbol(inst_id)
        key = (symbol, timeframe)
        merged = merge_okx_candle_rows(buffers.get(key, []), data)
        buffers[key] = merged
        try:
            store.write_candles(symbol, timeframe, merged)
        except OSError as error:
            log(f"OKX 캔들 저장 오류: {symbol} {timeframe} {error!r}")

    def handle_state(payload: dict) -> None:
        health_state["captured_at_local"] = datetime.now().astimezone().isoformat()
        health_state["connected"] = payload.get("connected")
        health_state["event"] = payload.get("event")
        health_state["last_message_received_at"] = payload.get("last_message_received_at")
        health_state["reconnect_count"] = payload.get("reconnect_count")
        store.write_health(health_state)
        event = payload.get("event")
        if event == "connected":
            log(f"OKX 캔들 웹소켓 연결 성공: {len(subscriptions)}개 채널 구독 ({', '.join(alt_symbols)} + BTC)")
        elif event == "error":
            log(f"OKX 캔들 웹소켓 오류: {payload.get('error')}")
        elif event == "closed":
            log(f"OKX 캔들 웹소켓 종료: status={payload.get('status_code')} message={payload.get('message')}")
        elif event == "stale_reconnect":
            log(f"OKX 캔들 웹소켓 무수신 재연결: idle={float(payload.get('idle_sec', 0.0)):.1f}초")

    client = OkxWebSocketClient(
        url=str(settings["url"]),
        subscriptions=subscriptions,
        on_candle=handle_candle,
        on_state=handle_state,
        reconnect_delay_sec=float(settings["reconnect_delay_sec"]),
        ping_interval_sec=float(settings["ping_interval_sec"]),
        heartbeat_interval_sec=float(settings["heartbeat_interval_sec"]),
        max_idle_sec=float(settings["max_idle_sec"]),
    )

    def _request_stop(*_: object) -> None:
        log("종료 신호를 받아 OKX 웹소켓 수집기를 중단합니다.")
        client.stop()

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    log("=== OKX 웹소켓 시장데이터 수집기 시작 ===")
    log(f"구독 심볼(알트): {', '.join(alt_symbols)} + {DEFAULT_OKX_BTC_SYMBOL}(1m)")
    log(f"웹소켓 URL: {settings['url']}")

    # 웹소켓은 과거 캔들을 backfill 하지 않으므로 시작 시 REST 로 버퍼를 채운다.
    seeded = seed_buffers(rest_client, seed_keys, buffers, store, log)
    log(f"REST seed 완료: {seeded}/{len(seed_keys)} (심볼,timeframe)")

    stop_event = threading.Event()

    def _reseed_loop() -> None:
        # 재연결 중 누락된 캔들을 메우기 위해 주기적으로 REST 로 버퍼를 보정한다.
        while not stop_event.wait(300.0):
            try:
                seed_buffers(rest_client, seed_keys, buffers, store, log)
            except Exception as error:
                log(f"OKX 캔들 주기적 re-seed 오류: {error!r}")

    reseed_thread = threading.Thread(target=_reseed_loop, name="okx-candle-reseed", daemon=True)
    reseed_thread.start()

    client.run_forever()
    stop_event.set()
    store.write_health(
        {
            "captured_at_local": datetime.now().astimezone().isoformat(),
            "event": "stopped",
            "connected": False,
            "managed_symbols": alt_symbols,
        }
    )
    log("OKX 웹소켓 시장데이터 수집기를 종료합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
