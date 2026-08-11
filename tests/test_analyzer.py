"""Unit Tests für den ClashStoreAnalyzer."""

import json
import os
import tempfile
import unittest

import numpy as np

from main import ClashStoreAnalyzer, _compute_price


def _make_analyzer(
    extra_rarities: dict | None = None, extra_prices: dict | None = None
) -> tuple[ClashStoreAnalyzer, str, str]:
    """Erstellt einen Analyzer mit temporären Testdateien.

    Args:
        extra_rarities: Zusätzliche Karten für self.rarities.
        extra_prices: Zusätzliche Preise für self.prices.

    Returns:
        Tupel aus (analyzer, template_dir, config_path).
    """
    rarities = {"knight": "common", "musketeer": "rare", "pekka": "epic"}
    prices = {"common": 10, "rare": 50, "epic": 200, "legendary": 15000}

    if extra_rarities:
        rarities.update(extra_rarities)
    if extra_prices:
        prices.update(extra_prices)

    template_dir = tempfile.mkdtemp()
    config_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
    json.dump({"prices": prices, "rarities": rarities}, config_file)
    config_file.close()

    analyzer = ClashStoreAnalyzer(
        template_dir=template_dir,
        config_path=config_file.name,
    )
    return analyzer, template_dir, config_file.name


class TestComputePrice(unittest.TestCase):
    """Tests für die Hilfsfunktion _compute_price."""

    def test_common_price(self):
        self.assertEqual(_compute_price(10, 80), 800)

    def test_rare_price(self):
        self.assertEqual(_compute_price(50, 10), 500)

    def test_zero_count(self):
        self.assertEqual(_compute_price(10, 0), 0)

    def test_legendary_price(self):
        self.assertEqual(_compute_price(15000, 1), 15000)


class TestCalculatePrice(unittest.TestCase):
    """Tests für ClashStoreAnalyzer.calculate_price."""

    def setUp(self):
        self.analyzer, self.template_dir, self.config_path = _make_analyzer()

    def tearDown(self):
        os.unlink(self.config_path)
        os.rmdir(self.template_dir)

    def test_common_card(self):
        self.assertEqual(self.analyzer.calculate_price("knight", 80), 800)

    def test_rare_card(self):
        self.assertEqual(self.analyzer.calculate_price("musketeer", 10), 500)

    def test_epic_card(self):
        self.assertEqual(self.analyzer.calculate_price("pekka", 5), 1000)

    def test_zero_count(self):
        self.assertEqual(self.analyzer.calculate_price("knight", 0), 0)

    def test_unknown_card_raises(self):
        with self.assertRaises(ValueError):
            self.analyzer.calculate_price("nichtexistent", 10)

    def test_unknown_rarity_raises(self):
        analyzer, template_dir, config_path = _make_analyzer(
            extra_rarities={"testcard": "hero"},
        )
        try:
            with self.assertRaises(ValueError):
                analyzer.calculate_price("testcard", 1)
        finally:
            os.unlink(config_path)
            os.rmdir(template_dir)


class TestInit(unittest.TestCase):
    """Tests für ClashStoreAnalyzer.__init__."""

    def test_missing_template_dir_raises(self):
        config_file = tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        )
        json.dump({"prices": {}, "rarities": {}}, config_file)
        config_file.close()
        try:
            with self.assertRaises(FileNotFoundError):
                ClashStoreAnalyzer(
                    template_dir="/pfad/existiert/nicht",
                    config_path=config_file.name,
                )
        finally:
            os.unlink(config_file.name)

    def test_missing_config_raises(self):
        template_dir = tempfile.mkdtemp()
        try:
            with self.assertRaises(FileNotFoundError):
                ClashStoreAnalyzer(
                    template_dir=template_dir,
                    config_path="/pfad/existiert/nicht.json",
                )
        finally:
            os.rmdir(template_dir)


class TestPreprocess(unittest.TestCase):
    """Tests für ClashStoreAnalyzer.preprocess."""

    def setUp(self):
        self.analyzer, self.template_dir, self.config_path = _make_analyzer()

    def tearDown(self):
        os.unlink(self.config_path)
        os.rmdir(self.template_dir)

    def test_output_width_is_1080(self):
        dummy = np.zeros((1920, 1600, 3), dtype=np.uint8)
        gray, color = self.analyzer.preprocess(dummy)
        self.assertEqual(color.shape[1], 1080)

    def test_grayscale_is_2d(self):
        dummy = np.zeros((1920, 1600, 3), dtype=np.uint8)
        gray, _ = self.analyzer.preprocess(dummy)
        self.assertEqual(len(gray.shape), 2)

    def test_aspect_ratio_preserved(self):
        dummy = np.zeros((1920, 1080, 3), dtype=np.uint8)
        _, color = self.analyzer.preprocess(dummy)
        self.assertEqual(color.shape[0], 1920)
        self.assertEqual(color.shape[1], 1080)


class TestAnalyzeScreenshots(unittest.TestCase):
    """Tests für ClashStoreAnalyzer.analyze_screenshots."""

    def setUp(self):
        self.analyzer, self.template_dir, self.config_path = _make_analyzer()

    def tearDown(self):
        os.unlink(self.config_path)
        os.rmdir(self.template_dir)

    def test_missing_image_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.analyzer.analyze_screenshots("/bild/existiert/nicht.jpg")


if __name__ == "__main__":
    unittest.main()
