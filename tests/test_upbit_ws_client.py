"""업비트 웹소켓 클라이언트 종료/재연결 제어 테스트."""

import threading
import unittest

from core.market_data.upbit_ws_client import UpbitWebSocketClient


class FakeSock:
    def __init__(self) -> None:
        self.aborted = False

    def abort(self) -> None:
        self.aborted = True


class FakeWebSocketApp:
    def __init__(self) -> None:
        self.keep_running = True
        self.sock = FakeSock()


class UpbitWebSocketClientTests(unittest.TestCase):
    def test_stop_aborts_active_websocket_app(self):
        client = UpbitWebSocketClient(
            url="wss://example.invalid",
            markets=[],
            on_payload=lambda payload: None,
        )
        app = FakeWebSocketApp()

        client._set_active_app(app)  # 운영 stop 신호가 현재 세션을 깨우는지 검증한다.
        client.stop()

        self.assertTrue(client.stop_event.is_set())
        self.assertFalse(app.keep_running)
        self.assertTrue(app.sock.aborted)  # shutdown 으로 select 를 깨운다(실제 close 는 teardown).

    def test_close_app_ignores_abort_errors(self):
        class BrokenSock:
            def abort(self) -> None:
                raise OSError("already closed")

        app = FakeWebSocketApp()
        app.sock = BrokenSock()
        UpbitWebSocketClient._close_app(app)

        self.assertFalse(app.keep_running)

    def test_watchdog_stops_on_session_stop_without_global_stop(self):
        # 재연결마다 새로 뜨는 watchdog 가 세션 종료 시 죽는지(좀비 누수 회귀) 검증한다.
        client = UpbitWebSocketClient(
            url="wss://example.invalid",
            markets=[],
            on_payload=lambda payload: None,
        )
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


if __name__ == "__main__":
    unittest.main()
