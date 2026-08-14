"""Modul zur SQLite-Persistierung von Shop-Analyse-Ergebnissen."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime

from analyzer import ShopOffer


class StoredOffer(ShopOffer):
    """Ein aus der Datenbank gelesenes Angebot inklusive Verlaufs-Metadaten."""

    scanned_at: str
    source_image: str


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Legt die Tabelle shop_offers an, falls noch nicht existent.

    Args:
        conn: Offene SQLite-Verbindung.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shop_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scanned_at TEXT NOT NULL,
            source_image TEXT NOT NULL,
            card_name TEXT NOT NULL,
            count INTEGER NOT NULL,
            calculated_price INTEGER NOT NULL,
            rarity TEXT NOT NULL,
            free INTEGER NOT NULL
        )
        """
    )


def _row_to_offer(row: tuple[str, str, str, int, int, str, int]) -> StoredOffer:
    """Verwandelt eine SQLite-Ergebniszeile in ein StoredOffer-Dict.

    Args:
        row: Tupel (scanned_at, source_image, card_name, count, calculated_price,
        rarity, free) wie von fetch_all_offers bestimmt.

    Returns:
        Das entsprechende StoredOffer-Dict, free als bool statt 0/1.
    """
    scanned_at, source_image, card_name, count, calculated_price, rarity, free = row
    return {
        "scanned_at": scanned_at,
        "source_image": source_image,
        "card_name": card_name,
        "count": count,
        "calculated_price": calculated_price,
        "rarity": rarity,
        "free": bool(free),
    }


def init_db(db_path: str) -> None:
    """Legt die SQLite-Datenbank und ihre Tabelle an, falls nötig.

    Args:
        db_path: Pfad zur SQLite-Datenbankdatei (wird bei Bedarf erstellt).

    Examples:
        >>> import os
        >>> import tempfile
        >>> tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        >>> tmp.close()
        >>> init_db(tmp.name)
        >>> os.path.exists(tmp.name)
        True
        >>> os.unlink(tmp.name)
    """
    assert db_path, "db_path darf nicht leer sein"

    with closing(sqlite3.connect(db_path)) as conn, conn:
        _ensure_schema(conn)


def save_offers(db_path: str, offers: list[ShopOffer], source_image: str) -> None:
    """Speichert Angebote als neuen, zeitgestempelten Analyse-Lauf.

    Alle Angebote eines Aufrufs teilen sich denselben Zeitstempel. Frühere
    Zeilen bleiben unverändert erhalten, sodass die Tabelle den vollen
    Verlauf aller bisherigen Analyse-Läufe abbildet statt nur den letzten
    Stand.

    Args:
        db_path: Pfad zur SQLite-Datenbankdatei.
        offers: Die von analyze_screenshots() erkannten Angebote.
        source_image: Pfad des analysierten Screenshots.

    Examples:
        >>> import os
        >>> import tempfile
        >>> tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        >>> tmp.close()
        >>> offer: ShopOffer = {
        ...     "card_name": "knight",
        ...     "count": 80,
        ...     "calculated_price": 800,
        ...     "rarity": "common",
        ...     "free": False,
        ... }
        >>> save_offers(tmp.name, [offer], "shop.png")
        >>> len(fetch_all_offers(tmp.name))
        1
        >>> os.unlink(tmp.name)
    """
    assert db_path, "db_path darf nicht leer sein"
    assert source_image, "source_image darf nicht leer sein"

    if not offers:
        return

    scanned_at = datetime.now(UTC).isoformat()
    with closing(sqlite3.connect(db_path)) as conn, conn:
        _ensure_schema(conn)
        conn.executemany(
            """
            INSERT INTO shop_offers
                (scanned_at, source_image, card_name, count,
                 calculated_price, rarity, free)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    scanned_at,
                    source_image,
                    offer["card_name"],
                    offer["count"],
                    offer["calculated_price"],
                    offer["rarity"],
                    int(offer["free"]),
                )
                for offer in offers
            ],
        )


def fetch_all_offers(db_path: str) -> list[StoredOffer]:
    """Liest alle gespeicherten Angebote zurück, älteste zuerst.

    Args:
        db_path: Pfad zur SQLite-Datenbankdatei.

    Returns:
        Alle gespeicherten Angebote inkl. Zeitstempel und Quellbild,
        sortiert nach scanned_at (bei Gleichstand nach Einfügereihenfolge).

    Examples:
        >>> import os
        >>> import tempfile
        >>> tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        >>> tmp.close()
        >>> init_db(tmp.name)
        >>> fetch_all_offers(tmp.name)
        []
        >>> os.unlink(tmp.name)
    """
    assert db_path, "db_path darf nicht leer sein"

    with closing(sqlite3.connect(db_path)) as conn, conn:
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT scanned_at, source_image, card_name, count,
                   calculated_price, rarity, free
            FROM shop_offers
            ORDER BY scanned_at, id
            """
        ).fetchall()

    return [_row_to_offer(row) for row in rows]
