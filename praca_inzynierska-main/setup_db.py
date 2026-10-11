"""Jednorazowa inicjalizacja bazy: tabele, role użytkowników i status awarii.

To samo robi aplikacja przy każdym starcie (main.py), więc ten skrypt jest opcjonalny -
przydaje się, gdy chcesz przygotować bazę bez uruchamiania okna aplikacji.
Dane połączenia są czytane z pliku data.env (wzór: data.env.example).

Uruchomienie:  python setup_db.py
"""
from dotenv import load_dotenv
load_dotenv("data.env")   # musi być przed importem db_utils (tam czytane są DB_*)
import db_utils


if __name__ == "__main__":
    try:
        db_utils.create_tables()
    except Exception as e:
        print("❌ Nie udało się przygotować bazy:")
        print(e)
        raise SystemExit(1)
