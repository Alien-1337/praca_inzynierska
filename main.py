from dotenv import load_dotenv
load_dotenv("data.env")
import db_utils
import login_window


def main():
    try:
        print("🔄 Inicjalizacja bazy danych...")
        db_utils.create_tables()
        print("✅ Baza danych gotowa")

    except Exception as e:
        print("❌ Błąd inicjalizacji bazy danych:")
        print(e)
        return

    try:
        login_window.show_login_window()
    except Exception as e:
        print("❌ Błąd uruchamiania aplikacji:")
        print(e)


if __name__ == "__main__":
    main()
