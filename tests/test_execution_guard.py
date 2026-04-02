"""체결률 기반 진입 가드 helper 에 대한 개발 테스트."""

import unittest
from unittest.mock import patch

from core.risk.execution_guard import ExecutionQualityGuard


class ExecutionQualityGuardTests(unittest.TestCase):
    def test_low_recent_fill_ratio_blocks_entry(self):
        guard = ExecutionQualityGuard(refresh_interval_sec=0)
        sample_records = [
            {
                "exchange": "OKX",
                "symbol": "ETH/USDT",
                "side": "buy",
                "recorded_at_local": "2099-01-01T00:00:00+09:00",
                "fill_ratio": 0.90,
            }
        ]
        with patch.object(guard, "_refresh_if_needed", lambda: None):
            guard._records = sample_records
            snapshot = guard.get_fill_quality_snapshot(
                exchange_name="OKX",
                symbol="ETH/USDT",
                since_seconds=3600,
                min_fill_ratio=0.95,
                min_sample_count=1,
            )
        self.assertTrue(snapshot.active)
        self.assertAlmostEqual(0.90, snapshot.avg_fill_ratio)

    def test_insufficient_samples_do_not_block(self):
        guard = ExecutionQualityGuard(refresh_interval_sec=0)
        sample_records = [
            {
                "exchange": "OKX",
                "symbol": "ETH/USDT",
                "side": "buy",
                "recorded_at_local": "2099-01-01T00:00:00+09:00",
                "fill_ratio": 0.92,
            }
        ]
        with patch.object(guard, "_refresh_if_needed", lambda: None):
            guard._records = sample_records
            snapshot = guard.get_fill_quality_snapshot(
                exchange_name="OKX",
                symbol="ETH/USDT",
                since_seconds=3600,
                min_fill_ratio=0.95,
                min_sample_count=2,
            )
        self.assertFalse(snapshot.active)
        self.assertEqual("insufficient_samples", snapshot.reason)


if __name__ == "__main__":
    unittest.main()
