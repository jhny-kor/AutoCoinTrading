import unittest

from core.risk.allocation import (
    apply_regime_position_scale,
    build_alt_position_sizing,
    build_btc_position_sizing,
    format_allocation_score_log,
    format_alt_position_sizing_log,
    format_btc_position_sizing_log,
    format_dynamic_bonus_log,
    format_portfolio_budget_log,
    AllocationScoreResult,
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


class DummyAllocationDecision:
    base_target_pct = 0.3
    effective_target_pct = 0.35
    current_cost_basis_quote = 1234.5678
    remaining_budget_quote = 9876.5432
    dynamic_bonus_pct = 0.05


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
        self.assertAlmostEqual(sizing.position_ratio, 0.02205)
        self.assertAlmostEqual(sizing.mean_reversion_lower_near_position_ratio, 0.02205)
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
        self.assertIn(
            "하단근접 probe 비중 0.0221",
            format_alt_position_sizing_log(
                symbol="ETH/KRW",
                sizing=sizing,
                btc_reference_regime="LOW_ENERGY",
                btc_reference_atr_pct=0.11,
                alt_atr_pct=1.2,
            ),
        )

    def test_lower_near_probe_keeps_small_position_when_symbol_regime_zero(self):
        sizing = build_alt_position_sizing(
            strategy=DummyAltStrategy(),
            symbol="XRP/KRW",
            base_position_ratio=0.3,
            symbol_regime="LOW_ENERGY",
            btc_reference_regime="LOW_ENERGY",
            btc_reference_atr_pct=0.11,
            alt_atr_pct=0.4,
            score_scale=0.75,
            mean_reversion_lower_near_position_scale=0.35,
        )

        self.assertAlmostEqual(sizing.regime_position_scale, 0.0)
        self.assertAlmostEqual(sizing.pre_score_position_ratio, 0.0)
        self.assertAlmostEqual(sizing.mean_reversion_lower_near_position_ratio, 0.00984375)
        self.assertAlmostEqual(sizing.position_ratio, 0.00984375)

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

    def test_format_allocation_score_log_preserves_fields(self):
        score = AllocationScoreResult(
            allocation_score=72.3,
            signal_score_component=80.0,
            market_score_component=60.0,
            execution_score_component=90.0,
            diversification_score_component=55.0,
            score_scale=0.9,
            reason_top="diversification",
        )

        self.assertEqual(
            "[XRP/KRW] allocation score: 총점 72.3 | "
            "signal 80.0, market 60.0, execution 90.0, diversification 55.0 | "
            "주요 사유 diversification",
            format_allocation_score_log(symbol="XRP/KRW", score=score),
        )

    def test_format_portfolio_budget_log_preserves_quote_precision(self):
        self.assertEqual(
            "[BTC/KRW] 포트폴리오 목표 비중: 기본 30.00% | 유효 35.00% | "
            "누적 투입 1235 KRW | 남은 예산 9877 KRW",
            format_portfolio_budget_log(
                symbol="BTC/KRW",
                allocation_decision=DummyAllocationDecision(),
                quote="KRW",
                quote_decimals=0,
            ),
        )
        self.assertEqual(
            "[BTC/USDT] 포트폴리오 목표 비중: 기본 30.00% | 유효 35.00% | "
            "누적 투입 1234.5678 USDT | 남은 예산 9876.5432 USDT",
            format_portfolio_budget_log(
                symbol="BTC/USDT",
                allocation_decision=DummyAllocationDecision(),
                quote="USDT",
                quote_decimals=4,
            ),
        )

    def test_format_dynamic_bonus_log_preserves_message(self):
        self.assertEqual(
            "[ETH/KRW] 거래량/추세 강세로 목표 비중을 +5.00% 임시 확대합니다.",
            format_dynamic_bonus_log(
                symbol="ETH/KRW",
                allocation_decision=DummyAllocationDecision(),
            ),
        )


if __name__ == "__main__":
    unittest.main()
