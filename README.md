
# Clashalyzer

Ein Analyse Tool für den Täglichen Store im Spiel 'Clash Royale'. 
Erkennt, welche Karten wie oft und für welchen Preis angeboten werden. 
Für Spieler, die auch gerne Daten sammeln.


## Lokal laufen lassen

### Voraussetzungen
- Python 3.14 oder neuer
- [uv](https://docs.astral.sh/uv/) als Paketmanager
- Falls `import tkinter` fehlschlägt
  - Fedora: `sudo dnf install python3-tkinter`
  - Debian/Ubuntu: `sudo apt install python3-tk`

Projekt klonen

```bash
  git clone https://github.com/CommanderExodus/Clashalyzer
```

In den Projektordner wechseln

```bash
  cd Clashalyzer
```

Abhängigkeiten installieren

```bash
  uv sync
```

Gui starten

```bash
  uv run python gui.py
```


## Tests laufen lassen

Um die Tests durchlaufen zu lassen

```bash
  uv run pytest
```


## Screenshots

![Main Screen](https://github.com/CommanderExodus/Clashalyzer/blob/main/Screenshots%20f%C3%BCr%20Readme/BaseScreenshot.png?raw=true)

![Verlauf Screen](https://github.com/CommanderExodus/Clashalyzer/blob/main/Screenshots%20f%C3%BCr%20Readme/VerlaufScreenshot.png?raw=true)

## Weiterentwicklung

Die Skripte `CoordinateFinder.py` und `TemplateSkript.py` können zur 
weiterentwicklung verwendet werden. Das Skript `CoordinateFinder.py` ist 
dafür da, die Koordinaten für `TemplateSkript.py` zu finden.


## Author

- [@CommanderExodus](https://github.com/CommanderExodus)

