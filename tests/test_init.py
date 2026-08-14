"""Tests für ClashStoreAnalyzer.__init__."""

import json
import os
import tempfile
import unittest

from analyzer import ClashStoreAnalyzer


class TestInit(unittest.TestCase):
    """Tests für ClashStoreAnalyzer.__init__."""

    def test_missing_template_dir_raises(self) -> None:
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

    def test_missing_config_raises(self) -> None:
        template_dir = tempfile.mkdtemp()
        try:
            with self.assertRaises(FileNotFoundError):
                ClashStoreAnalyzer(
                    template_dir=template_dir,
                    config_path="/pfad/existiert/nicht.json",
                )
        finally:
            os.rmdir(template_dir)


if __name__ == "__main__":
    unittest.main()
