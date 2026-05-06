"""자동복구 watchdog 의 대상 선별과 재기동 제한 테스트."""

import time
import unittest
from unittest.mock import patch

from tools.auto_recovery_watchdog import (
    RecoveryTarget,
    detect_recovery_targets,
    recover_target,
)


class AutoRecoveryWatchdogTests(unittest.TestCase):
    def test_detect_recovery_targets_includes_fail_and_warning_when_enabled(self):
        report = {
            "programs": {
                "okx": {"status": "FAIL", "alive": False, "pid": None},
                "upbit_stream": {
                    "status": "WARN",
                    "alive": True,
                    "pid": 123,
                    "ws_health": {"connected": False},
                },
                "telegram": {"status": "OK", "alive": True, "pid": 456},
            }
        }

        targets = detect_recovery_targets(
            report,
            recover_warnings=True,
            recoverable_programs=("okx", "upbit_stream", "telegram"),
        )

        self.assertEqual(["okx", "upbit_stream"], [target.name for target in targets])
        self.assertEqual("process_down", targets[0].reason)
        self.assertEqual("websocket_disconnected", targets[1].reason)

    def test_recover_target_skips_when_cooldown_is_active(self):
        now_ts = time.time()
        state = {
            "programs": {
                "okx": {
                    "last_recovery_ts": now_ts - 10,
                    "restart_timestamps": [now_ts - 10],
                }
            }
        }
        calls: list[str] = []
        target = RecoveryTarget(
            name="okx",
            status="FAIL",
            reason="process_down",
            item={"pid": 111, "alive": False},
        )

        event = recover_target(
            target,
            state=state,
            now_ts=now_ts,
            cooldown_sec=300,
            max_restarts_per_hour=3,
            dry_run=False,
            notify=False,
            stop_func=lambda name: calls.append(f"stop:{name}") or 0,
            start_func=lambda name: calls.append(f"start:{name}") or 0,
        )

        self.assertEqual("skipped", event["result"])
        self.assertEqual([], calls)
        self.assertEqual("recovery_cooldown_active", state["programs"]["okx"]["last_detail"].split(":", 1)[0])

    def test_recover_target_restarts_and_records_new_pid(self):
        now_ts = time.time()
        state = {"programs": {}}
        calls: list[str] = []
        target = RecoveryTarget(
            name="okx",
            status="FAIL",
            reason="process_down",
            item={"pid": None, "alive": False},
        )

        with patch("tools.auto_recovery_watchdog.read_pid_file", return_value=456), \
             patch("tools.auto_recovery_watchdog.is_pid_alive", return_value=True), \
             patch("tools.auto_recovery_watchdog.time.sleep", return_value=None):
            event = recover_target(
                target,
                state=state,
                now_ts=now_ts,
                cooldown_sec=300,
                max_restarts_per_hour=3,
                dry_run=False,
                notify=False,
                stop_func=lambda name: calls.append(f"stop:{name}") or 0,
                start_func=lambda name: calls.append(f"start:{name}") or 0,
            )

        self.assertEqual("recovered", event["result"])
        self.assertEqual(["stop:okx", "start:okx"], calls)
        self.assertEqual(456, state["programs"]["okx"]["last_pid"])


if __name__ == "__main__":
    unittest.main()
