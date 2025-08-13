# tasks_window.py
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

        # Treeview dla tabeli
        self.treeview = ttk.Treeview(tree_frame, columns=("Data", "Dzial", "Typ", "Opis"), show="headings")
        for col in ("Data", "Dzial", "Typ", "Opis"):
            self.treeview.heading(col, text=col, anchor="center")
            self.treeview.column(col, width=250, anchor="center")
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
        for task in db_utils.get_tpm_tasks():
            self.treeview.insert("", "end", values=(task[1], task[2], task[3], task[4]))

    def add_task(self):
        self.task_editor()

    def edit_task(self):
        selected = self.treeview.focus()
        if not selected:
            messagebox.showwarning("Brak wyboru", "Wybierz zadanie do edycji")
            return
        values = self.treeview.item(selected, 'values')
        self.task_editor(values)

    def task_editor(self, values=None):
        editor = ctk.CTkToplevel(self.window)
        editor.title("Edytuj zadanie" if values else "Dodaj zadanie")
        editor.geometry("800x500")
        editor.grab_set()

        title_label = ctk.CTkLabel(
            editor,
            text="Edytuj zadanie" if values else "Dodaj zadanie",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white"
        )
        title_label.pack(pady=(20, 10))

        form_frame = ctk.CTkFrame(editor)
        form_frame.pack(padx=40, pady=10, fill="both", expand=True)

        labels = ["Data przeglądu:", "Dział:", "Typ zadania:", "Opis czynności:"]
        self.entries = {}

        for i, text in enumerate(labels):
            lbl = ctk.CTkLabel(form_frame, text=text, font=ctk.CTkFont(size=16), text_color="white")
            lbl.grid(row=i, column=0, sticky="e", padx=10, pady=10)

            if text == "Data przeglądu:":
                entry = DateEntry(form_frame, width=16, background='darkblue',
                                  foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd', font=("Arial", 14))
            elif text == "Dział:":
                entry = ctk.CTkComboBox(form_frame, values=["mechanik", "elektryk", "automatyk"], width=400,
                                        font=ctk.CTkFont(size=16))
            elif text == "Opis czynności:":
                entry = ctk.CTkTextbox(form_frame, width=400, height=150, font=ctk.CTkFont(size=16))
                entry.configure(wrap="word")
            else:
                entry = ctk.CTkEntry(form_frame, width=400, font=ctk.CTkFont(size=16))
                entry.configure(justify="center")

            entry.grid(row=i, column=1, sticky="w", padx=10, pady=10)
            self.entries[text] = entry

        if values:
            self.entries["Data przeglądu:"].set_date(values[0])
            self.entries["Dział:"].set(values[1])
            self.entries["Typ zadania:"].insert(0, values[2])
            self.entries["Opis czynności:"].insert("0.0", values[3])

        save_btn = ctk.CTkButton(editor, text="Zapisz", width=150, height=50, font=ctk.CTkFont(size=16),
                                 command=lambda: self.save_task(editor, values))
        save_btn.pack(pady=20)

    def save_task(self, editor, values=None):
        date = self.entries["Data przeglądu:"].get()
        field = self.entries["Dział:"].get()
        type_ = self.entries["Typ zadania:"].get()
        desc_widget = self.entries["Opis czynności:"]
        desc = desc_widget.get("0.0", "end").strip()

        if not (date and field and type_ and desc):
            messagebox.showerror("Błąd", "Wszystkie pola muszą być wypełnione")
            return

        if values:
            db_utils.update_tpm_task(values[0], date, field, type_, desc)
        else:
            db_utils.add_tpm_task(date, field, type_, desc)

        editor.destroy()
        self.load_tasks()

    def on_close(self):
        self.window.destroy()
        self.back_callback()


# --- Funkcja wywołująca okno ---
def show_tasks_window(username, back_callback):
    TasksWindow(username, back_callback)
