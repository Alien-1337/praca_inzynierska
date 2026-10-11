import customtkinter as ctk
from tkinter import messagebox, ttk
import db_utils
import permissions


class UserManagementWindow:
    def __init__(self, username, back_callback):
        self.username = username
        self.back_callback = back_callback

        self.window = ctk.CTkToplevel()
        self.window.title("Zarządzanie Użytkownikami")
        self.window.geometry("800x780")
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
        ctk.CTkLabel(self.window, text="Zarządzanie Stawkami i Rolami Pracowników",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=20)

        self.frame = ctk.CTkFrame(self.window)
        self.frame.pack(fill="both", expand=True, padx=20, pady=10)

        columns = ("ID", "Użytkownik", "Rola", "Stawka")
        self.tree = ttk.Treeview(self.frame, columns=columns, show="headings")

        self.tree.heading("ID", text="ID")
        self.tree.heading("Użytkownik", text="Login")
        self.tree.heading("Rola", text="Rola")
        self.tree.heading("Stawka", text="PLN/h")

        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Użytkownik", width=200, anchor="center")
        self.tree.column("Rola", width=170, anchor="center")
        self.tree.column("Stawka", width=120, anchor="center")

        scrollbar = ctk.CTkScrollbar(self.frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # --- Zmiana stawki ---
        edit_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        edit_frame.pack(pady=(15, 5))

        ctk.CTkLabel(edit_frame, text="Nowa stawka:", width=100, anchor="e").pack(side="left", padx=10)

        self.rate_entry = ctk.CTkEntry(edit_frame, width=100)
        self.rate_entry.pack(side="left", padx=10)

        ctk.CTkButton(edit_frame, text="Zapisz stawkę", command=self.update_rate,
                      fg_color="green", width=140).pack(side="left", padx=10)

        # --- Zmiana roli ---
        role_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        role_frame.pack(pady=(5, 10))

        ctk.CTkLabel(role_frame, text="Rola:", width=100, anchor="e").pack(side="left", padx=10)

        self.role_box = ctk.CTkComboBox(role_frame, values=list(permissions.ALL_ROLES),
                                        width=100 + 70, state="readonly")
        self.role_box.set(permissions.DEFAULT_ROLE)
        self.role_box.pack(side="left", padx=10)

        ctk.CTkButton(role_frame, text="Zmień rolę", command=self.update_role,
                      fg_color="#1f6aa5", width=140).pack(side="left", padx=10)

        # --- Legenda ról ---
        legend = "\n".join(f"• {role} – {permissions.ROLE_DESCRIPTIONS[role]}"
                           for role in permissions.ALL_ROLES)
        ctk.CTkLabel(self.window, text=legend, justify="left", anchor="w",
                     text_color="gray").pack(pady=(0, 20), padx=30, anchor="w")

        self.load_users()
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def load_users(self):
        try:
            for row in self.tree.get_children():
                self.tree.delete(row)

            users = db_utils.get_all_users_with_roles()

            if not users:
                return

            for user_id, name, role, rate in users:
                rate = float(rate) if rate else 0.0
                self.tree.insert("", "end", values=(user_id, name, role, f"{rate:.2f}"))

        except Exception as e:
            print("❌ Błąd ładowania użytkowników:", e)
            messagebox.showerror("Błąd", "Nie udało się pobrać użytkowników")

    def on_select(self, event):
        selected = self.tree.focus()
        if selected:
            values = self.tree.item(selected, "values")
            self.rate_entry.delete(0, "end")
            self.rate_entry.insert(0, values[3])
            self.role_box.set(str(values[2]))

    def update_rate(self):
        selected = self.tree.focus()

        if not selected:
            messagebox.showwarning("Błąd", "Wybierz użytkownika")
            return

        user_id, username, _, _ = self.tree.item(selected, "values")

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

    def update_role(self):
        selected = self.tree.focus()

        if not selected:
            messagebox.showwarning("Błąd", "Wybierz użytkownika")
            return

        user_id, name, old_role, _ = self.tree.item(selected, "values")
        name, old_role = str(name), str(old_role)
        new_role = self.role_box.get()

        if new_role == old_role:
            messagebox.showinfo("Rola", f"{name} ma już rolę {new_role}.")
            return

        if name == self.username and new_role != permissions.ROLE_ADMIN:
            if not messagebox.askyesno(
                "Uwaga",
                "Zmieniasz rolę własnego konta - po zmianie stracisz dostęp do zarządzania "
                "użytkownikami.\n\nKontynuować?"
            ):
                return

        ok, message = db_utils.set_user_role(int(user_id), new_role, self.username)

        if ok:
            messagebox.showinfo("Sukces", message)
        else:
            messagebox.showerror("Błąd", message)

        self.load_users()

    def on_close(self):
        self.window.destroy()
        self.back_callback()


def show_user_management(username, back_callback):
    # Stawki i role może zmieniać tylko Administrator.
    if not db_utils.user_can(username, permissions.FEATURE_USERS):
        messagebox.showerror("Brak uprawnień", "Tylko Administrator może zarządzać użytkownikami.")
        back_callback()
        return

    UserManagementWindow(username, back_callback)
