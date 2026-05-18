import unittest

from bot_manager import command_matches_script, is_zombie_stat, parse_process_listing_line


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

    def test_command_matches_script_uses_process_prefix_only(self):
        command = "/opt/python run/ma_crossover_bot.py --some-flag"

        self.assertTrue(command_matches_script(command, "run/ma_crossover_bot.py"))

    def test_command_matches_script_ignores_embedded_transcript_mentions(self):
        command = (
            "/Applications/Codex.app/SkyComputerUseClient turn-ended "
            '{"input":"old text mentions run/ma_crossover_bot.py later"}'
        )

        self.assertFalse(command_matches_script(command, "run/ma_crossover_bot.py"))


if __name__ == "__main__":
    unittest.main()
