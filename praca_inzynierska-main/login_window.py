import customtkinter as ctk
import hashlib
import db_utils
import main_menu


def hash_password(password, salt):
    if isinstance(salt, bytes):
        salt = salt.hex()
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()


def show_login_window():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    window = ctk.CTk()
    window.title("Logowanie - CMMS")
    window.geometry("400x400")
    window.resizable(False, False)

    frame = ctk.CTkFrame(window, corner_radius=15)
    frame.place(relx=0.5, rely=0.5, anchor="center")

    title = ctk.CTkLabel(frame, text="Logowanie", font=ctk.CTkFont(size=26, weight="bold"))
    title.pack(pady=(30, 20))

    entry_username = ctk.CTkEntry(frame, placeholder_text="Nazwa użytkownika", width=250)
    entry_username.pack(pady=10)

    entry_password = ctk.CTkEntry(frame, placeholder_text="Hasło", show="*", width=250)
    entry_password.pack(pady=10)

    label_message = ctk.CTkLabel(frame, text="", text_color="red")
    label_message.pack(pady=5)

    def go_to_main_menu(username, role):
        """Bezpieczne przejście do głównego menu — niszczy okno i otwiera nowe."""
        window.destroy()
        main_menu.show_main_menu(username, role)

    def login():
        username = entry_username.get().strip()
        password = entry_password.get().strip()

        if not username or not password:
            label_message.configure(text="Uzupełnij login i hasło", text_color="orange")
            return

        try:
            user_data = db_utils.get_user(username)
        except Exception as e:
            label_message.configure(text="Błąd połączenia z bazą danych", text_color="red")
            print(f"❌ Błąd bazy danych: {e}")
            return

        if user_data is None:
            label_message.configure(text="Nieprawidłowa nazwa użytkownika lub hasło", text_color="red")
            return

        try:
            _, _, stored_hash, stored_salt, *_ = user_data
            input_hash = hash_password(password, stored_salt)

            if input_hash == stored_hash:
                label_message.configure(text="Zalogowano pomyślnie ✅", text_color="green")
                role = db_utils.get_user_role(username)  # od roli zależy, jakie kafelki zobaczy
                # Krótkie opóźnienie żeby użytkownik zobaczył komunikat,
                # po czym niszczymy okno i otwieramy główne menu.
                # after() zamiast listy w lambdzie — bezpieczniejsze i czytelniejsze.
                window.after(800, lambda: go_to_main_menu(username, role))
            else:
                label_message.configure(text="Nieprawidłowa nazwa użytkownika lub hasło", text_color="red")

        except ValueError:
            label_message.configure(text="Błąd danych użytkownika", text_color="red")
            print(f"DEBUG: Otrzymano {len(user_data)} kolumn.")

    def open_register():
        """Przejście do okna rejestracji."""
        try:
            import register_window
            window.destroy()
            register_window.show_register_window()
        except Exception as e:
            print("❌ Błąd otwierania rejestracji:")
            import traceback
            traceback.print_exc()

    btn_login = ctk.CTkButton(frame, text="Zaloguj się", width=200, command=login)
    btn_login.pack(pady=(20, 10))

    btn_register = ctk.CTkButton(
        frame, text="Załóż konto", width=200,
        fg_color="#444", hover_color="#555",
        command=open_register
    )
    btn_register.pack(pady=(0, 30))

    window.bind("<Return>", lambda event: login())

    window.mainloop()