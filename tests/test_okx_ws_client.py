"""OKX 웹소켓 클라이언트 heartbeat·종료·재연결 제어 테스트."""

import threading
import unittest
from unittest.mock import patch

from core.market_data.okx_ws_client import OkxWebSocketClient


class FakeSock:
    def __init__(self) -> None:
        self.aborted = False

    def abort(self) -> None:
        self.aborted = True


class FakeWebSocketApp:
    def __init__(self) -> None:
        self.keep_running = True
        self.sock = FakeSock()
        self.sent: list[str] = []

    def send(self, message: str) -> None:
        self.sent.append(message)


class OkxWebSocketClientTests(unittest.TestCase):
    def _client(self) -> OkxWebSocketClient:
        return OkxWebSocketClient(
            url="wss://example.invalid",
            subscriptions=[("ETH-USDT", "candle1m")],
            on_candle=lambda inst_id, channel, data: None,
        )

    def test_stop_aborts_active_websocket_app(self):
        client = self._client()
        app = FakeWebSocketApp()

        client._set_active_app(app)
        client.stop()

        self.assertTrue(client.stop_event.is_set())
        self.assertFalse(app.keep_running)
        self.assertTrue(app.sock.aborted)

    def test_watchdog_stops_on_session_stop_without_global_stop(self):
        # 재연결마다 새로 뜨는 watchdog 가 세션 종료 시 죽는지(좀비 누수 회귀) 검증한다.
        client = self._client()
        session_stop = threading.Event()
        thread = threading.Thread(
            target=client._watchdog_loop,
            args=({"app": FakeWebSocketApp()}, session_stop),
            daemon=True,
        )
        thread.start()
        session_stop.set()  # 전역 stop_event 는 건드리지 않고 이 세션만 종료한다.
        thread.join(timeout=2.5)

        self.assertFalse(thread.is_alive())
        self.assertFalse(client.stop_event.is_set())

    def test_okx_application_ping_gets_pong(self):
        client = self._client()
        app = FakeWebSocketApp()

        client._handle_message(app, "ping")

        self.assertEqual(["pong"], app.sent)

    def test_okx_disables_websocket_client_rfc_ping(self):
        captured: dict[str, object] = {}

        class CaptureApp(FakeWebSocketApp):
            def __init__(self, *args, **kwargs):
                super().__init__()
                captured["app"] = self

            def run_forever(self, **kwargs):
                captured["run_kwargs"] = kwargs

        client = self._client()
        with patch("core.market_data.okx_ws_client.websocket.WebSocketApp", CaptureApp):
            client._run_single_session()

        run_kwargs = captured["run_kwargs"]
        self.assertEqual(0, run_kwargs["ping_interval"])
        self.assertNotIn("ping_timeout", run_kwargs)


if __name__ == "__main__":
    unittest.main()
