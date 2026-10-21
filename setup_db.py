"""Przygotowuje bazę (tabele, role, status awarii) bez uruchamiania aplikacji.
To samo robi main.py przy starcie. Dane połączenia z pliku data.env.

Uruchomienie: python setup_db.py
"""
from dotenv import load_dotenv
load_dotenv("data.env")   # przed importem db_utils, bo tam czytane są DB_*
import db_utils


if __name__ == "__main__":
    try:
        db_utils.create_tables()
    except Exception as e:
        print("Nie udało się przygotować bazy:")
        print(e)
        raise SystemExit(1)
