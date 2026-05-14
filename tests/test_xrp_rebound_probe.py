import unittest

from core.strategy.xrp_rebound_probe import (
    evaluate_xrp_rebound_probe,
    resolve_xrp_rebound_probe_state,
)


class XrpReboundProbeTest(unittest.TestCase):
    def test_allows_only_high_score_non_bearish_filtered_xrp_candidate(self):
        decision = evaluate_xrp_rebound_probe(
            enabled=True,
            symbol="XRP/KRW",
            eligible_symbols=("XRP/KRW",),
            signal_score=72.0,
            min_signal_score=70.0,
            htf_bearish=False,
            rsi_filter_passed=True,
            macd_filter_passed=True,
            lower_reclaim_confirmed=False,
            falling_knife_blocked=False,
            position_scale=0.25,
            extra_confirmation_loops=3,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual("xrp_rebound_probe_allowed", decision.reason)
        self.assertEqual(0.25, decision.position_scale)
        self.assertEqual(3, decision.extra_confirmation_loops)

    def test_blocks_score_htf_and_filter_failures(self):
        base = {
            "enabled": True,
            "symbol": "XRP/KRW",
            "eligible_symbols": ("XRP/KRW",),
            "signal_score": 72.0,
            "min_signal_score": 70.0,
            "htf_bearish": False,
            "rsi_filter_passed": True,
            "macd_filter_passed": True,
            "lower_reclaim_confirmed": False,
            "falling_knife_blocked": False,
            "position_scale": 0.25,
            "extra_confirmation_loops": 3,
        }

        self.assertEqual(
            "xrp_rebound_probe_signal_score_low",
            evaluate_xrp_rebound_probe(**{**base, "signal_score": 69.9}).reason,
        )
        self.assertEqual(
            "xrp_rebound_probe_htf_bearish",
            evaluate_xrp_rebound_probe(**{**base, "htf_bearish": True}).reason,
        )
        self.assertEqual(
            "xrp_rebound_probe_rsi_blocked",
            evaluate_xrp_rebound_probe(**{**base, "rsi_filter_passed": False}).reason,
        )
        self.assertEqual(
            "xrp_rebound_probe_macd_blocked",
            evaluate_xrp_rebound_probe(**{**base, "macd_filter_passed": False}).reason,
        )

    def test_xrp_scope_suppresses_global_lower_near_when_probe_fails(self):
        state = resolve_xrp_rebound_probe_state(
            enabled=True,
            symbol="XRP/KRW",
            eligible_symbols=("XRP/KRW",),
            strategy_key="mean_reversion",
            signal_score=65.0,
            min_signal_score=70.0,
            htf_bearish=False,
            rsi_filter_passed=True,
            macd_filter_passed=True,
            lower_reclaim_confirmed=False,
            falling_knife_blocked=False,
            position_scale=0.25,
            extra_confirmation_loops=3,
            entry_signal=True,
            signal_is_strong=False,
            bullish=True,
            mean_reversion_lower_near_probe_allowed=True,
            mean_reversion_lower_near_extra_confirmation_loops=3,
        )

        self.assertFalse(state.decision.allowed)
        self.assertTrue(state.lower_near_suppressed)
        self.assertFalse(state.entry_signal)
        self.assertFalse(state.bullish)
        self.assertFalse(state.mean_reversion_lower_near_probe_allowed)

    def test_allowed_xrp_probe_promotes_entry_without_lower_near(self):
        state = resolve_xrp_rebound_probe_state(
            enabled=True,
            symbol="XRP/KRW",
            eligible_symbols=("XRP/KRW",),
            strategy_key="mean_reversion",
            signal_score=75.0,
            min_signal_score=70.0,
            htf_bearish=False,
            rsi_filter_passed=True,
            macd_filter_passed=True,
            lower_reclaim_confirmed=False,
            falling_knife_blocked=False,
            position_scale=0.25,
            extra_confirmation_loops=3,
            entry_signal=False,
            signal_is_strong=False,
            bullish=False,
            mean_reversion_lower_near_probe_allowed=False,
            mean_reversion_lower_near_extra_confirmation_loops=0,
        )

        self.assertTrue(state.decision.allowed)
        self.assertTrue(state.entry_signal)
        self.assertTrue(state.signal_is_strong)
        self.assertTrue(state.bullish)
        self.assertFalse(state.mean_reversion_lower_near_probe_allowed)


if __name__ == "__main__":
    unittest.main()
