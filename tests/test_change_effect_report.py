import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from reporting.change_effect_report import (
    build_change_effect_report,
    format_change_effect_text,
)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


class ChangeEffectReportTests(unittest.TestCase):
    def test_build_change_effect_report_compares_before_after_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            strategy_root = root / "structured_logs" / "live"
            trade_root = root / "trade_logs"
            write_jsonl(
                strategy_root / "2026-05-06" / "ma_crossover_bot" / "strategy.jsonl",
                [
                    {
                        "recorded_at_local": "2026-05-06T11:30:00",
                        "program_name": "ma_crossover_bot",
                        "symbol": "ETH/USDT",
                        "side": "entry",
                        "stage": "scan",
                        "result": "seen",
                        "metrics": {"signal_score": 52, "effective_position_ratio": 0.1},
                    },
                    {
                        "recorded_at_local": "2026-05-06T11:30:01",
                        "program_name": "ma_crossover_bot",
                        "symbol": "ETH/USDT",
                        "side": "entry",
                        "stage": "volume",
                        "result": "blocked",
                        "reason": "volume_low",
                    },
                    {
                        "recorded_at_local": "2026-05-06T12:30:00",
                        "program_name": "ma_crossover_bot",
                        "symbol": "ETH/USDT",
                        "side": "entry",
                        "stage": "scan",
                        "result": "seen",
                        "metrics": {"signal_score": 72, "effective_position_ratio": 0.25},
                    },
                    {
                        "recorded_at_local": "2026-05-06T12:30:01",
                        "program_name": "ma_crossover_bot",
                        "symbol": "ETH/USDT",
                        "side": "entry",
                        "stage": "buy_ready",
                        "result": "ready",
                    },
                    {
                        "recorded_at_local": "2026-05-06T12:30:02",
                        "program_name": "ma_crossover_bot",
                        "symbol": "ETH/USDT",
                        "side": "entry",
                        "stage": "order_requested",
                        "result": "requested",
                    },
                    {
                        "recorded_at_local": "2026-05-06T12:30:03",
                        "program_name": "ma_crossover_bot",
                        "symbol": "ETH/USDT",
                        "side": "entry",
                        "stage": "filled",
                        "result": "filled",
                    },
                ],
            )
            write_jsonl(
                trade_root / "2026-05-06" / "trade_history.jsonl",
                [
                    {
                        "recorded_at_local": "2026-05-06T11:45:00",
                        "side": "sell",
                        "reason": "stop_loss",
                        "net_realized_pnl_pct": -0.4,
                        "net_realized_pnl_quote": -1.0,
                    },
                    {
                        "recorded_at_local": "2026-05-06T12:45:00",
                        "side": "sell",
                        "reason": "take_profit",
                        "net_realized_pnl_pct": 0.6,
                        "net_realized_pnl_quote": 1.5,
                    },
                ],
            )

            report = build_change_effect_report(
                change_at=datetime(2026, 5, 6, 12, 0, 0),
                hours=1.0,
                now=datetime(2026, 5, 6, 13, 0, 0),
                strategy_log_root=strategy_root,
                trade_log_root=trade_root,
            )

            self.assertEqual(1, report["before"]["scan_count"])
            self.assertEqual(1, report["after"]["entry_filled_count"])
            self.assertEqual(1, report["before"]["stop_loss_count"])
            self.assertEqual(0, report["after"]["stop_loss_count"])
            self.assertEqual(20.0, report["delta"]["avg_signal_score"])
            text = format_change_effect_text(report)
            self.assertIn("변경 효과 자동 비교", text)
            self.assertIn("판정:", text)
            self.assertIn("scan/h", text)


if __name__ == "__main__":
    unittest.main()
