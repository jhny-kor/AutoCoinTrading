"""백테스트 레지스트리의 확인필요/삭제 메타데이터에 대한 개발 테스트."""

import json
import tempfile
import unittest
from pathlib import Path

from tools.update_backtest_registry import build_batch_entry, build_single_backtest_entry


class BacktestRegistryTests(unittest.TestCase):
    def test_batch_entry_marks_review_required_and_delete_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            batch_dir = Path(tmp) / "20260408_000000__weekly"
            batch_dir.mkdir(parents=True)
            payload = {
                "label": "weekly",
                "created_at": "2026-04-08T00:00:00",
                "since": "2026-04-01",
                "until": "2026-04-08",
                "rows": [
                    {
                        "symbol": "XRP/USDT",
                        "comparison": {
                            "comments": [
                                "입력 데이터 주기나 설정값 불일치 여부를 먼저 확인하는 것이 좋습니다."
                            ]
                        },
                    }
                ],
            }
            (batch_dir / "batch_summary.json").write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )

            entry = build_batch_entry(batch_dir)

            self.assertIsNotNone(entry)
            self.assertTrue(entry["review_required"])
            self.assertEqual("확인필요", entry["review_status"])
            self.assertIn("actions", entry)
            self.assertEqual("삭제", entry["actions"]["delete"]["label"])

    def test_single_entry_without_comparison_is_normal(self):
        with tempfile.TemporaryDirectory() as tmp:
            backtest_dir = Path(tmp) / "20260408_000001__alt__ETH_KRW"
            backtest_dir.mkdir(parents=True)
            payload = {
                "label": "single",
                "created_at": "2026-04-08T00:00:01",
                "symbol": "ETH/KRW",
                "exchange_name": "upbit",
                "strategy_type": "alt",
            }
            (backtest_dir / "summary.json").write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )

            entry = build_single_backtest_entry(backtest_dir)

            self.assertIsNotNone(entry)
            self.assertFalse(entry["review_required"])
            self.assertEqual("정상", entry["review_status"])
            self.assertNotIn("actions", entry)


if __name__ == "__main__":
    unittest.main()
