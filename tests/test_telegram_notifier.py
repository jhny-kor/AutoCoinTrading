"""텔레그램 알림 유틸 테스트.

수정 요약
- 2026-05-24: 거래소 허용 IP 오류 진단 문구와 반복 인시던트 전송 억제 테스트를 추가했다.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from reporting.telegram_notifier import TelegramNotifier


def make_notifier() -> TelegramNotifier:
    """테스트용 텔레그램 알림 객체를 만든다."""
    return TelegramNotifier(
        enabled=True,
        bot_token="token",
        chat_id="chat",
        enable_buy_notification=True,
        enable_sell_notification=True,
        enable_stop_loss_notification=True,
        enable_error_notification=True,
        enable_daily_limit_notification=True,
        enable_attention_notification=True,
        enable_error_action_buttons=True,
        error_dedupe_window_sec=3600,
    )


class TelegramNotifierTests(unittest.TestCase):
    def test_error_message_adds_ip_authorization_hint(self) -> None:
        detail = (
            "ExchangeError('upbit {\"error\":{\"name\":\"no_authorization_ip\","
            "\"message\":\"This is not a verified IP.\"}}')"
        )
        notifier = make_notifier()

        with patch(
            "reporting.telegram_notifier.register_incident",
            return_value={"id": "inc_1", "count": 1, "status": "open"},
        ), patch.object(
            TelegramNotifier,
            "send_message_detailed",
            autospec=True,
            return_value=(True, None),
        ) as send:
            sent = notifier.notify_error_message("UPBIT", "ETH/KRW", detail)

        self.assertTrue(sent)
        message_text = send.call_args.args[1]
        self.assertIn("업비트 Open API 키 허용 IP", message_text)
        self.assertIn("Oracle Cloud", message_text)

    def test_repeated_incident_does_not_send_again(self) -> None:
        notifier = make_notifier()

        with patch(
            "reporting.telegram_notifier.register_incident",
            return_value={"id": "inc_1", "count": 2, "status": "open"},
        ) as register, patch.object(
            TelegramNotifier,
            "send_message_detailed",
            autospec=True,
            return_value=(True, None),
        ) as send:
            sent = notifier.notify_error_message("OKX", "SOL/USDT", "RequestTimeout('okx')")

        self.assertFalse(sent)
        send.assert_not_called()
        self.assertEqual(3600, register.call_args.kwargs["dedupe_window_sec"])


if __name__ == "__main__":
    unittest.main()
