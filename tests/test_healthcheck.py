import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
