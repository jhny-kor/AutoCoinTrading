"""
작업 요약
- 거래소별 시장가 주문 어댑터가 기존 주문 방향, tgtCcy, 업비트 후처리를 유지하는지 검증한다.
"""

from __future__ import annotations

import unittest

from core.execution.order_adapters import (
    submit_okx_market_buy,
    submit_okx_market_sell,
    submit_upbit_market_buy,
    submit_upbit_market_sell,
)


class SequenceClock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        self.value += 1.0
        return self.value


class OrderAdapterTests(unittest.TestCase):
    def test_okx_buy_and_sell_use_existing_tgt_ccy_policy(self) -> None:
        calls = []

        def fake_place_order(exchange, symbol, side, size, *, tgt_ccy=None):
            calls.append((exchange, symbol, side, size, tgt_ccy))
            return {"side": side, "size": size}

        buy = submit_okx_market_buy(
            exchange="okx",
            symbol="BTC/USDT",
            order_value_quote=10.0,
            clock=SequenceClock(),
            place_order=fake_place_order,
        )
        sell = submit_okx_market_sell(
            exchange="okx",
            symbol="BTC/USDT",
            amount=0.01,
            clock=SequenceClock(),
            place_order=fake_place_order,
        )

        self.assertEqual(("okx", "BTC/USDT", "buy", 10.0, "quote_ccy"), calls[0])
        self.assertEqual(("okx", "BTC/USDT", "sell", 0.01, "base_ccy"), calls[1])
        self.assertLess(buy.request_started_at, buy.response_received_at)
        self.assertLess(sell.request_started_at, sell.response_received_at)

    def test_upbit_buy_enriches_order_and_invalidates_caches(self) -> None:
        calls = []

        def fake_place_order(exchange, symbol, order_value_quote):
            calls.append(("place", exchange, symbol, order_value_quote))
            return {"id": "order-1"}

        def fake_enrich_order(order, *, symbol, market_data_provider=None):
            calls.append(("enrich", order["id"], symbol, market_data_provider))
            return {**order, "enriched": True}

        def fake_invalidate_balance(exchange):
            calls.append(("balance", exchange))

        def fake_invalidate_orderbook(exchange, symbol):
            calls.append(("orderbook", exchange, symbol))

        result = submit_upbit_market_buy(
            exchange="upbit",
            symbol="BTC/KRW",
            order_value_quote=5000.0,
            market_data_provider="provider",
            clock=SequenceClock(),
            place_order=fake_place_order,
            enrich_order=fake_enrich_order,
            invalidate_balance_cache=fake_invalidate_balance,
            invalidate_orderbook_cache=fake_invalidate_orderbook,
        )

        self.assertEqual({"id": "order-1", "enriched": True}, result.order)
        self.assertEqual(
            [
                ("place", "upbit", "BTC/KRW", 5000.0),
                ("enrich", "order-1", "BTC/KRW", "provider"),
                ("balance", "upbit"),
                ("orderbook", "upbit", "BTC/KRW"),
            ],
            calls,
        )

    def test_upbit_sell_uses_amount_and_keeps_post_order_flow(self) -> None:
        calls = []

        def fake_place_order(exchange, symbol, amount):
            calls.append(("place", exchange, symbol, amount))
            return {"id": "order-2"}

        def fake_enrich_order(order, *, symbol, market_data_provider=None):
            calls.append(("enrich", order["id"], symbol))
            return order

        result = submit_upbit_market_sell(
            exchange="upbit",
            symbol="BTC/KRW",
            amount=0.02,
            clock=SequenceClock(),
            place_order=fake_place_order,
            enrich_order=fake_enrich_order,
            invalidate_balance_cache=lambda exchange: calls.append(("balance", exchange)),
            invalidate_orderbook_cache=lambda exchange, symbol: calls.append(("orderbook", exchange, symbol)),
        )

        self.assertEqual({"id": "order-2"}, result.order)
        self.assertEqual(
            [
                ("place", "upbit", "BTC/KRW", 0.02),
                ("enrich", "order-2", "BTC/KRW"),
                ("balance", "upbit"),
                ("orderbook", "upbit", "BTC/KRW"),
            ],
            calls,
        )


if __name__ == "__main__":
    unittest.main()
