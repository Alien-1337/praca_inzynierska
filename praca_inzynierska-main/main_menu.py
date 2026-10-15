import customtkinter as ctk
from tkinter import messagebox
from tasks_window import show_tasks_window
from failure_window import open_failure_window as show_failure_window
from failure_resolve_window import show_failure_resolve_window
from inventory_window import show_inventory_window
from tpm_module import print_tpm
import login_window
import db_utils
import permissions

# --- BEZPIECZNE IMPORTY ---
try:
    from Analytics import show_analytics_window
except ImportError:
    def show_analytics_window(u, b):
        print("⚠️ Brak pliku Analytics.py")


try:
    from accept_tpm_window import show_accept_window
except ImportError:
    def show_accept_window(u, b):
        print("⚠️ Brak pliku accept_tpm_window.py")


try:
    from user_management_window import show_user_management
except ImportError:
    def show_user_management(u, b):
        print("⚠️ Brak pliku user_management_window.py")


COLUMNS = 3  # kafelków w jednym rzędzie


def show_main_menu(username, role=None):
    # Rola decyduje, które kafelki zobaczy użytkownik (patrz permissions.py).
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

    # --- TWORZENIE KAFELKA ---
    def create_tile(parent, title, desc, color, command, row, col, icon="🛠", wide=False):
        width = 900 if wide else 400
        height = 360 if wide else 240
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

        def safe_click(event=None):
            try:
                command()
            except Exception as e:
                print(f"❌ Błąd w kafelku '{title}': {e}")

        for widget in (frame, label_icon, label_title, label_desc):
            widget.bind("<Button-1>", safe_click)

    # --- OTWIERANIE PODOKIEN ---
    def open_subwindow(func):
        try:
            window.withdraw()
            func(username, lambda: window.deiconify())
        except Exception as e:
            print("❌ Błąd otwierania okna:", e)
            window.deiconify()

    # --- KONTROLA UPRAWNIEŃ ---
    def guarded(feature, action):
        """Przed każdym otwarciem sprawdza rolę w bazie - zmiana roli działa od razu,
        a kafelek z przestarzałego menu nie otworzy funkcji, do której konto straciło dostęp."""
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

    # --- WYLOGOWANIE ---

    def logout():
        window.destroy()
        login_window.show_login_window()

    # --- KAFELKI ---
    # (funkcja z permissions.py, tytuł, opis, kolor, akcja, ikona, szeroki?)
    # Kafelek pojawia się tylko u ról, które mają daną funkcję w permissions.ROLE_FEATURES.
    # Funkcja None = kafelek dla każdego (Wyloguj).
    tiles = [
        (permissions.FEATURE_TPM_TASKS, "Zadania", "Edytuj definicje zadań", "#3B82F6",
         lambda: open_subwindow(show_tasks_window), "📋", True),

        (permissions.FEATURE_TPM_PRINT, "Drukowanie TPM", "Drukuj listę zadań", "#10B981",
         print_tpm, "🖨", False),

        (permissions.FEATURE_FAILURE_REPORT, "Zgłoszenie Awarii", "Rejestracja usterek i przestojów", "#EF4444",
         lambda: open_subwindow(show_failure_window), "🔧", True),

        (permissions.FEATURE_FAILURE_RESOLVE, "Rozwiązywanie Awarii", "Naprawy i stan zgłoszeń", "#EC4899",
         lambda: open_subwindow(show_failure_resolve_window), "🛠", False),

        (permissions.FEATURE_INVENTORY, "Magazyn", "Podgląd części", "#F59E0B",
         lambda: open_subwindow(show_inventory_window), "📦", False),

        (permissions.FEATURE_ANALYTICS, "Statystyki", "Raporty i analizy", "#8B5CF6",
         lambda: open_subwindow(show_analytics_window), "📊", False),

        (permissions.FEATURE_TPM_ACCEPT, "Zatwierdź TPM", "Odhacz wykonane zadania", "#059669",
         lambda: open_subwindow(show_accept_window), "✅", False),

        (permissions.FEATURE_USERS, "Użytkownicy", "Stawki i uprawnienia", "#6366F1",
         lambda: open_subwindow(show_user_management), "👥", False),

        (None, "Wyloguj", "Zakończ pracę", "#6B7280",
         lambda: window.after(0, logout), "🚪", False),
    ]

    visible = [t for t in tiles if t[0] is None or permissions.can(role, t[0])]

    for index, (feature, title, desc, color, action, icon, wide) in enumerate(visible):
        command = action if feature is None else guarded(feature, action)
        create_tile(grid, title, desc, color, command, index // COLUMNS, index % COLUMNS, icon, wide)

    # uniform = wszystkie kafelki w rzędzie/kolumnie mają ten sam rozmiar (też gdy rola widzi ich mało)
    for i in range((len(visible) + COLUMNS - 1) // COLUMNS):
        grid.grid_rowconfigure(i, weight=1, uniform="tile_rows")
    for j in range(min(COLUMNS, len(visible))):
        grid.grid_columnconfigure(j, weight=1, uniform="tile_cols")

    window.mainloop()
