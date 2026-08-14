"""Tests fürs Laden der Mengen- und Status-Templates in __init__."""

import json
import os
import shutil
import tempfile
import unittest

import cv2
from helpers import _random_pattern

from analyzer import ClashStoreAnalyzer


class TestNumberAndStatusTemplateLoading(unittest.TestCase):
    """Tests fürs Laden der Mengen- und Status-Templates in __init__."""

    def setUp(self) -> None:
        self.template_dir = tempfile.mkdtemp()
        self.number_template_dir = tempfile.mkdtemp()
        self.config_file = tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        )
        json.dump({"prices": {}, "rarities": {}}, self.config_file)
        self.config_file.close()

        pattern = _random_pattern(20, 20, seed=1)
        for filename in ["x5.png", "x50.png", "xabc.png", "notanumber.png"]:
            cv2.imwrite(os.path.join(self.number_template_dir, filename), pattern)
        for filename in ["collected.png", "free!.png"]:
            cv2.imwrite(os.path.join(self.number_template_dir, filename), pattern)

        cv2.imwrite(os.path.join(self.template_dir, "knight.png"), pattern)
        with open(os.path.join(self.template_dir, "readme.txt"), "w") as f:
            f.write("keine Bilddatei")

    def tearDown(self) -> None:
        os.unlink(self.config_file.name)
        shutil.rmtree(self.template_dir)
        shutil.rmtree(self.number_template_dir)

    def test_loads_only_valid_number_templates(self) -> None:
        analyzer = ClashStoreAnalyzer(
            template_dir=self.template_dir,
            config_path=self.config_file.name,
            number_template_dir=self.number_template_dir,
        )
        self.assertEqual(set(analyzer.number_templates.keys()), {5, 50})

    def test_loads_status_templates(self) -> None:
        analyzer = ClashStoreAnalyzer(
            template_dir=self.template_dir,
            config_path=self.config_file.name,
            number_template_dir=self.number_template_dir,
        )
        self.assertEqual(set(analyzer.status_templates.keys()), {"collected", "free"})

    def test_loads_card_templates(self) -> None:
        analyzer = ClashStoreAnalyzer(
            template_dir=self.template_dir,
            config_path=self.config_file.name,
            number_template_dir=self.number_template_dir,
        )
        self.assertEqual(set(analyzer.template.keys()), {"knight"})

    def test_missing_number_template_dir_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            ClashStoreAnalyzer(
                template_dir=self.template_dir,
                config_path=self.config_file.name,
                number_template_dir="/pfad/existiert/nicht",
            )


if __name__ == "__main__":
    unittest.main()
