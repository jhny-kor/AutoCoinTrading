"""업비트 웹소켓 클라이언트 종료/재연결 제어 테스트."""

import unittest

from core.market_data.upbit_ws_client import UpbitWebSocketClient


class FakeWebSocketApp:
    def __init__(self) -> None:
        self.keep_running = True
        self.closed = False

    def close(self) -> None:
        self.closed = True


class UpbitWebSocketClientTests(unittest.TestCase):
    def test_stop_closes_active_websocket_app(self):
        client = UpbitWebSocketClient(
            url="wss://example.invalid",
            markets=[],
            on_payload=lambda payload: None,
        )
        app = FakeWebSocketApp()

        client._set_active_app(app)  # 운영 stop 신호가 현재 세션을 닫는지 검증한다.
        client.stop()

        self.assertTrue(client.stop_event.is_set())
        self.assertFalse(app.keep_running)
        self.assertTrue(app.closed)

    def test_close_app_ignores_close_errors(self):
        class BrokenApp(FakeWebSocketApp):
            def close(self) -> None:
                raise OSError("already closed")

        app = BrokenApp()
        UpbitWebSocketClient._close_app(app)

        self.assertFalse(app.keep_running)


if __name__ == "__main__":
    unittest.main()
