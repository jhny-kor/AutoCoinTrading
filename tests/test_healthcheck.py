"""운영 헬스체크의 warning/strict 리포트 생성에 대한 개발 테스트.

수정 요약
- UTC/KST 날짜 불일치 상황에서도 가장 최근 날짜 로그를 사용하는 회귀 테스트를 추가했다.
"""

import tempfile
import unittest
import json
import os
import time
from pathlib import Path
from unittest.mock import patch

from tools.healthcheck import build_health_report


class HealthcheckTests(unittest.TestCase):
    def test_health_report_ok_when_logs_are_recent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs_dir = root / "logs" / "2026-03-29"
            analysis_dir = root / "analysis_logs" / "2026-03-29"
            structured_dir = root / "structured_logs" / "live" / "2026-03-29" / "x"
            logs_dir.mkdir(parents=True)
            analysis_dir.mkdir(parents=True)
            structured_dir.mkdir(parents=True)

            (logs_dir / "ma_crossover_bot.log").write_text("ok", encoding="utf-8")
            (logs_dir / "upbit_ma_crossover_bot.log").write_text("ok", encoding="utf-8")
            (logs_dir / "okx_btc_ema_trend_bot.log").write_text("ok", encoding="utf-8")
            (logs_dir / "upbit_btc_ema_trend_bot.log").write_text("ok", encoding="utf-8")
            (logs_dir / "telegram_command_listener.log").write_text("ok", encoding="utf-8")
            (analysis_dir / "okx__ETH_USDT.jsonl").write_text("{}", encoding="utf-8")
            (structured_dir / "strategy.jsonl").write_text("{}", encoding="utf-8")

            programs = {
                "okx": "run/ma_crossover_bot.py",
                "upbit": "run/upbit_ma_crossover_bot.py",
                "okx_btc": "run/okx_btc_ema_trend_bot.py",
                "upbit_btc": "run/upbit_btc_ema_trend_bot.py",
                "collector": "run/analysis_log_collector.py",
                "telegram": "run/telegram_command_listener.py",
            }

            with patch("tools.healthcheck.PROGRAMS", programs), \
                 patch("tools.healthcheck.current_date_str", return_value="2026-03-29"), \
                 patch("tools.healthcheck.read_pid_file", return_value=123), \
                 patch("tools.healthcheck.is_pid_alive", return_value=True), \
                 patch("tools.healthcheck.Path", side_effect=lambda p='': root / p if p else root):
                report = build_health_report(1800)

            self.assertTrue(report["ok"])
            self.assertTrue(all(item["ok"] for item in report["programs"].values()))

    def test_warning_mode_does_not_fail_overall_for_warning_program(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs_dir = root / "logs" / "2026-03-29"
            analysis_dir = root / "analysis_logs" / "2026-03-29"
            structured_dir = root / "structured_logs" / "live" / "2026-03-29" / "x"
            logs_dir.mkdir(parents=True)
            analysis_dir.mkdir(parents=True)
            structured_dir.mkdir(parents=True)

            (logs_dir / "ma_crossover_bot.log").write_text("ok", encoding="utf-8")
            (analysis_dir / "okx__ETH_USDT.jsonl").write_text("{}", encoding="utf-8")
            (structured_dir / "strategy.jsonl").write_text("{}", encoding="utf-8")

            programs = {
                "okx": "run/ma_crossover_bot.py",
                "upbit_stream": "run/upbit_market_data_stream.py",
            }

            def fake_path(path_str=""):
                return root / path_str if path_str else root

            with patch("tools.healthcheck.PROGRAMS", programs), \
                 patch("tools.healthcheck.current_date_str", return_value="2026-03-29"), \
                 patch("tools.healthcheck.read_pid_file", return_value=123), \
                 patch("tools.healthcheck.is_pid_alive", return_value=True), \
                 patch("tools.healthcheck.Path", side_effect=fake_path):
                warning_report = build_health_report(1800, mode="warning")
                strict_report = build_health_report(1800, mode="strict")

            self.assertEqual("WARN", warning_report["programs"]["upbit_stream"]["status"])
            self.assertEqual("WARN", warning_report["status"])
            self.assertEqual("FAIL", strict_report["status"])

    def test_upbit_stream_uses_runtime_health_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs_dir = root / "logs" / "2026-03-29"
            analysis_dir = root / "analysis_logs" / "2026-03-29"
            structured_dir = root / "structured_logs" / "live" / "2026-03-29" / "x"
            health_dir = root / "logs" / "runtime" / "upbit_ws"
            logs_dir.mkdir(parents=True)
            analysis_dir.mkdir(parents=True)
            structured_dir.mkdir(parents=True)
            health_dir.mkdir(parents=True)

            (analysis_dir / "okx__ETH_USDT.jsonl").write_text("{}", encoding="utf-8")
            (structured_dir / "strategy.jsonl").write_text("{}", encoding="utf-8")
            (health_dir / "health.json").write_text(
                json.dumps(
                    {
                        "connected": True,
                        "public": {
                            "event": "heartbeat",
                            "connected": True,
                            "last_message_received_at": time.time(),
                        },
                    }
                ),
                encoding="utf-8",
            )

            programs = {"upbit_stream": "run/upbit_market_data_stream.py"}

            def fake_path(path_str=""):
                return root / path_str if path_str else root

            with patch("tools.healthcheck.PROGRAMS", programs), \
                 patch("tools.healthcheck.current_date_str", return_value="2026-03-29"), \
                 patch("tools.healthcheck.read_pid_file", return_value=123), \
                 patch("tools.healthcheck.is_pid_alive", return_value=True), \
                 patch("tools.healthcheck.Path", side_effect=fake_path):
                report = build_health_report(1800, mode="warning")

            self.assertEqual("OK", report["programs"]["upbit_stream"]["status"])
            self.assertTrue(report["programs"]["upbit_stream"]["ws_health"]["connected"])

    def test_okx_stream_uses_runtime_health_json(self):
        # okx health.json 은 평면 구조(connected/event/last_message_received_at 가 최상위)라
        # 정상 가동 중 .log 가 침묵해도 log_stale 로 오탐 재기동되면 안 된다.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            analysis_dir = root / "analysis_logs" / "2026-03-29"
            structured_dir = root / "structured_logs" / "live" / "2026-03-29" / "x"
            health_dir = root / "logs" / "runtime" / "okx_ws"
            analysis_dir.mkdir(parents=True)
            structured_dir.mkdir(parents=True)
            health_dir.mkdir(parents=True)

            (analysis_dir / "okx__ETH_USDT.jsonl").write_text("{}", encoding="utf-8")
            (structured_dir / "strategy.jsonl").write_text("{}", encoding="utf-8")
            (health_dir / "health.json").write_text(
                json.dumps(
                    {
                        "connected": True,
                        "event": "heartbeat",
                        "last_message_received_at": time.time(),
                    }
                ),
                encoding="utf-8",
            )

            programs = {"okx_stream": "run/okx_market_data_stream.py"}

            def fake_path(path_str=""):
                return root / path_str if path_str else root

            with patch("tools.healthcheck.PROGRAMS", programs), \
                 patch("tools.healthcheck.current_date_str", return_value="2026-03-29"), \
                 patch("tools.healthcheck.read_pid_file", return_value=123), \
                 patch("tools.healthcheck.is_pid_alive", return_value=True), \
                 patch("tools.healthcheck.Path", side_effect=fake_path):
                report = build_health_report(1800, mode="warning")

            self.assertEqual("OK", report["programs"]["okx_stream"]["status"])
            self.assertTrue(report["programs"]["okx_stream"]["ws_health"]["connected"])
            self.assertEqual("heartbeat", report["programs"]["okx_stream"]["ws_health"]["public_event"])

    def test_health_report_uses_previous_day_files_when_today_files_are_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prev_logs_dir = root / "logs" / "2026-03-28"
            analysis_dir = root / "analysis_logs" / "2026-03-28"
            structured_dir = root / "structured_logs" / "live" / "2026-03-28" / "x"
            prev_logs_dir.mkdir(parents=True)
            analysis_dir.mkdir(parents=True)
            structured_dir.mkdir(parents=True)

            prev_log = prev_logs_dir / "ma_crossover_bot.log"
            prev_log.write_text("recent previous day log", encoding="utf-8")
            (analysis_dir / "okx__ETH_USDT.jsonl").write_text("{}", encoding="utf-8")
            (structured_dir / "strategy.jsonl").write_text("{}", encoding="utf-8")

            programs = {"okx": "run/ma_crossover_bot.py"}

            def fake_path(path_str=""):
                return root / path_str if path_str else root

            with patch("tools.healthcheck.PROGRAMS", programs), \
                 patch("tools.healthcheck.current_date_str", return_value="2026-03-29"), \
                 patch("tools.healthcheck.read_pid_file", return_value=123), \
                 patch("tools.healthcheck.is_pid_alive", return_value=True), \
                 patch("tools.healthcheck.Path", side_effect=fake_path):
                report = build_health_report(1800)

            self.assertEqual("OK", report["programs"]["okx"]["status"])
            self.assertTrue(
                report["programs"]["okx"]["latest_log"].endswith(
                    "logs/2026-03-28/ma_crossover_bot.log"
                )
            )
            self.assertTrue(
                report["analysis_logs_latest"].endswith(
                    "analysis_logs/2026-03-28/okx__ETH_USDT.jsonl"
                )
            )
            self.assertTrue(
                report["structured_logs_latest"].endswith(
                    "structured_logs/live/2026-03-28/x/strategy.jsonl"
                )
            )

    def test_health_report_uses_newer_dated_file_when_current_date_file_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            utc_logs_dir = root / "logs" / "2026-05-23"
            kst_logs_dir = root / "logs" / "2026-05-24"
            analysis_dir = root / "analysis_logs" / "2026-05-24"
            structured_dir = root / "structured_logs" / "live" / "2026-05-24" / "x"
            utc_logs_dir.mkdir(parents=True)
            kst_logs_dir.mkdir(parents=True)
            analysis_dir.mkdir(parents=True)
            structured_dir.mkdir(parents=True)

            stale_log = utc_logs_dir / "upbit_ma_crossover_bot.log"
            fresh_log = kst_logs_dir / "upbit_ma_crossover_bot.log"
            stale_log.write_text("stale utc date log", encoding="utf-8")
            fresh_log.write_text("fresh kst date log", encoding="utf-8")
            (analysis_dir / "upbit__BTC_KRW.jsonl").write_text("{}", encoding="utf-8")
            (structured_dir / "strategy.jsonl").write_text("{}", encoding="utf-8")
            old_ts = time.time() - 3600
            stale_log.touch()
            fresh_log.touch()
            os.utime(stale_log, (old_ts, old_ts))

            programs = {"upbit": "run/upbit_ma_crossover_bot.py"}

            def fake_path(path_str=""):
                return root / path_str if path_str else root

            with patch("tools.healthcheck.PROGRAMS", programs), \
                 patch("tools.healthcheck.current_date_str", return_value="2026-05-23"), \
                 patch("tools.healthcheck.read_pid_file", return_value=123), \
                 patch("tools.healthcheck.is_pid_alive", return_value=True), \
                 patch("tools.healthcheck.Path", side_effect=fake_path):
                report = build_health_report(1800)

            self.assertEqual("OK", report["programs"]["upbit"]["status"])
            self.assertTrue(
                report["programs"]["upbit"]["latest_log"].endswith(
                    "logs/2026-05-24/upbit_ma_crossover_bot.log"
                )
            )


if __name__ == "__main__":
    unittest.main()
