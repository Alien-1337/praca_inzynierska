import customtkinter as ctk
import tkinter.messagebox
import db_utils
from datetime import datetime, timedelta


class FailureWindow(ctk.CTkToplevel):
    def __init__(self, username, return_callback):
        super().__init__()
        self.return_callback = return_callback
        self.username = username
        self.title("Zgłoszenie awarii - CMMS by RafałS")
        self.geometry("1200x850")
        self.resizable(False, False)

        # 1. Pobieramy części z magazynu i tworzymy "mapę" oraz listę do wyświetlenia
        self.inventory_cache = []  # Przechowujemy dane w pamięci, żeby szukać po SAP
        part_display_list = [""]

        try:
            # Pobiera: (id, name, sap_number, reference_number, quantity, location, price)
            self.inventory_cache = db_utils.get_inventory_items()

            # Tworzymy czytelną listę do wyboru: "Nazwa | SAP: 12345"
            for item in self.inventory_cache:
                name = item[1]
                sap = item[2]
                display_str = f"{name} | SAP: {sap}"
                part_display_list.append(display_str)

        except Exception:
            part_display_list = [""]

        # --- Scrollable Frame ---
        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=1150, height=700, corner_radius=15)
        self.scrollable_frame.pack(pady=20, padx=20)

        # --- Pola formularza ---
        self.fields = {
            "Obszar systemu": ctk.CTkEntry(self.scrollable_frame),
            "Podsystem": ctk.CTkEntry(self.scrollable_frame),
            "Podsystem funkcjonalny": ctk.CTkEntry(self.scrollable_frame),
            "Data zgłoszenia (YYYY-MM-DD)": ctk.CTkEntry(self.scrollable_frame),
            "Zmiana": ctk.CTkComboBox(self.scrollable_frame, values=["1", "2", "3"]),
            "Godzina zgłoszenia (HH:MM)": ctk.CTkEntry(self.scrollable_frame),
            "Godzina zakończenia (HH:MM)": ctk.CTkEntry(self.scrollable_frame),
            "Czas awarii (minuty)": ctk.CTkEntry(self.scrollable_frame),
            "Dział": ctk.CTkComboBox(self.scrollable_frame,
                                     values=["Utrzymanie ruchu", "IT", "Produkcja", "Logistyka"]),
            "Kategoria awarii": ctk.CTkComboBox(self.scrollable_frame,
                                                values=["Mechaniczna", "Elektryczna", "Programowa", "Inna"]),
            "Typ awarii": ctk.CTkComboBox(self.scrollable_frame,
                                          values=["Błąd czujnika", "Uszkodzenie silnika", "Brak zasilania",
                                                  "Zawieszenie systemu"]),

            # ZMIANA: Lista zawiera teraz Nazwę i SAP. Użytkownik może wpisać cokolwiek.
            "Zużyta część (opcjonalne)": ctk.CTkComboBox(self.scrollable_frame, values=part_display_list),

            "Opis awarii": ctk.CTkTextbox(self.scrollable_frame, height=120),
        }

        # --- Domyślne wartości ---
        self.fields["Dział"].set("Utrzymanie ruchu")
        self.fields["Kategoria awarii"].set("Mechaniczna")
        self.fields["Typ awarii"].set("Błąd czujnika")
        self.fields["Data zgłoszenia (YYYY-MM-DD)"].insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.fields["Godzina zgłoszenia (HH:MM)"].insert(0, datetime.now().strftime("%H:%M"))

        # Czas awarii readonly
        self.fields["Czas awarii (minuty)"].configure(state="disabled")

        # --- Wyświetlanie pól ---
        for label, widget in self.fields.items():
            ctk.CTkLabel(self.scrollable_frame, text=label, text_color="white", anchor="w").pack(
                fill="x", pady=(8, 0), padx=10
            )
            widget.pack(padx=10, fill="x")

        # Bind do liczenia czasu
        self.fields["Godzina zgłoszenia (HH:MM)"].bind("<FocusOut>", self.calculate_downtime)
        self.fields["Godzina zakończenia (HH:MM)"].bind("<FocusOut>", self.calculate_downtime)

        # --- Dolny pasek ---
        self.bottom_frame = ctk.CTkFrame(self, fg_color="#2b2b2b")
        self.bottom_frame.pack(pady=10)

        self.submit_button = ctk.CTkButton(
            self.bottom_frame, text="Zapisz Zgłoszenie", command=self.submit_failure, fg_color="#1f6aa5"
        )
        self.submit_button.pack(side="left", padx=10)

        self.history_button = ctk.CTkButton(
            self.bottom_frame, text="Pokaż historię", command=self.show_history, fg_color="#1f6aa5"
        )
        self.history_button.pack(side="left", padx=10)

        self.back_button = ctk.CTkButton(
            self.bottom_frame, text="Powrót", fg_color="#6B7280", command=self.back_to_menu
        )
        self.back_button.pack(side="left", padx=10)

    def calculate_downtime(self, event=None):
        try:
            start = self.fields["Godzina zgłoszenia (HH:MM)"].get()
            end = self.fields["Godzina zakończenia (HH:MM)"].get()
            if start and end:
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
        except:
            pass

    def submit_failure(self):
        # 1. Pobierz czas awarii
        try:
            downtime = int(self.fields["Czas awarii (minuty)"].get())
        except ValueError:
            tkinter.messagebox.showwarning("Błąd", "Najpierw podaj godziny, aby obliczyć czas awarii.")
            return

        # 2. LOGIKA ROZPOZNAWANIA CZĘŚCI (Nazwa lub SAP)
        raw_input = self.fields["Zużyta część (opcjonalne)"].get().strip()
        final_part_name = ""

        if raw_input:
            # Sytuacja A: Użytkownik wybrał z listy format "Nazwa | SAP: 123"
            if " | SAP:" in raw_input:
                final_part_name = raw_input.split(" | SAP:")[0]

            # Sytuacja B: Użytkownik wpisał ręcznie SAP lub Nazwę
            else:
                found = False
                for item in self.inventory_cache:
                    db_name = item[1]  # Nazwa
                    db_sap = item[2]  # SAP

                    # Sprawdzamy czy wpisane tekst to SAP lub Nazwa
                    if raw_input == db_sap or raw_input.lower() == db_name.lower():
                        final_part_name = db_name  # Zawsze zamieniamy na nazwę, żeby baza policzyła cenę
                        found = True
                        break

                if not found:
                    # Jeśli nie znaleziono w bazie, zapisujemy to co wpisał (cena będzie 0)
                    final_part_name = raw_input

        # 3. Przygotowujemy dane
        data = {
            "username": self.username,
            "obszar_system": self.fields["Obszar systemu"].get(),
            "podsystem": self.fields["Podsystem"].get(),
            "podsystem_funkcjonalny": self.fields["Podsystem funkcjonalny"].get(),
            "data_zgloszenia": self.fields["Data zgłoszenia (YYYY-MM-DD)"].get(),
            "zmiana": self.fields["Zmiana"].get(),
            "godzina_zgloszenia": self.fields["Godzina zgłoszenia (HH:MM)"].get(),
            "godzina_zakonczenia": self.fields["Godzina zakończenia (HH:MM)"].get(),
            "czas_awarii": downtime,
            "dzial": self.fields["Dział"].get(),
            "kategoria_awarii": self.fields["Kategoria awarii"].get(),
            "awaria_jaka": self.fields["Typ awarii"].get(),
            "opis_awarii": self.fields["Opis awarii"].get("0.0", "end").strip(),
            "osoba_niwelujaca": self.username,

            # Przekazujemy "czystą" nazwę części (nawet jeśli wpisano SAP)
            "uzyta_czesc": final_part_name
        }

        db_utils.add_failure(data)
        tkinter.messagebox.showinfo("Sukces", "Awaria została zapisana.")
        self.destroy()
        if self.return_callback:
            self.return_callback()

    def show_history(self):
        history_window = ctk.CTkToplevel(self)
        history_window.title("Historia Awarii")
        history_window.geometry("1100x600")

        failures = db_utils.get_failure_history()
        text = ctk.CTkTextbox(history_window, font=("Consolas", 12), wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)

        if not failures:
            text.insert("end", "Brak danych.")
        else:
            for f in failures:
                try:
                    headers = db_utils.FAILURE_HEADERS
                    entry_lines = []
                    for k, v in zip(headers, f[1:]):
                        entry_lines.append(f"{k}: {v}")

                    entry = "\n".join(entry_lines)
                    text.insert("end", entry + "\n" + "-" * 60 + "\n")
                except Exception:
                    text.insert("end", str(f) + "\n" + "-" * 60 + "\n")

    def back_to_menu(self):
        self.destroy()
        if self.return_callback:
            self.return_callback()


def open_failure_window(username, return_callback):
    window = FailureWindow(username, return_callback)
    window.grab_set()
