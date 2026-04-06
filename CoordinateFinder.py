import cv2

# Lade dein Bild
img = cv2.imread('clash_store.jpg')


def show_coordinates(event, x, y, flags, param):
    if event == cv2.EVENT_MOUSEMOVE:
        # Kopie des Bildes machen, damit die alten Zahlen verschwinden
        img_copy = img.copy()
        text = f"X: {x}, Y: {y}"
        # Text ans Bild heften
        cv2.putText(img_copy, text, (x + 10, y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.imshow('Coordinate Picker', img_copy)

    if event == cv2.EVENT_LBUTTONDOWN:
        # Bei Linksklick Koordinate fest in die Konsole drucken
        print(f"Festgelegt: x={x}, y={y}")


# Fenster erstellen und Maus-Callback registrieren
cv2.namedWindow('Coordinate Picker')
cv2.setMouseCallback('Coordinate Picker', show_coordinates)

print("Bewege die Maus über das Bild. Linksklick zum Loggen. Drücke 'q' zum Beenden.")

while True:
    cv2.imshow('Coordinate Picker', img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()