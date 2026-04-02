"""진입 상태 머신 helper 에 대한 개발 테스트."""

import unittest

from core.strategy.timing import update_entry_timing_state


class EntryTimingTests(unittest.TestCase):
    def test_entry_requires_multiple_confirmations(self):
        state_store = {}
        first = update_entry_timing_state(
            state_store=state_store,
            symbol="ETH/USDT",
            has_position=False,
            candidate_active=True,
            required_confirmations=2,
        )
        second = update_entry_timing_state(
            state_store=state_store,
            symbol="ETH/USDT",
            has_position=False,
            candidate_active=True,
            required_confirmations=2,
        )
        self.assertEqual("ARM", first.phase)
        self.assertFalse(first.ready)
        self.assertEqual("READY", second.phase)
        self.assertTrue(second.ready)

    def test_entry_resets_to_watch_when_signal_disappears(self):
        state_store = {}
        update_entry_timing_state(
            state_store=state_store,
            symbol="ETH/USDT",
            has_position=False,
            candidate_active=True,
            required_confirmations=3,
        )
        reset = update_entry_timing_state(
            state_store=state_store,
            symbol="ETH/USDT",
            has_position=False,
            candidate_active=False,
            required_confirmations=3,
        )
        self.assertEqual("WATCH", reset.phase)
        self.assertEqual(0, reset.confirmation_count)


if __name__ == "__main__":
    unittest.main()
