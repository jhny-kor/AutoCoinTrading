"""
수정 요약
- 스냅샷 파일 저장 오류가 웹소켓 연결 루프를 끊지 않도록 storage_error health 기록과 제한적 로그를 추가했다.
- heartbeat health 기록과 max idle 기반 재연결 설정을 추가해 수집기 정상 여부를 운영에서 판단할 수 있게 개선
- 업비트 private 웹소켓을 추가해 myOrder / myAsset 이벤트를 실시간 수집하고 로컬 latest/jsonl 파일로 저장하도록 확장했다.
- 업비트 공개 웹소켓에서 trade, orderbook, candle.1m 스트림을 공용으로 수집해 로컬 스냅샷으로 저장하는 1단계 수집기를 추가했다.
- 수집기 연결 상태를 health JSON 으로 남기고 봇 프로세스 관리 대상에 연결할 준비를 맞췄다.

업비트 시장데이터 웹소켓 수집기

- 단일 `.env` 대신 중앙 환경 로더를 통해 `.env.settings`, `.env.secrets`, `.env.local` 까지 읽을 수 있게 정리

- 목적:
  - 업비트 알트/BTC/분석 수집기가 나중에 같은 실시간 시세를 공유할 수 있도록 1단계 기반을 만든다.
- 현재 단계:
  - 시장 데이터만 웹소켓으로 수집한다.
  - 주문과 잔고는 기존 REST 구조를 유지한다.
"""

from __future__ import annotations

import os
import signal
import sys
import time
from datetime import datetime
import threading

from bot_logger import BotLogger
from core.market_data.upbit_private_auth import build_upbit_private_ws_headers
from core.market_data.upbit_market_state import (
    UpbitMarketStateStore,
    symbol_to_upbit_market,
)
from core.market_data.upbit_snapshot_store import UpbitSnapshotStore
from core.market_data.upbit_ws_client import UpbitWebSocketClient
from settings.env import load_project_env
from strategy_settings import load_managed_symbols


DEFAULT_UPBIT_WS_URL = "wss://api.upbit.com/websocket/v1"
DEFAULT_UPBIT_PRIVATE_WS_URL = "wss://api.upbit.com/websocket/v1/private"


def build_runtime_settings() -> dict[str, float | str | bool]:
    """환경 변수에서 업비트 웹소켓 수집기 설정을 읽는다."""
    load_project_env()
    return {
        "url": os.getenv("UPBIT_WEBSOCKET_URL", DEFAULT_UPBIT_WS_URL).strip(),
        "private_url": os.getenv(
            "UPBIT_PRIVATE_WEBSOCKET_URL",
            DEFAULT_UPBIT_PRIVATE_WS_URL,
        ).strip(),
        "reconnect_delay_sec": float(os.getenv("UPBIT_WS_RECONNECT_DELAY_SEC", "3.0")),
        "ping_interval_sec": float(os.getenv("UPBIT_WS_PING_INTERVAL_SEC", "20.0")),
        "latest_write_interval_sec": float(
            os.getenv("UPBIT_WS_LATEST_WRITE_INTERVAL_SEC", "0.4")
        ),
        "heartbeat_interval_sec": float(
            os.getenv("UPBIT_WS_HEARTBEAT_INTERVAL_SEC", "60.0")
        ),
        "max_idle_sec": float(os.getenv("UPBIT_WS_MAX_IDLE_SEC", "120.0")),
        "enable_trade": os.getenv("UPBIT_WS_ENABLE_TRADE", "true").strip().lower() in {"1", "true", "yes", "y", "on"},
        "enable_orderbook": os.getenv("UPBIT_WS_ENABLE_ORDERBOOK", "true").strip().lower() in {"1", "true", "yes", "y", "on"},
        "enable_candle_1m": os.getenv("UPBIT_WS_ENABLE_CANDLE_1M", "true").strip().lower() in {"1", "true", "yes", "y", "on"},
        "enable_private": os.getenv("UPBIT_WS_ENABLE_PRIVATE", "true").strip().lower() in {"1", "true", "yes", "y", "on"},
        "enable_myorder": os.getenv("UPBIT_WS_ENABLE_MYORDER", "true").strip().lower() in {"1", "true", "yes", "y", "on"},
        "enable_myasset": os.getenv("UPBIT_WS_ENABLE_MYASSET", "true").strip().lower() in {"1", "true", "yes", "y", "on"},
        "access_key": os.getenv("UPBIT_API_KEY", "").strip(),
        "secret_key": os.getenv("UPBIT_API_SECRET", "").strip(),
    }


def main() -> int:
    """업비트 웹소켓 수집기 진입점."""
    settings = build_runtime_settings()
    logger = BotLogger("upbit_market_data_stream")
    log = logger.log

    symbols = load_managed_symbols("upbit")
    markets = [symbol_to_upbit_market(symbol) for symbol in symbols]
    state_store = UpbitMarketStateStore(markets)
    snapshot_store = UpbitSnapshotStore(
        latest_write_interval_sec=float(settings["latest_write_interval_sec"]),
    )
    health_state: dict[str, object] = {
        "captured_at_local": datetime.now().astimezone().isoformat(),
        "managed_symbols": symbols,
    }
    last_storage_error_log_at = 0.0

    def handle_payload(payload: dict) -> None:
        nonlocal last_storage_error_log_at
        state = state_store.apply_payload(payload)
        if state is None:
            return
        snapshot = state.to_snapshot()
        try:
            snapshot_store.write_latest(snapshot)
            snapshot_store.append_candle_1m(snapshot)
        except OSError as error:
            now_ts = time.time()
            health_state["captured_at_local"] = datetime.now().astimezone().isoformat()
            health_state["storage_error"] = repr(error)
            health_state["storage_error_symbol"] = snapshot.get("symbol")
            try:
                snapshot_store.write_health(health_state)
            except OSError:
                pass
            if now_ts - last_storage_error_log_at >= 30.0:
                last_storage_error_log_at = now_ts
                log(
                    f"업비트 웹소켓 스냅샷 저장 오류: {snapshot.get('symbol')} {error!r}"
                )

    def handle_state(payload: dict) -> None:
        health_state["captured_at_local"] = datetime.now().astimezone().isoformat()
        health_state["public"] = payload
        health_state["connected"] = payload.get("connected")
        health_state["event"] = payload.get("event")
        health_state["last_message_received_at"] = payload.get("last_message_received_at")
        health_state["public_url"] = payload.get("url")
        snapshot_store.write_health(health_state)
        event = payload.get("event")
        if event == "connected":
            log(
                f"업비트 웹소켓 연결 성공: 시장 {len(markets)}개 구독 "
                f"({', '.join(symbols)})"
            )
        elif event == "error":
            log(f"업비트 웹소켓 오류: {payload.get('error')}")
        elif event == "closed":
            log(
                f"업비트 웹소켓 종료: status={payload.get('status_code')} "
                f"message={payload.get('message')}"
            )
        elif event == "stale_reconnect":
            log(
                f"업비트 웹소켓 무수신 재연결: idle={payload.get('idle_sec'):.1f}초"
            )

    def handle_private_payload(payload: dict) -> None:
        event_type = str(payload.get("type", "") or "")
        event_name = event_type.lower() or "private_event"
        event_payload = {
            "captured_at_local": datetime.now().astimezone().isoformat(),
            **payload,
        }
        snapshot_store.append_private_event(event_name, event_payload)
        if event_type == "myAsset":
            snapshot_store.write_private_latest("myasset_latest", event_payload)
        elif event_type == "myOrder":
            snapshot_store.write_private_latest("myorder_latest", event_payload)

    def handle_private_state(payload: dict) -> None:
        health_state["captured_at_local"] = datetime.now().astimezone().isoformat()
        health_state["private"] = payload
        snapshot_store.write_health(health_state)
        event = payload.get("event")
        if event == "connected":
            log("업비트 private 웹소켓 연결 성공: myOrder / myAsset 구독")
        elif event == "error":
            log(f"업비트 private 웹소켓 오류: {payload.get('error')}")
        elif event == "closed":
            log(
                f"업비트 private 웹소켓 종료: status={payload.get('status_code')} "
                f"message={payload.get('message')}"
            )
        elif event == "stale_reconnect":
            log(
                f"업비트 private 웹소켓 무수신 재연결: idle={payload.get('idle_sec'):.1f}초"
            )

    client = UpbitWebSocketClient(
        url=str(settings["url"]),
        markets=markets,
        on_payload=handle_payload,
        on_state=handle_state,
        subscribe_trade=bool(settings["enable_trade"]),
        subscribe_orderbook=bool(settings["enable_orderbook"]),
        subscribe_candle_1m=bool(settings["enable_candle_1m"]),
        reconnect_delay_sec=float(settings["reconnect_delay_sec"]),
        ping_interval_sec=float(settings["ping_interval_sec"]),
        heartbeat_interval_sec=float(settings["heartbeat_interval_sec"]),
        max_idle_sec=float(settings["max_idle_sec"]),
        client_label="public",
    )

    private_client = None
    private_thread = None
    if (
        bool(settings["enable_private"])
        and bool(settings["access_key"])
        and bool(settings["secret_key"])
        and (bool(settings["enable_myorder"]) or bool(settings["enable_myasset"]))
    ):
        private_payload: list[dict[str, object]] = [{"ticket": f"private-{int(time.time())}"}]
        if bool(settings["enable_myorder"]):
            private_payload.append({"type": "myOrder"})
        if bool(settings["enable_myasset"]):
            private_payload.append({"type": "myAsset"})
        private_payload.append({"format": "DEFAULT"})
        private_headers = build_upbit_private_ws_headers(
            str(settings["access_key"]),
            str(settings["secret_key"]),
        )
        private_client = UpbitWebSocketClient(
            url=str(settings["private_url"]),
            markets=[],
            on_payload=handle_private_payload,
            on_state=handle_private_state,
            subscribe_trade=False,
            subscribe_orderbook=False,
            subscribe_candle_1m=False,
            reconnect_delay_sec=float(settings["reconnect_delay_sec"]),
            ping_interval_sec=float(settings["ping_interval_sec"]),
            heartbeat_interval_sec=float(settings["heartbeat_interval_sec"]),
            max_idle_sec=float(settings["max_idle_sec"]),
            subscription_payload=private_payload,
            headers=private_headers,
            client_label="private",
        )
        private_thread = threading.Thread(
            target=private_client.run_forever,
            name="upbit-private-ws",
            daemon=True,
        )

    def _request_stop(*_: object) -> None:
        log("종료 신호를 받아 업비트 웹소켓 수집기를 중단합니다.")
        client.stop()
        if private_client is not None:
            private_client.stop()

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    log("=== 업비트 웹소켓 시장데이터 수집기 시작 ===")
    log(f"구독 심볼: {', '.join(symbols)}")
    log(f"웹소켓 URL: {settings['url']}")
    if private_thread is not None:
        log(f"업비트 private 웹소켓 URL: {settings['private_url']}")
        private_thread.start()
    client.run_forever()
    if private_thread is not None:
        private_thread.join(timeout=5.0)
    snapshot_store.write_health(
        {
            "captured_at_local": datetime.now().astimezone().isoformat(),
            "event": "stopped",
            "managed_symbols": symbols,
            "connected": False,
            "last_message_received_at": client.last_message_received_at,
            "public": health_state.get("public"),
            "private": health_state.get("private"),
        }
    )
    log("업비트 웹소켓 시장데이터 수집기를 종료합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
