"""백테스트용 임시 TOML override context 에 대한 개발 테스트."""

import tempfile
import unittest
from pathlib import Path

from settings.env import EXTRA_TOML_ENV_KEY, temporary_runtime_overrides


class EnvOverrideTests(unittest.TestCase):
    def test_temporary_runtime_overrides_sets_and_restores_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.toml"
            path.write_text("[strategy]\nversion = \"x\"\n", encoding="utf-8")

            self.assertIsNone(__import__("os").environ.get(EXTRA_TOML_ENV_KEY))
            with temporary_runtime_overrides([path]):
                self.assertIn(str(path), __import__("os").environ.get(EXTRA_TOML_ENV_KEY, ""))
            self.assertIsNone(__import__("os").environ.get(EXTRA_TOML_ENV_KEY))


if __name__ == "__main__":
    unittest.main()
