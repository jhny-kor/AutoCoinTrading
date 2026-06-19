"""OKX 공개 캔들 웹소켓 클라이언트.

- ccxt.pro 가 현재 환경의 aiohttp 버전과 비호환이라(`parse_frame`), 업비트와 동일하게
  `websocket-client` 기반의 경량 동기 클라이언트로 OKX v5 candle 채널을 구독한다.
- OKX candle 채널은 business 엔드포인트(`/ws/v5/business`)에서 제공된다.
- 메시지: {"arg":{"channel":"candle1m","instId":"ETH-USDT"},"data":[[ts,o,h,l,c,vol,volCcy,volCcyQuote,confirm]]}
"""

from __future__ import annotations

import json
import ssl
import threading
import time
from collections.abc import Callable
from typing import Any

import websocket


CandleHandler = Callable[[str, str, list[list[str]]], None]
StateHandler = Callable[[dict[str, Any]], None]

DEFAULT_OKX_BUSINESS_WS_URL = "wss://ws.okx.com:8443/ws/v5/business"


class OkxWebSocketClient:
    """OKX 공개 캔들 웹소켓 클라이언트(websocket-client 기반)."""

    def __init__(
        self,
        *,
        url: str,
        subscriptions: list[tuple[str, str]],
        on_candle: CandleHandler,
        on_state: StateHandler | None = None,
        reconnect_delay_sec: float = 3.0,
        ping_interval_sec: float = 20.0,
        heartbeat_interval_sec: float = 60.0,
        max_idle_sec: float = 120.0,
    ) -> None:
        # subscriptions: [(instId, channel)] 예: [("ETH-USDT","candle1m"), ...]
        self.url = url
        self.subscriptions = list(dict.fromkeys(subscriptions))
        self.on_candle = on_candle
        self.on_state = on_state
        self.reconnect_delay_sec = reconnect_delay_sec
        self.ping_interval_sec = ping_interval_sec
        self.heartbeat_interval_sec = heartbeat_interval_sec
        self.max_idle_sec = max_idle_sec
        self.stop_event = threading.Event()
        self.connected = False
        self.last_message_received_at = 0.0
        self.connection_started_at = 0.0
        self.reconnect_count = 0
        self.last_heartbeat_at = 0.0
        self.last_app_ping_at = 0.0
        self._active_app: websocket.WebSocketApp | None = None
        self._active_app_lock = threading.Lock()

    def build_subscribe_message(self) -> dict[str, Any]:
        """OKX 구독 메시지를 생성한다."""
        return {
            "op": "subscribe",
            "args": [
                {"channel": channel, "instId": inst_id}
                for inst_id, channel in self.subscriptions
            ],
        }

    def build_state_snapshot(self, *, event: str) -> dict[str, Any]:
        return {
            "event": event,
            "url": self.url,
            "subscription_count": len(self.subscriptions),
            "connected": self.connected,
            "reconnect_count": self.reconnect_count,
            "connection_started_at": self.connection_started_at,
            "last_message_received_at": self.last_message_received_at,
            "captured_at": time.time(),
        }

    def stop(self) -> None:
        self.stop_event.set()
        self._close_active_app()

    def run_forever(self) -> None:
        while not self.stop_event.is_set():
            self._run_single_session()
            if self.stop_event.is_set():
                break
            self.reconnect_count += 1
            time.sleep(self.reconnect_delay_sec)

    def _run_single_session(self) -> None:
        subscribe_message = json.dumps(self.build_subscribe_message())
        app_holder: dict[str, websocket.WebSocketApp] = {}

        def on_open(ws_app: websocket.WebSocketApp) -> None:
            self.connected = True
            self.connection_started_at = time.time()
            self.last_message_received_at = 0.0
            self.last_heartbeat_at = 0.0
            self.last_app_ping_at = time.time()
            ws_app.send(subscribe_message)
            self._emit_state("connected")

        def on_message(_: websocket.WebSocketApp, message: str | bytes) -> None:
            self.last_message_received_at = time.time()
            text = message.decode("utf-8") if isinstance(message, bytes) else message
            if text == "pong":
                return
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                return
            if not isinstance(payload, dict):
                return
            event = payload.get("event")
            if event in ("subscribe", "error", "unsubscribe"):
                if event == "error":
                    self._emit_state("error", error=str(payload))
                return
            arg = payload.get("arg") or {}
            data = payload.get("data")
            channel = str(arg.get("channel", "") or "")
            inst_id = str(arg.get("instId", "") or "")
            if channel and inst_id and isinstance(data, list) and data:
                self.on_candle(inst_id, channel, data)

        def on_error(_: websocket.WebSocketApp, error: Any) -> None:
            self.connected = False
            self._emit_state("error", error=str(error))

        def on_close(_: websocket.WebSocketApp, status_code: Any, message: Any) -> None:
            self.connected = False
            self._emit_state("closed", status_code=status_code, message=message)

        app = websocket.WebSocketApp(
            self.url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        app_holder["app"] = app
        self._set_active_app(app)
        watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            args=(app_holder,),
            name="okx-candle-watchdog",
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
            self._clear_active_app(app)
            watchdog_thread.join(timeout=1.0)

    def _emit_state(self, event: str, **extra: Any) -> None:
        if self.on_state is None:
            return
        payload = self.build_state_snapshot(event=event)
        payload.update(extra)
        self.on_state(payload)

    def _watchdog_loop(self, app_holder: dict[str, websocket.WebSocketApp]) -> None:
        """heartbeat 발행 + OKX app-level ping 전송 + 장시간 무수신 시 재연결 유도."""
        while not self.stop_event.is_set():
            time.sleep(1.0)
            now_ts = time.time()
            if self.heartbeat_interval_sec > 0 and (
                now_ts - self.last_heartbeat_at
            ) >= self.heartbeat_interval_sec:
                self.last_heartbeat_at = now_ts
                self._emit_state("heartbeat")

            # OKX 는 30초 내 데이터/ping 이 없으면 연결을 끊으므로 app-level "ping" 을 보낸다.
            if (
                self.connected
                and self.ping_interval_sec > 0
                and (now_ts - self.last_app_ping_at) >= self.ping_interval_sec
            ):
                self.last_app_ping_at = now_ts
                app = app_holder.get("app")
                if app is not None:
                    try:
                        app.send("ping")
                    except Exception:
                        pass

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
        try:
            app.keep_running = False
        except Exception:
            pass
        try:
            app.close()
        except Exception:
            pass
