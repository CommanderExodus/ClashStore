"""Modul zur Erkennung von Shop-Kacheln in Clash Royale mittels OpenCV."""
import json
import os

import cv2
import numpy as np
import pytesseract


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
        target_width: Die Standartbreite, auf die alle Bilder skaliert werden.
    """

    def __init__(self, template_dir: str, target_width: int = 1080, config_path: str = 'cards.json'):
        """Initialisiert den Analyzer mit einem Template.

        Args:
            template_dir: Directionary mit den Templates.
            target_width: Breite für die Normalisierung (Standart: 1080px).
            config_path: Seltenheit aller Karten und Preise im Shop.
        """
        self.target_width = target_width
        self.template = {}

        with open(config_path, 'r') as f:
            data = json.load(f)
            self.prices = data['prices']
            self.rarities = data['rarities']

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

    def preprocess(self, image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Bringt das Bild auf Standartgröße und Graustufen.

        Args:
            image: Das Originalbild

        Returns:
            Das resized Graustufenbild.
        """
        height, width = image.shape[:2]
        scale = self.target_width / float(width)
        resized = cv2.resize(image, (self.target_width, int(height * scale)), interpolation=cv2.INTER_AREA)
        return cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY), resized

    def read_number_from_zone(self, zone_img: np.ndarray) -> int:
        """Bereitet einen Bildausschnitt für OCR vor und extrahiert die Zahl.

        Args:
            zone_img: Der Farbausschnitt

        Returns:
            Die erkannte Zahl als Integer oder 0 bei Fehler.
        """

        # 1. Vergrößern
        resized = cv2.resize(zone_img, None, fx=3, fy=3, interpolation=cv2.INTER_LINEAR)

        # 2. Graustufen und Binarisierung
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 300, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 2,5. Morphologische Erosion
        kernel = np.ones((2, 2), np.uint8)
        thinned = cv2.erode(thresh, kernel, iterations=1)

        # 3. OCR
        tesseract_ready = cv2.bitwise_not(thinned)

        padded_img = cv2.copyMakeBorder(
            tesseract_ready,
            top=20, bottom=20, left=20, right=20,
            borderType=cv2.BORDER_CONSTANT,
            value=[255, 255, 255]
        )

        custom_config = r'--psm 7 -c tessedit_char_whitelist=0123456789x'
        text = pytesseract.image_to_string(padded_img, config=custom_config)

        # 4. Bereinigung: Aus "x80" mach "80"
        numbers_only = "".join(filter(str.isdigit, text))

        if numbers_only:
            return int(numbers_only)
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

                # Zonen zum lesen
                count_zone = img_color_scaled[y + 188:y + 255, x + 62:x + 185]

                # OCR
                count_val = self.read_number_from_zone(count_zone)
                calculated_price = self.calculate_price(card_name, count_val)

                # Ergebnise an result anhängen
                results.append({
                    "card_name": card_name,
                    "count": count_val,
                    "calculated_price": calculated_price,
                    "rarity": self.rarities[card_name]
                })
        return results


def main():
    try:
        analyzer = ClashStoreAnalyzer(template_dir='templates/cards')

        # Screenshots analysieren
        db_data = analyzer.analyze_screenshots('shop_pictures/3.jpeg')

        for row in db_data:
            print(f"Karte: {row['card_name'].upper():<10} | "
                  f"Anzahl: {row['count']} | "
                  f"Preis: {row['calculated_price']} Gold")

    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")

if __name__ == '__main__':
    main()