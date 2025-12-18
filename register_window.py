import customtkinter as ctk
import hashlib
import os
import db_utils


# WAŻNE: Nie importujemy tu login_window, bo to psuje program!

def hash_password(password, salt):
    if isinstance(salt, bytes):
        salt = salt.hex()
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()


def show_register_window():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    window = ctk.CTk()
    window.title("Rejestracja - CMMS by RafałS")
    window.geometry("400x400")
    window.resizable(False, False)

    frame = ctk.CTkFrame(window, corner_radius=15)
    frame.place(relx=0.5, rely=0.5, anchor="center")

    title = ctk.CTkLabel(frame, text="Rejestracja", font=ctk.CTkFont(size=26, weight="bold"))
    title.pack(pady=(30, 20))

    # Pole 1: Nazwa użytkownika
    entry_username = ctk.CTkEntry(frame, placeholder_text="Nazwa użytkownika", width=250)
    entry_username.pack(pady=10)

    # Pole 2: Hasło
    entry_password = ctk.CTkEntry(frame, placeholder_text="Hasło", show="*", width=250)
    entry_password.pack(pady=10)

    label_message = ctk.CTkLabel(frame, text="", text_color="red")
    label_message.pack(pady=5)

    def register():
        username = entry_username.get()
        password = entry_password.get()

        if not username or not password:
            label_message.configure(text="Wypełnij wszystkie pola", text_color="red")
            return

        salt = os.urandom(16).hex()
        password_hash = hash_password(password, salt)

        # Próbujemy dodać użytkownika (tylko nazwa, hasło, sól)
        try:
            success = db_utils.add_user(username, password_hash, salt)

            if success:
                label_message.configure(text="Konto utworzone pomyślnie!", text_color="green")
            else:
                label_message.configure(text="Taki użytkownik już istnieje", text_color="red")
        except Exception as e:
            label_message.configure(text="Błąd bazy danych", text_color="red")
            print(f"BŁĄD: {e}")

    def back_to_login():
        window.destroy()
        # Importujemy login_window DOPIERO TUTAJ, wewnątrz funkcji
        # To zapobiega wyłączaniu się programu
        import login_window
        login_window.show_login_window()

    btn_register = ctk.CTkButton(frame, text="Zarejestruj się", width=200, command=register)
    btn_register.pack(pady=(20, 10))

    btn_back = ctk.CTkButton(frame, text="Powrót do logowania", width=200, fg_color="#444", hover_color="#555",
                             command=back_to_login)
    btn_back.pack(pady=(0, 30))

    window.mainloop()