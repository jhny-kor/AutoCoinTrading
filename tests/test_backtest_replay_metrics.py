import unittest

from tools.backtest_replay import (
    Candle,
    EquityPoint,
    ExecutionModel,
    TradeRecord,
    apply_execution_price,
    compute_profit_factor,
    compute_sharpe_ratio,
    resolve_execution_candle,
)


class BacktestReplayMetricsTests(unittest.TestCase):
    def test_compute_profit_factor(self):
        sell_records = [
            TradeRecord(
                strategy_type="btc",
                symbol="BTC/USDT",
                side="sell",
                reason="take_profit",
                timestamp_ms=1,
                recorded_at="2026-01-01T00:00:00+00:00",
                price=100.0,
                amount=1.0,
                order_value_quote=100.0,
                fee_quote=0.0,
                realized_pnl_quote=10.0,
                realized_pnl_pct=10.0,
                net_realized_pnl_quote=9.0,
                net_realized_pnl_pct=9.0,
                cash_after=1000.0,
                position_amount_after=0.0,
                average_entry_price_after=None,
                entry_count_after=1,
                extra={},
            ),
            TradeRecord(
                strategy_type="btc",
                symbol="BTC/USDT",
                side="sell",
                reason="stop_loss",
                timestamp_ms=2,
                recorded_at="2026-01-01T00:01:00+00:00",
                price=90.0,
                amount=1.0,
                order_value_quote=90.0,
                fee_quote=0.0,
                realized_pnl_quote=-6.0,
                realized_pnl_pct=-6.0,
                net_realized_pnl_quote=-3.0,
                net_realized_pnl_pct=-3.0,
                cash_after=997.0,
                position_amount_after=0.0,
                average_entry_price_after=None,
                entry_count_after=1,
                extra={},
            ),
        ]

        self.assertEqual(3.0, compute_profit_factor(sell_records))

    def test_compute_sharpe_ratio_returns_value_for_rising_equity(self):
        equity_curve = [
            EquityPoint(timestamp_ms=1, equity_quote=1000.0, cash_quote=1000.0, position_amount=0.0, close=100.0),
            EquityPoint(timestamp_ms=2, equity_quote=1010.0, cash_quote=1010.0, position_amount=0.0, close=101.0),
            EquityPoint(timestamp_ms=3, equity_quote=1025.0, cash_quote=1025.0, position_amount=0.0, close=102.0),
            EquityPoint(timestamp_ms=4, equity_quote=1030.0, cash_quote=1030.0, position_amount=0.0, close=103.0),
        ]

        sharpe = compute_sharpe_ratio(equity_curve, timeframe="1m")

        self.assertIsNotNone(sharpe)
        self.assertGreater(sharpe, 0.0)

    def test_resolve_execution_candle_uses_next_open_when_latency_enabled(self):
        candles = [
            Candle(timestamp_ms=1, open=100.0, high=101.0, low=99.0, close=100.5, volume=10.0),
            Candle(timestamp_ms=2, open=101.0, high=102.0, low=100.0, close=101.5, volume=12.0),
        ]

        candle, index, timing = resolve_execution_candle(
            candles,
            current_index=0,
            execution_model=ExecutionModel(
                slippage_bps=0.0,
                buy_fill_ratio=1.0,
                sell_fill_ratio=1.0,
                latency_ms=200,
            ),
        )

        self.assertEqual(1, index)
        self.assertEqual("next_open", timing)
        self.assertEqual(101.0, candle.open)

    def test_apply_execution_price_moves_against_side(self):
        self.assertAlmostEqual(100.5, apply_execution_price(reference_price=100.0, side="buy", slippage_bps=50))
        self.assertAlmostEqual(99.5, apply_execution_price(reference_price=100.0, side="sell", slippage_bps=50))


if __name__ == "__main__":
    unittest.main()
