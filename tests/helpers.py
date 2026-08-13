"""Gemeinsame Hilfsfunktionen für die Testsuite."""

import json
import tempfile

import numpy as np

from main import ClashStoreAnalyzer


def _make_analyzer(
    extra_rarities: dict[str, str] | None = None,
    extra_prices: dict[str, int] | None = None,
) -> tuple[ClashStoreAnalyzer, str, str]:
    """Erstellt einen Analyzer mit temporären Testdateien.

    Args:
        extra_rarities: Zusätzliche Karten für self.rarities.
        extra_prices: Zusätzliche Preise für self.prices.

    Returns:
        Tupel aus (analyzer, template_dir, config_path).
    """
    rarities = {"knight": "common", "musketeer": "rare", "pekka": "epic"}
    prices = {"common": 10, "rare": 50, "epic": 200, "legendary": 15000}

    if extra_rarities:
        rarities.update(extra_rarities)
    if extra_prices:
        prices.update(extra_prices)

    template_dir = tempfile.mkdtemp()
    config_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
    json.dump({"prices": prices, "rarities": rarities}, config_file)
    config_file.close()

    analyzer = ClashStoreAnalyzer(
        template_dir=template_dir,
        config_path=config_file.name,
    )
    return analyzer, template_dir, config_file.name


def _embed(canvas: np.ndarray, patch: np.ndarray, row: int, col: int) -> np.ndarray:
    """Kopiert patch an Position (row, col) in eine Kopie von canvas.

    Args:
        canvas: Der Hintergrund, in den patch eingefügt wird.
        patch: Das einzufügende Muster.
        row: Zeilen-Offset.
        col: Spalten-Offset.

    Returns:
        Eine neue Canvas-Kopie mit eingefügtem Muster.
    """
    result = canvas.copy()
    h, w = patch.shape
    result[row : row + h, col : col + w] = patch
    return result


def _random_pattern(height: int, width: int, seed: int) -> np.ndarray:
    """Erzeugt ein reproduzierbares Zufallsmuster für Template-Tests.

    Args:
        height: Höhe des Musters.
        width: Breite des Musters.
        seed: Seed für den Zufallsgenerator.

    Returns:
        Ein Graustufen-Array mit Werten 0-255.
    """
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(height, width), dtype=np.uint8)
