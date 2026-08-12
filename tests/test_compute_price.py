"""Tests für die Hilfsfunktion _compute_price."""

import unittest

from main import _compute_price


class TestComputePrice(unittest.TestCase):
    """Tests für die Hilfsfunktion _compute_price."""

    def test_common_price(self):
        self.assertEqual(_compute_price(10, 80), 800)

    def test_rare_price(self):
        self.assertEqual(_compute_price(50, 10), 500)

    def test_zero_count(self):
        self.assertEqual(_compute_price(10, 0), 0)

    def test_epic_price(self):
        self.assertEqual(_compute_price(200, 5), 1000)

    def test_legendary_price(self):
        self.assertEqual(_compute_price(15000, 1), 15000)


if __name__ == "__main__":
    unittest.main()
