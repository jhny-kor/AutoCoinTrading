"""
작업 요약
- 텔레그램 로그 helper 의 시간 판정과 최근 줄 읽기 계약을 검증한다.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from reporting.telegram_log_helpers import is_in_recent_days, parse_local_timestamp, read_recent_lines


class TelegramLogHelperTests(unittest.TestCase):
    def test_parse_local_timestamp_accepts_iso_offset(self) -> None:
        parsed = parse_local_timestamp("2026-05-14T09:00:00+09:00")

        self.assertIsNotNone(parsed)
        self.assertIsNone(parsed.tzinfo)

    def test_is_in_recent_days_uses_supplied_now(self) -> None:
        self.assertTrue(
            is_in_recent_days(
                "2026-05-13T23:00:00",
                1,
                now=datetime(2026, 5, 14, 9, 0, 0),
            )
        )
        self.assertFalse(
            is_in_recent_days(
                "2026-05-12T08:59:59",
                1,
                now=datetime(2026, 5, 14, 9, 0, 0),
            )
        )

    def test_read_recent_lines_returns_tail_or_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.log"
            path.write_text("a\nb\nc\n", encoding="utf-8")

            self.assertEqual(["b", "c"], read_recent_lines(path, 2))
            self.assertEqual(["로그 파일이 없습니다."], read_recent_lines(Path(tmp_dir) / "missing.log", 2))


if __name__ == "__main__":
    unittest.main()
