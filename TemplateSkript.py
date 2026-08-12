"""Hilfsskript zum manuellen Ausschneiden neuer Karten-/Zahlen-Templates.

Lädt einen Referenz-Screenshot, normalisiert ihn auf die Standardbreite und
schneidet per Hand ermittelte Koordinaten (siehe CoordinateFinder.py) als
neues PNG-Template aus.
"""

import cv2


def create_normalized_template(
    image_path: str,
    troop_name: str,
    x: int,
    y: int,
    w: int,
    h: int,
    target_width: int = 1080,
):
    """Skaliert ein Bild und schneidet ein Template aus.

    Args:
      image_path: Pfad zum Original-Screenshot.
      troop_name: Name für die Truppe.
      x, y, w, h: Koordinaten und Größe des Ausschnitts im skalierten Bild.
      target_width: Die Standardbreite für dein System.
    """
    img = cv2.imread(image_path)
    if img is None:
        return

    # 1. Auf Standardbreite bringen
    height, width = img.shape[:2]
    scale = target_width / float(width)
    img_scaled = cv2.resize(img, (target_width, int(height * scale)))

    # 2. Ausschnitt wählen (z.B. das Gesicht des Knights)
    # Nutze dein Coordinate-Picker Skript, um x, y, w, h zu finden!
    template = img_scaled[y : y + h, x : x + w]

    # 3. Als Graustufen-PNG speichern für deine App
    # template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(f"templates/cards/{troop_name}.png", template)
    print(f"Neues Template '{troop_name}.png' wurde erstellt.")
    cv2.imshow(troop_name, template)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def main():
    """Schneidet die unten konfigurierten Templates aus dem Referenzbild aus."""
    # Template w = 208, h = 188
    # First Row, x = 85
    # Second Row, x = 432
    # Third Row, x = 777
    # Offset first to second row, y = y + 669
    # number width = 46  2:92  3:138  4:170
    # number height = 64

    shop_path = "shop_pictures/8.jpeg"

    # Slot 1
    create_normalized_template(shop_path, "collected", x=70, y=1235, w=245, h=47)
    # Slot 2
    # create_normalized_template(shop_path, "canon", x=432, y=722, w=208, h=188)
    # Slot 3
    # create_normalized_template(
    #     shop_path, "skeleton_barrel", x=780, y=800, w=208, h=188
    # )
    # Slot 4
    # create_normalized_template(shop_path, "zahl", x=140, y=940 + 669, w=92, h=64)
    # Slot 5
    # create_normalized_template(shop_path, "zahl", x=488, y=870 + 669, w=92, h=64)
    # Slot 6
    # create_normalized_template(
    #     shop_path, "ram_rider", x=776, y=629 + 669, w=208, h=188
    # )


if __name__ == "__main__":
    main()
