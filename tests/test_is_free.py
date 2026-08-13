"""Tests für ClashStoreAnalyzer.is_free."""

import unittest
from unittest.mock import patch

from helpers import AnalyzerTestCase, _embed, _random_pattern


class TestIsFree(AnalyzerTestCase):
    """Tests für ClashStoreAnalyzer.is_free."""

    def test_detects_collected_banner(self) -> None:
        banner = _random_pattern(50, 150, seed=10)
        self.analyzer.status_templates = {"collected": banner}

        canvas = _random_pattern(200, 300, seed=11)
        canvas = _embed(canvas, banner, row=50, col=40)

        self.assertTrue(self.analyzer.is_free(canvas))

    def test_returns_false_without_banner(self) -> None:
        banner = _random_pattern(50, 150, seed=10)
        self.analyzer.status_templates = {"collected": banner}

        canvas = _random_pattern(200, 300, seed=12)

        self.assertFalse(self.analyzer.is_free(canvas))

    def test_score_exactly_at_threshold_counts_as_match(self) -> None:
        # Grenzfall: der Vergleich in is_free ist ">=", nicht ">". Da sich
        # eine echte Pixel-Korrelation nicht auf einen exakten Float-Wert
        # erzwingen lässt, wird cv2.minMaxLoc gemockt.
        banner = _random_pattern(50, 150, seed=10)
        self.analyzer.status_templates = {"collected": banner}
        canvas = _random_pattern(200, 300, seed=11)
        threshold = self.analyzer._STATUS_MATCH_THRESHOLD

        with patch("cv2.minMaxLoc", return_value=(0.0, threshold, (0, 0), (0, 0))):
            result = self.analyzer.is_free(canvas)

        self.assertTrue(result)

    def test_score_just_below_threshold_is_not_a_match(self) -> None:
        banner = _random_pattern(50, 150, seed=10)
        self.analyzer.status_templates = {"collected": banner}
        canvas = _random_pattern(200, 300, seed=11)
        threshold = self.analyzer._STATUS_MATCH_THRESHOLD

        with patch(
            "cv2.minMaxLoc", return_value=(0.0, threshold - 0.001, (0, 0), (0, 0))
        ):
            result = self.analyzer.is_free(canvas)

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
