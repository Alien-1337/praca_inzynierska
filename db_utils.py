import sqlite3
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

DB_PATH = 'cmms.db'

# Nagłówki do historii (zaktualizowane o koszty)
FAILURE_HEADERS = [
    "Użytkownik", "Obszar", "Podsystem", "Podsystem funkcjonalny", "Data",
    "Zmiana", "Godzina zgłoszenia", "Godzina zakończenia", "Czas przestoju (min)",
    "Dział", "Kategoria", "Typ awarii", "Opis awarii", "Osoba niwelująca",
    "Użyta część", "Koszt Robocizny", "Koszt Części", "KOSZT CAŁKOWITY"
]


def connect():
    return sqlite3.connect(DB_PATH)


def create_tables():
    conn = connect()
    c = conn.cursor()

    # Tabela użytkowników
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        hourly_rate REAL DEFAULT 0.0
    )
    ''')

    # Tabela awarii (rozszerzona o used_part i koszty)
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
        resolver TEXT NOT NULL,
        used_part TEXT,
        labor_cost REAL DEFAULT 0.0,
        parts_cost REAL DEFAULT 0.0,
        total_cost REAL DEFAULT 0.0
    )
    ''')

    # Tabela TPM
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

    # Tabela magazynu (z ceną)
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sap_number TEXT NOT NULL,
            reference_number TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            location TEXT NOT NULL,
            price REAL DEFAULT 0.0
        )
    ''')

    conn.commit()
    conn.close()


# --- Użytkownicy ---
def add_user(username, password_hash, salt, hourly_rate=0.0):
    conn = connect()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, salt, hourly_rate) VALUES (?, ?, ?, ?)",
                  (username, password_hash, salt, hourly_rate))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user(username):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash, salt, hourly_rate FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return user


def get_user_rate_by_name(username):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT hourly_rate FROM users WHERE username = ?", (username,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else 0.0


# --- NOWE FUNKCJE (Dla panelu zarządzania użytkownikami) ---
def get_all_users():
    """Pobiera listę wszystkich użytkowników (id, login, stawka)."""
    conn = connect()
    c = conn.cursor()
    # Pobieramy ID, Nazwę i Stawkę. Jeśli stawka jest NULL, zamieniamy na 0.0
    c.execute("SELECT id, username, COALESCE(hourly_rate, 0.0) FROM users")
    users = c.fetchall()
    conn.close()
    return users


def update_user_rate(user_id, new_rate):
    """Aktualizuje stawkę godzinową użytkownika."""
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE users SET hourly_rate = ? WHERE id = ?", (new_rate, user_id))
    conn.commit()
    conn.close()


# --- Awarie (Automatyczne liczenie kosztów) ---
def add_failure(data):
    conn = connect()
    c = conn.cursor()

    # 1. Pobieranie stawki osoby naprawiającej (resolver)
    resolver_name = data.get("osoba_niwelujaca", "")
    c.execute("SELECT hourly_rate FROM users WHERE username = ?", (resolver_name,))
    user_res = c.fetchone()
    hourly_rate = user_res[0] if user_res else 0.0

    # 2. Koszt robocizny
    downtime = int(data.get("czas_awarii", 0))
    labor_cost = (downtime / 60.0) * hourly_rate

    # 3. Koszt części (pobierany z magazynu na podstawie nazwy)
    part_name = data.get("uzyta_czesc", "")
    parts_cost = 0.0
    if part_name:
        c.execute("SELECT price FROM inventory WHERE name = ?", (part_name,))
        part_res = c.fetchone()
        if part_res:
            parts_cost = part_res[0]
            # Opcjonalnie: Zdejmij ze stanu magazynowego (jeśli chcesz, odkomentuj linię niżej)
            # c.execute("UPDATE inventory SET quantity = quantity - 1 WHERE name = ?", (part_name,))

    # 4. Suma
    total_cost = labor_cost + parts_cost

    c.execute('''
        INSERT INTO failures (
            user, area, subsystem, functional_subsystem, date,
            shift, time_reported, time_resolved, downtime_minutes,
            department, category, failure_type, failure_description, resolver,
            used_part, labor_cost, parts_cost, total_cost
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data["username"], data["obszar_system"], data["podsystem"], data["podsystem_funkcjonalny"],
        data["data_zgloszenia"], data["zmiana"], data["godzina_zgloszenia"], data["godzina_zakonczenia"],
        downtime, data["dzial"], data["kategoria_awarii"], data["awaria_jaka"],
        data["opis_awarii"], resolver_name,
        part_name, round(labor_cost, 2), round(parts_cost, 2), round(total_cost, 2)
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
            department, category, failure_type, failure_description, resolver,
            used_part, labor_cost, parts_cost, total_cost
        FROM failures
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


# --- TPM (Zadania okresowe) ---
def add_tpm_task(date_start, interval, field, type_, desc):
    conn = connect()
    c = conn.cursor()
    c.execute(
        "INSERT INTO tpm_tasks (date, interval, field, type, description, last_done) VALUES (?, ?, ?, ?, ?, NULL)",
        (date_start, interval, field, type_, desc))
    conn.commit()
    conn.close()


def get_tpm_tasks():
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT id, date, interval, field, type, description FROM tpm_tasks")
    tasks = c.fetchall()
    conn.close()
    return tasks


def update_tpm_task(task_id, date_start, interval, field, type_, desc):
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE tpm_tasks SET date=?, interval=?, field=?, type=?, description=? WHERE id=?",
              (date_start, interval, field, type_, desc, task_id))
    conn.commit()
    conn.close()


def mark_task_as_done(task_id):
    today_str = date.today().isoformat()
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE tpm_tasks SET last_done = ? WHERE id = ?", (today_str, task_id))
    conn.commit()
    conn.close()


def get_pending_tpm_tasks():
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
            last_done = None
            if last_done_str:
                last_done = datetime.strptime(last_done_str, "%Y-%m-%d").date()
                if last_done == today: continue

            val_str, unit = interval_str.split(' ', 1)
            val = int(val_str)

            # Obliczanie dat wykonania
            due_dates_past_or_today = []
            temp_date = start_date
            limit = 0
            while temp_date <= today:
                due_dates_past_or_today.append(temp_date)
                if unit == "Dni":
                    temp_date += timedelta(days=val)
                elif unit == "Tygodnie":
                    temp_date += timedelta(weeks=val)
                elif unit == "Miesiące":
                    temp_date += relativedelta(months=val)
                elif unit == "Lata":
                    temp_date += relativedelta(years=val)
                limit += 1
                if limit > 2000: break

            if not due_dates_past_or_today: continue

            latest_due = due_dates_past_or_today[-1]
            status = None

            if last_done is None or last_done < latest_due:
                if latest_due == today:
                    status = "NA DZIŚ"
                else:
                    days_late = (today - latest_due).days
                    status = f"ZALEGŁE ({days_late} dni)"

            if status:
                pending_tasks.append((t_id, start_date_str, interval_str, field, type_, desc, status))
        except ValueError:
            continue

    return pending_tasks


# --- Magazyn ---
def get_inventory_items(search_query=""):
    conn = connect()
    c = conn.cursor()
    if search_query:
        # Wyszukiwanie po Nazwie LUB numerze SAP
        search_query = f"%{search_query}%"
        c.execute(
            """
            SELECT id, name, sap_number, reference_number, quantity, location, price 
            FROM inventory 
            WHERE name LIKE ? OR sap_number LIKE ?
            """,
            (search_query, search_query))
    else:
        c.execute("SELECT id, name, sap_number, reference_number, quantity, location, price FROM inventory")
    results = c.fetchall()
    conn.close()
    return results


def add_inventory_item(name, sap_number, reference_number, quantity, location, price=0.0):
    conn = connect()
    c = conn.cursor()
    c.execute(
        "INSERT INTO inventory (name, sap_number, reference_number, quantity, location, price) VALUES (?, ?, ?, ?, ?, ?)",
        (name, sap_number, reference_number, quantity, location, price))
    conn.commit()
    conn.close()