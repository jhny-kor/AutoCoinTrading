"""
수정 요약
- stop/stale 재연결 시 현재 WebSocketApp 을 직접 닫아 run loop 가 남아 자동복구 재시작을 반복하지 않도록 보강했다.
- heartbeat 상태 이벤트와 최대 무수신 시간 초과 시 세션 재연결을 요청하는 watchdog 을 추가
- 업비트 private 웹소켓도 같은 클라이언트로 처리할 수 있도록 사용자 지정 구독 payload, 헤더, 라벨을 지원하도록 확장했다.
- 업비트 시세용 공개 웹소켓 연결, 재연결, 구독 메시지 전송, payload 디코딩을 담당하는 경량 클라이언트를 추가했다.
- trade, orderbook, candle.1m 스트림을 한 연결에서 함께 구독하도록 구성했다.
"""

from __future__ import annotations

import json
import ssl
import threading
import time
import uuid
from collections.abc import Callable
from typing import Any

import websocket


PayloadHandler = Callable[[dict[str, Any]], None]
StateHandler = Callable[[dict[str, Any]], None]


class UpbitWebSocketClient:
    """업비트 공개 시세 웹소켓 클라이언트."""

    def __init__(
        self,
        *,
        url: str,
        markets: list[str] | None,
        on_payload: PayloadHandler,
        on_state: StateHandler | None = None,
        subscribe_trade: bool = True,
        subscribe_orderbook: bool = True,
        subscribe_candle_1m: bool = True,
        reconnect_delay_sec: float = 3.0,
        ping_interval_sec: float = 20.0,
        subscription_payload: list[dict[str, Any]] | None = None,
        headers: list[str] | None = None,
        client_label: str = "public",
        heartbeat_interval_sec: float = 60.0,
        max_idle_sec: float = 120.0,
    ) -> None:
        self.url = url
        self.markets = sorted(set(markets or []))
        self.on_payload = on_payload
        self.on_state = on_state
        self.subscribe_trade = subscribe_trade
        self.subscribe_orderbook = subscribe_orderbook
        self.subscribe_candle_1m = subscribe_candle_1m
        self.reconnect_delay_sec = reconnect_delay_sec
        self.ping_interval_sec = ping_interval_sec
        self.subscription_payload = subscription_payload
        self.headers = headers or []
        self.client_label = client_label
        self.heartbeat_interval_sec = heartbeat_interval_sec
        self.max_idle_sec = max_idle_sec
        self.stop_event = threading.Event()
        self.connected = False
        self.last_message_received_at = 0.0
        self.connection_started_at = 0.0
        self.reconnect_count = 0
        self.last_heartbeat_at = 0.0
        self._active_app: websocket.WebSocketApp | None = None
        self._active_app_lock = threading.Lock()

    def build_subscription_payload(self) -> list[dict[str, Any]]:
        """업비트 웹소켓 구독 payload 를 생성한다."""
        if self.subscription_payload is not None:
            return self.subscription_payload
        payload: list[dict[str, Any]] = [{"ticket": str(uuid.uuid4())}]
        if self.subscribe_trade:
            payload.append(
                {
                    "type": "trade",
                    "codes": self.markets,
                    "is_only_realtime": True,
                }
            )
        if self.subscribe_orderbook:
            payload.append(
                {
                    "type": "orderbook",
                    "codes": self.markets,
                    "is_only_realtime": True,
                }
            )
        if self.subscribe_candle_1m:
            payload.append(
                {
                    "type": "candle.1m",
                    "codes": self.markets,
                    "is_only_realtime": True,
                }
            )
        payload.append({"format": "DEFAULT"})
        return payload

    def build_state_snapshot(self, *, event: str) -> dict[str, Any]:
        """현재 연결 상태 스냅샷을 반환한다."""
        return {
            "event": event,
            "url": self.url,
            "client_label": self.client_label,
            "market_count": len(self.markets),
            "connected": self.connected,
            "reconnect_count": self.reconnect_count,
            "connection_started_at": self.connection_started_at,
            "last_message_received_at": self.last_message_received_at,
            "captured_at": time.time(),
        }

    def stop(self) -> None:
        """수집기 종료를 요청한다."""
        self.stop_event.set()
        self._close_active_app()

    def run_forever(self) -> None:
        """종료 요청 전까지 연결/재연결을 반복한다."""
        while not self.stop_event.is_set():
            self._run_single_session()
            if self.stop_event.is_set():
                break
            self.reconnect_count += 1
            time.sleep(self.reconnect_delay_sec)

    def _run_single_session(self) -> None:
        subscription_payload = self.build_subscription_payload()
        app_holder: dict[str, websocket.WebSocketApp] = {}

        def on_open(ws_app: websocket.WebSocketApp) -> None:
            self.connected = True
            self.connection_started_at = time.time()
            self.last_message_received_at = 0.0
            self.last_heartbeat_at = 0.0
            ws_app.send(json.dumps(subscription_payload))
            self._emit_state("connected")

        def on_message(_: websocket.WebSocketApp, message: str | bytes) -> None:
            self.last_message_received_at = time.time()
            payload = _decode_message(message)
            if isinstance(payload, dict):
                self.on_payload(payload)

        def on_error(_: websocket.WebSocketApp, error: Any) -> None:
            self.connected = False
            self._emit_state("error", error=str(error))

        def on_close(_: websocket.WebSocketApp, status_code: Any, message: Any) -> None:
            self.connected = False
            self._emit_state(
                "closed",
                status_code=status_code,
                message=message,
            )

        app = websocket.WebSocketApp(
            self.url,
            header=self.headers,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        app_holder["app"] = app
        self._set_active_app(app)
        session_stop = threading.Event()
        watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            args=(app_holder, session_stop),
            name=f"upbit-{self.client_label}-watchdog",
            daemon=True,
        )
        watchdog_thread.start()
        try:
            app.run_forever(
                ping_interval=self.ping_interval_sec,
                ping_timeout=max(5.0, self.ping_interval_sec / 2),
                sslopt={"cert_reqs": ssl.CERT_REQUIRED},
            )
        finally:
            session_stop.set()  # 이 세션의 watchdog 만 확실히 종료(좀비 스레드 방지).
            self._clear_active_app(app)
            watchdog_thread.join(timeout=1.0)

    def _emit_state(self, event: str, **extra: Any) -> None:
        if self.on_state is None:
            return
        payload = self.build_state_snapshot(event=event)
        payload.update(extra)
        self.on_state(payload)

    def _watchdog_loop(
        self,
        app_holder: dict[str, websocket.WebSocketApp],
        session_stop: threading.Event,
    ) -> None:
        """heartbeat 를 내보내고 무수신 상태가 길면 현재 세션을 닫아 재연결을 유도한다."""
        while not session_stop.is_set() and not self.stop_event.is_set():
            time.sleep(1.0)
            now_ts = time.time()
            if self.heartbeat_interval_sec > 0 and (
                now_ts - self.last_heartbeat_at
            ) >= self.heartbeat_interval_sec:
                self.last_heartbeat_at = now_ts
                self._emit_state("heartbeat")

            if not self.connected or self.max_idle_sec <= 0:
                continue

            last_activity_ts = self.last_message_received_at or self.connection_started_at
            if last_activity_ts <= 0:
                continue
            idle_sec = now_ts - last_activity_ts
            if idle_sec < self.max_idle_sec:
                continue

            self._emit_state("stale_reconnect", idle_sec=idle_sec)
            app = app_holder.get("app")
            if app is not None:
                self._close_app(app)
            break

    def _set_active_app(self, app: websocket.WebSocketApp) -> None:
        with self._active_app_lock:
            self._active_app = app

    def _clear_active_app(self, app: websocket.WebSocketApp) -> None:
        with self._active_app_lock:
            if self._active_app is app:
                self._active_app = None

    def _close_active_app(self) -> None:
        with self._active_app_lock:
            app = self._active_app
        if app is not None:
            self._close_app(app)

    @staticmethod
    def _close_app(app: websocket.WebSocketApp) -> None:
        # keep_running=False + 소켓 shutdown(SHUT_RDWR) 으로 ping_timeout(약 10초)만큼
        # select 에 블록된 run_forever 를 즉시 EOF 로 깨운다. 실제 close 는 run_forever
        # teardown 이 수행한다 — 여기서 fd 를 닫으면 select 재시도가 EOF 를 놓쳐 종료가 늦어진다.
        try:
            app.keep_running = False
        except Exception:
            pass
        try:
            sock = getattr(app, "sock", None)
            if sock is not None:
                sock.abort()
        except Exception:
            pass


def _decode_message(message: str | bytes) -> dict[str, Any] | None:
    """업비트 웹소켓 메시지를 JSON 딕셔너리로 디코딩한다."""
    if isinstance(message, bytes):
        raw_text = message.decode("utf-8")
    else:
        raw_text = message
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None
