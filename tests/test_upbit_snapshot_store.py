import json
import tempfile
import unittest
from pathlib import Path

from core.market_data.upbit_snapshot_store import UpbitSnapshotStore


class UpbitSnapshotStoreTests(unittest.TestCase):
    def test_snapshot_store_writes_latest_and_candle(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            store = UpbitSnapshotStore(root_dir=root, latest_write_interval_sec=0.0)
            snapshot = {
                "symbol": "BTC/KRW",
                "market": "KRW-BTC",
                "trade": {"price": 100.0},
                "candle_1m": {
                    "symbol": "BTC/KRW",
                    "candle_date_time_kst": "2026-04-03T12:00:00",
                    "trade_price": 100.0,
                },
            }

            store.write_latest(snapshot)
            store.append_candle_1m(snapshot)
            store.write_health({"event": "connected"})

            latest_path = root / "latest" / "BTC_KRW.json"
            candle_path = root / "candles_1m" / "BTC_KRW.jsonl"
            health_path = root / "health.json"

            self.assertTrue(latest_path.exists())
            self.assertTrue(candle_path.exists())
            self.assertTrue(health_path.exists())

            latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
            self.assertEqual(latest_payload["symbol"], "BTC/KRW")

            candle_lines = candle_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(candle_lines), 1)
            candle_payload = json.loads(candle_lines[0])
            self.assertEqual(candle_payload["trade_price"], 100.0)


if __name__ == "__main__":
    unittest.main()
