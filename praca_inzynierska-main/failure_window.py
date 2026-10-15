import customtkinter as ctk
from tkinter import messagebox
import db_utils
import permissions
from datetime import datetime, timedelta

FAILURE_HEADERS = [
    "ID", "Użytkownik", "Obszar", "Podsystem", "Podsystem funkcjonalny",
    "Data", "Zmiana", "Godzina zgłoszenia", "Godzina zakończenia",
    "Czas awarii (min)", "Dział", "Kategoria", "Typ awarii",
    "Opis", "Resolver", "Użyta część",
    "Koszt robocizny", "Koszt części", "Koszt całkowity", "Status"
]

# Co widzi w historii osoba bez prawa do rozwiązywania awarii (np. Użytkownik):
# tylko własne zgłoszenia i bez danych o naprawie oraz kosztach.
USER_VISIBLE_HEADERS = {
    "ID", "Obszar", "Podsystem", "Podsystem funkcjonalny", "Data", "Zmiana",
    "Godzina zgłoszenia", "Dział", "Kategoria", "Typ awarii", "Opis", "Status"
}

# Tryby formularza
MODE_REPORT = "report"  # samo zgłoszenie, bez naprawy (Użytkownik, Administrator)
MODE_FULL = "full"      # zapis awarii już naprawionej (Technik, Administrator)


class FailureWindow(ctk.CTkToplevel):
    def __init__(self, username, return_callback, mode=MODE_REPORT):
        super().__init__()
        self.return_callback = return_callback
        self.username = username
        self.mode = mode
        full = (mode == MODE_FULL)

        # Kto może rozwiązywać awarie, widzi całą historię; pozostali - tylko swoje zgłoszenia.
        self.sees_all = db_utils.user_can(username, permissions.FEATURE_FAILURE_RESOLVE)

        self.title("Zapis zakończonej awarii - CMMS" if full else "Zgłoszenie awarii - CMMS")
        self.geometry("1200x850")
        self.resizable(False, False)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.back_to_menu)

        # --- INVENTORY (część zużyta przy naprawie - tylko w trybie pełnym) ---
        self.inventory_cache = []
        part_display_list = [""]

        if full:
            try:
                self.inventory_cache = db_utils.get_inventory_items()
                for item in self.inventory_cache:
                    part_display_list.append(f"{item[1]} | SAP: {item[2]}")
            except Exception as e:
                print(f"⚠️ Błąd ładowania magazynu: {e}")

        # --- UI ---
        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=1150, height=700, corner_radius=15)
        self.scrollable_frame.pack(pady=20, padx=20)

        if not full:
            ctk.CTkLabel(
                self.scrollable_frame,
                text="Opisz usterkę. Technik zajmie się nią w module „Rozwiązywanie awarii”.",
                text_color="#9CA3AF", anchor="w"
            ).pack(fill="x", padx=10, pady=(5, 0))

        # Pola zgłoszenia (wspólne) + pola naprawy (tylko tryb pełny), w kolejności jak w formularzu
        self.fields = {
            "Obszar systemu":                  ctk.CTkEntry(self.scrollable_frame),
            "Podsystem":                       ctk.CTkEntry(self.scrollable_frame),
            "Podsystem funkcjonalny":          ctk.CTkEntry(self.scrollable_frame),
            "Data zgłoszenia (YYYY-MM-DD)":    ctk.CTkEntry(self.scrollable_frame),
            "Zmiana":                          ctk.CTkComboBox(self.scrollable_frame, values=["1", "2", "3"]),
            "Godzina zgłoszenia (HH:MM)":      ctk.CTkEntry(self.scrollable_frame),
        }
        if full:
            self.fields["Godzina zakończenia (HH:MM)"] = ctk.CTkEntry(self.scrollable_frame)
            self.fields["Czas awarii (minuty)"] = ctk.CTkEntry(self.scrollable_frame)

        self.fields["Dział"] = ctk.CTkComboBox(
            self.scrollable_frame, values=["Utrzymanie ruchu", "IT", "Produkcja", "Logistyka"])
        self.fields["Kategoria awarii"] = ctk.CTkComboBox(
            self.scrollable_frame, values=["Mechaniczna", "Elektryczna", "Programowa", "Inna"])
        self.fields["Typ awarii"] = ctk.CTkComboBox(
            self.scrollable_frame,
            values=["Błąd czujnika", "Uszkodzenie silnika", "Brak zasilania", "Zawieszenie systemu"])
        if full:
            self.fields["Zużyta część (opcjonalne)"] = ctk.CTkComboBox(
                self.scrollable_frame, values=part_display_list)
        self.fields["Opis awarii"] = ctk.CTkTextbox(self.scrollable_frame, height=120)

        # --- DEFAULTS ---
        self.fields["Dział"].set("Utrzymanie ruchu")
        self.fields["Kategoria awarii"].set("Mechaniczna")
        self.fields["Typ awarii"].set("Błąd czujnika")
        self.fields["Data zgłoszenia (YYYY-MM-DD)"].insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.fields["Godzina zgłoszenia (HH:MM)"].insert(0, datetime.now().strftime("%H:%M"))
        if full:
            self.fields["Czas awarii (minuty)"].configure(state="disabled")

        # --- RENDER ---
        for label, widget in self.fields.items():
            ctk.CTkLabel(self.scrollable_frame, text=label, text_color="white", anchor="w").pack(
                fill="x", pady=(8, 0), padx=10
            )
            widget.pack(padx=10, fill="x")

        if full:
            self.fields["Godzina zgłoszenia (HH:MM)"].bind("<FocusOut>", self.calculate_downtime)
            self.fields["Godzina zakończenia (HH:MM)"].bind("<FocusOut>", self.calculate_downtime)

        # --- BUTTONS ---
        self.bottom_frame = ctk.CTkFrame(self, fg_color="#2b2b2b")
        self.bottom_frame.pack(pady=10)

        ctk.CTkButton(self.bottom_frame, text="Zapisz awarię" if full else "Zgłoś awarię",
                      command=self.submit_failure, fg_color="#1f6aa5").pack(side="left", padx=10)

        ctk.CTkButton(self.bottom_frame, text="Pokaż historię" if self.sees_all else "Moje zgłoszenia",
                      command=self.show_history, fg_color="#1f6aa5").pack(side="left", padx=10)

        ctk.CTkButton(self.bottom_frame, text="Powrót",
                      fg_color="#6B7280", command=self.back_to_menu).pack(side="left", padx=10)

    def calculate_downtime(self, event=None):
        start = self.fields["Godzina zgłoszenia (HH:MM)"].get().strip()
        end = self.fields["Godzina zakończenia (HH:MM)"].get().strip()

        if not start or not end:
            return

        try:
            fmt = "%H:%M"
            start_dt = datetime.strptime(start, fmt)
            end_dt = datetime.strptime(end, fmt)

            if end_dt < start_dt:
                end_dt += timedelta(days=1)

            diff = int((end_dt - start_dt).total_seconds() / 60)

            self.fields["Czas awarii (minuty)"].configure(state="normal")
            self.fields["Czas awarii (minuty)"].delete(0, "end")
            self.fields["Czas awarii (minuty)"].insert(0, str(diff))
            self.fields["Czas awarii (minuty)"].configure(state="disabled")

        except ValueError:
            # Niepoprawny format godziny — czyścimy pole
            self.fields["Czas awarii (minuty)"].configure(state="normal")
            self.fields["Czas awarii (minuty)"].delete(0, "end")
            self.fields["Czas awarii (minuty)"].configure(state="disabled")

    def submit_failure(self):
        full = (self.mode == MODE_FULL)

        # Walidacja daty
        date_val = self.fields["Data zgłoszenia (YYYY-MM-DD)"].get().strip()
        try:
            datetime.strptime(date_val, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Błąd", "Niepoprawny format daty.\nUżyj formatu: YYYY-MM-DD")
            return

        # Walidacja godziny zgłoszenia - później liczony jest od niej przestój
        try:
            time_reported = datetime.strptime(
                self.fields["Godzina zgłoszenia (HH:MM)"].get().strip(), "%H:%M"
            ).strftime("%H:%M")
        except ValueError:
            messagebox.showerror("Błąd", "Niepoprawny format godziny zgłoszenia.\nUżyj formatu: HH:MM")
            return

        # Walidacja czasu awarii (tylko przy zapisie awarii już naprawionej)
        downtime = None
        if full:
            downtime_val = self.fields["Czas awarii (minuty)"].get().strip()
            if not downtime_val:
                messagebox.showwarning("Błąd", "Najpierw podaj godziny, aby obliczyć czas awarii.")
                return

            try:
                downtime = int(downtime_val)
            except ValueError:
                messagebox.showerror("Błąd", "Czas awarii musi być liczbą całkowitą.")
                return

        # Wymagane pola tekstowe
        required = {
            "Obszar systemu":               self.fields["Obszar systemu"].get().strip(),
            "Podsystem":                    self.fields["Podsystem"].get().strip(),
            "Podsystem funkcjonalny":       self.fields["Podsystem funkcjonalny"].get().strip(),
            "Opis awarii":                  self.fields["Opis awarii"].get("1.0", "end").strip(),
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            messagebox.showwarning("Brak danych",
                                   "Uzupełnij pola:\n" + "\n".join(f"• {m}" for m in missing))
            return

        data = {
            "username":               self.username,
            "obszar_system":          required["Obszar systemu"],
            "podsystem":              required["Podsystem"],
            "podsystem_funkcjonalny": required["Podsystem funkcjonalny"],
            "data_zgloszenia":        date_val,
            "zmiana":                 self.fields["Zmiana"].get(),
            "godzina_zgloszenia":     time_reported,
            "dzial":                  self.fields["Dział"].get(),
            "kategoria_awarii":       self.fields["Kategoria awarii"].get(),
            "awaria_jaka":            self.fields["Typ awarii"].get(),
            "opis_awarii":            required["Opis awarii"],
        }

        if full:
            # Parsowanie wybranej części z magazynu
            raw_part = self.fields["Zużyta część (opcjonalne)"].get().strip()
            if " | SAP:" in raw_part:
                final_part_name = raw_part.split(" | SAP:")[0]
            else:
                final_part_name = raw_part

            data.update({
                "godzina_zakonczenia": self.fields["Godzina zakończenia (HH:MM)"].get().strip(),
                "czas_awarii":         downtime,
                "osoba_niwelujaca":    self.username,
                "uzyta_czesc":         final_part_name,
            })

        try:
            if full:
                success = db_utils.add_failure(data)
                ok_message = "Awaria została zapisana."
            else:
                success = db_utils.report_failure(data)
                ok_message = "Awaria została zgłoszona.\nTechnik zajmie się nią w module „Rozwiązywanie awarii”."

            if success:
                messagebox.showinfo("Sukces", ok_message)
                self.back_to_menu()
            else:
                messagebox.showerror("Błąd", "Nie udało się zapisać awarii.\nSprawdź logi konsoli.")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nieoczekiwany błąd podczas zapisu:\n{e}")

    def show_history(self):
        history_window = ctk.CTkToplevel(self)
        history_window.title("Historia Awarii" if self.sees_all else "Moje zgłoszenia")
        history_window.geometry("1100x600")
        history_window.grab_set()

        text = ctk.CTkTextbox(history_window, font=("Consolas", 12), wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)

        try:
            failures = db_utils.get_failure_history(None if self.sees_all else self.username)
        except Exception as e:
            text.insert("end", f"❌ Błąd pobierania historii: {e}")
            return

        if not failures:
            text.insert("end", "Brak danych.")
            return

        for f in failures:
            try:
                lines = [
                    f"{k}: {'—' if v is None else v}"
                    for k, v in zip(FAILURE_HEADERS, f)
                    if self.sees_all or k in USER_VISIBLE_HEADERS
                ]
                text.insert("end", "\n".join(lines) + "\n" + "-" * 60 + "\n")
            except Exception as e:
                text.insert("end", str(f) + "\n" + "-" * 60 + "\n")

    def back_to_menu(self):
        self.destroy()
        if self.return_callback:
            self.return_callback()


def open_failure_window(username, return_callback):
    """Kafelek 'Zgłoszenie Awarii' - formularz samego zgłoszenia (bez naprawy)."""
    FailureWindow(username, return_callback, mode=MODE_REPORT)
