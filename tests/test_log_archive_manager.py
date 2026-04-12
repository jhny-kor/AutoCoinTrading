"""로그 압축 보관 기준 경계값 테스트."""

import unittest
from datetime import date
from pathlib import Path

from tools.log_archive_manager import get_keep_days_for_root, should_archive_day


class LogArchiveManagerTests(unittest.TestCase):
    def test_archives_day_once_keep_threshold_is_reached(self):
        self.assertTrue(should_archive_day(date(2026, 4, 2), date(2026, 4, 9), 7))

    def test_keeps_more_recent_days_unarchived(self):
        self.assertFalse(should_archive_day(date(2026, 4, 3), date(2026, 4, 9), 7))

    def test_structured_logs_uses_shorter_keep_window(self):
        self.assertEqual(get_keep_days_for_root(Path("structured_logs"), 7), 5)

    def test_other_roots_keep_default_window(self):
        self.assertEqual(get_keep_days_for_root(Path("logs"), 7), 7)


if __name__ == "__main__":
    unittest.main()
