import json
import tempfile
import unittest
from pathlib import Path

from reporting.shadow_candidate_tracker import (
    build_shadow_candidate_report,
    format_shadow_candidate_text,
)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


class ShadowCandidateTrackerTests(unittest.TestCase):
    def test_shadow_candidate_tracks_blocked_entry_until_virtual_take_profit(self):
        with tempfile.TemporaryDirectory() as tmp:
            strategy_root = Path(tmp) / "structured_logs" / "live"
            write_jsonl(
                strategy_root / "2026-05-06" / "ma_crossover_bot" / "strategy.jsonl",
                [
                    {
                        "recorded_at_local": "2026-05-06T10:00:00",
                        "program_name": "ma_crossover_bot",
                        "symbol": "ETH/USDT",
                        "side": "entry",
                        "stage": "scan",
                        "result": "seen",
                        "metrics": {
                            "price": 100.0,
                            "signal_score": 62.0,
                            "effective_position_ratio": 0.2,
                            "regime_strategy_key": "mean_reversion",
                            "symbol_regime": "SIDEWAYS",
                            "has_position": False,
                        },
                    },
                    {
                        "recorded_at_local": "2026-05-06T10:00:01",
                        "program_name": "ma_crossover_bot",
                        "symbol": "ETH/USDT",
                        "side": "entry",
                        "stage": "volume",
                        "result": "blocked",
                        "reason": "volume_low",
                    },
                    {
                        "recorded_at_local": "2026-05-06T10:10:00",
                        "program_name": "ma_crossover_bot",
                        "symbol": "ETH/USDT",
                        "side": "entry",
                        "stage": "scan",
                        "result": "seen",
                        "metrics": {"price": 100.3, "has_position": False},
                    },
                    {
                        "recorded_at_local": "2026-05-06T10:20:00",
                        "program_name": "ma_crossover_bot",
                        "symbol": "ETH/USDT",
                        "side": "entry",
                        "stage": "scan",
                        "result": "seen",
                        "metrics": {"price": 100.6, "has_position": False},
                    },
                ],
            )

            report = build_shadow_candidate_report(
                strategy_log_root=strategy_root,
                recent_days=0,
                lookback_hours=0,
                min_signal_score=50.0,
                min_effective_position_ratio=0.01,
                horizon_minutes=60,
                take_profit_pct=0.5,
                stop_loss_pct=0.8,
            )

            self.assertEqual(1, report["summary"]["candidate_count"])
            self.assertEqual(1, report["summary"]["would_take_profit_count"])
            self.assertEqual("volume_low", report["candidates"][0]["block_reason"])
            self.assertAlmostEqual(0.6, report["candidates"][0]["mfe_pct"])
            text = format_shadow_candidate_text(report)
            self.assertIn("미체결 후보 가상 추적", text)
            self.assertIn("판정:", text)

    def test_shadow_candidate_excludes_actual_entry_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            strategy_root = Path(tmp) / "structured_logs" / "live"
            write_jsonl(
                strategy_root / "2026-05-06" / "ma_crossover_bot" / "strategy.jsonl",
                [
                    {
                        "recorded_at_local": "2026-05-06T10:00:00",
                        "program_name": "ma_crossover_bot",
                        "symbol": "ETH/USDT",
                        "side": "entry",
                        "stage": "scan",
                        "result": "seen",
                        "metrics": {
                            "price": 100.0,
                            "signal_score": 70.0,
                            "effective_position_ratio": 0.2,
                            "has_position": False,
                        },
                    },
                    {
                        "recorded_at_local": "2026-05-06T10:00:01",
                        "program_name": "ma_crossover_bot",
                        "symbol": "ETH/USDT",
                        "side": "entry",
                        "stage": "buy_ready",
                        "result": "ready",
                    },
                    {
                        "recorded_at_local": "2026-05-06T10:10:00",
                        "program_name": "ma_crossover_bot",
                        "symbol": "ETH/USDT",
                        "side": "entry",
                        "stage": "scan",
                        "result": "seen",
                        "metrics": {"price": 101.0, "has_position": False},
                    },
                ],
            )

            report = build_shadow_candidate_report(
                strategy_log_root=strategy_root,
                recent_days=0,
                lookback_hours=0,
                min_signal_score=50.0,
                min_effective_position_ratio=0.01,
            )

            self.assertEqual(0, report["summary"]["candidate_count"])


if __name__ == "__main__":
    unittest.main()
