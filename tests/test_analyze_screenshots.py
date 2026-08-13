"""Tests für ClashStoreAnalyzer.analyze_screenshots."""

import os
import tempfile
import unittest

import cv2
import numpy as np
from helpers import AnalyzerTestCase, _embed, _make_analyzer, _random_pattern


def _write_temp_png(canvas: np.ndarray) -> str:
    """Schreibt canvas als temporäre PNG-Datei.

    Args:
        canvas: Graustufen-Bild.

    Returns:
        Pfad zur erzeugten PNG-Datei (Aufrufer muss sie löschen).
    """
    color_img = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    cv2.imwrite(tmp.name, color_img)
    return tmp.name


def _make_screenshot_file(
    card_template: np.ndarray,
    card_row: int,
    card_col: int,
    patches: list[tuple[np.ndarray, int, int]],
) -> str:
    """Baut einen synthetischen Screenshot als temporäre PNG-Datei.

    Bettet card_template an (card_row, card_col) ein, sowie beliebige
    weitere Patches (z.B. Mengen-/Status-Templates) relativ dazu.

    Args:
        card_template: Graustufen-Muster der "Karte".
        card_row: Zeilen-Offset der Karte im Screenshot.
        card_col: Spalten-Offset der Karte im Screenshot.
        patches: Liste aus (patch, row_offset, col_offset), jeweils
            relativ zu (card_row, card_col) eingefügt.

    Returns:
        Pfad zur erzeugten PNG-Datei (Aufrufer muss sie löschen).
    """
    canvas = _random_pattern(700, 1080, seed=42)
    canvas = _embed(canvas, card_template, card_row, card_col)
    for patch, row_offset, col_offset in patches:
        canvas = _embed(canvas, patch, card_row + row_offset, card_col + col_offset)

    return _write_temp_png(canvas)


class TestAnalyzeScreenshots(AnalyzerTestCase):
    """Tests für ClashStoreAnalyzer.analyze_screenshots."""

    def test_missing_image_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.analyzer.analyze_screenshots("/bild/existiert/nicht.jpg")

    def test_happy_path_finds_card_and_calculates_price(self) -> None:
        analyzer, template_dir, config_path = _make_analyzer(
            extra_rarities={"testcard": "common"}
        )
        card_template = _random_pattern(100, 120, seed=20)
        count_template = _random_pattern(60, 80, seed=21)
        analyzer.template = {"testcard": card_template}
        analyzer.number_templates = {5: count_template}
        analyzer.status_templates = {}

        image_path = _make_screenshot_file(
            card_template,
            card_row=50,
            card_col=50,
            patches=[(count_template, 180, 10)],
        )
        try:
            results = analyzer.analyze_screenshots(image_path)
        finally:
            os.unlink(image_path)
            os.unlink(config_path)
            os.rmdir(template_dir)

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0],
            {
                "card_name": "testcard",
                "count": 5,
                "calculated_price": 50,
                "rarity": "common",
                "free": False,
            },
        )

    def test_happy_path_marks_collected_card_as_free(self) -> None:
        analyzer, template_dir, config_path = _make_analyzer(
            extra_rarities={"testcard": "common"}
        )
        card_template = _random_pattern(100, 120, seed=22)
        count_template = _random_pattern(60, 80, seed=23)
        collected_template = _random_pattern(50, 150, seed=24)
        analyzer.template = {"testcard": card_template}
        analyzer.number_templates = {5: count_template}
        analyzer.status_templates = {"collected": collected_template}

        image_path = _make_screenshot_file(
            card_template,
            card_row=50,
            card_col=50,
            patches=[
                (count_template, 180, 10),
                (collected_template, 320, 10),
            ],
        )
        try:
            results = analyzer.analyze_screenshots(image_path)
        finally:
            os.unlink(image_path)
            os.unlink(config_path)
            os.rmdir(template_dir)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["free"])
        # Free/Collected hat nichts gekostet -> einheitlich Preis 0, auch
        # wenn die zugrunde liegende Seltenheit einen Preis > 0 hätte.
        self.assertEqual(results[0]["calculated_price"], 0)

    def test_card_below_threshold_is_not_included(self) -> None:
        analyzer, template_dir, config_path = _make_analyzer(
            extra_rarities={"testcard": "common"}
        )
        card_template = _random_pattern(100, 120, seed=30)
        analyzer.template = {"testcard": card_template}
        analyzer.number_templates = {}
        analyzer.status_templates = {}

        # card_template wird NICHT eingebettet -> Konfidenz bleibt weit
        # unter der 0.8-Schwelle in analyze_screenshots.
        canvas = _random_pattern(700, 1080, seed=31)
        image_path = _write_temp_png(canvas)
        try:
            results = analyzer.analyze_screenshots(image_path)
        finally:
            os.unlink(image_path)
            os.unlink(config_path)
            os.rmdir(template_dir)

        self.assertEqual(results, [])

    def test_multiple_cards_are_all_detected(self) -> None:
        analyzer, template_dir, config_path = _make_analyzer(
            extra_rarities={"card_a": "common", "card_b": "rare"}
        )
        card_a = _random_pattern(100, 120, seed=50)
        card_b = _random_pattern(100, 120, seed=51)
        count_a = _random_pattern(60, 80, seed=52)
        count_b = _random_pattern(60, 80, seed=53)
        analyzer.template = {"card_a": card_a, "card_b": card_b}
        analyzer.number_templates = {5: count_a, 10: count_b}
        analyzer.status_templates = {}

        # Zwei Karten weit auseinander im selben Screenshot platzieren,
        # jede mit eigenem Mengen-Template in ihrem Suchbereich.
        canvas = _random_pattern(750, 1080, seed=54)
        canvas = _embed(canvas, card_a, row=50, col=50)
        canvas = _embed(canvas, count_a, row=230, col=60)
        canvas = _embed(canvas, card_b, row=400, col=600)
        canvas = _embed(canvas, count_b, row=580, col=610)
        image_path = _write_temp_png(canvas)

        try:
            results = analyzer.analyze_screenshots(image_path)
        finally:
            os.unlink(image_path)
            os.unlink(config_path)
            os.rmdir(template_dir)

        results_by_name = {r["card_name"]: r for r in results}
        self.assertEqual(set(results_by_name), {"card_a", "card_b"})
        self.assertEqual(results_by_name["card_a"]["count"], 5)
        self.assertEqual(results_by_name["card_a"]["calculated_price"], 50)
        self.assertEqual(results_by_name["card_b"]["count"], 10)
        self.assertEqual(results_by_name["card_b"]["calculated_price"], 500)


if __name__ == "__main__":
    unittest.main()
