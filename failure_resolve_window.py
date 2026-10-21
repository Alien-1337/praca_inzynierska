import customtkinter as ctk
from tkinter import messagebox, ttk
from datetime import datetime
import db_utils
import permissions
import failure_window

# Kolory statusów w tabeli
STATUS_COLORS = {
    db_utils.STATUS_REPORTED: "#F87171",    # czerwony - czeka na Technika
    db_utils.STATUS_IN_REPAIR: "#FBBF24",   # żółty - ktoś nad nią pracuje
    db_utils.STATUS_RESOLVED: "#34D399",    # zielony - zamknięta
}

# Indeksy w wierszu zwracanym przez db_utils.get_open_failures (kolejność = db_utils.FAILURE_COLUMNS)
(I_ID, I_USER, I_AREA, I_SUBSYSTEM, I_FUNC, I_DATE, I_SHIFT, I_T_REPORTED, I_T_RESOLVED,
 I_DOWNTIME, I_DEPARTMENT, I_CATEGORY, I_TYPE, I_DESC, I_RESOLVER, I_PART,
 I_LABOR, I_PARTS, I_TOTAL, I_STATUS) = range(20)


def _safe_grab(window):
    """grab_set() potrafi rzucić wyjątek, gdy okno nie jest jeszcze widoczne - wtedy próbujemy ponownie."""
    try:
        window.grab_set()
    except Exception:
        try:
            window.after(150, lambda: _safe_grab(window))
        except Exception:
            pass


class ResolveDialog(ctk.CTkToplevel):
    """Okno 'Zakończ naprawę': data i godzina zakończenia, zużyta część, podgląd przestoju."""

    def __init__(self, parent, failure_row, username):
        super().__init__(parent)
        self.parent = parent
        self.failure = failure_row
        self.username = username

        self.title(f"Zakończ naprawę - awaria #{failure_row[I_ID]}")
        self.geometry("580x640")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.close)
        _safe_grab(self)

        # --- Podsumowanie zgłoszenia ---
        summary = (
            f"{failure_row[I_AREA]} / {failure_row[I_SUBSYSTEM]} / {failure_row[I_FUNC]}\n"
            f"{failure_row[I_TYPE]} ({failure_row[I_CATEGORY]}) - {failure_row[I_DEPARTMENT]}\n"
            f"Zgłoszono: {failure_row[I_DATE]} {failure_row[I_T_REPORTED]} "
            f"przez {failure_row[I_USER]}\n\n"
            f"{failure_row[I_DESC] or ''}"
        )
        ctk.CTkLabel(self, text=summary, justify="left", anchor="w", wraplength=520,
                     text_color="#D1D5DB").pack(fill="x", padx=30, pady=(25, 10))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=30)

        # --- Data i godzina zakończenia ---
        ctk.CTkLabel(form, text="Data zakończenia (YYYY-MM-DD)", anchor="w").pack(fill="x", pady=(10, 0))
        self.entry_date = ctk.CTkEntry(form)
        self.entry_date.pack(fill="x")
        self.entry_date.insert(0, datetime.now().strftime("%Y-%m-%d"))

        ctk.CTkLabel(form, text="Godzina zakończenia (HH:MM)", anchor="w").pack(fill="x", pady=(10, 0))
        self.entry_time = ctk.CTkEntry(form)
        self.entry_time.pack(fill="x")
        self.entry_time.insert(0, datetime.now().strftime("%H:%M"))

        # --- Zużyta część z magazynu ---
        parts = [""]
        try:
            for item in db_utils.get_inventory_items():
                parts.append(f"{item[1]} | SAP: {item[2]}")
        except Exception as e:
            print(f"Błąd ładowania magazynu: {e}")

        ctk.CTkLabel(form, text="Zużyta część (opcjonalne)", anchor="w").pack(fill="x", pady=(10, 0))
        self.part_box = ctk.CTkComboBox(form, values=parts)
        self.part_box.pack(fill="x")
        self.part_box.set("")

        # --- Podgląd przestoju ---
        self.downtime_label = ctk.CTkLabel(form, text="", anchor="w", justify="left", wraplength=520)
        self.downtime_label.pack(fill="x", pady=(18, 0))
        self.entry_date.bind("<KeyRelease>", self.update_preview)
        self.entry_time.bind("<KeyRelease>", self.update_preview)
        self.update_preview()

        # --- Przyciski ---
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=30, pady=25)

        ctk.CTkButton(buttons, text="Zakończ naprawę", fg_color="#10B981", hover_color="#059669",
                      height=40, command=self.save).pack(side="left", expand=True, fill="x", padx=(0, 10))
        ctk.CTkButton(buttons, text="Anuluj", fg_color="#6B7280", hover_color="#4B5563",
                      height=40, command=self.close).pack(side="left", expand=True, fill="x", padx=(10, 0))

    def update_preview(self, event=None):
        try:
            minutes = db_utils.compute_downtime_minutes(
                self.failure[I_DATE], self.failure[I_T_REPORTED],
                self.entry_date.get(), self.entry_time.get()
            )
            self.downtime_label.configure(
                text=f"Przestój: {minutes} min ({minutes // 60} h {minutes % 60} min)",
                text_color="#D1D5DB"
            )
        except ValueError as e:
            self.downtime_label.configure(text=str(e), text_color="#F59E0B")

    def save(self):
        raw_part = self.part_box.get().strip()
        part_name = raw_part.split(" | SAP:")[0] if " | SAP:" in raw_part else raw_part

        ok, message = db_utils.resolve_failure(
            self.failure[I_ID], self.username,
            self.entry_date.get().strip(), self.entry_time.get().strip(), part_name
        )

        if ok:
            messagebox.showinfo("Sukces", message, parent=self)
            self.close(refresh=True)
        else:
            messagebox.showerror("Błąd", message, parent=self)

    def close(self, refresh=False):
        parent = self.parent
        self.destroy()
        parent.after_dialog(refresh)


class FailureResolveWindow(ctk.CTkToplevel):
    """Kolejka awarii dla Technika: przejęcie naprawy, zakończenie naprawy, zapis awarii po fakcie."""

    def __init__(self, username, return_callback):
        super().__init__()
        self.username = username
        self.return_callback = return_callback
        self.failures = {}

        self.title("Rozwiązywanie awarii - CMMS")
        self.geometry("1450x720")
        self.protocol("WM_DELETE_WINDOW", self.back_to_menu)
        _safe_grab(self)

        # --- STYL TABELI ---
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background="#2b2b2b",
                        foreground="white",
                        fieldbackground="#2b2b2b",
                        rowheight=30)
        style.map('Treeview', background=[('selected', '#1f6aa5')])
        style.configure("Treeview.Heading", background="#1a1a1a", foreground="white")

        # --- NAGŁÓWEK ---
        ctk.CTkLabel(self, text="Rozwiązywanie awarii",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(
            self,
            text="Zaznacz awarię: „Rozpocznij naprawę” przypisuje ją Tobie, "
                 "„Zakończ naprawę” zamyka zgłoszenie i liczy przestój oraz koszty.",
            text_color="#9CA3AF"
        ).pack()

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=25, pady=(15, 0))

        self.show_all = ctk.CTkSwitch(top, text="Pokaż także rozwiązane", command=self.load_failures)
        self.show_all.pack(side="left")

        self.count_label = ctk.CTkLabel(top, text="", text_color="#9CA3AF")
        self.count_label.pack(side="right")

        # --- TABELA ---
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        columns = ("ID", "Data", "Godz.", "Obszar", "Podsystem", "Typ awarii",
                   "Opis", "Zgłosił", "Status", "Technik")
        widths = (50, 100, 70, 150, 150, 160, 360, 110, 100, 110)

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        for column, width in zip(columns, widths):
            self.tree.heading(column, text=column)
            self.tree.column(column, width=width, anchor="w" if column == "Opis" else "center")

        for status, color in STATUS_COLORS.items():
            self.tree.tag_configure(status, foreground=color)

        scrollbar = ctk.CTkScrollbar(table_frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # --- PRZYCISKI ---
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(pady=(5, 20))

        ctk.CTkButton(buttons, text="Rozpocznij naprawę", fg_color="#F59E0B", hover_color="#D97706",
                      width=190, height=38, command=self.start_repair).pack(side="left", padx=8)
        ctk.CTkButton(buttons, text="Zakończ naprawę", fg_color="#10B981", hover_color="#059669",
                      width=190, height=38, command=self.finish_repair).pack(side="left", padx=8)
        ctk.CTkButton(buttons, text="Dodaj zakończoną awarię", fg_color="#1f6aa5",
                      width=210, height=38, command=self.add_completed_failure).pack(side="left", padx=8)
        ctk.CTkButton(buttons, text="Odśwież", fg_color="#444", hover_color="#555",
                      width=120, height=38, command=self.load_failures).pack(side="left", padx=8)
        ctk.CTkButton(buttons, text="Powrót", fg_color="#6B7280", hover_color="#4B5563",
                      width=120, height=38, command=self.back_to_menu).pack(side="left", padx=8)

        self.load_failures()

    # --- DANE ---
    def load_failures(self):
        try:
            previous = self.tree.focus()   # zaznaczenie sprzed odświeżenia

            for iid in self.tree.get_children():
                self.tree.delete(iid)

            rows = db_utils.get_open_failures(include_resolved=bool(self.show_all.get()))
            self.failures = {row[I_ID]: row for row in rows}

            for row in rows:
                description = (row[I_DESC] or "").replace("\n", " ")
                if len(description) > 70:
                    description = description[:67] + "..."

                self.tree.insert("", "end", iid=str(row[I_ID]), tags=(row[I_STATUS],), values=(
                    row[I_ID], str(row[I_DATE]), row[I_T_REPORTED] or "",
                    row[I_AREA] or "", row[I_SUBSYSTEM] or "", row[I_TYPE] or "",
                    description, row[I_USER] or "", row[I_STATUS], row[I_RESOLVER] or ""
                ))

            # Po odświeżeniu zostaje zaznaczenie - np. po "Rozpocznij naprawę" od razu
            # można kliknąć "Zakończ naprawę" bez szukania wiersza od nowa.
            if previous and self.tree.exists(previous):
                self.tree.selection_set(previous)
                self.tree.focus(previous)

            open_count = sum(1 for row in rows if row[I_STATUS] != db_utils.STATUS_RESOLVED)
            self.count_label.configure(text=f"Do rozwiązania: {open_count}")

        except Exception as e:
            print("Błąd ładowania awarii:", e)
            messagebox.showerror("Błąd", "Nie udało się pobrać awarii", parent=self)

    def selected_failure(self):
        selected = self.tree.focus()
        row = self.failures.get(int(selected)) if selected else None
        if row is None:
            messagebox.showwarning("Wybierz awarię", "Zaznacz awarię na liście.", parent=self)
        return row

    # --- AKCJE ---
    def start_repair(self):
        row = self.selected_failure()
        if row is None:
            return

        ok, message = db_utils.start_repair(row[I_ID], self.username)
        if ok:
            messagebox.showinfo("Rozpocznij naprawę", message, parent=self)
        else:
            messagebox.showwarning("Rozpocznij naprawę", message, parent=self)
        self.load_failures()

    def finish_repair(self):
        row = self.selected_failure()
        if row is None:
            return

        if row[I_STATUS] == db_utils.STATUS_RESOLVED:
            messagebox.showinfo("Awaria rozwiązana", "Ta awaria jest już zamknięta.", parent=self)
            return

        ResolveDialog(self, row, self.username)

    def add_completed_failure(self):
        """Awaria, która została naprawiona od razu i nigdy nie była zgłoszona - pełny formularz."""
        failure_window.FailureWindow(self.username, self.after_full_form, mode=failure_window.MODE_FULL)

    def after_dialog(self, refresh):
        if refresh:
            self.load_failures()
        _safe_grab(self)

    def after_full_form(self):
        self.load_failures()
        _safe_grab(self)

    def back_to_menu(self):
        self.destroy()
        if self.return_callback:
            self.return_callback()


def show_failure_resolve_window(username, back_callback):
    # Rozwiązywać awarie mogą Technik i Administrator.
    if not db_utils.user_can(username, permissions.FEATURE_FAILURE_RESOLVE):
        messagebox.showerror("Brak uprawnień", "Rozwiązywać awarie mogą: Technik i Administrator.")
        back_callback()
        return

    FailureResolveWindow(username, back_callback)
