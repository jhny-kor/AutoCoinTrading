"""공통 프로그램 레지스트리 일관성 테스트."""

import unittest

from core.runtime.program_registry import (
    PROGRAM_BY_NAME,
    PROGRAM_CHOICES,
    PROGRAM_SPECS,
    PROGRAMS,
    START_ALL_ORDER,
    TRADE_PROGRAM_SPECS,
)


class ProgramRegistryTests(unittest.TestCase):
    def test_program_choices_match_specs(self):
        self.assertEqual(PROGRAM_CHOICES, tuple(spec.name for spec in PROGRAM_SPECS))

    def test_start_all_order_contains_all_runtime_programs_once(self):
        self.assertEqual(set(START_ALL_ORDER), set(PROGRAMS))
        self.assertEqual(len(START_ALL_ORDER), len(PROGRAMS))

    def test_trade_specs_have_runtime_metadata(self):
        for spec in TRADE_PROGRAM_SPECS:
            self.assertIsNotNone(spec.structure_name)
            self.assertIsNotNone(spec.exchange)
            self.assertIsNotNone(spec.strategy_type)
            self.assertIsNotNone(spec.report_label)
            self.assertEqual(PROGRAM_BY_NAME[spec.name], spec)


if __name__ == "__main__":
    unittest.main()

