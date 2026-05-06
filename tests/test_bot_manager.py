import unittest

from bot_manager import is_zombie_stat, parse_process_listing_line


class BotManagerProcessParsingTests(unittest.TestCase):
    def test_parse_process_listing_line_with_stat_and_command(self):
        entry = parse_process_listing_line(
            "22336 8620 07:05 Z /opt/python run/upbit_ma_crossover_bot.py"
        )

        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.pid, 22336)
        self.assertEqual(entry.ppid, 8620)
        self.assertEqual(entry.elapsed, "07:05")
        self.assertEqual(entry.stat, "Z")
        self.assertEqual(entry.command, "/opt/python run/upbit_ma_crossover_bot.py")

    def test_is_zombie_stat_handles_macos_variants(self):
        self.assertTrue(is_zombie_stat("Z"))
        self.assertTrue(is_zombie_stat("Z+"))
        self.assertFalse(is_zombie_stat("S"))


if __name__ == "__main__":
    unittest.main()
