import customtkinter as ctk
import sqlite3


def show_inventory_window(username, back_to_menu_func):
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # Tworzymy podokno zamiast nowego okna głównego
    window = ctk.CTkToplevel()
    window.title("Magazyn - CMMS by RafałS")
    window.geometry("700x600")
    window.grab_set()  # blokuje interakcję z głównym oknem
    window.protocol("WM_DELETE_WINDOW", lambda: back_to_menu(window, back_to_menu_func, username))

    frame = ctk.CTkFrame(window, corner_radius=15)
    frame.place(relx=0.5, rely=0.5, anchor="center")

    label = ctk.CTkLabel(
        frame,
        text=f"Przegląd magazynu\nUżytkownik: {username}",
        font=ctk.CTkFont(size=20, weight="bold"),
        justify="center"
    )
    label.pack(pady=(20, 10))

    search_entry = ctk.CTkEntry(frame, placeholder_text="Wyszukaj po nazwie lub Numerze SAP", width=400)
    search_entry.pack(pady=(5, 5))

    list_frame = ctk.CTkScrollableFrame(frame, width=650, height=350, corner_radius=10)
    list_frame.pack(pady=(0, 15))

    def update_list(data):
        for widget in list_frame.winfo_children():
            widget.destroy()
        for row in data:
            text = f"ID: {row[0]} | Nazwa: {row[1]} | SAP: {row[2]} | Ref: {row[3]} | Ilość: {row[4]} | Miejsce: {row[5]}"
            ctk.CTkLabel(list_frame, text=text, anchor="w", font=ctk.CTkFont(size=14), justify="left").pack(
                anchor="w", padx=10, pady=2
            )

    def search_inventory():
        query = search_entry.get().strip()
        conn = sqlite3.connect("cmms.db")
        c = conn.cursor()
        if query:
            c.execute("""
                SELECT id, name, sap_number, reference_number, quantity, location
                FROM inventory
                WHERE name LIKE ? OR sap_number LIKE ?
            """, (f"%{query}%", f"%{query}%"))
        else:
            c.execute("SELECT id, name, sap_number, reference_number, quantity, location FROM inventory")
        data = c.fetchall()
        conn.close()
        update_list(data)

    ctk.CTkButton(frame, text="Szukaj", command=search_inventory).pack(pady=(0, 10))

    # Pierwsze wczytanie danych
    conn = sqlite3.connect("cmms.db")
    c = conn.cursor()
    c.execute("SELECT id, name, sap_number, reference_number, quantity, location FROM inventory")
    update_list(c.fetchall())
    conn.close()

    btn_back = ctk.CTkButton(
        frame,
        text="Powrót do menu",
        width=200,
        command=lambda: back_to_menu(window, back_to_menu_func, username)
    )
    btn_back.pack(pady=(10, 10))


def back_to_menu(window, back_to_menu_func, username):
    window.destroy()
    back_to_menu_func()
