"""텔레그램 인시던트 dedupe 동작 테스트.

수정 요약
- 2026-05-24: 거래소 API 허용 IP 오류 정규화와 ignored 인시던트 반복 묶기 테스트를 추가했다.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.incident_manager import register_incident, update_incident_status


class IncidentManagerTests(unittest.TestCase):
    def test_upbit_ip_authorization_errors_share_signature(self) -> None:
        first_detail = (
            "ExchangeError('upbit {\"error\":{\"message\":\"This is not a verified IP.\","
            "\"name\":\"no_authorization_ip\"}}')"
        )
        second_detail = (
            "ExchangeError('upbit {\"error\":{\"name\":\"no_authorization_ip\","
            "\"message\":\"This is not a verified IP.\"}}')"
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "incidents.json"
            with patch("tools.incident_manager.time.time", side_effect=[1000.0, 1005.0]):
                first = register_incident(
                    exchange_name="UPBIT",
                    symbol="ETH/KRW",
                    detail=first_detail,
                    path=path,
                )
                second = register_incident(
                    exchange_name="UPBIT",
                    symbol="ETH/KRW",
                    detail=second_detail,
                    path=path,
                )

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(2, second["count"])
        self.assertEqual("UPBIT|ETH/KRW|upbit_ip_authorization_required", second["signature"])

    def test_ignored_incident_keeps_deduping_after_window(self) -> None:
        detail = (
            "PermissionDenied('okx {\"msg\":\"Your IP 203.255.249.253 is not included "
            "in your API key's key-id IP whitelist.\",\"code\":\"50110\"}')"
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "incidents.json"
            with patch("tools.incident_manager.time.time", return_value=1000.0):
                first = register_incident(
                    exchange_name="OKX",
                    symbol="SOL/USDT",
                    detail=detail,
                    dedupe_window_sec=1,
                    path=path,
                )

            update_incident_status(first["id"], status="ignored", action="ignore", path=path)

            with patch("tools.incident_manager.time.time", return_value=5000.0):
                repeated = register_incident(
                    exchange_name="OKX",
                    symbol="SOL/USDT",
                    detail=detail,
                    dedupe_window_sec=1,
                    path=path,
                )

        self.assertEqual(first["id"], repeated["id"])
        self.assertEqual("ignored", repeated["status"])
        self.assertEqual(2, repeated["count"])


if __name__ == "__main__":
    unittest.main()
