"""BTC 손절 후 패턴 재진입 gate 테스트."""

import unittest

from core.strategy.btc import compute_btc_stop_loss_reentry_gate


class BtcReentryGateTests(unittest.TestCase):
    def test_pattern_reentry_blocks_until_signal_recovers(self):
        blocked = compute_btc_stop_loss_reentry_gate(
            enabled=True,
            elapsed_since_stop_loss_sec=120,
            min_cooldown_sec=180,
            entry_signal=True,
            bullish=False,
            signal_score=68.0,
            min_signal_score=72.0,
            volume_filter_passed=True,
            atr_filter_passed=True,
            confirm_bullish=False,
            require_confirm_bullish=True,
            require_fresh_cross=True,
        )
        self.assertFalse(blocked["pattern_ready"])

        ready = compute_btc_stop_loss_reentry_gate(
            enabled=True,
            elapsed_since_stop_loss_sec=240,
            min_cooldown_sec=180,
            entry_signal=True,
            bullish=True,
            signal_score=78.0,
            min_signal_score=72.0,
            volume_filter_passed=True,
            atr_filter_passed=True,
            confirm_bullish=True,
            require_confirm_bullish=True,
            require_fresh_cross=True,
        )
        self.assertTrue(ready["pattern_ready"])


if __name__ == "__main__":
    unittest.main()
