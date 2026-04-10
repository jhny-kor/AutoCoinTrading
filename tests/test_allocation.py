"""포트폴리오 배분 래퍼 호출 구조에 대한 개발 테스트."""

import unittest

from core.risk.allocation import build_alt_allocation, build_btc_allocations


class DummyDecision:
    def __init__(self, requested):
        self.approved_order_value_quote = requested * 0.5
        self.base_target_pct = 0.6
        self.effective_target_pct = 0.65
        self.dynamic_bonus_pct = 0.05
        self.dynamic_bonus_applied = True
        self.total_portfolio_quote = 1000.0
        self.current_cost_basis_quote = 200.0
        self.remaining_budget_quote = 300.0
        self.target_budget_quote = 500.0


class DummyAllocator:
    def __init__(self):
        self.calls = []

    def build_buy_decision(self, **kwargs):
        self.calls.append(kwargs)
        return DummyDecision(kwargs["requested_order_value_quote"])


class AllocationTests(unittest.TestCase):
    def test_build_alt_allocation_wraps_allocator(self):
        allocator = DummyAllocator()
        requested, decision = build_alt_allocation(
            portfolio_allocator=allocator,
            exchange="EX",
            symbol="ETH/USDT",
            quote_free=100.0,
            position_ratio=0.5,
            buy_split_ratio=0.2,
            dynamic_bonus_eligible=True,
        )
        self.assertEqual(10.0, requested)
        self.assertEqual(1, len(allocator.calls))
        self.assertEqual("ETH/USDT", allocator.calls[0]["symbol"])
        self.assertAlmostEqual(5.0, decision.approved_order_value_quote)

    def test_build_btc_allocations_calls_allocator_twice(self):
        allocator = DummyAllocator()
        requested, add_on_requested, decision, add_on_decision = build_btc_allocations(
            portfolio_allocator=allocator,
            exchange="EX",
            symbol="BTC/USDT",
            quote_free=200.0,
            risk_per_trade=1.0,
            position_ratio=0.25,
            pyramid_position_ratio=0.1,
            score_scale=1.0,
            dynamic_bonus_eligible=False,
        )
        self.assertEqual(50.0, requested)
        self.assertEqual(20.0, add_on_requested)
        self.assertEqual(2, len(allocator.calls))
        self.assertAlmostEqual(25.0, decision.approved_order_value_quote)
        self.assertAlmostEqual(10.0, add_on_decision.approved_order_value_quote)


if __name__ == "__main__":
    unittest.main()
