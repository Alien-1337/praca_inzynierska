"""Okno wyboru zakresu raportu oraz zapis i druk PDF (tylko Kierownik)."""
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

import db_utils
import permissions
import report_generator as rg


def open_file(path, to_printer=False):
    """Otwiera plik w domyślnym programie albo wysyła go do drukarki.
    Zwraca True tylko wtedy, gdy plik poszedł do druku."""
    if sys.platform.startswith("win"):
        if to_printer:
            try:
                os.startfile(path, "print")
                return True
            except OSError:
                pass  # program do PDF nie obsługuje druku z poziomu systemu, otwieramy plik
        os.startfile(path)
        return False
    subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])
    return False


class ReportDialog(ctk.CTkToplevel):
    def __init__(self, parent, username):
        super().__init__(parent)
        self.parent = parent
        self.username = username
        self.months = db_utils.get_failure_months()
        self.month_labels = [rg.month_label(y, m) for y, m in self.months]

        self.title("Raport awaryjności")
        self.geometry("470x430")
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(100, self._grab)

        ctk.CTkLabel(self, text="Raport do wydruku",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(25, 4))
        ctk.CTkLabel(self, text="Wybierz miesiąc oraz maszynę albo cały miesiąc.",
                     text_color="#9CA3AF").pack()

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=40, pady=(20, 0))

        ctk.CTkLabel(form, text="Miesiąc", anchor="w").pack(fill="x")
        self.month_box = ctk.CTkComboBox(form, values=self.month_labels, state="readonly",
                                         command=self.on_month_change)
        self.month_box.pack(fill="x", pady=(2, 12))
        self.month_box.set(self.month_labels[0])

        ctk.CTkLabel(form, text="Zakres", anchor="w").pack(fill="x")
        self.machine_box = ctk.CTkComboBox(form, values=[rg.ALL_MACHINES], state="readonly",
                                           command=lambda _: self.refresh_count())
        self.machine_box.pack(fill="x", pady=(2, 12))

        self.info = ctk.CTkLabel(form, text="", anchor="w", text_color="#9CA3AF")
        self.info.pack(fill="x", pady=(0, 5))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=40, pady=(10, 0))
        self.save_button = ctk.CTkButton(buttons, text="Zapisz PDF", height=38, fg_color="#1f6aa5",
                                         command=self.save_pdf)
        self.save_button.pack(fill="x", pady=4)
        self.print_button = ctk.CTkButton(buttons, text="Drukuj", height=38, fg_color="#10B981",
                                          hover_color="#059669", command=self.print_report)
        self.print_button.pack(fill="x", pady=4)
        ctk.CTkButton(buttons, text="Zamknij", height=38, fg_color="#6B7280", hover_color="#4B5563",
                      command=self.close).pack(fill="x", pady=4)

        self.on_month_change()

    def _grab(self):
        try:
            self.grab_set()
        except Exception:
            pass

    # --- wybrany zakres ---
    def period(self):
        return self.months[self.month_labels.index(self.month_box.get())]

    def machine(self):
        value = self.machine_box.get()
        return None if value == rg.ALL_MACHINES else value

    def rows(self):
        year, month = self.period()
        start, end = rg.month_range(year, month)
        return db_utils.get_failures_for_report(start, end, self.machine())

    def on_month_change(self, _value=None):
        year, month = self.period()
        start, end = rg.month_range(year, month)
        self.machine_box.configure(values=[rg.ALL_MACHINES] + db_utils.get_failure_areas(start, end))
        self.machine_box.set(rg.ALL_MACHINES)
        self.refresh_count()

    def refresh_count(self):
        count = len(self.rows())
        self.info.configure(text=f"Awarii w wybranym zakresie: {count}")
        state = "normal" if count else "disabled"
        self.save_button.configure(state=state)
        self.print_button.configure(state=state)

    # --- generowanie ---
    def _allowed(self):
        if db_utils.user_can(self.username, permissions.FEATURE_ANALYTICS_PRINT):
            return True
        messagebox.showerror("Brak uprawnień", "Druk raportów jest dostępny tylko dla Kierownika.", parent=self)
        return False

    def _build(self, path):
        year, month = self.period()
        author = f"{self.username} ({db_utils.get_user_role(self.username)})"
        try:
            rg.build_report(self.rows(), year, month, self.machine(), author, path)
            return True
        except ValueError as e:
            messagebox.showinfo("Raport", str(e), parent=self)
        except Exception as e:
            print("Błąd generowania raportu:", e)
            messagebox.showerror("Błąd", f"Nie udało się wygenerować raportu:\n{e}", parent=self)
        return False

    def save_pdf(self):
        if not self._allowed():
            return
        year, month = self.period()
        path = filedialog.asksaveasfilename(
            parent=self, title="Zapisz raport", defaultextension=".pdf",
            filetypes=[("Dokument PDF", "*.pdf")],
            initialfile=rg.default_filename(year, month, self.machine()))
        if not path or not self._build(path):
            return
        try:
            open_file(path)
        except OSError:
            messagebox.showinfo("Raport zapisany", f"Zapisano plik:\n{path}", parent=self)

    def print_report(self):
        if not self._allowed():
            return
        year, month = self.period()
        path = os.path.join(tempfile.gettempdir(), rg.default_filename(year, month, self.machine()))
        if not self._build(path):
            return
        try:
            printed = open_file(path, to_printer=True)
        except OSError as e:
            messagebox.showerror("Błąd", f"Nie udało się otworzyć raportu:\n{e}", parent=self)
            return
        if printed:
            messagebox.showinfo("Drukowanie", "Raport wysłano do drukarki domyślnej.", parent=self)
        else:
            messagebox.showinfo("Drukowanie", "Raport otwarto w programie do PDF. "
                                "Wydrukuj go stamtąd (Ctrl+P).", parent=self)

    def close(self):
        self.destroy()
        try:
            self.parent.grab_set()
        except Exception:
            pass


def show_report_dialog(parent, username):
    # druk raportów ma tylko Kierownik
    if not db_utils.user_can(username, permissions.FEATURE_ANALYTICS_PRINT):
        messagebox.showerror("Brak uprawnień", "Druk raportów jest dostępny tylko dla Kierownika.", parent=parent)
        return None
    if not db_utils.get_failure_months():
        messagebox.showinfo("Raport", "W bazie nie ma jeszcze awarii, więc nie ma czego drukować.", parent=parent)
        return None
    return ReportDialog(parent, username)
