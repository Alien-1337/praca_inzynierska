import customtkinter as ctk
from tasks_window import show_tasks_window
from failure_window import open_failure_window as show_failure_window
from inventory_window import show_inventory_window
from tpm_module import print_tpm
import login_window

try:
    from Analytics import show_analytics_window
except ImportError:
    def show_analytics_window(u, b):
        print("Brak pliku Analytics.py")

try:
    from accept_tpm_window import show_accept_window
except ImportError:
    def show_accept_window(u, b):
        print("Brak pliku accept_tpm_window.py")

try:
    from user_management_window import show_user_management
except ImportError:
    def show_user_management(u, b):
        print("Brak pliku user_management_window.py")


def show_main_menu(username):
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    window = ctk.CTk()
    window.title(f"Panel główny - CMMS by RafałS ({username})")
    window.geometry("1920x1080")
    window.state("zoomed")

    header = ctk.CTkLabel(
        window,
        text=f"CMMS by RafałS – Witaj, {username}",
        font=ctk.CTkFont(size=28, weight="bold"),
        text_color="#f5f5f5"
    )
    header.pack(pady=20)

    grid = ctk.CTkFrame(window, fg_color="transparent")
    grid.pack(expand=True)

    def create_tile(parent, title, desc, color, command, row, col, icon="🛠", wide=False):
        if wide:
            width = 900
            height = 360
        else:
            width = 400
            height = 240
        wrap = 320

        frame = ctk.CTkFrame(parent, corner_radius=20, fg_color=color, width=width, height=height)
        frame.grid(row=row, column=col, padx=25, pady=25, sticky="nsew")
        frame.grid_propagate(False)

        label_icon = ctk.CTkLabel(frame, text=icon, font=ctk.CTkFont(size=48), text_color="white")
        label_icon.pack(pady=(25, 10))

        label_title = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=20, weight="bold"), text_color="white")
        label_title.pack()

        label_desc = ctk.CTkLabel(frame, text=desc, font=ctk.CTkFont(size=14), text_color="white", wraplength=wrap)
        label_desc.pack(pady=(8, 15))

        for widget in (frame, label_icon, label_title, label_desc):
            widget.bind("<Button-1>", lambda e: command())

    def open_subwindow(func):
        window.withdraw()
        func(username, lambda: [window.deiconify()])

    # --- UKŁAD KAFELKÓW ---

    # Rząd 0
    create_tile(grid, "Zadania", "Edytuj definicje zadań", "#3B82F6",
                lambda: open_subwindow(show_tasks_window), 0, 0, "📋", wide=True)

    create_tile(grid, "Drukowanie TPM", "Drukuj listę zadań", "#10B981",
                print_tpm, 0, 1, "🖨")

    # ZMIANA: Przywrócono ikonę techniczną i usunięto wzmiankę o kosztach z nazwy
    create_tile(grid, "Zgłoszenie Awarii", "Rejestracja usterek i przestojów", "#EF4444",
                lambda: open_subwindow(show_failure_window), 0, 2, "🔧", wide=True)

    # Rząd 1
    create_tile(grid, "Magazyn", "Podgląd części", "#F59E0B",
                lambda: open_subwindow(show_inventory_window), 1, 0, "📦")

    create_tile(grid, "Statystyki", "Raporty i analizy", "#8B5CF6",
                lambda: open_subwindow(show_analytics_window), 1, 1, "📊")

    create_tile(grid, "Zatwierdź TPM", "Odhacz wykonane zadania", "#059669",
                lambda: open_subwindow(show_accept_window), 1, 2, "✅")

    # Rząd 2 - Użytkownicy i Wyloguj

    create_tile(grid, "Użytkownicy", "Stawki i uprawnienia", "#6366F1",
                lambda: open_subwindow(show_user_management), 2, 0, "👥")

    create_tile(grid, "Wyloguj", "Zakończ pracę", "#6B7280",
                lambda: [window.destroy(), login_window.show_login_window()], 2, 2, "🚪")

    for i in range(3):
        grid.grid_rowconfigure(i, weight=1)
    for j in range(3):
        grid.grid_columnconfigure(j, weight=1)

    window.mainloop()