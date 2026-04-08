"""현재 레짐 스냅샷 단계/설명 출력에 대한 개발 테스트."""

import unittest

from reporting.current_regime_snapshot import build_regime_snapshot_payload


class RegimeSnapshotTests(unittest.TestCase):
    def test_payload_contains_stage_catalog_and_stage_info(self):
        payload = build_regime_snapshot_payload(
            [
                {
                    "exchange": "upbit",
                    "symbol": "BTC/KRW",
                    "collected_at": "2026-04-08T09:00:00",
                    "volume_ratio": 1.4,
                    "avg_abs_change_pct": 0.22,
                    "gap_pct": 0.18,
                    "rsi": 55.0,
                    "adx": 28.0,
                    "public_buy_ready": False,
                    "bullish_signal": True,
                    "bearish_signal": False,
                    "above_ma": True,
                    "htf_bullish": True,
                }
            ]
        )

        self.assertEqual(6, len(payload["stage_catalog"]))
        self.assertEqual("LOW_ENERGY", payload["stage_catalog"][0]["regime"])
        self.assertEqual("TRENDING", payload["rows"][0]["regime"])
        self.assertEqual(4, payload["rows"][0]["stage_index"])
        self.assertIn("추세", payload["rows"][0]["meaning"])
        self.assertIn("ADX", payload["rows"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
