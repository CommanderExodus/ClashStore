"""Modul zur Erkennung von Shop-Kacheln in Clash Royale mittels OpenCV."""

import json
import os

import cv2
import numpy as np


def _compute_price(unit_price: int, count: int) -> int:
    """Berechnet den Gesamtpreis aus Einzelpreis und Anzahl.

    Args:
        unit_price: Preis pro Karte in Gold.
        count: Anzahl der Karten.

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
    return unit_price * count


class ClashStoreAnalyzer:
    """Analysiert Shop-Screenshots, um Langfristige Analysen zu machen.

    Attributes:
        template: Graustufen-Bild eines Templates einer Karte.
        number_templates: Graustufen-Template je bekannter Store-Menge
            (z.B. 80 -> Template von "x80"), fürs Erkennen der Anzahl.
        target_width: Die Standartbreite, auf die alle Bilder skaliert werden.
    """

    # Suchbereich unterhalb der Karte, in dem die Mengen-Templates gesucht
    # werden (relativ zur oberen linken Ecke des Karten-Treffers).
    _COUNT_SEARCH_Y = (170, 270)
    _COUNT_SEARCH_X = (0, 260)
    _COUNT_MATCH_THRESHOLD = 0.85

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
                (Dateiname "x<Menge>.png", z.B. "x80.png").
        """
        self.target_width = target_width
        self.template = {}
        self.number_templates = {}

        with open(config_path, "r") as f:
            data = json.load(f)
            self.prices = data["prices"]
            self.rarities = data["rarities"]

        # 1. Templates aus dem Ordner laden
        if not os.path.exists(template_dir):
            raise FileNotFoundError(f"Ordner nicht gefunden: {template_dir}")

        for filename in os.listdir(template_dir):
            if filename.endswith(".png"):
                card_name = os.path.splitext(filename)[0]
                filepath = os.path.join(template_dir, filename)

                # Bild greyscalen
                img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    self.template[card_name] = img

        print(f"{len(self.template)} Templates in RAM geladen.")

        # 2. Mengen-Templates laden (Dateiname "x<Menge>.png")
        if not os.path.exists(number_template_dir):
            raise FileNotFoundError(f"Ordner nicht gefunden: {number_template_dir}")

        for filename in os.listdir(number_template_dir):
            if filename.startswith("x") and filename.endswith(".png"):
                value_str = filename[1:-4]
                if not value_str.isdigit():
                    continue
                filepath = os.path.join(number_template_dir, filename)
                img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    self.number_templates[int(value_str)] = img

        print(f"{len(self.number_templates)} Mengen-Templates in RAM geladen.")

    def preprocess(self, image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Bringt das Bild auf Standartgröße und Graustufen.

        Args:
            image: Das Originalbild

        Returns:
            Das resized Graustufenbild.
        """
        height, width = image.shape[:2]
        scale = self.target_width / float(width)
        resized = cv2.resize(
            image,
            (self.target_width, int(height * scale)),
            interpolation=cv2.INTER_AREA,
        )
        return cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY), resized

    def match_count(self, search_zone_gray: np.ndarray) -> int:
        """Ermittelt die Store-Menge per Template-Matching.

        Template matching der z.B. x80 gegen großes Suchfeld, die höchste konfidenz gewinnt

        Args:
            search_zone_gray: Graustufen-Suchbereich unterhalb der Karte.

        Returns:
            Die erkannte Menge, oder 0 wenn keine Menge sicher genug
            erkannt wurde.
        """
        best_value = 0
        best_score = 0.0

        for value, template in self.number_templates.items():
            if (
                template.shape[0] > search_zone_gray.shape[0]
                or template.shape[1] > search_zone_gray.shape[1]
            ):
                continue

            res = cv2.matchTemplate(search_zone_gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)

            if max_val > best_score:
                best_score = max_val
                best_value = value

        if best_score >= self._COUNT_MATCH_THRESHOLD:
            return best_value
        return 0

    def calculate_price(self, card_name: str, count: int) -> int:
        """Berechnet den Preis der Karte anhand ihrer Anzahl und Seltenheit.

        Args:
            card_name: Der Name der karte
            count: Die erkannte Anzahl

        Returns:
            Den berechneten Gold-Preis
        """
        rarity = self.rarities.get(card_name)
        if not rarity:
            raise ValueError(f"Karte nicht gefunden: {card_name}")

        unit_price = self.prices.get(rarity)
        if unit_price is None:
            raise ValueError(f"Preis für Seltenheit nicht gefunden: {rarity}")
        return _compute_price(unit_price, count)

    def analyze_screenshots(self, image_path: str) -> list[dict]:
        """Durchsucht das Bild nach allen bekannten Templates und liest die Werte.

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

        results = []

        # Überprüfe alle Templates auf dem Screenshot
        for card_name, template in self.template.items():
            res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if max_val >= 0.8:
                x, y = max_loc

                # Suchbereich für die Mengen-Templates unterhalb der Karte
                sy0, sy1 = self._COUNT_SEARCH_Y
                sx0, sx1 = self._COUNT_SEARCH_X
                search_zone = img_color_scaled[y + sy0 : y + sy1, x + sx0 : x + sx1]
                search_zone_gray = cv2.cvtColor(search_zone, cv2.COLOR_BGR2GRAY)

                count_val = self.match_count(search_zone_gray)
                calculated_price = self.calculate_price(card_name, count_val)

                # Ergebnise an result anhängen
                results.append(
                    {
                        "card_name": card_name,
                        "count": count_val,
                        "calculated_price": calculated_price,
                        "rarity": self.rarities[card_name],
                    }
                )
        return results


def main():
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
