"""포지션 snapshot helper 테스트."""

import unittest
from unittest.mock import patch

from reporting.position_snapshot import load_recovered_entry_prices


class PositionSnapshotTests(unittest.TestCase):
    def test_load_recovered_entry_prices_ignores_empty_entries(self):
        state_with_price = type("State", (), {"average_entry_price": 123.4})()
        state_without_price = type("State", (), {"average_entry_price": None})()

        with patch(
            "reporting.position_snapshot.restore_program_position_states",
            side_effect=[
                {"BTC/USDT": state_with_price},
                {"ETH/USDT": state_without_price},
            ],
        ):
            result = load_recovered_entry_prices(
                (
                    ("okx_btc_ema_trend_bot", ["BTC/USDT"]),
                    ("ma_crossover_bot", ["ETH/USDT"]),
                )
            )

        self.assertEqual(result, {"BTC/USDT": 123.4})


if __name__ == "__main__":
    unittest.main()

