import json
import tempfile
import unittest
from pathlib import Path

from core.risk.review import build_trade_risk_review
from reporting.decision_journal import (
    append_decision_journal_entry,
    build_recent_reflection_summary,
)


class DecisionJournalTests(unittest.TestCase):
    def test_risk_review_flags_weak_entry(self):
        review = build_trade_risk_review(
            {
                "side": "buy",
                "reason": "entry",
                "symbol": "ETH/USDT",
                "extra": {
                    "signal_score": 48,
                    "volume_filter_passed": False,
                    "volatility_filter_passed": True,
                    "htf_bullish": False,
                },
            }
        )

        self.assertEqual("block_candidate", review.posture)
        self.assertIn("entry_signal_score_very_low", review.concerns)
        self.assertIn("entry_volume_filter_failed", review.concerns)

    def test_risk_review_flags_stop_loss_pattern(self):
        review = build_trade_risk_review(
            {
                "side": "sell",
                "reason": "stop_loss",
                "symbol": "BTC/KRW",
                "net_realized_pnl_pct": -0.42,
                "mfe_pct": 0.05,
                "holding_seconds": 75,
            }
        )

        self.assertEqual("block_candidate", review.posture)
        self.assertIn("stop_loss_exit", review.concerns)
        self.assertIn("fast_failure_after_entry", review.concerns)

    def test_journal_summary_includes_reflection_and_concerns(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            append_decision_journal_entry(
                {
                    "recorded_at": "2026-04-28T00:00:00+00:00",
                    "recorded_at_local": "2026-04-28T09:00:00+09:00",
                    "exchange": "OKX",
                    "program_name": "ma_crossover_bot",
                    "symbol": "SOL/USDT",
                    "side": "sell",
                    "reason": "stop_loss",
                    "net_realized_pnl_pct": -0.4,
                    "mfe_pct": 0.03,
                    "holding_seconds": 90,
                    "extra": {},
                },
                root_dir=root,
            )

            journal_path = next(root.rglob("decision_journal.jsonl"))
            payload = json.loads(journal_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual("SOL/USDT", payload["symbol"])
            self.assertIn("reflection", payload)

            summary = build_recent_reflection_summary(days=7, root_dir=root)
            self.assertIn("최근 7일 의사결정 리뷰", summary)
            self.assertIn("stop_loss_exit", summary)
            self.assertIn("SOL/USDT", summary)


if __name__ == "__main__":
    unittest.main()
