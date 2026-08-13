"""Tkinter-Desktop-GUI zum Hochladen von Screenshots und Auswerten der Historie."""

import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, messagebox, ttk
from typing import Literal

from database import StoredOffer, fetch_all_offers, save_offers
from main import ClashStoreAnalyzer
from stats import (
    export_to_csv,
    filter_card_summaries,
    summarize_by_card,
    summarize_by_rarity,
    total_gold_spent,
)

DB_PATH = "clashstore.db"
_Anchor = Literal["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"]
_RARITY_COLORS = {
    "legendary": "#7f8c8d",
    "epic": "#9b59b6",
    "rare": "#e67e22",
    "common": "#3498db",
}


class ClashStoreApp:
    """Desktop-GUI: Screenshots hochladen, Shop-Historie durchsuchen und auswerten.

    Schließt den Kreislauf, für den database.py gebaut wurde: die Anzeige
    lädt aus der Datenbank, ein Upload lässt den Analyzer laufen und
    schreibt zurück in die Datenbank.
    """

    def __init__(self, root: tk.Tk) -> None:
        """Baut das Fenster auf und lädt den aktuellen Datenbank-Stand.

        Args:
            root: Das Tk-Wurzelfenster.
        """
        self.root = root
        self.root.title("ClashStore")
        self.root.geometry("1100x700")

        self.analyzer = ClashStoreAnalyzer(template_dir="templates/cards")
        self.offers: list[StoredOffer] = []
        self._sort_state: dict[tuple[ttk.Treeview, str], bool] = {}

        self._build_layout()
        self._refresh()

    def _build_layout(self) -> None:
        """Baut Sidebar, Rarity-Zusammenfassung und die beiden Tabs auf."""
        self._build_sidebar()

        main_area = ttk.Frame(self.root)
        main_area.pack(side="left", fill="both", expand=True)

        self._build_rarity_summary(main_area)

        notebook = ttk.Notebook(main_area)
        notebook.pack(fill="both", expand=True)
        self._build_card_table(notebook)
        self._build_history_tab(notebook)

    def _build_sidebar(self) -> None:
        """Baut die linke Sidebar mit Upload, Statistiken und CSV-Export auf."""
        sidebar = ttk.Frame(self.root, padding=10)
        sidebar.pack(side="left", fill="y")

        ttk.Label(sidebar, text="Upload", font=("", 12, "bold")).pack(anchor="w")
        ttk.Button(sidebar, text="Screenshot hochladen", command=self._on_upload).pack(
            fill="x", pady=(4, 20)
        )

        ttk.Label(sidebar, text="Statistiken", font=("", 12, "bold")).pack(anchor="w")
        self.total_gold_label = ttk.Label(sidebar, text="")
        self.total_gold_label.pack(anchor="w", pady=2)
        self.last_scan_label = ttk.Label(sidebar, text="")
        self.last_scan_label.pack(anchor="w", pady=(2, 20))

        ttk.Button(
            sidebar, text="Als CSV exportieren", command=self._on_export_csv
        ).pack(fill="x")

    def _build_rarity_summary(self, parent: tk.Widget) -> None:
        """Baut die Zusammenfassungs-Panels je Seltenheit auf.

        Args:
            parent: Übergeordnetes Widget für die Panels.
        """
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill="x")

        style = ttk.Style()
        for rarity, color in _RARITY_COLORS.items():
            style.configure(f"{rarity}.TFrame", background=color)
            style.configure(f"{rarity}.TLabel", background=color, foreground="white")

        self.rarity_labels: dict[str, tuple[ttk.Label, ttk.Label]] = {}
        rarities = [r["rarity"] for r in summarize_by_rarity([])]
        for col, rarity in enumerate(rarities):
            frame_style = f"{rarity}.TFrame" if rarity in _RARITY_COLORS else "TFrame"
            label_style = f"{rarity}.TLabel" if rarity in _RARITY_COLORS else "TLabel"

            panel = ttk.Frame(frame, padding=10, style=frame_style)
            panel.grid(row=0, column=col, sticky="nsew", padx=5)
            frame.columnconfigure(col, weight=1)

            ttk.Label(
                panel,
                text=rarity.capitalize(),
                font=("", 11, "bold"),
                style=label_style,
            ).pack(anchor="w")
            count_label = ttk.Label(panel, text="0 Karten", style=label_style)
            count_label.pack(anchor="w")
            gold_label = ttk.Label(panel, text="0 Gold", style=label_style)
            gold_label.pack(anchor="w")
            self.rarity_labels[rarity] = (count_label, gold_label)

    def _build_card_table(self, notebook: ttk.Notebook) -> None:
        """Baut den Übersicht-Tab: Suchfeld + Tabelle je Karte auf.

        Args:
            notebook: Das Tab-Widget, dem der neue Tab hinzugefügt wird.
        """
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="Übersicht")

        search_row = ttk.Frame(tab)
        search_row.pack(fill="x", pady=(0, 5))
        ttk.Label(search_row, text="Suche:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._render_card_table())
        ttk.Entry(search_row, textvariable=self.search_var).pack(
            side="left", fill="x", expand=True, padx=5
        )

        columns: list[tuple[str, str, int, _Anchor]] = [
            ("card_name", "Karte", 200, "w"),
            ("rarity", "Seltenheit", 100, "center"),
            ("count", "Anzahl", 80, "e"),
            ("gold", "Gold", 80, "e"),
        ]
        self.card_table = ttk.Treeview(
            tab, columns=[c[0] for c in columns], show="headings"
        )
        for key, heading, width, anchor in columns:
            self.card_table.heading(
                key,
                text=heading,
                command=self._make_sort_handler(self.card_table, key),
            )
            self.card_table.column(key, width=width, anchor=anchor)
        self.card_table.pack(fill="both", expand=True)

    def _build_history_tab(self, notebook: ttk.Notebook) -> None:
        """Baut den Verlauf-Tab mit der rohen Scan-Historie auf.

        Args:
            notebook: Das Tab-Widget, dem der neue Tab hinzugefügt wird.
        """
        tab = ttk.Frame(notebook, padding=10)
        notebook.add(tab, text="Verlauf")

        columns: list[tuple[str, str, int, _Anchor]] = [
            ("scanned_at", "Gescannt am", 180, "w"),
            ("source_image", "Screenshot", 220, "w"),
            ("card_name", "Karte", 140, "w"),
            ("count", "Anzahl", 70, "e"),
            ("calculated_price", "Preis", 70, "e"),
            ("rarity", "Seltenheit", 90, "center"),
            ("free", "Gratis/Collected", 120, "center"),
        ]
        self.history_table = ttk.Treeview(
            tab, columns=[c[0] for c in columns], show="headings"
        )
        for key, heading, width, anchor in columns:
            self.history_table.heading(
                key,
                text=heading,
                command=self._make_sort_handler(self.history_table, key),
            )
            self.history_table.column(key, width=width, anchor=anchor)
        self.history_table.pack(fill="both", expand=True)

    def _on_upload(self) -> None:
        """Lässt den Nutzer einen Screenshot wählen, analysiert und speichert ihn."""
        path = filedialog.askopenfilename(
            title="Screenshot auswählen",
            filetypes=[("Bilder", "*.jpg *.jpeg *.png"), ("Alle Dateien", "*.*")],
        )
        if not path:
            return

        try:
            offers = self.analyzer.analyze_screenshots(path)
            save_offers(DB_PATH, offers, path)
        except Exception as e:
            messagebox.showerror("Fehler bei der Analyse", str(e))
            return

        self._refresh()

    def _on_export_csv(self) -> None:
        """Lässt den Nutzer einen Pfad wählen und exportiert die Historie als CSV."""
        path = filedialog.asksaveasfilename(
            title="CSV speichern unter",
            defaultextension=".csv",
            filetypes=[("CSV-Dateien", "*.csv")],
        )
        if not path:
            return

        try:
            export_to_csv(self.offers, path)
        except OSError as e:
            messagebox.showerror("Fehler beim Export", str(e))

    def _refresh(self) -> None:
        """Lädt den aktuellen Datenbank-Stand und aktualisiert alle Widgets."""
        self.offers = fetch_all_offers(DB_PATH)

        total_gold = total_gold_spent(self.offers)
        self.total_gold_label.config(text=f"Gold ausgegeben: {total_gold}")

        last_scan = max((o["scanned_at"] for o in self.offers), default="–")[:10]
        self.last_scan_label.config(text=f"Letzter Scan: {last_scan}")

        rarity_summaries = {r["rarity"]: r for r in summarize_by_rarity(self.offers)}
        for rarity, (count_label, gold_label) in self.rarity_labels.items():
            summary = rarity_summaries[rarity]
            count_label.config(text=f"{summary['count']} Karten")
            gold_label.config(text=f"{summary['gold']} Gold")

        self._render_card_table()
        self._render_history_table()

    def _render_card_table(self) -> None:
        """Rendert die Pro-Karte-Tabelle, gefiltert nach dem Suchfeld."""
        query = self.search_var.get()
        summaries = filter_card_summaries(summarize_by_card(self.offers), query)

        self.card_table.delete(*self.card_table.get_children())
        for summary in summaries:
            self.card_table.insert(
                "",
                "end",
                values=(
                    summary["card_name"],
                    summary["rarity"],
                    summary["count"],
                    summary["gold"],
                ),
            )

    def _render_history_table(self) -> None:
        """Rendert die rohe Verlaufs-Tabelle."""
        self.history_table.delete(*self.history_table.get_children())
        for offer in self.offers:
            self.history_table.insert(
                "",
                "end",
                values=(
                    offer["scanned_at"],
                    offer["source_image"],
                    offer["card_name"],
                    offer["count"],
                    offer["calculated_price"],
                    offer["rarity"],
                    "Ja" if offer["free"] else "Nein",
                ),
            )

    def _make_sort_handler(self, tree: ttk.Treeview, column: str) -> Callable[[], None]:
        """Baut einen Klick-Handler, der eine Tabelle nach column sortiert.

        Eine echte Funktion statt eines Lambdas mit Default-Argument, damit
        column pro Spaltenkopf korrekt gebunden bleibt (kein Closure-Bug
        durch die Schleifenvariable) und mypy --strict den Typ prüfen kann.

        Args:
            tree: Die zu sortierende Tabelle.
            column: Die Spalte, nach der bei Klick sortiert werden soll.

        Returns:
            Eine parameterlose Funktion, geeignet für heading(command=...).
        """

        def handler() -> None:
            self._sort_treeview(tree, column)

        return handler

    def _sort_treeview(self, tree: ttk.Treeview, column: str) -> None:
        """Sortiert eine Tabelle nach der angeklickten Spalte.

        Numerische Spaltenwerte werden numerisch sortiert, alles andere
        als Text (case-insensitive). Erneutes Klicken kehrt die Richtung um.

        Args:
            tree: Die zu sortierende Tabelle.
            column: Die angeklickte Spalte.
        """
        reverse = self._sort_state.get((tree, column), False)

        def sort_key(item_id: str) -> tuple[int, float | str]:
            value = tree.set(item_id, column)
            try:
                return (0, float(value))
            except ValueError:
                return (1, value.lower())

        items = sorted(tree.get_children(""), key=sort_key, reverse=reverse)
        for index, item_id in enumerate(items):
            tree.move(item_id, "", index)

        self._sort_state[(tree, column)] = not reverse


def main() -> None:
    """Startet die ClashStore-GUI."""
    root = tk.Tk()
    try:
        ClashStoreApp(root)
    except Exception as e:
        root.withdraw()
        messagebox.showerror("Fehler beim Start", str(e))
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
