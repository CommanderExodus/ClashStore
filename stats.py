"""Modul für Aggregationen und Auswertungen über gespeicherte Shop-Angebote."""

import csv
from typing import TypedDict

from database import StoredOffer

_RARITY_ORDER = ["legendary", "epic", "rare", "common"]
_RARITY_RANK = {rarity: rank for rank, rarity in enumerate(_RARITY_ORDER)}


class RaritySummary(TypedDict):
    """Aggregierte Werte für eine Seltenheitsstufe."""

    rarity: str
    count: int
    gold: int


class CardSummary(TypedDict):
    """Aggregierte Werte für eine einzelne Karte über die gesamte Historie."""

    card_name: str
    rarity: str
    count: int
    gold: int


def summarize_by_rarity(offers: list[StoredOffer]) -> list[RaritySummary]:
    """Summiert Anzahl und Gold je Seltenheitsstufe.

    Läuft über alle Angebote unabhängig von "free" (bei kostenlosen Angeboten
    ist calculated_price ohnehin 0). Die vier bekannten Seltenheiten erscheinen
    immer, auch mit count=0/gold=0, falls sie noch nie vorkamen – damit z.B.
    das Legendary-Panel in der GUI nie fehlt.

    Args:
        offers: Die auszuwertenden, gespeicherten Angebote.

    Returns:
        Eine Zeile je Seltenheit, feste Reihenfolge zuerst (legendary,
        epic, rare, common), unbekannte Seltenheiten danach.

    Examples:
        >>> offers: list[StoredOffer] = [{
        ...     "scanned_at": "t", "source_image": "s", "card_name": "knight",
        ...     "count": 80, "calculated_price": 800, "rarity": "common",
        ...     "free": False,
        ... }]
        >>> summarize_by_rarity(offers)[-1]
        {'rarity': 'common', 'count': 80, 'gold': 800}
    """
    totals: dict[str, RaritySummary] = {}
    for rarity in _RARITY_ORDER:
        totals[rarity] = {"rarity": rarity, "count": 0, "gold": 0}

    for offer in offers:
        rarity = offer["rarity"]
        if rarity not in totals:
            totals[rarity] = {"rarity": rarity, "count": 0, "gold": 0}
        totals[rarity]["count"] += offer["count"]
        totals[rarity]["gold"] += offer["calculated_price"]

    unknown = [r for r in totals if r not in _RARITY_ORDER]
    return [totals[r] for r in _RARITY_ORDER] + [totals[r] for r in unknown]


def summarize_by_card(offers: list[StoredOffer]) -> list[CardSummary]:
    """Summiert Anzahl und Gold je Karte über die gesamte Historie.

    Args:
        offers: Die auszuwertenden, gespeicherten Angebote.

    Returns:
        Eine Zeile je Karte, die mindestens einmal vorkam, alphabetisch
        nach card_name sortiert.

    Examples:
        >>> offers: list[StoredOffer] = [
        ...     {"scanned_at": "t1", "source_image": "s", "card_name": "knight",
        ...      "count": 80, "calculated_price": 800, "rarity": "common",
        ...      "free": False},
        ...     {"scanned_at": "t2", "source_image": "s", "card_name": "knight",
        ...      "count": 5, "calculated_price": 0, "rarity": "common",
        ...      "free": True},
        ... ]
        >>> summarize_by_card(offers)
        [{'card_name': 'knight', 'rarity': 'common', 'count': 85, 'gold': 800}]
    """
    totals: dict[str, CardSummary] = {}
    for offer in offers:
        name = offer["card_name"]
        if name not in totals:
            totals[name] = {
                "card_name": name,
                "rarity": offer["rarity"],
                "count": 0,
                "gold": 0,
            }
        totals[name]["count"] += offer["count"]
        totals[name]["gold"] += offer["calculated_price"]

    return [totals[name] for name in sorted(totals)]


def filter_card_summaries(
    summaries: list[CardSummary], query: str
) -> list[CardSummary]:
    """Filtert Karten-Zusammenfassungen nach einem Namens-Suchbegriff.

    Args:
        summaries: Die zu filternden Zusammenfassungen.
        query: Suchbegriff, case-insensitive als Teilstring gegen
            card_name geprüft. Ein leerer String liefert alle Zeilen.

    Returns:
        Die Teilmenge von summaries, deren card_name query enthält.

    Examples:
        >>> summaries: list[CardSummary] = [
        ...     {"card_name": "knight", "rarity": "common", "count": 80, "gold": 800},
        ...     {"card_name": "pekka", "rarity": "epic", "count": 5, "gold": 1000},
        ... ]
        >>> [s["card_name"] for s in filter_card_summaries(summaries, "KNI")]
        ['knight']
    """
    needle = query.lower()
    return [s for s in summaries if needle in s["card_name"].lower()]


def total_gold_spent(offers: list[StoredOffer]) -> int:
    """Summiert calculated_price über alle Angebote.

    Args:
        offers: Die auszuwertenden, gespeicherten Angebote.

    Returns:
        Die Summe aller calculated_price-Werte.

    Examples:
        >>> offers: list[StoredOffer] = [{
        ...     "scanned_at": "t", "source_image": "s", "card_name": "knight",
        ...     "count": 80, "calculated_price": 800, "rarity": "common",
        ...     "free": False,
        ... }]
        >>> total_gold_spent(offers)
        800
    """
    return sum(offer["calculated_price"] for offer in offers)


def collected_ratio(offers: list[StoredOffer]) -> tuple[int, int]:
    """Zählt, wie viele Angebote als free/collected markiert waren.

    Args:
        offers: Die auszuwertenden, gespeicherten Angebote.

    Returns:
        Tupel (Anzahl mit free=True, Gesamtanzahl).

    Examples:
        >>> offers: list[StoredOffer] = [
        ...     {"scanned_at": "t", "source_image": "s", "card_name": "knight",
        ...      "count": 80, "calculated_price": 800, "rarity": "common",
        ...      "free": False},
        ...     {"scanned_at": "t", "source_image": "s", "card_name": "zappies",
        ...      "count": 25, "calculated_price": 0, "rarity": "rare",
        ...      "free": True},
        ... ]
        >>> collected_ratio(offers)
        (1, 2)
    """
    collected = sum(1 for offer in offers if offer["free"])
    return collected, len(offers)


def export_to_csv(offers: list[StoredOffer], path: str) -> None:
    """Schreibt die Angebots-Historie als CSV-Datei.

    Args:
        offers: Die zu exportierenden, gespeicherten Angebote.
        path: Zielpfad der CSV-Datei.

    Examples:
        >>> import os
        >>> import tempfile
        >>> offers: list[StoredOffer] = [{
        ...     "scanned_at": "t", "source_image": "s", "card_name": "knight",
        ...     "count": 80, "calculated_price": 800, "rarity": "common",
        ...     "free": False,
        ... }]
        >>> tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        >>> tmp.close()
        >>> export_to_csv(offers, tmp.name)
        >>> with open(tmp.name) as f:
        ...     "knight" in f.read()
        True
        >>> os.unlink(tmp.name)
    """
    assert path, "path darf nicht leer sein"

    fieldnames = [
        "scanned_at",
        "source_image",
        "card_name",
        "count",
        "calculated_price",
        "rarity",
        "free",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(offers)


def column_sort_key(column: str, value: str) -> tuple[int, float | str]:
    """Berechnet den Sortier-Schlüssel für einen Tabellenzellwert.

    Die Seltenheits-Spalte sortiert nach Rang statt alphabetisch.
    Numerische Werte werden numerisch sortiert, alles andere als Text
    (case-insensitive). Unbekannte Seltenheiten landen hinter allen bekannten.

    Args:
        column: Name der Spalte, aus der value stammt.
        value: Roher Zellwert als Text (z.B. aus ttk.Treeview.set()).

    Returns:
        Ein mit sorted() vergleichbares Tupel; numerische und Rang-Werte
        (erste Position 0) kommen vor Text-Werten (erste Position 1).

    Examples:
        >>> column_sort_key("rarity", "epic")
        (0, 1.0)
        >>> column_sort_key("count", "80")
        (0, 80.0)
        >>> column_sort_key("card_name", "Knight")
        (1, 'knight')
    """
    if column == "rarity":
        return (0, float(_RARITY_RANK.get(value, len(_RARITY_RANK))))
    try:
        return (0, float(value))
    except ValueError:
        return (1, value.lower())
