"""Tests für ClashStoreAnalyzer.calculate_price."""

import os
import unittest

from helpers import AnalyzerTestCase, _make_analyzer


class TestCalculatePrice(AnalyzerTestCase):
    """Tests für ClashStoreAnalyzer.calculate_price."""

    def test_common_card(self) -> None:
        self.assertEqual(self.analyzer.calculate_price("knight", 80), 800)

    def test_rare_card(self) -> None:
        self.assertEqual(self.analyzer.calculate_price("musketeer", 10), 500)

    def test_epic_card(self) -> None:
        self.assertEqual(self.analyzer.calculate_price("pekka", 5), 1000)

    def test_zero_count(self) -> None:
        self.assertEqual(self.analyzer.calculate_price("knight", 0), 0)

    def test_unknown_card_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.analyzer.calculate_price("nichtexistent", 10)

    def test_unknown_rarity_raises(self) -> None:
        analyzer, template_dir, config_path = _make_analyzer(
            extra_rarities={"testcard": "hero"},
        )
        try:
            with self.assertRaises(ValueError):
                analyzer.calculate_price("testcard", 1)
        finally:
            os.unlink(config_path)
            os.rmdir(template_dir)


if __name__ == "__main__":
    unittest.main()
