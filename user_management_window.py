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

        # --- STYL TABELI ---
        style = ttk.Style()
        style.theme_use("default")

        style.configure("Treeview",
                        background="#2b2b2b",
                        foreground="white",
                        fieldbackground="#2b2b2b",
                        rowheight=30)

        style.map('Treeview', background=[('selected', '#1f6aa5')])

        style.configure("Treeview.Heading",
                        background="#1a1a1a",
                        foreground="white")

        # --- GUI ---
        ctk.CTkLabel(self.window, text="Zarządzanie Stawkami Pracowników",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=20)

        self.frame = ctk.CTkFrame(self.window)
        self.frame.pack(fill="both", expand=True, padx=20, pady=10)

        columns = ("ID", "Użytkownik", "Stawka")
        self.tree = ttk.Treeview(self.frame, columns=columns, show="headings")

        self.tree.heading("ID", text="ID")
        self.tree.heading("Użytkownik", text="Login")
        self.tree.heading("Stawka", text="PLN/h")

        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Użytkownik", width=200, anchor="center")
        self.tree.column("Stawka", width=150, anchor="center")

        scrollbar = ctk.CTkScrollbar(self.frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        edit_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        edit_frame.pack(pady=20)

        ctk.CTkLabel(edit_frame, text="Nowa stawka:").pack(side="left", padx=10)

        self.rate_entry = ctk.CTkEntry(edit_frame, width=100)
        self.rate_entry.pack(side="left", padx=10)

        ctk.CTkButton(edit_frame, text="Zapisz", command=self.update_rate,
                      fg_color="green").pack(side="left", padx=10)

        self.load_users()
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def load_users(self):
        try:
            for row in self.tree.get_children():
                self.tree.delete(row)

            users = db_utils.get_all_users()

            if not users:
                return

            for user_id, name, rate in users:
                rate = float(rate) if rate else 0.0
                self.tree.insert("", "end", values=(user_id, name, f"{rate:.2f}"))

        except Exception as e:
            print("❌ Błąd ładowania użytkowników:", e)
            messagebox.showerror("Błąd", "Nie udało się pobrać użytkowników")

    def on_select(self, event):
        selected = self.tree.focus()
        if selected:
            values = self.tree.item(selected, "values")
            self.rate_entry.delete(0, "end")
            self.rate_entry.insert(0, values[2])

    def update_rate(self):
        selected = self.tree.focus()

        if not selected:
            messagebox.showwarning("Błąd", "Wybierz użytkownika")
            return

        user_id, username, _ = self.tree.item(selected, "values")

        try:
            val = self.rate_entry.get().replace(",", ".")
            new_rate = float(val)

            if new_rate < 0:
                messagebox.showerror("Błąd", "Stawka nie może być ujemna")
                return

            db_utils.update_user_rate(user_id, new_rate)

            messagebox.showinfo("Sukces", f"{username}: {new_rate:.2f} PLN/h")
            self.load_users()
            self.rate_entry.delete(0, "end")

        except ValueError:
            messagebox.showerror("Błąd", "Podaj poprawną liczbę (np. 25.50)")
        except Exception as e:
            print("❌ Błąd zapisu stawki:", e)
            messagebox.showerror("Błąd", "Nie udało się zapisać")

    def on_close(self):
        self.window.destroy()
        self.back_callback()


def show_user_management(username, back_callback):
    UserManagementWindow(username, back_callback)