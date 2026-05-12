"""장기 과거 시장 데이터 수집 도구 테스트.

페이지 단위 장기 수집에서 중복 timestamp 를 메모리 set 으로 유지하고, launch/watch 알림 인자를 안전하게 구성하는 흐름까지 검증한다.
"""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.historical_market_collector import (
    append_jsonl_unique,
    build_collection_notification,
    build_collect_argv,
    build_default_targets,
    build_watch_argv,
    CollectionTarget,
    find_ohlcv_gaps,
    load_existing_timestamps,
    parse_okx_funding_rows,
    parse_okx_history_candles,
    parse_upbit_candles,
    synthesize_short_ohlcv_gaps,
    years_for_symbol,
)


class HistoricalMarketCollectorTests(unittest.TestCase):
    def test_years_for_symbol_uses_three_years_for_btc_and_eth_only(self):
        self.assertEqual(3, years_for_symbol("BTC/USDT", core_years=3, alt_years=1))
        self.assertEqual(3, years_for_symbol("ETH/KRW", core_years=3, alt_years=1))
        self.assertEqual(1, years_for_symbol("XRP/KRW", core_years=3, alt_years=1))

    def test_build_default_targets_applies_years_per_symbol(self):
        targets = build_default_targets(
            exchanges=["okx"],
            timeframe="1m",
            core_years=3,
            alt_years=1,
            symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        )

        by_symbol = {target.symbol: target for target in targets}
        self.assertEqual(3, by_symbol["BTC/USDT"].years)
        self.assertEqual(3, by_symbol["ETH/USDT"].years)
        self.assertEqual(1, by_symbol["SOL/USDT"].years)

    def test_parse_okx_history_candles_keeps_backtest_volume_and_quote_volume(self):
        rows = parse_okx_history_candles(
            exchange_name="okx",
            symbol="BTC/USDT",
            timeframe="1m",
            rows=[
                [
                    "1700000000000",
                    "100.0",
                    "101.0",
                    "99.0",
                    "100.5",
                    "2.0",
                    "201.0",
                    "201.0",
                    "1",
                ]
            ],
            collected_at="2026-05-06T00:00:00+00:00",
        )

        self.assertEqual(1, len(rows))
        self.assertEqual(2.0, rows[0]["volume"])
        self.assertEqual(2.0, rows[0]["volume_base"])
        self.assertEqual(201.0, rows[0]["quote_volume"])
        self.assertEqual(1, rows[0]["confirm"])

    def test_parse_upbit_candles_keeps_acc_trade_price_as_quote_volume(self):
        rows = parse_upbit_candles(
            symbol="BTC/KRW",
            timeframe="1m",
            rows=[
                {
                    "market": "KRW-BTC",
                    "candle_date_time_utc": "2023-11-14T22:13:20",
                    "candle_date_time_kst": "2023-11-15T07:13:20",
                    "opening_price": 100.0,
                    "high_price": 101.0,
                    "low_price": 99.0,
                    "trade_price": 100.5,
                    "timestamp": 1700000000000,
                    "candle_acc_trade_price": 100500.0,
                    "candle_acc_trade_volume": 1.0,
                    "unit": 1,
                }
            ],
            collected_at="2026-05-06T00:00:00+00:00",
        )

        self.assertEqual("KRW-BTC", rows[0]["market_id"])
        self.assertEqual(1699999980000, rows[0]["timestamp_ms"])
        self.assertEqual(1.0, rows[0]["volume"])
        self.assertEqual(100500.0, rows[0]["quote_volume"])

    def test_load_existing_timestamps_uses_upbit_candle_minute_for_dedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ohlcv.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "timestamp_ms": 1700000000123,
                        "candle_date_time_utc": "2023-11-14T22:13:00",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            self.assertEqual({1699999980000}, load_existing_timestamps(path))

    def test_find_ohlcv_gaps_reports_missing_minute_ranges(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ohlcv.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps({"timestamp_ms": 60_000}),
                        json.dumps({"timestamp_ms": 180_000}),
                        json.dumps({"timestamp_ms": 300_000}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self.assertEqual(
                [(120_000, 120_000, 1), (240_000, 240_000, 1)],
                find_ohlcv_gaps(path, timeframe_ms=60_000),
            )

    def test_synthesize_short_ohlcv_gaps_fills_only_short_missing_minutes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ohlcv.jsonl"
            path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "timestamp_ms": 60_000,
                                "candle_date_time_utc": "1970-01-01T00:01:00",
                                "close": 100.0,
                            }
                        ),
                        json.dumps(
                            {
                                "timestamp_ms": 180_000,
                                "candle_date_time_utc": "1970-01-01T00:03:00",
                                "close": 101.0,
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            written = synthesize_short_ohlcv_gaps(
                path,
                target=CollectionTarget("upbit", "BTC/KRW", "1m", 3),
                timeframe_ms=60_000,
                max_gap_minutes=1,
            )

            self.assertEqual(1, written)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            synthetic = [row for row in rows if row.get("synthetic")]
            self.assertEqual(1, len(synthetic))
            self.assertEqual(120_000, synthetic[0]["timestamp_ms"])
            self.assertEqual(100.0, synthetic[0]["close"])
            self.assertEqual(0.0, synthetic[0]["volume"])

    def test_append_jsonl_unique_skips_existing_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ohlcv.jsonl"
            path.write_text(
                json.dumps({"timestamp_ms": 1, "close": 100}) + "\n",
                encoding="utf-8",
            )

            written, skipped = append_jsonl_unique(
                path,
                [
                    {"timestamp_ms": 1, "close": 100},
                    {"timestamp_ms": 2, "close": 101},
                ],
                key="timestamp_ms",
            )

            self.assertEqual(1, written)
            self.assertEqual(1, skipped)
            self.assertEqual(2, len(path.read_text(encoding="utf-8").splitlines()))

    def test_append_jsonl_unique_reuses_existing_key_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ohlcv.jsonl"
            existing = {1}

            written, skipped = append_jsonl_unique(
                path,
                [
                    {"timestamp_ms": 1, "close": 100},
                    {"timestamp_ms": 2, "close": 101},
                ],
                key="timestamp_ms",
                existing_keys=existing,
            )

            self.assertEqual(1, written)
            self.assertEqual(1, skipped)
            self.assertEqual({1, 2}, existing)

    def test_build_collect_argv_preserves_launch_options(self):
        argv = build_collect_argv(
            SimpleNamespace(
                exchange="okx",
                symbols="BTC/USDT,ETH/USDT",
                timeframe="1m",
                core_years=3,
                alt_years=1,
                start=None,
                end=None,
                output_root="historical_data",
                max_pages=2,
                request_delay_sec=0.2,
                skip_funding=True,
                no_telegram=False,
            )
        )

        self.assertIn("collect", argv)
        self.assertIn("--exchange", argv)
        self.assertIn("okx", argv)
        self.assertIn("--symbols", argv)
        self.assertIn("BTC/USDT,ETH/USDT", argv)
        self.assertIn("--max-pages", argv)
        self.assertIn("2", argv)
        self.assertIn("--skip-funding", argv)
        self.assertIn("--notify-telegram", argv)

    def test_build_watch_argv_preserves_pid_path_and_interval(self):
        argv = build_watch_argv(
            SimpleNamespace(
                pid=1234,
                pid_path="logs/pids/historical_market_collector.pid",
                output_root="historical_data",
                interval_sec=10.0,
            )
        )

        self.assertIn("watch", argv)
        self.assertIn("--pid", argv)
        self.assertIn("1234", argv)
        self.assertIn("--pid-path", argv)
        self.assertIn("logs/pids/historical_market_collector.pid", argv)
        self.assertIn("--interval-sec", argv)
        self.assertIn("10.0", argv)

    def test_build_collection_notification_summarizes_rows(self):
        text = build_collection_notification(
            summary={
                "target_count": 2,
                "ohlcv": [
                    {"written_rows": 100, "page_count": 1},
                    {"written_rows": 200, "page_count": 2},
                ],
                "funding": [{"written_rows": 3}],
            },
            output_root=Path("historical_data"),
            status="완료",
        )

        self.assertIn("대상: 2개", text)
        self.assertIn("OHLCV 신규 저장: 300 rows", text)
        self.assertIn("Funding 신규 저장: 3 rows", text)
        self.assertIn("OHLCV page: 3", text)

    def test_parse_okx_funding_rows_keeps_realized_rate_and_formula(self):
        rows = parse_okx_funding_rows(
            symbol="BTC/USDT",
            swap_inst_id="BTC-USDT-SWAP",
            rows=[
                {
                    "formulaType": "withRate",
                    "fundingRate": "0.0001",
                    "fundingTime": "1700000000000",
                    "instId": "BTC-USDT-SWAP",
                    "instType": "SWAP",
                    "method": "next_period",
                    "realizedRate": "0.00009",
                }
            ],
            collected_at="2026-05-06T00:00:00+00:00",
        )

        self.assertEqual(0.0001, rows[0]["funding_rate"])
        self.assertEqual(0.00009, rows[0]["realized_rate"])
        self.assertEqual("withRate", rows[0]["formula_type"])


if __name__ == "__main__":
    unittest.main()
