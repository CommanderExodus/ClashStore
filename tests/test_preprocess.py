"""Tests für ClashStoreAnalyzer.preprocess."""

import os
import unittest

import numpy as np
from helpers import _make_analyzer


class TestPreprocess(unittest.TestCase):
    """Tests für ClashStoreAnalyzer.preprocess."""

    def setUp(self) -> None:
        self.analyzer, self.template_dir, self.config_path = _make_analyzer()

    def tearDown(self) -> None:
        os.unlink(self.config_path)
        os.rmdir(self.template_dir)

    def test_output_width_is_1080(self) -> None:
        dummy = np.zeros((1920, 1600, 3), dtype=np.uint8)
        gray, color = self.analyzer.preprocess(dummy)
        self.assertEqual(color.shape[1], 1080)

    def test_grayscale_is_2d(self) -> None:
        dummy = np.zeros((1920, 1600, 3), dtype=np.uint8)
        gray, _ = self.analyzer.preprocess(dummy)
        self.assertEqual(len(gray.shape), 2)

    def test_aspect_ratio_preserved(self) -> None:
        dummy = np.zeros((1920, 1080, 3), dtype=np.uint8)
        _, color = self.analyzer.preprocess(dummy)
        self.assertEqual(color.shape[0], 1920)
        self.assertEqual(color.shape[1], 1080)


if __name__ == "__main__":
    unittest.main()
