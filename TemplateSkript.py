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
    # Template w = 208, h = 188
    # First Row, x = 85
    # Second Row, x = 432
    # Third Row, x = 777
    # Offset first to second row, y = y + 669

    temp = 510 + 240
    shop_path = "shop_pictures/2.jpeg"

    # Slot 1
    # create_normalized_template(shop_path, "gold_chest", x=85, y=temp, w=208, h=188)
    # Slot 2
    # create_normalized_template(shop_path, "gold_chest", x=432, y=temp, w=208, h=188)
    # Slot 3
    # create_normalized_template(shop_path, "void", x=777, y=temp, w=208, h=188)
    # Slot 4
    create_normalized_template(shop_path, "guards", x=85, y=temp + 669, w=208, h=188)
    # Slot 5
    # create_normalized_template(
    #     shop_path, "mother_witch", x=432, y=temp + 669, w=208, h=188
    # )
    # Slot 6
    # create_normalized_template(shop_path, "sparky", x=777, y=temp + 669, w=208, h=188)

    # 765


if __name__ == "__main__":
    main()
