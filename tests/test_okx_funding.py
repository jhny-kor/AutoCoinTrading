"""OKX funding rate helper 테스트."""

import unittest

from core.execution.okx import spot_symbol_to_okx_swap_inst_id


class OkxFundingTests(unittest.TestCase):
    def test_spot_symbol_maps_to_swap_inst_id(self):
        self.assertEqual("BTC-USDT-SWAP", spot_symbol_to_okx_swap_inst_id("BTC/USDT"))
        self.assertEqual("SOL-USDT-SWAP", spot_symbol_to_okx_swap_inst_id("SOL/USDT"))

    def test_invalid_symbol_returns_none(self):
        self.assertIsNone(spot_symbol_to_okx_swap_inst_id("BTCUSDT"))


if __name__ == "__main__":
    unittest.main()
