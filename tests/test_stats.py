"""Tests für das stats-Modul (Aggregationen über Shop-Angebote)."""

import os
import tempfile
import unittest

from database import StoredOffer
from stats import (
    collected_ratio,
    export_to_csv,
    filter_card_summaries,
    summarize_by_card,
    summarize_by_rarity,
    total_gold_spent,
)


def _offer(
    card_name: str,
    rarity: str,
    count: int,
    calculated_price: int,
    free: bool = False,
    scanned_at: str = "2026-01-01T00:00:00+00:00",
    source_image: str = "shop.png",
) -> StoredOffer:
    """Baut ein StoredOffer-Dict mit sinnvollen Defaults für Tests."""
    return {
        "scanned_at": scanned_at,
        "source_image": source_image,
        "card_name": card_name,
        "count": count,
        "calculated_price": calculated_price,
        "rarity": rarity,
        "free": free,
    }


class TestSummarizeByRarity(unittest.TestCase):
    """Tests für summarize_by_rarity."""

    def test_sums_count_and_gold_per_rarity(self) -> None:
        offers = [
            _offer("knight", "common", 80, 800),
            _offer("archers", "common", 20, 200),
            _offer("pekka", "epic", 5, 1000),
        ]
        result = {r["rarity"]: r for r in summarize_by_rarity(offers)}

        self.assertEqual(
            result["common"], {"rarity": "common", "count": 100, "gold": 1000}
        )
        self.assertEqual(result["epic"], {"rarity": "epic", "count": 5, "gold": 1000})

    def test_includes_zero_for_unseen_rarities(self) -> None:
        offers = [_offer("knight", "common", 80, 800)]
        result = {r["rarity"]: r for r in summarize_by_rarity(offers)}

        self.assertEqual(
            result["legendary"], {"rarity": "legendary", "count": 0, "gold": 0}
        )

    def test_fixed_display_order(self) -> None:
        offers = [_offer("knight", "common", 1, 10)]
        result = summarize_by_rarity(offers)

        self.assertEqual(
            [r["rarity"] for r in result], ["legendary", "epic", "rare", "common"]
        )

    def test_free_offers_still_count_towards_count(self) -> None:
        offers = [_offer("zappies", "rare", 25, 0, free=True)]
        result = {r["rarity"]: r for r in summarize_by_rarity(offers)}

        self.assertEqual(result["rare"]["count"], 25)
        self.assertEqual(result["rare"]["gold"], 0)

    def test_unknown_rarity_is_appended_without_crashing(self) -> None:
        offers = [_offer("mystery", "champion", 1, 999)]
        result = summarize_by_rarity(offers)

        self.assertEqual(result[-1], {"rarity": "champion", "count": 1, "gold": 999})


class TestSummarizeByCard(unittest.TestCase):
    """Tests für summarize_by_card."""

    def test_sums_across_multiple_scans_of_same_card(self) -> None:
        offers = [
            _offer("knight", "common", 80, 800, scanned_at="t1"),
            _offer("knight", "common", 5, 0, free=True, scanned_at="t2"),
        ]
        result = summarize_by_card(offers)

        self.assertEqual(
            result,
            [{"card_name": "knight", "rarity": "common", "count": 85, "gold": 800}],
        )

    def test_sorted_alphabetically(self) -> None:
        offers = [
            _offer("pekka", "epic", 5, 1000),
            _offer("archers", "common", 20, 200),
        ]
        result = summarize_by_card(offers)

        self.assertEqual([c["card_name"] for c in result], ["archers", "pekka"])

    def test_empty_history_returns_empty_list(self) -> None:
        self.assertEqual(summarize_by_card([]), [])


class TestFilterCardSummaries(unittest.TestCase):
    """Tests für filter_card_summaries."""

    def setUp(self) -> None:
        self.summaries = summarize_by_card(
            [_offer("Knight", "common", 80, 800), _offer("Pekka", "epic", 5, 1000)]
        )

    def test_matches_substring_case_insensitive(self) -> None:
        result = filter_card_summaries(self.summaries, "KNI")
        self.assertEqual([s["card_name"] for s in result], ["Knight"])

    def test_empty_query_returns_all(self) -> None:
        result = filter_card_summaries(self.summaries, "")
        self.assertEqual(len(result), 2)

    def test_no_match_returns_empty(self) -> None:
        result = filter_card_summaries(self.summaries, "golem")
        self.assertEqual(result, [])


class TestTotalGoldSpent(unittest.TestCase):
    """Tests für total_gold_spent."""

    def test_sums_calculated_price(self) -> None:
        offers = [_offer("knight", "common", 80, 800), _offer("pekka", "epic", 5, 1000)]
        self.assertEqual(total_gold_spent(offers), 1800)

    def test_empty_list_is_zero(self) -> None:
        self.assertEqual(total_gold_spent([]), 0)

    def test_free_offers_contribute_zero(self) -> None:
        offers = [_offer("zappies", "rare", 25, 0, free=True)]
        self.assertEqual(total_gold_spent(offers), 0)


class TestCollectedRatio(unittest.TestCase):
    """Tests für collected_ratio."""

    def test_counts_free_offers_against_total(self) -> None:
        offers = [
            _offer("knight", "common", 80, 800),
            _offer("zappies", "rare", 25, 0, free=True),
        ]
        self.assertEqual(collected_ratio(offers), (1, 2))

    def test_empty_list_is_zero_of_zero(self) -> None:
        self.assertEqual(collected_ratio([]), (0, 0))


class TestExportToCsv(unittest.TestCase):
    """Tests für export_to_csv."""

    def setUp(self) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        tmp.close()
        self.csv_path = tmp.name

    def tearDown(self) -> None:
        os.unlink(self.csv_path)

    def test_writes_header_and_rows(self) -> None:
        offers = [_offer("knight", "common", 80, 800)]
        export_to_csv(offers, self.csv_path)

        with open(self.csv_path, newline="", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("card_name", content)
        self.assertIn("knight", content)
        self.assertIn("800", content)

    def test_empty_offers_writes_only_header(self) -> None:
        export_to_csv([], self.csv_path)

        with open(self.csv_path, newline="", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 1)


if __name__ == "__main__":
    unittest.main()
