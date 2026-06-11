"""
작업 요약
- 알트/BTC 청산 퍼널 ready reason helper 의 우선순위를 검증한다.
- 알트 순익 trailing exit reason 우선순위를 검증한다.
"""

from __future__ import annotations

import unittest

from core.strategy.exit_reasons import (
    resolve_alt_exit_ready_reason,
    resolve_btc_exit_ready_reason,
)


class ExitReasonTests(unittest.TestCase):
    def test_alt_exit_ready_reason_uses_existing_priority(self) -> None:
        self.assertEqual(
            "stop_loss_triggered",
            resolve_alt_exit_ready_reason(
                stop_loss_triggered=True,
                profit_protect_triggered=True,
                break_even_guard_triggered=True,
                volume_spike_exit_triggered=True,
                sol_probe_time_exit_triggered=True,
            ),
        )
        self.assertEqual(
            "alt_profit_trailing_exit_triggered",
            resolve_alt_exit_ready_reason(
                stop_loss_triggered=False,
                profit_protect_triggered=True,
                break_even_guard_triggered=True,
                volume_spike_exit_triggered=True,
                sol_probe_time_exit_triggered=True,
                alt_profit_trailing_exit_triggered=True,
            ),
        )
        self.assertEqual(
            "volume_spike_exit_triggered",
            resolve_alt_exit_ready_reason(
                stop_loss_triggered=False,
                profit_protect_triggered=False,
                break_even_guard_triggered=False,
                volume_spike_exit_triggered=True,
                sol_probe_time_exit_triggered=True,
            ),
        )
        self.assertEqual(
            "take_profit_conditions_met",
            resolve_alt_exit_ready_reason(
                stop_loss_triggered=False,
                profit_protect_triggered=False,
                break_even_guard_triggered=False,
                volume_spike_exit_triggered=False,
                sol_probe_time_exit_triggered=False,
            ),
        )

    def test_btc_exit_ready_reason_uses_existing_priority(self) -> None:
        self.assertEqual(
            "stop_loss_triggered",
            resolve_btc_exit_ready_reason(
                stop_loss_triggered=True,
                partial_take_profit_triggered=True,
                profit_protect_triggered=True,
                trailing_stop_triggered=True,
                donchian_failure_triggered=True,
                trend_exit_triggered=True,
            ),
        )
        self.assertEqual(
            "trailing_stop_triggered",
            resolve_btc_exit_ready_reason(
                stop_loss_triggered=False,
                partial_take_profit_triggered=False,
                profit_protect_triggered=False,
                trailing_stop_triggered=True,
                donchian_failure_triggered=True,
                trend_exit_triggered=True,
            ),
        )
        self.assertEqual(
            "trend_exit_triggered",
            resolve_btc_exit_ready_reason(
                stop_loss_triggered=False,
                partial_take_profit_triggered=False,
                profit_protect_triggered=False,
                trailing_stop_triggered=False,
                donchian_failure_triggered=False,
                trend_exit_triggered=False,
            ),
        )


if __name__ == "__main__":
    unittest.main()
