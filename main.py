"""Modul zur Erkennung von Shop-Kacheln in Clash Royale mittels OpenCV."""

import json
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import NamedTuple, TypedDict, TypeVar

import cv2
import numpy as np

_K = TypeVar("_K")


class ShopOffer(TypedDict):
    """Ein einzelnes erkanntes Angebot aus dem Shop-Screenshot."""

    card_name: str
    count: int
    calculated_price: int
    rarity: str
    free: bool


class Region(NamedTuple):
    """Ein rechteckiger Suchbereich relativ zu einer Kartenposition."""

    y0: int
    y1: int
    x0: int
    x1: int


def _load_gray_templates(
    directory: str, key_for_filename: Callable[[str], _K | None]
) -> dict[_K, np.ndarray]:
    """Lädt alle .png-Dateien eines Ordners als Graustufen-Templates.

    Gemeinsame Ladelogik für Karten-, Mengen- und Status-Templates, die
    sich nur darin unterscheiden, wie aus einem Dateinamen der Dict-
    Schlüssel abgeleitet wird.

    Args:
        directory: Ordner mit den Template-Bildern (muss existieren).
        key_for_filename: Wandelt einen Dateinamen (inkl. ".png") in den
            Dict-Schlüssel um, oder gibt None zurück, um die Datei zu
            überspringen (z.B. falsches Namensschema).

    Returns:
        Dict von abgeleitetem Schlüssel auf Graustufen-Bild.
    """
    templates: dict[_K, np.ndarray] = {}
    for filename in os.listdir(directory):
        if not filename.endswith(".png"):
            continue
        key = key_for_filename(filename)
        if key is None:
            continue
        filepath = os.path.join(directory, filename)
        img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            templates[key] = img
    return templates


def _number_template_key(filename: str) -> int | None:
    """Leitet die Store-Menge aus einem Mengen-Template-Dateinamen ab.

    Args:
        filename: Dateiname inkl. ".png", z.B. "x80.png".

    Returns:
        Die Menge als int (z.B. 80), oder None, wenn der Dateiname nicht
        dem Schema "x<Zahl>.png" entspricht (z.B. "collected.png").
    """
    if not filename.startswith("x"):
        return None
    value_str = filename[1:-4]  # "x80.png" -> "80" (führendes "x", ".png"-Endung ab).
    return int(value_str) if value_str.isdigit() else None


def _score_template(zone_gray: np.ndarray, template: np.ndarray) -> float | None:
    """Matcht ein Template gegen einen Suchbereich per Kreuzkorrelation.

    Gemeinsame Matching-Logik für match_count() und is_free(), die sich
    nur darin unterscheiden, WELCHE Templates sie durchprobieren und wie
    sie die beste Konfidenz auswählen.

    Args:
        zone_gray: Graustufen-Suchbereich.
        template: Graustufen-Template, das gesucht wird.

    Returns:
        Die Konfidenz (TM_CCOEFF_NORMED, bis 1.0), oder None, wenn das
        Template größer als der Suchbereich ist und daher nicht hineinpasst.
    """
    if template.shape[0] > zone_gray.shape[0] or template.shape[1] > zone_gray.shape[1]:
        return None
    res = cv2.matchTemplate(zone_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return float(max_val)


def _match_card(
    img_gray: np.ndarray, template: np.ndarray
) -> tuple[float, tuple[int, int]]:
    """Matcht ein einzelnes Karten-Template gegen das gesamte Bild.

    Reine Funktion ohne Seiteneffekte (liest nur img_gray/template) -
    wird in analyze_screenshots parallel für alle Karten-Templates
    aufgerufen, da das Matching gegen das volle Bild der mit Abstand
    teuerste Teil der Analyse ist (siehe Profiling: ~99% der Laufzeit).

    Args:
        img_gray: Graustufen-Screenshot in voller Größe.
        template: Graustufen-Template einer Karte.

    Returns:
        Tupel (beste Konfidenz, (x, y)-Position des besten Treffers).
    """
    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    x, y = max_loc
    return float(max_val), (x, y)


def _slice_gray(img_color: np.ndarray, x: int, y: int, region: Region) -> np.ndarray:
    """Schneidet einen Suchbereich relativ zu (x, y) aus und macht ihn grau.

    Args:
        img_color: Das normierte Farbbild (siehe ClashStoreAnalyzer.preprocess).
        x: X-Offset der Kartenposition im Bild.
        y: Y-Offset der Kartenposition im Bild.
        region: Der Suchbereich relativ zu (x, y).

    Returns:
        Der zugeschnittene Bereich in Graustufen.
    """
    zone = img_color[y + region.y0 : y + region.y1, x + region.x0 : x + region.x1]
    return cv2.cvtColor(zone, cv2.COLOR_BGR2GRAY)


def _compute_price(unit_price: int, count: int) -> int:
    """Berechnet den Gesamtpreis aus Einzelpreis und Anzahl.

    Design by Contract: unit_price und count sind laut Vertrag nie negativ
    (Aufrufer-Pflicht) und das Ergebnis ist es entsprechend auch nie
    (Garantie dieser Funktion) — beides wird per assert erzwungen, da eine
    Verletzung ein Programmierfehler wäre, kein normaler Nutzerfehler.

    Args:
        unit_price: Preis pro Karte in Gold (>= 0).
        count: Anzahl der Karten (>= 0).

    Returns:
        Den berechneten Gesamtpreis in Gold.

    Examples:
        >>> _compute_price(10, 80)
        800
        >>> _compute_price(50, 0)
        0
        >>> _compute_price(200, 5)
        1000
    """
    assert unit_price >= 0, f"unit_price darf nicht negativ sein: {unit_price}"
    assert count >= 0, f"count darf nicht negativ sein: {count}"
    result = unit_price * count
    assert result >= 0, f"Ergebnis darf nicht negativ sein: {result}"
    return result


def _known_free_count(rarity: str) -> int | None:
    """Liefert die bekannte, feste Menge für kostenlose Angebote einer Seltenheit.

    Bei Collected!/FREE!-Angeboten zeigt der Screenshot keine Ziffer mehr
    an (das Banner ersetzt den Mengen-Text an dieser Stelle) - match_count()
    findet dort also nie eine echte Ziffer. Für Epic-Karten ist die Menge
    beim sonntäglichen Gratis-Angebot aber eine feste, aus dem Spiel
    bekannte Regel (immer 5 Karten) und lässt sich daher ohne Bilderkennung
    direkt einsetzen, statt fälschlich bei 0 zu bleiben.

    Args:
        rarity: Die Seltenheit der Karte.

    Returns:
        Die bekannte feste Menge, oder None, wenn für diese Seltenheit
        keine feste Gratis-Menge bekannt ist.

    Examples:
        >>> _known_free_count("epic")
        5
        >>> _known_free_count("common") is None
        True
    """
    if rarity == "epic":
        return 5
    return None


class ClashStoreAnalyzer:
    """Analysiert Shop-Screenshots, um Langfristige Analysen zu machen.

    Attributes:
        template: Graustufen-Bild eines Templates einer Karte.
        number_templates: Graustufen-Template je bekannter Store-Menge
            (z.B. 80 -> Template von "x80"), fürs Erkennen der Anzahl.
        status_templates: Graustufen-Template je Status-Banner
            ("collected" -> "Collected!", "free" -> "FREE!"), zeigt an,
            dass die Karte nichts gekostet hat.
        target_width: Die Standartbreite, auf die alle Bilder skaliert werden.
    """

    # Konfidenz-Schwelle fürs Erkennen, DASS eine Karte überhaupt im Bild
    # ist. Höher als die beiden Schwellen unten, da Kartenkunst deutlich
    # markanter/eindeutiger ist als die kleinen Zahlen-/Status-Banner.
    _CARD_MATCH_THRESHOLD = 0.8

    # Suchbereich unterhalb der Karte, in dem die Mengen-Templates gesucht
    # werden (relativ zur oberen linken Ecke des Karten-Treffers).
    _COUNT_SEARCH = Region(y0=170, y1=270, x0=0, x1=260)
    # War 0.85; empirisch gegen alle 181 Test-Screenshots geprüft (siehe
    # Projektbericht/Commit-Historie): mit der Ziffernanzahl-Gruppierung
    # (statt Pixel-Breite) behebt 0.8 12 zuvor unerkannte Mengen (45 -> 33
    # von 984 Erkennungen bleiben 0), ohne eine einzige neue Fehlerkennung
    # zu verursachen.
    _COUNT_MATCH_THRESHOLD = 0.8

    # Suchbereich für die Status-Banner (Collected!/FREE!), die weiter
    # unten auf der Kachel sitzen, an der Stelle des Goldpreises.
    _STATUS_SEARCH = Region(y0=170, y1=500, x0=0, x1=330)
    # Deutlich niedriger als _COUNT_MATCH_THRESHOLD: hier geht es nur um
    # "Banner da oder nicht", nicht um die Unterscheidung ähnlicher
    # Templates. Normale (bezahlte) Karten scoren konstant ~0.28, ein
    # echtes "Collected!"-Banner ~0.41 -> 0.35 trennt beide sauber.
    _STATUS_MATCH_THRESHOLD = 0.35

    def __init__(
        self,
        template_dir: str,
        target_width: int = 1080,
        config_path: str = "cards.json",
        number_template_dir: str = "templates/numbers",
    ):
        """Initialisiert den Analyzer mit einem Template.

        Args:
            template_dir: Directionary mit den Templates.
            target_width: Breite für die Normalisierung (Standart: 1080px).
            config_path: Seltenheit aller Karten und Preise im Shop.
            number_template_dir: Directionary mit den Mengen-Templates
                (Dateiname "x<Menge>.png", z.B. "x80.png") sowie den
                Status-Templates "collected.png" und "free!.png".
        """
        self.target_width = target_width

        # analyze_screenshots matcht die Karten-Templates parallel über
        # mehrere Python-Threads (siehe dort). OpenCVs eigene interne
        # Parallelisierung (standardmäßig ein Thread je CPU-Kern) würde
        # sonst mit diesen Threads um dieselben Kerne konkurrieren -
        # daher hier auf einen internen Thread pro Aufruf begrenzt.
        cv2.setNumThreads(1)

        with open(config_path, "r") as f:
            data = json.load(f)
            self.prices = data["prices"]
            self.rarities = data["rarities"]

        # 1. Karten-Templates laden: jede .png zählt, Schlüssel = Dateiname
        # ohne Endung (z.B. "knight.png" -> "knight").
        if not os.path.exists(template_dir):
            raise FileNotFoundError(f"Ordner nicht gefunden: {template_dir}")
        self.template = _load_gray_templates(
            template_dir, lambda filename: os.path.splitext(filename)[0]
        )
        print(f"{len(self.template)} Templates in RAM geladen.")

        # 2. Mengen-Templates laden (Dateiname "x<Menge>.png", z.B. "x80.png").
        if not os.path.exists(number_template_dir):
            raise FileNotFoundError(f"Ordner nicht gefunden: {number_template_dir}")
        self.number_templates = _load_gray_templates(
            number_template_dir, _number_template_key
        )
        print(f"{len(self.number_templates)} Mengen-Templates in RAM geladen.")

        # 3. Status-Templates laden (Collected!/FREE!, zeigen "kostenlos" an)
        # — fest benannte Dateien im selben Ordner wie die Mengen-Templates.
        status_names = {"collected.png": "collected", "free!.png": "free"}
        self.status_templates = _load_gray_templates(
            number_template_dir, status_names.get
        )
        print(f"{len(self.status_templates)} Status-Templates in RAM geladen.")

    def preprocess(self, image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Bringt das Bild auf Standartgröße und Graustufen.

        Args:
            image: Das Originalbild

        Returns:
            Das resized Graustufenbild.

        Examples:
            >>> import numpy as np
            >>> analyzer = ClashStoreAnalyzer.__new__(ClashStoreAnalyzer)
            >>> analyzer.target_width = 1080
            >>> dummy = np.zeros((1920, 1600, 3), dtype=np.uint8)
            >>> gray, color = analyzer.preprocess(dummy)
            >>> color.shape[1]
            1080
        """
        assert image.ndim == 3 and image.shape[2] == 3, (
            "image muss ein BGR-Farbbild sein"
        )
        assert self.target_width > 0, (
            f"target_width muss positiv sein: {self.target_width}"
        )

        height, width = image.shape[:2]
        scale = self.target_width / float(width)
        resized = cv2.resize(
            image,
            (self.target_width, int(height * scale)),
            interpolation=cv2.INTER_AREA,
        )
        color_scaled = resized
        assert color_scaled.shape[1] == self.target_width, (
            "Ergebnisbreite muss target_width entsprechen"
        )
        return cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY), color_scaled

    def match_count(self, search_zone_gray: np.ndarray) -> int:
        """Ermittelt die Store-Menge per Template-Matching.

        Template matching der z.B. x80 gegen großes Suchfeld. Kürzere
        Mengen wie "x8" sind optisch ein Präfix von längeren wie "x80"
        und erreichen dort ebenfalls eine hohe Konfidenz. Deshalb werden
        die Templates nach Ziffernanzahl (nicht nach Pixel-Breite - beim
        manuellen Zuschneiden bekommen selbst gleich lange Zahlen wie
        "x20"/"x30" leicht unterschiedliche Breiten, was sie sonst in
        unterschiedliche Gruppen und damit in die falsche Prüfreihenfolge
        gebracht hätte) gruppiert und von der längsten zur kürzesten
        Gruppe durchprobiert: Sobald in einer Gruppe eine Menge die
        Schwelle erreicht, gewinnt die Menge mit der höchsten Konfidenz
        innerhalb dieser Gruppe — so gewinnt "x80" gegen "x8" und "x30"
        gegen das gleich lange "x50".

        Args:
            search_zone_gray: Graustufen-Suchbereich unterhalb der Karte.

        Returns:
            Die erkannte Menge, oder 0 wenn keine Menge sicher genug
            erkannt wurde.

        Examples:
            >>> import numpy as np
            >>> pattern = np.array([[0, 255], [255, 0]], dtype=np.uint8)
            >>> analyzer = ClashStoreAnalyzer.__new__(ClashStoreAnalyzer)
            >>> analyzer.number_templates = {5: pattern}
            >>> analyzer.match_count(pattern)
            5
        """
        assert search_zone_gray.size > 0, "search_zone_gray darf nicht leer sein"
        assert search_zone_gray.ndim == 2, "search_zone_gray muss Graustufen sein"

        digit_counts = sorted(
            {len(str(value)) for value in self.number_templates}, reverse=True
        )

        for digit_count in digit_counts:
            best_value = 0
            best_score = 0.0

            for value, template in self.number_templates.items():
                if len(str(value)) != digit_count:
                    continue

                score = _score_template(search_zone_gray, template)
                if score is None:
                    continue

                if score > best_score:
                    best_score = score
                    best_value = value

            if best_score >= self._COUNT_MATCH_THRESHOLD:
                return best_value

        return 0

    def is_free(self, status_search_gray: np.ndarray) -> bool:
        """Prüft, ob die Kachel als kostenlos markiert ist.

        Erkennt die Banner "Collected!" (bereits abgeholt/gekauft) und
        "FREE!" (Gratis-Angebot), die anstelle des Goldpreises stehen.

        Args:
            status_search_gray: Graustufen-Suchbereich an der Stelle des
                Goldpreises unterhalb der Karte.

        Returns:
            True, wenn eines der Status-Banner erkannt wurde.

        Examples:
            >>> import numpy as np
            >>> pattern = np.array([[0, 255], [255, 0]], dtype=np.uint8)
            >>> analyzer = ClashStoreAnalyzer.__new__(ClashStoreAnalyzer)
            >>> analyzer.status_templates = {"collected": pattern}
            >>> analyzer.is_free(pattern)
            True
        """
        assert status_search_gray.size > 0, "status_search_gray darf nicht leer sein"
        assert status_search_gray.ndim == 2, "status_search_gray muss Graustufen sein"

        for template in self.status_templates.values():
            score = _score_template(status_search_gray, template)
            if score is not None and score >= self._STATUS_MATCH_THRESHOLD:
                return True

        return False

    def calculate_price(self, card_name: str, count: int) -> int:
        """Berechnet den Preis der Karte anhand ihrer Anzahl und Seltenheit.

        Design by Contract: card_name darf nicht leer sein und count nicht
        negativ (Aufrufer-Pflicht, per assert erzwungen). Ist die Karte
        oder ihre Seltenheit unbekannt, ist das dagegen ein normaler,
        erwartbarer Fall (z.B. Tippfehler in cards.json) und wird über
        ValueError behandelt statt über assert.

        Args:
            card_name: Der Name der karte
            count: Die erkannte Anzahl (>= 0)

        Returns:
            Den berechneten Gold-Preis

        Examples:
            >>> analyzer = ClashStoreAnalyzer.__new__(ClashStoreAnalyzer)
            >>> analyzer.rarities = {"knight": "common"}
            >>> analyzer.prices = {"common": 10}
            >>> analyzer.calculate_price("knight", 80)
            800
        """
        assert card_name, "card_name darf nicht leer sein"
        assert count >= 0, f"count darf nicht negativ sein: {count}"

        rarity = self.rarities.get(card_name)
        if not rarity:
            raise ValueError(f"Karte nicht gefunden: {card_name}")

        unit_price = self.prices.get(rarity)
        if unit_price is None:
            raise ValueError(f"Preis für Seltenheit nicht gefunden: {rarity}")
        return _compute_price(unit_price, count)

    def analyze_screenshots(self, image_path: str) -> list[ShopOffer]:
        """Durchsucht das Bild nach allen bekannten Templates und liest die Werte.

        Das Matching der Karten-Templates gegen das volle Bild ist der
        teuerste Teil (siehe _match_card) und läuft daher über mehrere
        Threads parallel; alles danach (Mengen/Status/Preis je Treffer)
        ist billig genug, um sequentiell zu bleiben.

        Args:
            image_path: Pfad zum Screenshot

        Returns:
            Eine Liste von Dictionaries, ready für DB anbindung.
        """
        raw_img = cv2.imread(image_path)
        if raw_img is None:
            raise FileNotFoundError(f"Screenshot nicht gefunden: {image_path}")

        # preprocess gibt schon greyscaled und skaliertes Bild wieder
        img_gray, img_color_scaled = self.preprocess(raw_img)

        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = {
                card_name: executor.submit(_match_card, img_gray, template)
                for card_name, template in self.template.items()
            }
            card_matches = {name: future.result() for name, future in futures.items()}

        results: list[ShopOffer] = []

        # Überprüfe alle Templates auf dem Screenshot
        for card_name, (max_val, max_loc) in card_matches.items():
            if max_val >= self._CARD_MATCH_THRESHOLD:
                x, y = max_loc

                # Suchbereich für die Mengen-Templates unterhalb der Karte
                search_zone_gray = _slice_gray(
                    img_color_scaled, x, y, self._COUNT_SEARCH
                )
                count_val = self.match_count(search_zone_gray)

                # Suchbereich für Collected!/FREE! an Stelle des Goldpreises
                status_zone_gray = _slice_gray(
                    img_color_scaled, x, y, self._STATUS_SEARCH
                )
                free = self.is_free(status_zone_gray)

                # Collected!/FREE! ersetzt die Mengen-Ziffer im Screenshot,
                # match_count() findet dort also nie eine echte Zahl. Für
                # Seltenheiten mit bekannter fester Gratis-Menge (aktuell
                # nur Epic, siehe _known_free_count) wird die Menge daher
                # direkt eingesetzt statt fälschlich bei 0 zu bleiben.
                if free:
                    known_count = _known_free_count(self.rarities[card_name])
                    if known_count is not None:
                        count_val = known_count

                # Preis trotzdem berechnen (validiert Karte/Seltenheit auch
                # bei Free-Karten), aber Collected!/FREE! haben nichts
                # gekostet -> als Preis wird einheitlich 0 gespeichert.
                price = self.calculate_price(card_name, count_val)
                calculated_price = 0 if free else price

                # Ergebnise an result anhängen
                results.append(
                    {
                        "card_name": card_name,
                        "count": count_val,
                        "calculated_price": calculated_price,
                        "rarity": self.rarities[card_name],
                        "free": free,
                    }
                )
        return results


def main() -> None:
    try:
        analyzer = ClashStoreAnalyzer(template_dir="templates/cards")

        # Screenshots analysieren
        db_data = analyzer.analyze_screenshots("shop_pictures/3.jpeg")

        for row in db_data:
            print(
                f"Karte: {row['card_name'].upper():<10} | "
                f"Anzahl: {row['count']} | "
                f"Preis: {row['calculated_price']} Gold"
            )

    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")


if __name__ == "__main__":
    main()
