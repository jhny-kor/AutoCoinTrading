"""OKX 웹소켓 캔들 provider/store/merge 개발 테스트."""

import json
import tempfile
import time
import unittest
from pathlib import Path

from core.market_data.okx_candle_store import (
    OkxCandleStore,
    merge_okx_candle_rows,
    okx_channel_to_timeframe,
)
from core.market_data.okx_provider import OkxMarketDataProvider, create_okx_market_data_provider


def _okx_row(ts, c, confirm=0):
    # [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
    return [str(ts), "100", "101", "99", str(c), "5", "0", "0", str(confirm)]


class MergeTests(unittest.TestCase):
    def test_updates_forming_candle_in_place(self):
        existing = [[1000, 100.0, 101.0, 99.0, 100.5, 5.0]]
        merged = merge_okx_candle_rows(existing, [_okx_row(1000, 100.8)])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0][4], 100.8)  # close updated

    def test_appends_new_timestamp_and_sorts(self):
        existing = [[1000, 100.0, 101.0, 99.0, 100.5, 5.0]]
        merged = merge_okx_candle_rows(existing, [_okx_row(2000, 102.0), _okx_row(1000, 100.9)])
        self.assertEqual([r[0] for r in merged], [1000, 2000])
        self.assertEqual(merged[0][4], 100.9)
        self.assertEqual(merged[1][4], 102.0)

    def test_keeps_max_rows(self):
        existing = [[i * 60000, 1.0, 1.0, 1.0, 1.0, 1.0] for i in range(10)]
        merged = merge_okx_candle_rows(existing, [_okx_row(10 * 60000, 2.0)], max_rows=5)
        self.assertEqual(len(merged), 5)
        self.assertEqual(merged[-1][0], 10 * 60000)

    def test_skips_malformed(self):
        merged = merge_okx_candle_rows([], [["x", "y"], _okx_row(1000, 100.0)])
        self.assertEqual(len(merged), 1)


class ChannelTests(unittest.TestCase):
    def test_channel_to_timeframe(self):
        self.assertEqual(okx_channel_to_timeframe("candle1m"), "1m")
        self.assertEqual(okx_channel_to_timeframe("candle5m"), "5m")
        self.assertIsNone(okx_channel_to_timeframe("trades"))


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = OkxCandleStore(self.root, write_interval_sec=0.0)
        self.provider = OkxMarketDataProvider(self.root, cache_ttl_sec=0.0, stale_sec=8.0)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, symbol, tf, n, connected=True):
        rows = [[1000 + i * 60000, 100.0, 101.0, 99.0, 100.0 + i, 5.0] for i in range(n)]
        self.store.write_candles(symbol, tf, rows, force=True)
        self.store.write_health({"connected": connected})

    def test_returns_rows_when_fresh(self):
        self._write("ETH/USDT", "1m", 60)
        rows = self.provider.get_recent_ohlcv("ETH/USDT", "1m", 50)
        self.assertIsNotNone(rows)
        self.assertEqual(len(rows), 50)
        self.assertEqual(rows[0][0], 1000 + 10 * 60000)  # last 50 of 60

    def test_none_when_disconnected(self):
        self._write("ETH/USDT", "1m", 60, connected=False)
        self.assertIsNone(self.provider.get_recent_ohlcv("ETH/USDT", "1m", 50))

    def test_none_when_insufficient_rows(self):
        self._write("ETH/USDT", "1m", 30)
        self.assertIsNone(self.provider.get_recent_ohlcv("ETH/USDT", "1m", 50))

    def test_none_when_stale(self):
        self._write("ETH/USDT", "1m", 60)
        # overwrite updated_at_ms to be old
        path = self.store.candle_path("ETH/USDT", "1m")
        payload = json.loads(path.read_text())
        payload["updated_at_ms"] = int((time.time() - 60) * 1000)
        path.write_text(json.dumps(payload))
        self.provider._ohlcv_cache.clear()
        self.assertIsNone(self.provider.get_recent_ohlcv("ETH/USDT", "1m", 50))

    def test_none_when_missing_symbol(self):
        self._write("ETH/USDT", "1m", 60)
        self.assertIsNone(self.provider.get_recent_ohlcv("XRP/USDT", "1m", 50))

    def test_factory_disabled_by_default(self):
        self.assertIsNone(create_okx_market_data_provider({}))
        self.assertIsNotNone(create_okx_market_data_provider({"enable_okx_ws_provider": True}))


if __name__ == "__main__":
    unittest.main()
