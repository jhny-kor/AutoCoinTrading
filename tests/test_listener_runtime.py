"""텔레그램 리스너 런타임 설정 유틸 테스트."""

import tempfile
import unittest
from pathlib import Path

from reporting.listener_runtime import load_offset, parse_bool, save_offset


class ListenerRuntimeTests(unittest.TestCase):
    def test_parse_bool_handles_common_values(self):
        self.assertTrue(parse_bool("true"))
        self.assertTrue(parse_bool("On"))
        self.assertFalse(parse_bool("false"))
        self.assertFalse(parse_bool(None, default=False))
        self.assertTrue(parse_bool(None, default=True))

    def test_offset_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "offset.txt"
            save_offset(path, 42)
            self.assertEqual(load_offset(path), 42)


if __name__ == "__main__":
    unittest.main()
