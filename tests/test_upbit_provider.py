import json
import tempfile
import time
import unittest
from pathlib import Path

from core.market_data.upbit_provider import UpbitMarketDataProvider


class UpbitProviderTests(unittest.TestCase):
    def test_provider_returns_best_bid_when_snapshot_is_fresh(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            latest_dir = root / "latest"
            latest_dir.mkdir(parents=True, exist_ok=True)
            (root / "health.json").write_text(
                json.dumps({"connected": True}),
                encoding="utf-8",
            )
            payload = {
                "symbol": "BTC/KRW",
                "updated_at_ms": int(time.time() * 1000),
                "orderbook": {
                    "best_bid_price": 100.0,
                    "timestamp_ms": int(time.time() * 1000),
                },
            }
            (latest_dir / "BTC_KRW.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            provider = UpbitMarketDataProvider(root_dir=root, cache_ttl_sec=0.0, stale_sec=5.0)
            self.assertEqual(provider.get_best_bid("BTC/KRW"), 100.0)

    def test_provider_returns_none_when_snapshot_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            latest_dir = root / "latest"
            latest_dir.mkdir(parents=True, exist_ok=True)
            old_ts_ms = int((time.time() - 30) * 1000)
            payload = {
                "symbol": "BTC/KRW",
                "updated_at_ms": old_ts_ms,
                "orderbook": {
                    "best_bid_price": 100.0,
                    "timestamp_ms": old_ts_ms,
                },
            }
            (latest_dir / "BTC_KRW.json").write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            provider = UpbitMarketDataProvider(root_dir=root, cache_ttl_sec=0.0, stale_sec=5.0)
            self.assertIsNone(provider.get_best_bid("BTC/KRW"))

    def test_provider_reads_private_balances_and_order_event(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            private_dir = root / "private"
            private_dir.mkdir(parents=True, exist_ok=True)

            myasset_payload = {
                "assets": [
                    {"currency": "BTC", "balance": "0.1234"},
                    {"currency": "KRW", "balance": "50000"},
                ]
            }
            (private_dir / "myasset_latest.json").write_text(
                json.dumps(myasset_payload),
                encoding="utf-8",
            )

            myorder_payload = {
                "uuid": "order-123",
                "market": "KRW-BTC",
                "executed_volume": "0.01",
                "remaining_volume": "0.00",
                "state": "done",
                "captured_at_local": "2099-01-01T00:00:00+09:00",
            }
            (private_dir / "myorder_latest.json").write_text(
                json.dumps(myorder_payload),
                encoding="utf-8",
            )

            provider = UpbitMarketDataProvider(root_dir=root, cache_ttl_sec=0.0, stale_sec=5.0)
            balances = provider.get_private_balances("BTC", "KRW")
            self.assertEqual(balances, (0.1234, 50000.0))

            event = provider.find_recent_myorder_event(
                order_id="order-123",
                market="KRW-BTC",
                max_age_sec=999999999,
            )
            self.assertIsNotNone(event)
            self.assertEqual(event["state"], "done")

    def test_provider_backfills_private_balances_from_jsonl_when_latest_is_partial(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            private_dir = root / "private"
            private_dir.mkdir(parents=True, exist_ok=True)

            (private_dir / "myasset_latest.json").write_text(
                json.dumps(
                    {
                        "assets": [
                            {"currency": "KRW", "balance": "1000.0"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (private_dir / "myasset.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "assets": [
                                    {"currency": "ETH", "balance": "0.02483831"},
                                ]
                            }
                        ),
                        json.dumps(
                            {
                                "assets": [
                                    {"currency": "KRW", "balance": "1000.0"},
                                ]
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            provider = UpbitMarketDataProvider(root_dir=root, cache_ttl_sec=0.0, stale_sec=5.0)
            balances = provider.get_private_balances("ETH", "KRW")
            self.assertEqual(balances, (0.02483831, 1000.0))

    def test_provider_reads_recent_ohlcv_1m(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            latest_dir = root / "latest"
            candle_dir = root / "candles_1m"
            latest_dir.mkdir(parents=True, exist_ok=True)
            candle_dir.mkdir(parents=True, exist_ok=True)
            now_ms = int(time.time() * 1000)
            (root / "health.json").write_text(
                json.dumps({"connected": True}),
                encoding="utf-8",
            )
            (latest_dir / "BTC_KRW.json").write_text(
                json.dumps(
                    {
                        "symbol": "BTC/KRW",
                        "updated_at_ms": now_ms,
                        "orderbook": {"best_bid_price": 100.0, "timestamp_ms": now_ms},
                    }
                ),
                encoding="utf-8",
            )
            candle_path = candle_dir / "BTC_KRW.jsonl"
            candle_rows = [
                {
                    "candle_date_time_kst": "2026-04-03T12:00:00",
                    "opening_price": 100.0,
                    "high_price": 101.0,
                    "low_price": 99.0,
                    "trade_price": 100.5,
                    "candle_acc_trade_volume": 1.2,
                },
                {
                    "candle_date_time_kst": "2026-04-03T12:01:00",
                    "opening_price": 100.5,
                    "high_price": 102.0,
                    "low_price": 100.0,
                    "trade_price": 101.5,
                    "candle_acc_trade_volume": 1.5,
                },
            ]
            candle_path.write_text(
                "\n".join(json.dumps(row) for row in candle_rows) + "\n",
                encoding="utf-8",
            )

            provider = UpbitMarketDataProvider(root_dir=root, cache_ttl_sec=0.0, stale_sec=5.0)
            rows = provider.get_recent_ohlcv_1m("BTC/KRW", 2)
            self.assertIsNotNone(rows)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[-1][1], 100.5)
            self.assertEqual(rows[-1][4], 101.5)

    def test_provider_resamples_recent_ohlcv_5m(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            latest_dir = root / "latest"
            candle_dir = root / "candles_1m"
            latest_dir.mkdir(parents=True, exist_ok=True)
            candle_dir.mkdir(parents=True, exist_ok=True)
            now_ms = int(time.time() * 1000)
            (root / "health.json").write_text(json.dumps({"connected": True}), encoding="utf-8")
            (latest_dir / "BTC_KRW.json").write_text(
                json.dumps(
                    {
                        "symbol": "BTC/KRW",
                        "updated_at_ms": now_ms,
                        "orderbook": {"best_bid_price": 100.0, "timestamp_ms": now_ms},
                    }
                ),
                encoding="utf-8",
            )

            rows = []
            prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0]
            for minute, price in enumerate(prices):
                rows.append(
                    {
                        "candle_date_time_kst": (
                            f"2026-04-03T12:0{minute}:00"
                            if minute < 10
                            else f"2026-04-03T12:{minute}:00"
                        ),
                        "opening_price": price,
                        "high_price": price + 1,
                        "low_price": price - 1,
                        "trade_price": price + 0.5,
                        "candle_acc_trade_volume": 1.0,
                    }
                )
            candle_path = candle_dir / "BTC_KRW.jsonl"
            candle_path.write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n",
                encoding="utf-8",
            )

            provider = UpbitMarketDataProvider(root_dir=root, cache_ttl_sec=0.0, stale_sec=5.0)
            result = provider.get_recent_ohlcv("BTC/KRW", "5m", 1)
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0][1], 110.0)
            self.assertEqual(result[0][2], 115.0)
            self.assertEqual(result[0][3], 109.0)
            self.assertEqual(result[0][4], 114.5)
            self.assertEqual(result[0][5], 5.0)


if __name__ == "__main__":
    unittest.main()
