"""로그 압축 보관 기준 경계값 테스트."""

import unittest
from datetime import date

from tools.log_archive_manager import should_archive_day


class LogArchiveManagerTests(unittest.TestCase):
    def test_archives_day_once_keep_threshold_is_reached(self):
        self.assertTrue(should_archive_day(date(2026, 4, 2), date(2026, 4, 9), 7))

    def test_keeps_more_recent_days_unarchived(self):
        self.assertFalse(should_archive_day(date(2026, 4, 3), date(2026, 4, 9), 7))


if __name__ == "__main__":
    unittest.main()
