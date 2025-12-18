import customtkinter as ctk
from tkcalendar import DateEntry
from tkinter import ttk, messagebox
import db_utils


class TasksWindow:
    def __init__(self, username, back_callback):
        self.username = username
        self.back_callback = back_callback

        # --- Główne okno ---
        self.window = ctk.CTkToplevel()
        self.window.title("Zadania TPM")
        self.window.geometry("1200x700")
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # --- Nagłówek ---
        header = ctk.CTkLabel(
            self.window,
            text=f"Zadania TPM – Użytkownik: {self.username}",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white"
        )
        header.pack(pady=20)

        # --- Ramka z tabelą ---
        tree_frame = ctk.CTkFrame(self.window)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Treeview dla tabeli - DODANO KOLUMNĘ INTERWAŁ
        columns = ("Data", "Interwał", "Dzial", "Typ", "Opis")
        self.treeview = ttk.Treeview(tree_frame, columns=columns, show="headings")

        self.treeview.heading("Data", text="Data Startu")
        self.treeview.column("Data", width=100, anchor="center")

        self.treeview.heading("Interwał", text="Interwał")
        self.treeview.column("Interwał", width=100, anchor="center")

        self.treeview.heading("Dzial", text="Dział")
        self.treeview.column("Dzial", width=150, anchor="center")

        self.treeview.heading("Typ", text="Typ")
        self.treeview.column("Typ", width=150, anchor="center")

        self.treeview.heading("Opis", text="Opis")
        self.treeview.column("Opis", width=400, anchor="w")

        self.treeview.pack(fill="both", expand=True, pady=10, padx=10)

        # --- Przyciski ---
        btn_frame = ctk.CTkFrame(self.window)
        btn_frame.pack(pady=15)

        add_btn = ctk.CTkButton(btn_frame, text="Dodaj zadanie", width=180, height=50, font=ctk.CTkFont(size=16),
                                command=self.add_task)
        edit_btn = ctk.CTkButton(btn_frame, text="Edytuj zadanie", width=180, height=50, font=ctk.CTkFont(size=16),
                                 command=self.edit_task)
        add_btn.grid(row=0, column=0, padx=15)
        edit_btn.grid(row=0, column=1, padx=15)

        # --- Załaduj zadania ---
        self.load_tasks()

    def load_tasks(self):
        for row in self.treeview.get_children():
            self.treeview.delete(row)
        # db_utils zwraca: (id, date, interval, field, type, description)
        # Treeview potrzebuje ukrytego ID, ale tu upraszczamy wyświetlanie
        # Przechowujemy ID w ukrytym tagu lub po prostu mapujemy po zaznaczeniu
        # Tutaj insertujemy values widoczne, a ID przekażemy przy edycji w inny sposób
        self.current_tasks_data = db_utils.get_tpm_tasks()  # Cache danych żeby mieć ID
        for task in self.current_tasks_data:
            # task = (id, date, interval, field, type, description)
            self.treeview.insert("", "end", iid=task[0], values=(task[1], task[2], task[3], task[4], task[5]))

    def add_task(self):
        self.task_editor()

    def edit_task(self):
        selected_iid = self.treeview.focus()  # To jest ID z bazy danych (ustawione w iid)
        if not selected_iid:
            messagebox.showwarning("Brak wyboru", "Wybierz zadanie do edycji")
            return

        # Pobieramy wartości z drzewa
        values = self.treeview.item(selected_iid, 'values')
        # values = (Data, Interwał, Dzial, Typ, Opis)
        # Potrzebujemy przekazać też ID (selected_iid)
        full_data = (selected_iid,) + values
        self.task_editor(full_data)

    def task_editor(self, values=None):
        editor = ctk.CTkToplevel(self.window)
        editor.title("Edytuj zadanie" if values else "Dodaj zadanie")
        editor.geometry("600x600")
        editor.grab_set()

        title_label = ctk.CTkLabel(
            editor,
            text="Edytuj zadanie" if values else "Dodaj zadanie",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white"
        )
        title_label.pack(pady=(20, 10))

        form_frame = ctk.CTkFrame(editor)
        form_frame.pack(padx=20, pady=10, fill="both", expand=True)

        self.entries = {}

        # 1. Data
        ctk.CTkLabel(form_frame, text="Data startu:").grid(row=0, column=0, sticky="e", padx=10, pady=10)
        date_entry = DateEntry(form_frame, width=16, background='darkblue', foreground='white', borderwidth=2,
                               date_pattern='yyyy-mm-dd')
        date_entry.grid(row=0, column=1, sticky="w", padx=10, pady=10)
        self.entries["Data"] = date_entry

        # 2. Interwał (Liczba + Jednostka)
        ctk.CTkLabel(form_frame, text="Interwał:").grid(row=1, column=0, sticky="e", padx=10, pady=10)
        interval_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        interval_frame.grid(row=1, column=1, sticky="w", padx=10)

        int_num = ctk.CTkEntry(interval_frame, width=50, justify="center")
        int_num.pack(side="left", padx=(0, 5))
        int_num.insert(0, "1")

        int_unit = ctk.CTkComboBox(interval_frame, values=["Dni", "Tygodnie", "Miesiące", "Lata"], width=120)
        int_unit.pack(side="left")

        self.entries["IntervalNum"] = int_num
        self.entries["IntervalUnit"] = int_unit

        # 3. Dział
        ctk.CTkLabel(form_frame, text="Dział:").grid(row=2, column=0, sticky="e", padx=10, pady=10)
        field_entry = ctk.CTkComboBox(form_frame, values=["mechanik", "elektryk", "automatyk"], width=250)
        field_entry.grid(row=2, column=1, sticky="w", padx=10, pady=10)
        self.entries["Dzial"] = field_entry

        # 4. Typ
        ctk.CTkLabel(form_frame, text="Typ zadania:").grid(row=3, column=0, sticky="e", padx=10, pady=10)
        type_entry = ctk.CTkEntry(form_frame, width=250)
        type_entry.grid(row=3, column=1, sticky="w", padx=10, pady=10)
        self.entries["Typ"] = type_entry

        # 5. Opis
        ctk.CTkLabel(form_frame, text="Opis czynności:").grid(row=4, column=0, sticky="e", padx=10, pady=10)
        desc_entry = ctk.CTkTextbox(form_frame, width=250, height=100)
        desc_entry.grid(row=4, column=1, sticky="w", padx=10, pady=10)
        self.entries["Opis"] = desc_entry

        # Wypełnianie danymi przy edycji
        if values:
            # values = (ID, Data, InterwałString, Dzial, Typ, Opis)
            self.entries["Data"].set_date(values[1])

            # Rozbijanie interwału np. "2 Tygodnie"
            full_int = values[2]
            try:
                num, unit = full_int.split(' ', 1)
                self.entries["IntervalNum"].delete(0, "end")
                self.entries["IntervalNum"].insert(0, num)
                self.entries["IntervalUnit"].set(unit)
            except:
                pass  # Zostaw domyślne

            self.entries["Dzial"].set(values[3])
            self.entries["Typ"].insert(0, values[4])
            self.entries["Opis"].insert("0.0", values[5])

        save_btn = ctk.CTkButton(editor, text="Zapisz", width=150, height=40, font=ctk.CTkFont(size=16),
                                 command=lambda: self.save_task(editor, values))
        save_btn.pack(pady=20)

    def save_task(self, editor, values=None):
        date_val = self.entries["Data"].get()

        # Łączenie interwału
        i_num = self.entries["IntervalNum"].get()
        i_unit = self.entries["IntervalUnit"].get()
        if not i_num.isdigit():
            messagebox.showerror("Błąd", "Interwał musi być liczbą")
            return
        interval_val = f"{i_num} {i_unit}"

        field_val = self.entries["Dzial"].get()
        type_val = self.entries["Typ"].get()
        desc_val = self.entries["Opis"].get("0.0", "end").strip()

        if not (date_val and field_val and type_val and desc_val):
            messagebox.showerror("Błąd", "Wszystkie pola muszą być wypełnione")
            return

        if values:
            # values[0] to ID
            db_utils.update_tpm_task(values[0], date_val, interval_val, field_val, type_val, desc_val)
        else:
            db_utils.add_tpm_task(date_val, interval_val, field_val, type_val, desc_val)

        editor.destroy()
        self.load_tasks()

    def on_close(self):
        self.window.destroy()
        self.back_callback()


def show_tasks_window(username, back_callback):
    TasksWindow(username, back_callback)