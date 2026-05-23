"""최신 로그 창 제한 helper 회귀 테스트."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reporting import analyze_logs, analyze_strategy_logs


def write_jsonl(path: Path, rows: list[dict]) -> None:
    """테스트용 JSONL 파일을 쓴다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def analysis_record(symbol: str, collected_at: str, gap_pct: float = 0.1) -> dict:
    """요약 가능한 분석 로그 1건을 만든다."""
    return {
        "exchange": "upbit",
        "symbol": symbol,
        "collected_at": collected_at,
        "gap_pct": gap_pct,
        "close_change_pct": 0.2,
        "close": 100.0,
        "bullish_signal": True,
        "bearish_signal": False,
        "above_ma": True,
    }


class LogWindowingTests(unittest.TestCase):
    def test_recent_analysis_summaries_ignore_older_date_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(
                root / "2026-05-23" / "upbit__BTC_KRW.jsonl",
                [analysis_record("BTC/KRW", "2026-05-23T10:00:00", gap_pct=9.0)],
            )
            write_jsonl(
                root / "2026-05-24" / "upbit__BTC_KRW.jsonl",
                [analysis_record("BTC/KRW", "2026-05-24T10:00:00", gap_pct=1.0)],
            )

            summaries = analyze_logs.build_recent_summaries(root, max_date_dirs=1)

        self.assertEqual(1, len(summaries))
        self.assertEqual(1, summaries[0].count)
        self.assertAlmostEqual(1.0, summaries[0].avg_gap_pct)

    def test_latest_analysis_records_read_file_tail_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(
                root / "2026-05-24" / "upbit__BTC_KRW.jsonl",
                [
                    analysis_record("BTC/KRW", "2026-05-24T09:00:00", gap_pct=1.0),
                    analysis_record("BTC/KRW", "2026-05-24T10:00:00", gap_pct=2.0),
                ],
            )

            records = analyze_logs.load_latest_records(root, symbols={"BTC/KRW"})

        self.assertEqual(1, len(records))
        self.assertEqual("2026-05-24T10:00:00", records[0]["collected_at"])
        self.assertEqual(2.0, records[0]["gap_pct"])

    def test_strategy_summary_limits_recent_date_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_jsonl(
                root / "2026-05-23" / "upbit_ma_crossover_bot" / "strategy.jsonl",
                [
                    {
                        "symbol": "BTC/KRW",
                        "side": "entry",
                        "stage": "scan",
                        "result": "seen",
                    },
                    {
                        "symbol": "BTC/KRW",
                        "side": "entry",
                        "stage": "scan",
                        "result": "seen",
                    },
                ],
            )
            write_jsonl(
                root / "2026-05-24" / "upbit_ma_crossover_bot" / "strategy.jsonl",
                [
                    {
                        "symbol": "BTC/KRW",
                        "side": "entry",
                        "stage": "scan",
                        "result": "seen",
                    }
                ],
            )

            rows = analyze_strategy_logs.build_summary_rows(root, max_date_dirs=1)

        self.assertEqual(1, len(rows))
        self.assertEqual(1, rows[0]["scans"])


if __name__ == "__main__":
    unittest.main()
