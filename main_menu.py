import customtkinter as ctk
from tasks_window import show_tasks_window
from failure_window import open_failure_window as show_failure_window
from inventory_window import show_inventory_window
from tpm_module import print_tpm
import login_window


def show_main_menu(username):
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    window = ctk.CTk()
    window.title(f"Panel główny - CMMS by RafałS ({username})")
    window.geometry("1920x1080")
    window.state("zoomed")

    # --- Nagłówek ---
    header = ctk.CTkLabel(
        window,
        text=f"CMMS by RafałS – Witaj, {username}",
        font=ctk.CTkFont(size=28, weight="bold"),
        text_color="#f5f5f5"
    )
    header.pack(pady=20)

    # --- Siatka kafelków ---
    grid = ctk.CTkFrame(window, fg_color="transparent")
    grid.pack(expand=True)

    # --- pomocnicza funkcja kafelka ---
    def create_tile(parent, title, desc, color, command, row, col, icon="🛠", wide=False):
        # większe kafelki dla wide=True
        if wide:
            width = 900  # zwiększona szerokość samego tła
            height = 360  # zwiększona wysokość samego tła
        else:
            width = 400
            height = 240

        wrap = 320  # pozostał oryginalny wraplength, tekst się nie zwiększa

        frame = ctk.CTkFrame(
            parent, corner_radius=20, fg_color=color,
            width=width, height=height
        )
        frame.grid(row=row, column=col, padx=25, pady=25, sticky="nsew")
        frame.grid_propagate(False)

        label_icon = ctk.CTkLabel(frame, text=icon, font=ctk.CTkFont(size=48), text_color="white")
        label_icon.pack(pady=(25, 10))

        label_title = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=20, weight="bold"), text_color="white")
        label_title.pack()

        label_desc = ctk.CTkLabel(frame, text=desc, font=ctk.CTkFont(size=14), text_color="white", wraplength=wrap)
        label_desc.pack(pady=(8, 15))

        # wycentrowanie tekstu
        label_title.configure(anchor="center", justify="center")
        label_desc.configure(anchor="center", justify="center")
        label_icon.configure(anchor="center")

        # umożliwienie kliknięcia w cały kafelek
        for widget in (frame, label_icon, label_title, label_desc):
            widget.bind("<Button-1>", lambda e: command())

    # --- funkcja otwierająca podokno ---
    def open_subwindow(func):
        window.withdraw()
        func(username, lambda: [window.deiconify()])

    # --- kafelki ---
    create_tile(grid, "Zadania", "Przeglądaj i zarządzaj zadaniami", "#3B82F6",
                lambda: open_subwindow(show_tasks_window), 0, 0, "📋", wide=True)

    create_tile(grid, "Drukowanie TPM", "Wydruk zadań dziennych", "#10B981",
                print_tpm, 0, 1, "🖨")

    create_tile(grid, "Awaria", "Zgłoś lub sprawdź awarię", "#EF4444",
                lambda: open_subwindow(show_failure_window), 0, 2, "⚠️", wide=True)

    create_tile(grid, "Magazyn", "Podgląd części i materiałów", "#F59E0B",
                lambda: open_subwindow(show_inventory_window), 1, 0, "📦")

    create_tile(grid, "Statystyki", "Raporty i analizy", "#8B5CF6",
                lambda: print("TODO: raporty"), 1, 1, "📊")

    create_tile(grid, "Wyloguj", "Zakończ pracę", "#6B7280",
                lambda: [window.destroy(), login_window.show_login_window()], 1, 2, "🚪")

    # --- proporcje siatki ---
    for i in range(2):
        grid.grid_rowconfigure(i, weight=1)
    for j in range(3):
        grid.grid_columnconfigure(j, weight=1)

    grid.grid_columnconfigure(2, minsize=250)
    grid.grid_columnconfigure(1, minsize=250)

    window.mainloop()
