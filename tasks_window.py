import customtkinter as ctk
from tkcalendar import DateEntry
from tkinter import ttk, messagebox
import db_utils


class TasksWindow:
    def __init__(self, username, back_callback):
        self.username = username
        self.back_callback = back_callback

        self.window = ctk.CTkToplevel()
        self.window.title("Zadania TPM")
        self.window.geometry("1200x700")
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        header = ctk.CTkLabel(
            self.window,
            text=f"Zadania TPM – Użytkownik: {self.username}",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white"
        )
        header.pack(pady=20)

        tree_frame = ctk.CTkFrame(self.window)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=10)

        columns = ("Data", "Interwał", "Dzial", "Typ", "Opis")
        self.treeview = ttk.Treeview(tree_frame, columns=columns, show="headings")

        for col, w in zip(columns, [100, 100, 150, 150, 400]):
            self.treeview.heading(col, text=col)
            self.treeview.column(col, width=w, anchor="center" if col != "Opis" else "w")

        self.treeview.pack(fill="both", expand=True, pady=10, padx=10)

        btn_frame = ctk.CTkFrame(self.window)
        btn_frame.pack(pady=15)

        ctk.CTkButton(btn_frame, text="Dodaj zadanie", width=180, height=50,
                      command=self.add_task).grid(row=0, column=0, padx=15)

        ctk.CTkButton(btn_frame, text="Edytuj zadanie", width=180, height=50,
                      command=self.edit_task).grid(row=0, column=1, padx=15)

        self.load_tasks()

    def load_tasks(self):
        try:
            for row in self.treeview.get_children():
                self.treeview.delete(row)

            self.current_tasks_data = db_utils.get_tpm_tasks()

            for task in self.current_tasks_data:
                self.treeview.insert("", "end", iid=task[0],
                                     values=(task[1], task[2], task[3], task[4], task[5]))
        except Exception as e:
            print("❌ Błąd ładowania zadań:", e)
            messagebox.showerror("Błąd", "Nie udało się pobrać danych")

    def add_task(self):
        self.task_editor()

    def edit_task(self):
        selected = self.treeview.focus()
        if not selected:
            messagebox.showwarning("Brak wyboru", "Wybierz zadanie")
            return

        values = self.treeview.item(selected, 'values')
        self.task_editor((selected,) + values)

    def task_editor(self, values=None):
        editor = ctk.CTkToplevel(self.window)
        editor.title("Edytuj zadanie" if values else "Dodaj zadanie")
        editor.geometry("600x600")
        editor.grab_set()

        form = ctk.CTkFrame(editor)
        form.pack(padx=20, pady=20, fill="both", expand=True)

        self.entries = {}

        # Data
        ctk.CTkLabel(form, text="Data:").grid(row=0, column=0)
        date_entry = DateEntry(form, date_pattern='yyyy-mm-dd')
        date_entry.grid(row=0, column=1)
        self.entries["Data"] = date_entry

        # Interwał
        int_num = ctk.CTkEntry(form, width=60)
        int_unit = ctk.CTkComboBox(form, values=["Dni", "Tygodnie", "Miesiące", "Lata"])

        int_num.grid(row=1, column=1, sticky="w")
        int_unit.grid(row=1, column=1, sticky="e")

        self.entries["IntervalNum"] = int_num
        self.entries["IntervalUnit"] = int_unit

        # Dział
        field = ctk.CTkComboBox(form, values=["mechanik", "elektryk", "automatyk"])
        field.grid(row=2, column=1)
        self.entries["Dzial"] = field

        # Typ
        typ = ctk.CTkEntry(form)
        typ.grid(row=3, column=1)
        self.entries["Typ"] = typ

        # Opis
        desc = ctk.CTkTextbox(form, height=100)
        desc.grid(row=4, column=1)
        self.entries["Opis"] = desc

        if values:
            self.entries["Data"].set_date(values[1])

            try:
                num, unit = values[2].split(' ', 1)
                int_num.insert(0, num)
                int_unit.set(unit)
            except:
                pass

            field.set(values[3])
            typ.insert(0, values[4])
            desc.insert("0.0", values[5])

        ctk.CTkButton(editor, text="Zapisz",
                      command=lambda: self.save_task(editor, values)).pack(pady=20)

    def save_task(self, editor, values=None):
        try:
            date_val = self.entries["Data"].get()

            num = self.entries["IntervalNum"].get()
            unit = self.entries["IntervalUnit"].get()

            if not num.isdigit():
                messagebox.showerror("Błąd", "Interwał musi być liczbą")
                return

            interval = f"{num} {unit}"

            field = self.entries["Dzial"].get()
            typ = self.entries["Typ"].get()
            desc = self.entries["Opis"].get("0.0", "end").strip()

            if not (date_val and field and typ and desc):
                messagebox.showerror("Błąd", "Wszystkie pola wymagane")
                return

            if values:
                db_utils.update_tpm_task(values[0], date_val, interval, field, typ, desc)
            else:
                db_utils.add_tpm_task(date_val, interval, field, typ, desc)

            editor.destroy()
            self.load_tasks()

        except Exception as e:
            print("❌ Błąd zapisu:", e)
            messagebox.showerror("Błąd", "Nie udało się zapisać")

    def on_close(self):
        self.window.destroy()
        self.back_callback()


def show_tasks_window(username, back_callback):
    TasksWindow(username, back_callback)