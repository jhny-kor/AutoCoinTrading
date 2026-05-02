"""거래량 급등 소액 진입 후보 판단 테스트."""

import unittest

from core.strategy.volume_spike_entry import evaluate_volume_spike_entry_downgrade


class VolumeSpikeEntryDowngradeTests(unittest.TestCase):
    def test_allows_small_entry_only_when_risk_conditions_pass(self):
        result = evaluate_volume_spike_entry_downgrade(
            enabled=True,
            symbol="ETH/KRW",
            eligible_symbols=("ETH/KRW", "XRP/KRW"),
            volume_ratio=5.0,
            max_volume_ratio=2.5,
            hard_max_volume_ratio=30.0,
            signal_score=88.0,
            min_signal_score=85.0,
            htf_bullish=True,
            require_htf_bullish=True,
            orderbook_pressure_score=68.0,
            min_orderbook_pressure_score=65.0,
            atr_percentile=55.0,
            max_atr_percentile=60.0,
            position_scale=0.25,
            extra_confirmation_loops=2,
        )

        self.assertTrue(result.allowed)
        self.assertEqual("small_size_extra_confirmation", result.reason)
        self.assertEqual(0.25, result.position_scale)
        self.assertEqual(2, result.extra_confirmation_loops)

    def test_blocks_extreme_volume_even_for_enabled_symbol(self):
        result = evaluate_volume_spike_entry_downgrade(
            enabled=True,
            symbol="ETH/KRW",
            eligible_symbols=("ETH/KRW", "XRP/KRW"),
            volume_ratio=111.0,
            max_volume_ratio=2.5,
            hard_max_volume_ratio=30.0,
            signal_score=90.0,
            min_signal_score=85.0,
            htf_bullish=True,
            require_htf_bullish=True,
            orderbook_pressure_score=70.0,
            min_orderbook_pressure_score=65.0,
            atr_percentile=40.0,
            max_atr_percentile=60.0,
            position_scale=0.25,
            extra_confirmation_loops=2,
        )

        self.assertFalse(result.allowed)
        self.assertEqual("volume_extreme", result.reason)

    def test_blocks_when_orderbook_pressure_is_weak(self):
        result = evaluate_volume_spike_entry_downgrade(
            enabled=True,
            symbol="XRP/KRW",
            eligible_symbols=("ETH/KRW", "XRP/KRW"),
            volume_ratio=4.0,
            max_volume_ratio=2.0,
            hard_max_volume_ratio=30.0,
            signal_score=90.0,
            min_signal_score=85.0,
            htf_bullish=True,
            require_htf_bullish=True,
            orderbook_pressure_score=40.0,
            min_orderbook_pressure_score=65.0,
            atr_percentile=45.0,
            max_atr_percentile=60.0,
            position_scale=0.25,
            extra_confirmation_loops=2,
        )

        self.assertFalse(result.allowed)
        self.assertEqual("orderbook_pressure_low", result.reason)


if __name__ == "__main__":
    unittest.main()
