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

        ctk.CTkButton(btn_frame, text="🔙 Powrót", width=180, height=50,
                      fg_color="#555", hover_color="#444",
                      command=self.on_close).grid(row=0, column=2, padx=15)

        self.load_tasks()

    def load_tasks(self):
        try:
            for row in self.treeview.get_children():
                self.treeview.delete(row)

            self.current_tasks_data = db_utils.get_tpm_tasks()

            for task in self.current_tasks_data:
                date_str = str(task[1]) if task[1] is not None else ""
                self.treeview.insert("", "end", iid=task[0],
                                     values=(date_str, task[2], task[3], task[4], task[5]))
        except Exception as e:
            print("❌ Błąd ładowania zadań:", e)
            messagebox.showerror("Błąd", "Nie udało się pobrać danych")

    def add_task(self):
        self.task_editor()

    def edit_task(self):
        selected = self.treeview.focus()
        if not selected:
            messagebox.showwarning("Brak wyboru", "Wybierz zadanie do edycji")
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

        entries = {}

        labels = ["Data:", "Interwał:", "Dział:", "Typ:", "Opis:"]
        for i, label_text in enumerate(labels):
            ctk.CTkLabel(form, text=label_text).grid(row=i, column=0, padx=10, pady=8, sticky="e")

        # Data
        date_entry = DateEntry(form, date_pattern='yyyy-mm-dd')
        date_entry.grid(row=0, column=1, sticky="w", pady=8)
        entries["Data"] = date_entry

        # Interwał
        interval_frame = ctk.CTkFrame(form, fg_color="transparent")
        interval_frame.grid(row=1, column=1, sticky="w", pady=8)

        int_num = ctk.CTkEntry(interval_frame, width=60)
        int_num.pack(side="left", padx=(0, 5))

        int_unit = ctk.CTkComboBox(interval_frame, values=["Dni", "Tygodnie", "Miesiące", "Lata"], width=130)
        int_unit.pack(side="left")

        entries["IntervalNum"] = int_num
        entries["IntervalUnit"] = int_unit

        # Dział
        field = ctk.CTkComboBox(form, values=["mechanik", "elektryk", "automatyk"])
        field.grid(row=2, column=1, sticky="w", pady=8)
        entries["Dzial"] = field

        # Typ
        typ = ctk.CTkEntry(form)
        typ.grid(row=3, column=1, sticky="w", pady=8)
        entries["Typ"] = typ

        # Opis
        desc = ctk.CTkTextbox(form, height=100)
        desc.grid(row=4, column=1, sticky="w", pady=8)
        entries["Opis"] = desc

        if values:
            try:
                entries["Data"].set_date(values[1])
            except Exception as e:
                print(f"⚠️ Nie udało się ustawić daty: {e}")

            try:
                num, unit = values[2].split(' ', 1)
                int_num.insert(0, num)
                int_unit.set(unit)
            except ValueError:
                print(f"⚠️ Nie udało się sparsować interwału: '{values[2]}'")

            field.set(values[3])
            typ.insert(0, values[4])
            desc.insert("0.0", values[5])

        ctk.CTkButton(
            editor, text="Zapisz",
            command=lambda: self.save_task(editor, entries, values)
        ).pack(pady=20)

    def save_task(self, editor, entries, values=None):
        try:
            date_val = str(entries["Data"].get())

            num = entries["IntervalNum"].get().strip()
            unit = entries["IntervalUnit"].get()

            if not num.isdigit():
                messagebox.showerror("Błąd", "Interwał musi być liczbą całkowitą")
                return

            interval = f"{num} {unit}"

            field = entries["Dzial"].get()
            typ = entries["Typ"].get().strip()
            desc = entries["Opis"].get("0.0", "end").strip()

            if not all([date_val, field, typ, desc]):
                messagebox.showerror("Błąd", "Wszystkie pola są wymagane")
                return

            if values:
                db_utils.update_tpm_task(values[0], date_val, interval, field, typ, desc)
            else:
                db_utils.add_tpm_task(date_val, interval, field, typ, desc)

            editor.destroy()
            self.load_tasks()

        except Exception as e:
            print("❌ Błąd zapisu:", e)
            messagebox.showerror("Błąd", f"Nie udało się zapisać:\n{e}")

    def on_close(self):
        self.window.destroy()
        self.back_callback()


def show_tasks_window(username, back_callback):
    TasksWindow(username, back_callback)