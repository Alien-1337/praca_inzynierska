import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime, timedelta
import db_utils
import permissions


def show_failure_form(username, back_callback=None):

    # Ten formularz zapisuje awarię już naprawioną (z osobą usuwającą i czasem),
    # więc wymaga prawa do rozwiązywania awarii: Technik lub Administrator.
    if not db_utils.user_can(username, permissions.FEATURE_FAILURE_RESOLVE):
        messagebox.showerror("Brak uprawnień",
                             "Zapis rozwiązanej awarii mogą wykonać: Technik i Administrator.")
        if back_callback:
            back_callback()
        return

    win = ctk.CTkToplevel()
    win.title("Zgłoszenie awarii")
    win.geometry("600x750")
    win.grab_set()
    win.protocol("WM_DELETE_WINDOW", lambda: on_close())

    def on_close():
        win.destroy()
        if back_callback:
            back_callback()

    ctk.CTkLabel(
        win,
        text="Zgłoszenie Awarii",
        font=ctk.CTkFont(size=22, weight="bold")
    ).pack(pady=(20, 10))

    form_frame = ctk.CTkFrame(win)
    form_frame.pack(padx=20, pady=10, fill="both", expand=True)

    # --- Pomocnicza funkcja do tworzenia pól ---
    def add_field(label, row):
        ctk.CTkLabel(form_frame, text=label, anchor="e").grid(
            row=row, column=0, padx=(10, 5), pady=6, sticky="e"
        )
        entry = ctk.CTkEntry(form_frame, width=300)
        entry.grid(row=row, column=1, padx=(0, 10), pady=6, sticky="w")
        return entry

    entry_area           = add_field("Obszar / System:", 0)
    entry_subsystem      = add_field("Podsystem:", 1)
    entry_func_subsystem = add_field("Podsystem funkcjonalny:", 2)
    entry_date           = add_field("Data (YYYY-MM-DD):", 3)
    entry_shift          = add_field("Zmiana (1/2/3):", 4)
    entry_time_reported  = add_field("Godzina zgłoszenia (HH:MM):", 5)
    entry_time_resolved  = add_field("Godzina zakończenia (HH:MM):", 6)
    entry_department     = add_field("Dział:", 7)
    entry_category       = add_field("Kategoria:", 8)
    entry_failure_type   = add_field("Typ awarii:", 9)
    entry_description    = add_field("Opis awarii:", 10)
    entry_resolver       = add_field("Osoba usuwająca:", 11)
    entry_used_part      = add_field("Użyta część (opcjonalnie):", 12)

    # --- Pole czasu awarii (readonly, wypełniane automatycznie) ---
    ctk.CTkLabel(form_frame, text="Czas awarii (min):", anchor="e").grid(
        row=13, column=0, padx=(10, 5), pady=6, sticky="e"
    )
    entry_downtime = ctk.CTkEntry(form_frame, width=300, state="disabled")
    entry_downtime.grid(row=13, column=1, padx=(0, 10), pady=6, sticky="w")

    # --- Auto-obliczanie czasu awarii ---
    def calculate_downtime(event=None):
        start = entry_time_reported.get().strip()
        end = entry_time_resolved.get().strip()
        if not start or not end:
            return
        try:
            fmt = "%H:%M"
            start_dt = datetime.strptime(start, fmt)
            end_dt = datetime.strptime(end, fmt)

            if end_dt < start_dt:
                end_dt += timedelta(days=1)

            diff = int((end_dt - start_dt).total_seconds() / 60)

            entry_downtime.configure(state="normal")
            entry_downtime.delete(0, "end")
            entry_downtime.insert(0, str(diff))
            entry_downtime.configure(state="disabled")

        except ValueError:
            entry_downtime.configure(state="normal")
            entry_downtime.delete(0, "end")
            entry_downtime.configure(state="disabled")

    entry_time_reported.bind("<FocusOut>", calculate_downtime)
    entry_time_resolved.bind("<FocusOut>", calculate_downtime)

    # --- Walidacja i zapis ---
    def submit():
        # Walidacja daty
        date_val = entry_date.get().strip()
        try:
            datetime.strptime(date_val, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Błąd", "Niepoprawny format daty.\nUżyj formatu: YYYY-MM-DD")
            return

        # Walidacja czasu
        downtime_val = entry_downtime.get().strip()
        if not downtime_val:
            messagebox.showerror("Błąd", "Uzupełnij godzinę zgłoszenia i zakończenia,\naby obliczyć czas awarii.")
            return

        try:
            downtime_int = int(downtime_val)
        except ValueError:
            messagebox.showerror("Błąd", "Czas awarii musi być liczbą całkowitą.")
            return

        # Wymagane pola (bez used_part - opcjonalne)
        required = {
            "Obszar / System":         entry_area.get().strip(),
            "Podsystem":               entry_subsystem.get().strip(),
            "Podsystem funkcjonalny":  entry_func_subsystem.get().strip(),
            "Zmiana":                  entry_shift.get().strip(),
            "Godzina zgłoszenia":      entry_time_reported.get().strip(),
            "Godzina zakończenia":     entry_time_resolved.get().strip(),
            "Dział":                   entry_department.get().strip(),
            "Kategoria":               entry_category.get().strip(),
            "Typ awarii":              entry_failure_type.get().strip(),
            "Opis awarii":             entry_description.get().strip(),
            "Osoba usuwająca":         entry_resolver.get().strip(),
        }

        missing = [k for k, v in required.items() if not v]
        if missing:
            messagebox.showwarning("Brak danych", f"Uzupełnij pola:\n" + "\n".join(f"- {m}" for m in missing))
            return

        data = {
            "username":               username,
            "obszar_system":          required["Obszar / System"],
            "podsystem":              required["Podsystem"],
            "podsystem_funkcjonalny": required["Podsystem funkcjonalny"],
            "data_zgloszenia":        date_val,
            "zmiana":                 required["Zmiana"],
            "godzina_zgloszenia":     required["Godzina zgłoszenia"],
            "godzina_zakonczenia":    required["Godzina zakończenia"],
            "czas_awarii":            downtime_int,
            "dzial":                  required["Dział"],
            "kategoria_awarii":       required["Kategoria"],
            "awaria_jaka":            required["Typ awarii"],
            "opis_awarii":            required["Opis awarii"],
            "osoba_niwelujaca":       required["Osoba usuwająca"],
            "uzyta_czesc":            entry_used_part.get().strip(),
        }

        try:
            success = db_utils.add_failure(data)
            if success:
                messagebox.showinfo("Sukces", "Awaria została zgłoszona.")
                on_close()
            else:
                messagebox.showerror("Błąd", "Nie udało się zapisać awarii.\nSprawdź logi konsoli.")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nieoczekiwany błąd:\n{e}")

    # --- Przyciski ---
    btn_frame = ctk.CTkFrame(win, fg_color="transparent")
    btn_frame.pack(pady=15, padx=20, fill="x")

    ctk.CTkButton(
        btn_frame,
        text="Zgłoś awarię",
        font=ctk.CTkFont(size=15, weight="bold"),
        fg_color="#EF4444",
        hover_color="#DC2626",
        height=45,
        command=submit
    ).pack(side="left", expand=True, fill="x", padx=(0, 10))

    ctk.CTkButton(
        btn_frame,
        text="Anuluj",
        fg_color="#555",
        hover_color="#444",
        height=45,
        command=on_close
    ).pack(side="left", expand=True, fill="x", padx=(10, 0))