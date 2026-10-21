import customtkinter as ctk
import tkinter.messagebox
import db_utils


def show_inventory_window(username, back_to_menu_func):
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    window = ctk.CTkToplevel()
    window.title("Magazyn - CMMS")
    window.geometry("900x700")
    window.grab_set()
    window.protocol("WM_DELETE_WINDOW", lambda: back_to_menu(window, back_to_menu_func, username))

    frame = ctk.CTkFrame(window, corner_radius=15)
    frame.place(relx=0.5, rely=0.5, anchor="center")

    label = ctk.CTkLabel(
        frame,
        text=f"Stan Magazynowy\nUżytkownik: {username}",
        font=ctk.CTkFont(size=22, weight="bold"),
        justify="center"
    )
    label.pack(pady=(20, 15))

    search_entry = ctk.CTkEntry(frame, placeholder_text="Wpisz nazwę części lub numer SAP...", width=500)
    search_entry.pack(pady=(5, 5))

    list_frame = ctk.CTkScrollableFrame(frame, width=800, height=400, corner_radius=10)
    list_frame.pack(pady=(10, 15))

    def update_list(data):
        for widget in list_frame.winfo_children():
            widget.destroy()

        if not data:
            ctk.CTkLabel(list_frame, text="Brak wyników.", text_color="gray").pack(pady=10)
            return

        for row in data:
            p_id, name, sap, ref, qty, loc, price = row

            # cena może być pusta
            try:
                price_str = f"{float(price):.2f} PLN"
            except:
                price_str = "0.00 PLN"

            text = f"ID: {p_id} | {name}\nSAP: {sap} | Ref: {ref} | Lok: {loc} | Ilość: {qty} szt. | Cena: {price_str}"

            item_card = ctk.CTkFrame(list_frame, fg_color="#333333", corner_radius=8)
            item_card.pack(fill="x", pady=5, padx=5)

            ctk.CTkLabel(item_card, text=text, anchor="w", justify="left",
                         font=ctk.CTkFont(size=14)).pack(pady=8, padx=10, anchor="w")

    def search_inventory():
        query = search_entry.get().strip()
        results = db_utils.get_inventory_items(query)
        update_list(results)

    ctk.CTkButton(frame, text="Szukaj", width=200, command=search_inventory).pack(pady=(0, 10))

    def open_add_item_window():
        add_win = ctk.CTkToplevel(window)
        add_win.title("Dodaj element do magazynu")
        add_win.geometry("500x600")
        add_win.grab_set()

        ctk.CTkLabel(add_win, text="Nowa Część", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)

        entry_name = ctk.CTkEntry(add_win, placeholder_text="Nazwa części", width=300)
        entry_name.pack(pady=10)

        entry_sap = ctk.CTkEntry(add_win, placeholder_text="Numer SAP", width=300)
        entry_sap.pack(pady=10)

        entry_ref = ctk.CTkEntry(add_win, placeholder_text="Numer Referencyjny", width=300)
        entry_ref.pack(pady=10)

        entry_qty = ctk.CTkEntry(add_win, placeholder_text="Ilość (szt.)", width=300)
        entry_qty.pack(pady=10)

        entry_loc = ctk.CTkEntry(add_win, placeholder_text="Lokalizacja (np. Regał A)", width=300)
        entry_loc.pack(pady=10)

        entry_price = ctk.CTkEntry(add_win, placeholder_text="Cena jednostkowa (PLN)", width=300)
        entry_price.pack(pady=10)

        def save_item():
            try:
                name = entry_name.get().strip()
                sap = entry_sap.get().strip()
                ref = entry_ref.get().strip()
                loc = entry_loc.get().strip()

                if not name or not sap:
                    tkinter.messagebox.showwarning("Błąd", "Nazwa i SAP są wymagane.")
                    return

                # walidacja
                try:
                    qty = int(entry_qty.get())
                except:
                    tkinter.messagebox.showerror("Błąd", "Ilość musi być liczbą całkowitą.")
                    return

                try:
                    price = float(entry_price.get().replace(",", "."))
                except:
                    tkinter.messagebox.showerror("Błąd", "Cena musi być liczbą (np. 12.50).")
                    return

                db_utils.add_inventory_item(name, sap, ref, qty, loc, price)

                tkinter.messagebox.showinfo("Sukces", "Dodano element do magazynu.")
                add_win.destroy()
                search_inventory()

            except Exception as e:
                tkinter.messagebox.showerror("Błąd bazy", str(e))

        ctk.CTkButton(add_win, text="Zapisz", command=save_item, fg_color="green").pack(pady=30)

    ctk.CTkButton(frame, text="+ Dodaj nową część",
                  fg_color="#D97706", hover_color="#B45309",
                  width=200, command=open_add_item_window).pack(pady=(10, 5))

    search_inventory()

    ctk.CTkButton(
        frame,
        text="Powrót do menu",
        width=200,
        fg_color="#444", hover_color="#555",
        command=lambda: back_to_menu(window, back_to_menu_func, username)
    ).pack(pady=(10, 20))


def back_to_menu(window, back_to_menu_func, username):
    window.destroy()
    back_to_menu_func()