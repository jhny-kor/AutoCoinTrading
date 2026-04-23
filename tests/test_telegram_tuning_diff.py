import unittest

from reporting.telegram_command_listener import (
    build_tuning_diff_rows_from_batch_summaries,
    format_tuning_diff_row,
)


class TelegramTuningDiffTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
