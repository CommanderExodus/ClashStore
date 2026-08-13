"""Tests für ClashStoreAnalyzer.match_count."""

import os
import unittest
from unittest.mock import patch

from helpers import _embed, _make_analyzer, _random_pattern


class TestMatchCount(unittest.TestCase):
    """Tests für ClashStoreAnalyzer.match_count."""

    def setUp(self) -> None:
        self.analyzer, self.template_dir, self.config_path = _make_analyzer()

    def tearDown(self) -> None:
        os.unlink(self.config_path)
        os.rmdir(self.template_dir)

    def test_finds_exact_match(self) -> None:
        template = _random_pattern(60, 80, seed=1)
        self.analyzer.number_templates = {5: template}

        canvas = _random_pattern(120, 200, seed=2)
        canvas = _embed(canvas, template, row=20, col=30)

        self.assertEqual(self.analyzer.match_count(canvas), 5)

    def test_returns_zero_without_match(self) -> None:
        template = _random_pattern(60, 80, seed=1)
        self.analyzer.number_templates = {5: template}

        canvas = _random_pattern(120, 200, seed=99)

        self.assertEqual(self.analyzer.match_count(canvas), 0)

    def test_prefers_wider_template_over_narrower_prefix(self) -> None:
        # Regression: "x8" ist optisch ein Präfix von "x80" und matcht
        # überall dort ebenfalls fast perfekt. Die breitere, spezifischere
        # Menge muss gewinnen, wenn beide infrage kommen.
        wide = _random_pattern(60, 100, seed=3)
        narrow = wide[:, :40]  # exaktes Präfix von "wide"
        self.analyzer.number_templates = {8: narrow, 80: wide}

        canvas = _random_pattern(120, 200, seed=4)
        canvas = _embed(canvas, wide, row=15, col=25)

        self.assertEqual(self.analyzer.match_count(canvas), 80)

    def test_picks_best_score_within_same_width_group(self) -> None:
        # Regression: bei gleich breiten Templates (z.B. "x30"/"x50") darf
        # nicht die zufällige Dict-Reihenfolge gewinnen, sondern die
        # höhere Konfidenz innerhalb der Breiten-Gruppe.
        correct = _random_pattern(60, 90, seed=5)
        same_width_decoy = _random_pattern(60, 90, seed=6)
        self.analyzer.number_templates = {30: correct, 50: same_width_decoy}

        canvas = _random_pattern(120, 200, seed=7)
        canvas = _embed(canvas, correct, row=10, col=10)

        self.assertEqual(self.analyzer.match_count(canvas), 30)

    def test_template_larger_than_search_zone_is_skipped(self) -> None:
        template = _random_pattern(60, 80, seed=1)
        self.analyzer.number_templates = {5: template}

        tiny_canvas = _random_pattern(30, 40, seed=8)

        self.assertEqual(self.analyzer.match_count(tiny_canvas), 0)

    def test_score_exactly_at_threshold_counts_as_match(self) -> None:
        # Grenzfall: der Vergleich in match_count ist ">=", nicht ">".
        # Da sich eine echte Pixel-Korrelation nicht auf einen exakten
        # Float-Wert erzwingen lässt, wird cv2.minMaxLoc gemockt.
        template = _random_pattern(60, 80, seed=1)
        self.analyzer.number_templates = {5: template}
        canvas = _random_pattern(120, 200, seed=2)
        threshold = self.analyzer._COUNT_MATCH_THRESHOLD

        with patch("cv2.minMaxLoc", return_value=(0.0, threshold, (0, 0), (0, 0))):
            result = self.analyzer.match_count(canvas)

        self.assertEqual(result, 5)

    def test_score_just_below_threshold_is_not_a_match(self) -> None:
        template = _random_pattern(60, 80, seed=1)
        self.analyzer.number_templates = {5: template}
        canvas = _random_pattern(120, 200, seed=2)
        threshold = self.analyzer._COUNT_MATCH_THRESHOLD

        with patch(
            "cv2.minMaxLoc", return_value=(0.0, threshold - 0.001, (0, 0), (0, 0))
        ):
            result = self.analyzer.match_count(canvas)

        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
