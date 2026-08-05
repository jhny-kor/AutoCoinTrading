"""
수정 요약
- 백테스트와 실거래가 모두 0건일 때 방향성 유사로 오판하지 않는지 검증한다.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reporting.compare_backtest_to_live import (
    build_comparison_payload,
    build_markdown_report,
    generate_comments,
    summarize_sell_records,
)


class CompareBacktestToLiveTests(unittest.TestCase):
    def test_zero_samples_are_reported_as_inconclusive(self):
        empty_summary = summarize_sell_records([])

        comments = generate_comments(empty_summary, empty_summary)

        self.assertIn("모두 0건", comments[0])
        self.assertNotIn("비슷", " ".join(comments))

    def test_partial_replay_is_preserved_as_non_deployment_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            backtest_dir = Path(temp_dir)
            (backtest_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "symbol": "SOL/USDT",
                        "exchange_name": "okx",
                        "strategy_type": "alt",
                        "replay_fidelity": "partial_closed_candle",
                        "deployment_evidence_eligible": False,
                        "replay_confirmation_unit": "closed_candle",
                        "replay_unavailable_context": ["live_orderbook"],
                    }
                ),
                encoding="utf-8",
            )
            (backtest_dir / "trades.jsonl").write_text("", encoding="utf-8")
            with patch("reporting.compare_backtest_to_live.read_trade_history", return_value=[]):
                payload = build_comparison_payload(backtest_dir=backtest_dir)

        report = build_markdown_report(payload)
        self.assertFalse(payload["backtest_evidence"]["deployment_evidence_eligible"])
        self.assertIn("배포 근거로 사용할 수 없습니다", " ".join(payload["comments"]))
        self.assertIn("partial_closed_candle", report)
        self.assertIn("배포 근거 적격성: `아니요`", report)

    def test_missing_eligibility_is_reported_as_unknown(self):
        empty_summary = summarize_sell_records([])

        comments = generate_comments(empty_summary, empty_summary, {})

        self.assertIn("적격성이 기록되지 않아", comments[0])


if __name__ == "__main__":
    unittest.main()
