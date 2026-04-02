import unittest

from core.market_data.upbit_market_state import (
    UpbitMarketStateStore,
    symbol_to_upbit_market,
    upbit_market_to_symbol,
)


class UpbitMarketStateTests(unittest.TestCase):
    def test_symbol_market_conversion_roundtrip(self):
        symbol = "BTC/KRW"
        market = symbol_to_upbit_market(symbol)
        self.assertEqual(market, "KRW-BTC")
        self.assertEqual(upbit_market_to_symbol(market), symbol)

    def test_apply_trade_and_orderbook_payload_updates_snapshot(self):
        store = UpbitMarketStateStore(["KRW-BTC"])

        store.apply_payload(
            {
                "type": "trade",
                "code": "KRW-BTC",
                "trade_price": 100.0,
                "trade_volume": 0.3,
                "ask_bid": "BID",
                "trade_timestamp": 123456789,
                "timestamp": 123456789,
            }
        )
        store.apply_payload(
            {
                "type": "orderbook",
                "code": "KRW-BTC",
                "timestamp": 123456799,
                "total_ask_size": 3.0,
                "total_bid_size": 4.0,
                "orderbook_units": [
                    {
                        "ask_price": 101.0,
                        "bid_price": 99.0,
                        "ask_size": 1.0,
                        "bid_size": 2.0,
                    }
                ],
            }
        )

        snapshot = store.snapshot_by_market("KRW-BTC")
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["symbol"], "BTC/KRW")
        self.assertEqual(snapshot["trade"]["price"], 100.0)
        self.assertEqual(snapshot["orderbook"]["best_bid_price"], 99.0)
        self.assertEqual(snapshot["orderbook"]["best_ask_price"], 101.0)


if __name__ == "__main__":
    unittest.main()
