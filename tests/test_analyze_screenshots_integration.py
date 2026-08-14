"""Integrationstest: ClashStoreAnalyzer gegen echte Screenshots und Templates.

Nutzt die echten Assets aus templates/ und shop_pictures/ statt Synthetik,
um den kompletten Pfad (Karten-Matching, Mengen-Matching, Preisberechnung)
gegen reale Daten abzusichern - insbesondere die Regressionsfälle
"x8"/"x80"-Präfixverwechslung und den "x30"/"x50"-Gleichstand, die beide
mit synthetischen Templates allein nicht aufgefallen wären.
"""

import unittest

from analyzer import ClashStoreAnalyzer, ShopOffer

# (Screenshot, Kartenname, erwartete Menge) - manuell aus den Screenshots
# abgelesene Ground Truth, siehe Session-Verlauf.
GROUND_TRUTH = [
    ("shop_pictures/0clashtest.jpeg", "knight", 80),
    ("shop_pictures/0clashtest.jpeg", "golem", 5),
    ("shop_pictures/3.jpeg", "skeleton_barrel", 80),
    ("shop_pictures/173.jpg", "cannon", 80),
    ("shop_pictures/85.jpg", "earthquake", 30),
    ("shop_pictures/21.jpeg", "electro_giant", 8),
]


class TestAnalyzeScreenshotsIntegration(unittest.TestCase):
    """Integrationstest mit echten Templates und Screenshots."""

    analyzer: ClashStoreAnalyzer
    results_by_image: dict[str, list[ShopOffer]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.analyzer = ClashStoreAnalyzer(template_dir="templates/cards")
        cls.results_by_image = {}
        for image_path, _, _ in GROUND_TRUTH:
            if image_path not in cls.results_by_image:
                cls.results_by_image[image_path] = cls.analyzer.analyze_screenshots(
                    image_path
                )

    def test_known_cards_are_detected_with_correct_count(self) -> None:
        for image_path, card_name, expected_count in GROUND_TRUTH:
            with self.subTest(image=image_path, card=card_name):
                results = self.results_by_image[image_path]
                found = next((r for r in results if r["card_name"] == card_name), None)
                self.assertIsNotNone(
                    found, f"{card_name} nicht in {image_path} erkannt"
                )
                assert found is not None  # für mypy, s.o. bereits per assert geprüft
                self.assertEqual(found["count"], expected_count)

    def test_detected_cards_have_valid_rarity_and_price(self) -> None:
        for results in self.results_by_image.values():
            for result in results:
                self.assertIn(result["rarity"], self.analyzer.prices)
                self.assertGreaterEqual(result["calculated_price"], 0)


if __name__ == "__main__":
    unittest.main()
