import unittest

from upbit_ma_crossover_bot import build_empty_position_runtime_metrics


class UpbitMaCrossoverRegressionTests(unittest.TestCase):
    def test_build_empty_position_runtime_metrics_returns_all_expected_keys(self):
        metrics = build_empty_position_runtime_metrics()
        self.assertEqual(
            set(metrics.keys()),
            {
                "pnl_pct",
                "mfe_pct",
                "mae_pct",
                "current_net_realized_pnl_quote",
                "current_net_realized_pnl_pct",
            },
        )
        self.assertTrue(all(value is None for value in metrics.values()))


if __name__ == "__main__":
    unittest.main()
