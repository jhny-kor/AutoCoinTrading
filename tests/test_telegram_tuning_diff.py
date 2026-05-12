import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from reporting.listener_runtime import ListenerSettings
from reporting.telegram_command_listener import (
    build_backtest_comparison_text,
    build_tuning_diff_rows_from_batch_summaries,
    enrich_summary_metrics_from_result_dir,
    format_tuning_diff_row,
    join_report_sections,
    map_strategy_reason_to_label,
)


class TelegramTuningDiffTests(unittest.TestCase):
    def test_join_report_sections_hides_empty_helper_sections(self):
        text = join_report_sections(
            [
                "핵심 요약\n- 판단 가능",
                "시간대 성과 요약\n- 아직 시간대별 체결 데이터가 없습니다.",
                "",
            ]
        )

        self.assertIn("핵심 요약", text)
        self.assertNotIn("시간대 성과 요약", text)

    def test_build_tuning_diff_rows_from_batch_summaries_includes_new_metrics(self):
        before_payload = {
            "rows": [
                {
                    "exchange_name": "okx",
                    "symbol": "BTC/USDT",
                    "summary": {
                        "net_return_pct": 1.0,
                        "trade_count": 5,
                        "max_drawdown_pct": 3.0,
                        "sharpe_ratio": 0.8,
                        "profit_factor": 1.2,
                    },
                }
            ]
        }
        after_payload = {
            "rows": [
                {
                    "exchange_name": "okx",
                    "symbol": "BTC/USDT",
                    "summary": {
                        "net_return_pct": 2.5,
                        "trade_count": 7,
                        "max_drawdown_pct": 2.0,
                        "sharpe_ratio": 1.1,
                        "profit_factor": 1.6,
                    },
                }
            ]
        }

        rows = build_tuning_diff_rows_from_batch_summaries(before_payload, after_payload)

        self.assertEqual(1, len(rows))
        self.assertEqual("okx::BTC/USDT", rows[0]["key"])
        self.assertEqual(0.8, rows[0]["before_sharpe_ratio"])
        self.assertEqual(1.6, rows[0]["after_profit_factor"])

    def test_format_tuning_diff_row_prints_sharpe_and_pf_when_present(self):
        row = {
            "key": "okx::BTC/USDT",
            "before_return_pct": 1.0,
            "after_return_pct": 2.0,
            "return_diff_pct": 1.0,
            "before_trade_count": 5,
            "after_trade_count": 6,
            "before_max_drawdown_pct": 3.0,
            "after_max_drawdown_pct": 2.5,
            "before_sharpe_ratio": 0.8,
            "after_sharpe_ratio": 1.1,
            "before_profit_factor": 1.2,
            "after_profit_factor": 1.5,
        }

        text = format_tuning_diff_row(row)

        self.assertIn("Sharpe 0.800 -> 1.100", text)
        self.assertIn("PF 1.200 -> 1.500", text)

    def test_enrich_summary_metrics_from_result_dir_backfills_missing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            result_dir = Path(tmp)
            (result_dir / "equity_curve.jsonl").write_text(
                "\n".join(
                    json.dumps({"equity_quote": value})
                    for value in [1000.0, 1010.0, 1020.0, 1015.0]
                )
                + "\n",
                encoding="utf-8",
            )
            (result_dir / "trades.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"side": "sell", "net_realized_pnl_quote": 10.0}),
                        json.dumps({"side": "sell", "net_realized_pnl_quote": -5.0}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            metrics = enrich_summary_metrics_from_result_dir(
                {},
                result_dir=str(result_dir),
                timeframe="1m",
            )

            self.assertIsNotNone(metrics["sharpe_ratio"])
            self.assertEqual(2.0, metrics["profit_factor"])

    def test_strategy_reason_mapping_avoids_generic_other_label(self):
        self.assertEqual(
            "평균회귀 하단 복귀 미확인",
            map_strategy_reason_to_label(
                "mean_reversion_lower_reclaim_missing",
                {"bb_lower_distance_pct": 0.2},
                {"lower_near_max_distance_pct": 0.12},
                stage="raw_entry_signal",
                side="entry",
            ),
        )
        self.assertNotIn(
            "기타",
            map_strategy_reason_to_label(
                "new_reason_code",
                {},
                {},
                stage="entry_signal_integrity",
                side="entry",
            ),
        )

    def test_backtest_comparison_text_explains_empty_future_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            comparison_path = Path(tmp) / "comparison.json"
            comparison_path.write_text(
                json.dumps(
                    {
                        "filters": {
                            "symbol": "XRP/KRW",
                            "exchange_name": "upbit",
                            "strategy_type": "alt",
                            "program_name": "upbit_ma_crossover_bot",
                            "since": "2099-01-01",
                            "until": "2099-01-02",
                            "backtest_dir": "reports/backtests/example",
                        },
                        "backtest": {"trade_count": 0, "sell_count": 0},
                        "live": {"trade_count": 0, "sell_count": 0},
                        "comments": [],
                    }
                ),
                encoding="utf-8",
            )
            settings = ListenerSettings(
                poll_interval_sec=5,
                offset_path=Path("logs/test.offset"),
                report_state_path=Path("logs/test.state"),
                analysis_log_dir=Path("analysis_logs"),
                okx_symbols=["BTC/USDT"],
                upbit_symbols=["XRP/KRW"],
                recent_log_line_count=5,
                daily_report_enabled=True,
                morning_report_hour=8,
                noon_report_hour=12,
                evening_report_hour=18,
                night_report_hour=21,
                weekly_report_enabled=True,
                weekly_report_weekday=0,
                weekly_report_hour=9,
            )

            with patch(
                "reporting.telegram_command_listener.iter_files",
                return_value=[comparison_path],
            ):
                text = build_backtest_comparison_text(settings)

        self.assertIn("값 없음", text)
        self.assertIn("비교 기간이 미래 테스트 기간", text)
        self.assertNotIn("승률 차이 +0.00%p", text)


if __name__ == "__main__":
    unittest.main()
