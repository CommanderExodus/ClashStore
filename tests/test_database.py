"""Tests für das database-Modul (SQLite-Persistierung)."""

import os
import tempfile
import unittest

from database import fetch_all_offers, init_db, save_offers
from main import ShopOffer


class TestDatabase(unittest.TestCase):
    """Tests für init_db, save_offers und fetch_all_offers."""

    def setUp(self) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name

    def tearDown(self) -> None:
        os.unlink(self.db_path)

    def test_init_db_creates_table(self) -> None:
        init_db(self.db_path)
        self.assertEqual(fetch_all_offers(self.db_path), [])

    def test_save_offers_persists_data(self) -> None:
        offer: ShopOffer = {
            "card_name": "knight",
            "count": 80,
            "calculated_price": 800,
            "rarity": "common",
            "free": False,
        }
        save_offers(self.db_path, [offer], "shop.png")

        results = fetch_all_offers(self.db_path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["card_name"], "knight")
        self.assertEqual(results[0]["count"], 80)
        self.assertEqual(results[0]["calculated_price"], 800)
        self.assertEqual(results[0]["rarity"], "common")
        self.assertFalse(results[0]["free"])
        self.assertEqual(results[0]["source_image"], "shop.png")
        self.assertIsInstance(results[0]["scanned_at"], str)

    def test_free_flag_roundtrips_as_bool(self) -> None:
        offer: ShopOffer = {
            "card_name": "pekka",
            "count": 1,
            "calculated_price": 0,
            "rarity": "epic",
            "free": True,
        }
        save_offers(self.db_path, [offer], "shop.png")

        results = fetch_all_offers(self.db_path)
        self.assertIs(results[0]["free"], True)

    def test_empty_offers_list_is_a_noop(self) -> None:
        save_offers(self.db_path, [], "shop.png")
        self.assertEqual(fetch_all_offers(self.db_path), [])

    def test_multiple_runs_are_all_kept_not_overwritten(self) -> None:
        offer_a: ShopOffer = {
            "card_name": "knight",
            "count": 5,
            "calculated_price": 50,
            "rarity": "common",
            "free": False,
        }
        offer_b: ShopOffer = {
            "card_name": "knight",
            "count": 10,
            "calculated_price": 100,
            "rarity": "common",
            "free": False,
        }
        save_offers(self.db_path, [offer_a], "shop_run1.png")
        save_offers(self.db_path, [offer_b], "shop_run2.png")

        results = fetch_all_offers(self.db_path)
        self.assertEqual(len(results), 2)
        self.assertEqual([r["count"] for r in results], [5, 10])

    def test_fetch_all_offers_orders_chronologically(self) -> None:
        offer: ShopOffer = {
            "card_name": "musketeer",
            "count": 3,
            "calculated_price": 150,
            "rarity": "rare",
            "free": False,
        }
        save_offers(self.db_path, [offer], "run1.png")
        save_offers(self.db_path, [offer], "run2.png")

        results = fetch_all_offers(self.db_path)
        scanned_ats = [r["scanned_at"] for r in results]
        self.assertEqual(scanned_ats, sorted(scanned_ats))


if __name__ == "__main__":
    unittest.main()
