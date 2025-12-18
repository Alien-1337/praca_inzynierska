import sqlite3
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

DB_PATH = 'cmms.db'

FAILURE_HEADERS = [
    "Użytkownik", "Obszar", "Podsystem", "Podsystem funkcjonalny", "Data",
    "Zmiana", "Godzina zgłoszenia", "Godzina zakończenia", "Czas przestoju (min)",
    "Dział", "Kategoria", "Typ awarii", "Opis awarii", "Osoba niwelująca"
]


def connect():
    return sqlite3.connect(DB_PATH)


def create_tables():
    conn = connect()
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS failures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        area TEXT NOT NULL,
        subsystem TEXT NOT NULL,
        functional_subsystem TEXT NOT NULL,
        date TEXT NOT NULL,
        shift TEXT NOT NULL,
        time_reported TEXT NOT NULL,
        time_resolved TEXT NOT NULL,
        downtime_minutes INTEGER NOT NULL,
        department TEXT NOT NULL,
        category TEXT NOT NULL,
        failure_type TEXT NOT NULL,
        failure_description TEXT NOT NULL,
        resolver TEXT NOT NULL
    )
    ''')

    # DODANO KOLUMNĘ last_done (Kiedy ostatnio zrobiono)
    c.execute('''
        CREATE TABLE IF NOT EXISTS tpm_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            interval TEXT NOT NULL,
            field TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            last_done TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sap_number TEXT NOT NULL,
            reference_number TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            location TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


# --- Users & Failures ---
def add_user(username, password_hash, salt):
    conn = connect()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)", (username, password_hash, salt))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user(username):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash, salt FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return user


def add_failure(data):
    conn = connect()
    c = conn.cursor()
    c.execute('''
        INSERT INTO failures (
            user, area, subsystem, functional_subsystem, date,
            shift, time_reported, time_resolved, downtime_minutes,
            department, category, failure_type, failure_description, resolver
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data["username"], data["obszar_system"], data["podsystem"], data["podsystem_funkcjonalny"],
        data["data_zgloszenia"], data["zmiana"], data["godzina_zgloszenia"], data["godzina_zakonczenia"],
        int(data["czas_awarii"]), data["dzial"], data["kategoria_awarii"], data["awaria_jaka"],
        data["opis_awarii"], data["osoba_niwelujaca"]
    ))
    conn.commit()
    conn.close()


def get_failure_history():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            id, user, area, subsystem, functional_subsystem, date,
            shift, time_reported, time_resolved, downtime_minutes,
            department, category, failure_type, failure_description, resolver
        FROM failures
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


# --- TPM TASKS - LOGIKA ZALEGŁOŚCI ---

def add_tpm_task(date, interval, field, type_, desc):
    conn = connect()
    c = conn.cursor()
    # Domyślnie last_done jest NULL (nigdy nie robione)
    c.execute(
        "INSERT INTO tpm_tasks (date, interval, field, type, description, last_done) VALUES (?, ?, ?, ?, ?, NULL)",
        (date, interval, field, type_, desc))
    conn.commit()
    conn.close()


def get_tpm_tasks():
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT id, date, interval, field, type, description FROM tpm_tasks")
    tasks = c.fetchall()
    conn.close()
    return tasks


def update_tpm_task(task_id, date, interval, field, type_, desc):
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE tpm_tasks SET date=?, interval=?, field=?, type=?, description=? WHERE id=?",
              (date, interval, field, type_, desc, task_id))
    conn.commit()
    conn.close()


def mark_task_as_done(task_id):
    """Oznacza zadanie jako wykonane dzisiaj."""
    today_str = date.today().isoformat()
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE tpm_tasks SET last_done = ? WHERE id = ?", (today_str, task_id))
    conn.commit()
    conn.close()


def get_pending_tpm_tasks():
    """
    Zwraca listę zadań do wykonania na dziś ORAZ zaległych.
    Zwraca listę krotek: (id, date, interval, field, type, description, STATUS)
    Status to string: 'TODAY' lub 'OVERDUE'
    """
    today = date.today()
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT id, date, interval, field, type, description, last_done FROM tpm_tasks")
    all_tasks = c.fetchall()
    conn.close()

    pending_tasks = []

    for task in all_tasks:
        t_id, start_date_str, interval_str, field, type_, desc, last_done_str = task

        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

            # Parsowanie ostatniego wykonania
            last_done = None
            if last_done_str:
                last_done = datetime.strptime(last_done_str, "%Y-%m-%d").date()
                # Jeśli zrobione dzisiaj, to już nie pokazuj
                if last_done == today:
                    continue

            # Parsowanie interwału
            val_str, unit = interval_str.split(' ', 1)
            val = int(val_str)

            # --- ALGORYTM WYZNACZANIA NASTĘPNEJ DATY ---
            # 1. Startujemy od daty początkowej
            current_due_date = start_date

            # 2. Przesuwamy się interwałami tak długo, aż trafimy w przyszłość
            #    Musimy znaleźć najnowszą datę wymagalności, która jest <= dzisiaj

            due_dates_past_or_today = []

            # Zabezpieczenie pętli
            limit = 0
            temp_date = start_date

            while temp_date <= today:
                due_dates_past_or_today.append(temp_date)

                # Dodaj interwał
                if unit == "Dni":
                    temp_date += timedelta(days=val)
                elif unit == "Tygodnie":
                    temp_date += timedelta(weeks=val)
                elif unit == "Miesiące":
                    temp_date += relativedelta(months=val)
                elif unit == "Lata":
                    temp_date += relativedelta(years=val)

                limit += 1
                if limit > 10000: break  # Safety break

            if not due_dates_past_or_today:
                continue  # Data startu w przyszłości

            # Najbardziej aktualna data wymagalności (dzisiaj lub w przeszłości)
            latest_due = due_dates_past_or_today[-1]

            # --- SPRAWDZENIE CZY ZROBIONE ---
            # Zadanie jest do zrobienia, jeśli:
            # 1. Nigdy nie było robione (last_done is None)
            # 2. LUB Data ostatniego wykonania jest starsza niż data wymagalności

            status = None

            if last_done is None or last_done < latest_due:
                if latest_due == today:
                    status = "NA DZIŚ"
                else:
                    days_late = (today - latest_due).days
                    status = f"ZALEGŁE ({days_late} dni)"

            if status:
                # Zwracamy task + status
                pending_tasks.append((t_id, start_date_str, interval_str, field, type_, desc, status))

        except ValueError:
            continue

    return pending_tasks


# --- Magazyn ---
def get_inventory_items(search_query=""):
    conn = connect()
    c = conn.cursor()
    if search_query:
        search_query = f"%{search_query}%"
        c.execute(
            "SELECT id, name, sap_number, reference_number, quantity, location FROM inventory WHERE name LIKE ? OR CAST(id AS TEXT) LIKE ?",
            (search_query, search_query))
    else:
        c.execute("SELECT id, name, sap_number, reference_number, quantity, location FROM inventory")
    results = c.fetchall()
    conn.close()
    return results


def add_inventory_item(name, sap_number, reference_number, quantity, location):
    conn = connect()
    c = conn.cursor()
    c.execute("INSERT INTO inventory (name, sap_number, reference_number, quantity, location) VALUES (?, ?, ?, ?, ?)",
              (name, sap_number, reference_number, quantity, location))
    conn.commit()
    conn.close()