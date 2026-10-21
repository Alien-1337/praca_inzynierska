import customtkinter as ctk
from tkinter import messagebox
from tasks_window import show_tasks_window
from failure_window import open_failure_window as show_failure_window
from failure_resolve_window import show_failure_resolve_window
from inventory_window import show_inventory_window
from accept_tpm_window import show_accept_window
from user_management_window import show_user_management
from Analytics import show_analytics_window
from tpm_module import print_tpm
import login_window
import db_utils
import permissions

COLUMNS = 3
TILE_WIDTH = 340
TILE_HEIGHT = 170


def show_main_menu(username, role=None):
    if role is None:
        role = db_utils.get_user_role(username)

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    window = ctk.CTk()
    window.title(f"Panel główny - CMMS ({username}, {role or 'brak roli'})")
    window.geometry("1920x1080")
    window.state("zoomed")

    header = ctk.CTkLabel(
        window,
        text=f"CMMS - Witaj, {username}",
        font=ctk.CTkFont(size=28, weight="bold"),
        text_color="#f5f5f5"
    )
    header.pack(pady=(20, 0))

    role_label = ctk.CTkLabel(
        window,
        text=f"Rola: {role}" if role else "Nie udało się ustalić roli konta - skontaktuj się z administratorem",
        font=ctk.CTkFont(size=16),
        text_color="#9CA3AF" if role else "#F59E0B"
    )
    role_label.pack(pady=(0, 10))

    grid = ctk.CTkFrame(window, fg_color="transparent")
    grid.pack(expand=True)

    def create_tile(parent, title, desc, color, command, row, col):
        frame = ctk.CTkFrame(parent, corner_radius=20, fg_color=color, width=TILE_WIDTH, height=TILE_HEIGHT)
        frame.grid(row=row, column=col, padx=25, pady=25)

        label_title = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=22, weight="bold"),
                                   text_color="white")
        label_title.place(relx=0.5, rely=0.42, anchor="center")

        label_desc = ctk.CTkLabel(frame, text=desc, font=ctk.CTkFont(size=14), text_color="white",
                                  wraplength=TILE_WIDTH - 40)
        label_desc.place(relx=0.5, rely=0.64, anchor="center")

        def on_click(event=None):
            try:
                command()
            except Exception as e:
                print(f"Błąd w kafelku '{title}': {e}")

        for widget in (frame, label_title, label_desc):
            widget.bind("<Button-1>", on_click)

    def open_subwindow(func):
        try:
            window.withdraw()
            func(username, lambda: window.deiconify())
        except Exception as e:
            print("Błąd otwierania okna:", e)
            window.deiconify()

    def guarded(feature, action):
        # rolę czytamy z bazy przy każdym otwarciu, więc zmiana roli działa od razu
        def run():
            if not permissions.can(db_utils.get_user_role(username), feature):
                messagebox.showerror(
                    "Brak uprawnień",
                    "Twoja rola nie ma dostępu do tej funkcji.\n"
                    "Jeśli rola została niedawno zmieniona, zaloguj się ponownie."
                )
                return
            action()
        return run

    def logout():
        window.destroy()
        login_window.show_login_window()

    # kafelek jest widoczny tylko dla ról, które mają daną funkcję w permissions.py
    # (funkcja None oznacza kafelek dla wszystkich)
    tiles = [
        (permissions.FEATURE_TPM_TASKS, "Zadania", "Edytuj definicje zadań", "#3B82F6",
         lambda: open_subwindow(show_tasks_window)),
        (permissions.FEATURE_TPM_PRINT, "Drukowanie TPM", "Drukuj listę zadań", "#10B981",
         print_tpm),
        (permissions.FEATURE_FAILURE_REPORT, "Zgłoszenie Awarii", "Rejestracja usterek i przestojów", "#EF4444",
         lambda: open_subwindow(show_failure_window)),
        (permissions.FEATURE_FAILURE_RESOLVE, "Rozwiązywanie Awarii", "Naprawy i stan zgłoszeń", "#EC4899",
         lambda: open_subwindow(show_failure_resolve_window)),
        (permissions.FEATURE_INVENTORY, "Magazyn", "Podgląd części", "#F59E0B",
         lambda: open_subwindow(show_inventory_window)),
        (permissions.FEATURE_ANALYTICS, "Statystyki", "Raporty i analizy", "#8B5CF6",
         lambda: open_subwindow(show_analytics_window)),
        (permissions.FEATURE_TPM_ACCEPT, "Zatwierdź TPM", "Odhacz wykonane zadania", "#059669",
         lambda: open_subwindow(show_accept_window)),
        (permissions.FEATURE_USERS, "Użytkownicy", "Stawki i uprawnienia", "#6366F1",
         lambda: open_subwindow(show_user_management)),
        (None, "Wyloguj", "Zakończ pracę", "#6B7280",
         lambda: window.after(0, logout)),
    ]

    visible = [t for t in tiles if t[0] is None or permissions.can(role, t[0])]

    for index, (feature, title, desc, color, action) in enumerate(visible):
        command = action if feature is None else guarded(feature, action)
        create_tile(grid, title, desc, color, command, index // COLUMNS, index % COLUMNS)

    window.mainloop()
