"""백테스트 레지스트리의 override 메타데이터 기록에 대한 개발 테스트."""

import json
import tempfile
import unittest
from pathlib import Path

from tools.update_backtest_registry import build_batch_entry, build_single_backtest_entry


class BacktestRegistryOverrideTests(unittest.TestCase):
    def test_batch_entry_keeps_override_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            batch_dir = Path(tmp) / "batch"
            batch_dir.mkdir(parents=True)
            payload = {
                "label": "weekly",
                "created_at": "2026-04-10T00:00:00",
                "override_set_names": ["experiments/btc_atr_strict.toml"],
                "override_paths": ["config/sets/experiments/btc_atr_strict.toml"],
                "rows": [{"symbol": "BTC/USDT"}],
            }
            (batch_dir / "batch_summary.json").write_text(json.dumps(payload), encoding="utf-8")
            entry = build_batch_entry(batch_dir)
            self.assertEqual(["experiments/btc_atr_strict.toml"], entry["override_set_names"])

    def test_single_entry_keeps_override_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "single"
            run_dir.mkdir(parents=True)
            payload = {
                "symbol": "BTC/USDT",
                "exchange_name": "okx",
                "strategy_type": "btc",
                "override_set_names": ["experiments/btc_atr_strict.toml"],
                "override_paths": ["config/sets/experiments/btc_atr_strict.toml"],
            }
            (run_dir / "summary.json").write_text(json.dumps(payload), encoding="utf-8")
            entry = build_single_backtest_entry(run_dir)
            self.assertEqual(["experiments/btc_atr_strict.toml"], entry["override_set_names"])


if __name__ == "__main__":
    unittest.main()
