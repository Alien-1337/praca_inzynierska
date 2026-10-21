import tkinter as tk
import db_utils


def show_inventory():
    win = tk.Toplevel()
    win.title("Stan magazynowy")
    win.geometry("400x500")

    try:
        # dane z bazy
        data = db_utils.get_inventory_items()

        if not data:
            tk.Label(win, text="Brak danych w magazynie").pack(pady=20)
            return

        for item in data:
            name = item[1]  # nazwa
            quantity = item[4]  # ilość

            tk.Label(win, text=f"{name} - {quantity} szt.").pack(anchor="w", padx=10, pady=2)

    except Exception as e:
        tk.Label(win, text=f"Błąd: {str(e)}").pack(pady=20)
