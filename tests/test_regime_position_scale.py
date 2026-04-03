import unittest

from core.risk.allocation import apply_regime_position_scale


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


if __name__ == "__main__":
    unittest.main()
