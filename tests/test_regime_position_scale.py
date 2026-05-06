import unittest

from core.risk.allocation import (
    apply_regime_position_scale,
    build_alt_position_sizing,
    build_btc_position_sizing,
    format_alt_position_sizing_log,
    format_btc_position_sizing_log,
)


class DummyAltStrategy:
    mean_reversion_lower_near_position_scale = 0.6

    def get_regime_position_scale(self, symbol_regime):
        return {"TRENDING": 1.0, "LOW_ENERGY": 0.0}.get(symbol_regime, 0.4)

    def get_btc_regime_position_scale_for_symbol(self, symbol, btc_regime):
        if symbol == "ETH/KRW" and btc_regime == "LOW_ENERGY":
            return 0.35
        return {"LOW_ENERGY": 0.5}.get(btc_regime, 1.0)

    def get_btc_atr_position_scale(self, atr_pct):
        if atr_pct is not None and atr_pct < 0.12:
            return 0.25
        if atr_pct is not None and atr_pct < 0.18:
            return 0.7
        return 1.0

    def get_alt_atr_position_scale(self, atr_pct):
        if atr_pct is not None and atr_pct > 1.0:
            return 0.8
        return 1.0


class DummyBtcSettings:
    low_energy_probe_position_scale = 0.25

    def get_regime_position_scale(self, symbol_regime):
        return {"TRENDING": 1.1, "CHOPPY": 0.5}.get(symbol_regime, 1.0)

    def get_atr_position_scale(self, atr_pct):
        if atr_pct is not None and atr_pct < 0.10:
            return 0.35
        if atr_pct is not None and atr_pct < 0.16:
            return 0.8
        return 1.0


class RegimePositionScaleTests(unittest.TestCase):
    def test_apply_regime_position_scale_basic(self):
        self.assertEqual(
            apply_regime_position_scale(base_position_ratio=0.5, regime_scale=0.4),
            0.2,
        )

    def test_apply_regime_position_scale_clamps_upper_bound(self):
        self.assertEqual(
            apply_regime_position_scale(base_position_ratio=1.0, regime_scale=2.0),
            1.2,
        )

    def test_apply_regime_position_scale_clamps_lower_bound(self):
        self.assertEqual(
            apply_regime_position_scale(base_position_ratio=0.5, regime_scale=-1.0),
            0.0,
        )

    def test_build_alt_position_sizing_preserves_scale_order(self):
        sizing = build_alt_position_sizing(
            strategy=DummyAltStrategy(),
            symbol="ETH/KRW",
            base_position_ratio=0.7,
            symbol_regime="TRENDING",
            btc_reference_regime="LOW_ENERGY",
            btc_reference_atr_pct=0.11,
            alt_atr_pct=1.2,
            score_scale=0.75,
            volume_spike_position_scale=0.5,
            mean_reversion_lower_near_position_scale=0.6,
            low_energy_probe_allowed=True,
            low_energy_probe_position_scale=0.4,
        )

        self.assertAlmostEqual(sizing.regime_position_scale, 1.0)
        self.assertAlmostEqual(sizing.btc_regime_position_scale, 0.35)
        self.assertAlmostEqual(sizing.btc_atr_position_scale, 0.25)
        self.assertAlmostEqual(sizing.alt_atr_position_scale, 0.8)
        self.assertAlmostEqual(sizing.pre_score_position_ratio, 0.049)
        self.assertAlmostEqual(sizing.position_ratio, 0.0147)
        self.assertAlmostEqual(sizing.low_energy_probe_position_ratio, 0.0147)
        self.assertIn(
            "BTC 레짐(LOW_ENERGY) 스케일 0.35x",
            format_alt_position_sizing_log(
                symbol="ETH/KRW",
                sizing=sizing,
                btc_reference_regime="LOW_ENERGY",
                btc_reference_atr_pct=0.11,
                alt_atr_pct=1.2,
            ),
        )

    def test_build_btc_position_sizing_preserves_low_energy_probe_order(self):
        sizing = build_btc_position_sizing(
            settings=DummyBtcSettings(),
            symbol="BTC/KRW",
            base_position_ratio=0.4,
            symbol_regime="CHOPPY",
            atr_pct=0.09,
            score_scale=0.75,
            low_energy_probe_allowed=True,
            low_energy_probe_position_scale=0.4,
        )

        self.assertAlmostEqual(sizing.regime_position_scale, 0.5)
        self.assertAlmostEqual(sizing.atr_position_scale, 0.35)
        self.assertAlmostEqual(sizing.pre_score_position_ratio, 0.07)
        self.assertAlmostEqual(sizing.position_ratio, 0.0525)
        self.assertIn(
            "ATR 스케일 0.35x",
            format_btc_position_sizing_log(symbol="BTC/KRW", sizing=sizing),
        )


if __name__ == "__main__":
    unittest.main()
