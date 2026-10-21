from dotenv import load_dotenv
load_dotenv("data.env")
import db_utils
import login_window
import permissions


def main():
    try:
        print("Inicjalizacja bazy danych...")
        db_utils.create_tables()
        print("Baza danych gotowa")

    except Exception as e:
        print("Błąd inicjalizacji bazy danych:")
        print(e)
        return

    # bez Administratora nikt nie nada ról w aplikacji
    role_counts = db_utils.get_role_counts()
    if not role_counts:
        print("Baza nie ma jeszcze kont - pierwsze założone konto zostanie Administratorem.")
    elif role_counts.get(permissions.ROLE_ADMIN, 0) == 0:
        print("W bazie nie ma Administratora - nadaj rolę w pgAdmin (patrz URUCHOMIENIE.md).")

    try:
        login_window.show_login_window()
    except Exception as e:
        print("Błąd uruchamiania aplikacji:")
        print(e)


if __name__ == "__main__":
    main()
