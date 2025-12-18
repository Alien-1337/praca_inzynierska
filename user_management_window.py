import customtkinter as ctk
from tkinter import messagebox, ttk
import db_utils


class UserManagementWindow:
    def __init__(self, username, back_callback):
        self.username = username
        self.back_callback = back_callback

        self.window = ctk.CTkToplevel()
        self.window.title("Zarządzanie Użytkownikami")
        self.window.geometry("700x550")
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        ctk.set_appearance_mode("dark")

        # --- KONFIGURACJA STYLU TABELI (WAŻNE DLA DARK MODE) ---
        style = ttk.Style()
        style.theme_use("default")

        # Kolory tabeli: Ciemne tło, biały tekst
        style.configure("Treeview",
                        background="#2b2b2b",
                        foreground="white",
                        fieldbackground="#2b2b2b",
                        rowheight=30,
                        font=("Arial", 12))

        # Kolor zaznaczonego wiersza
        style.map('Treeview', background=[('selected', '#1f6aa5')])

        # Nagłówki tabeli
        style.configure("Treeview.Heading",
                        background="#1a1a1a",
                        foreground="white",
                        font=("Arial", 12, "bold"))

        # --- GUI ---

        # Nagłówek okna
        ctk.CTkLabel(self.window, text="Zarządzanie Stawkami Pracowników",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=20)

        # Kontener na tabelę
        self.frame = ctk.CTkFrame(self.window, corner_radius=10)
        self.frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Drzewo użytkowników
        columns = ("ID", "Użytkownik", "Stawka (PLN/h)")
        self.tree = ttk.Treeview(self.frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("ID", text="ID")
        self.tree.column("ID", width=50, anchor="center")

        self.tree.heading("Użytkownik", text="Login")
        self.tree.column("Użytkownik", width=200, anchor="center")

        self.tree.heading("Stawka (PLN/h)", text="Stawka (PLN/h)")
        self.tree.column("Stawka (PLN/h)", width=150, anchor="center")

        # Pasek przewijania (Scrollbar)
        scrollbar = ctk.CTkScrollbar(self.frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # Panel edycji
        edit_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        edit_frame.pack(pady=20)

        ctk.CTkLabel(edit_frame, text="Zmień stawkę dla zaznaczonego:").pack(side="left", padx=10)

        self.rate_entry = ctk.CTkEntry(edit_frame, width=100, placeholder_text="0.0")
        self.rate_entry.pack(side="left", padx=10)

        btn_update = ctk.CTkButton(edit_frame, text="Zapisz Zmianę", command=self.update_rate, fg_color="green")
        btn_update.pack(side="left", padx=10)

        # Załaduj dane przy starcie
        self.load_users()

        # Obsługa kliknięcia w tabelę (żeby wpisać obecną stawkę w pole edycji)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def load_users(self):
        # Czyścimy tabelę
        for row in self.tree.get_children():
            self.tree.delete(row)

        try:
            # Pobieramy dane z bazy
            users = db_utils.get_all_users()  # (id, username, hourly_rate)

            if not users:
                # Jeśli pusto, ale nie ma błędu
                return

            for u in users:
                # Formatowanie stawki do 2 miejsc po przecinku
                user_id, name, rate = u
                formatted_rate = f"{float(rate):.2f}"
                self.tree.insert("", "end", values=(user_id, name, formatted_rate))

        except AttributeError:
            messagebox.showerror("Błąd Bazy", "Brak funkcji 'get_all_users' w db_utils.py!")
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def on_select(self, event):
        """Wpisuje stawkę klikniętego użytkownika w pole edycji."""
        selected = self.tree.focus()
        if selected:
            values = self.tree.item(selected, "values")
            # values[2] to stawka
            self.rate_entry.delete(0, "end")
            self.rate_entry.insert(0, values[2])

    def update_rate(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Błąd", "Najpierw kliknij użytkownika na liście.")
            return

        values = self.tree.item(selected, "values")
        user_id = values[0]
        username = values[1]

        try:
            # Zamiana przecinka na kropkę
            val_str = self.rate_entry.get().replace(",", ".")
            new_rate = float(val_str)

            # Aktualizacja w bazie
            db_utils.update_user_rate(user_id, new_rate)

            messagebox.showinfo("Sukces", f"Zaktualizowano stawkę dla {username} na {new_rate:.2f} PLN/h")
            self.load_users()
            self.rate_entry.delete(0, "end")

        except ValueError:
            messagebox.showerror("Błąd", "Stawka musi być liczbą (np. 25.50)!")
        except AttributeError:
            messagebox.showerror("Błąd", "Brak funkcji 'update_user_rate' w db_utils!")

    def on_close(self):
        self.window.destroy()
        self.back_callback()


def show_user_management(username, back_callback):
    UserManagementWindow(username, back_callback)
