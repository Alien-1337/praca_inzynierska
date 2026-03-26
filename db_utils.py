import psycopg2
from psycopg2 import IntegrityError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

# 🔧 KONFIGURACJA BAZY
DB_CONFIG = {
    "host": "localhost",
    "database": "cmms",
    "user": "postgres",
    "password": "Dsvdsvdsv9",  # ← ZMIEŃ
    "port": "5432"
}


def connect():
    return psycopg2.connect(**DB_CONFIG)


# 🔥 NAJWAŻNIEJSZE — TEGO BRAKOWAŁO
def create_tables():
    try:
        conn = connect()
        c = conn.cursor()

        print("🔄 Tworzenie tabel PostgreSQL...")

        # USERS
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            hourly_rate NUMERIC DEFAULT 0
        )
        """)

        # FAILURES
        c.execute("""
        CREATE TABLE IF NOT EXISTS failures (
            id SERIAL PRIMARY KEY,
            "user" TEXT,
            area TEXT,
            subsystem TEXT,
            functional_subsystem TEXT,
            date DATE,
            shift TEXT,
            time_reported TEXT,
            time_resolved TEXT,
            downtime_minutes INTEGER,
            department TEXT,
            category TEXT,
            failure_type TEXT,
            failure_description TEXT,
            resolver TEXT,
            used_part TEXT,
            labor_cost NUMERIC,
            parts_cost NUMERIC,
            total_cost NUMERIC
        )
        """)

        # TPM TASKS
        c.execute("""
        CREATE TABLE IF NOT EXISTS tpm_tasks (
            id SERIAL PRIMARY KEY,
            date DATE,
            interval TEXT,
            field TEXT,
            type TEXT,
            description TEXT,
            last_done DATE
        )
        """)

        # INVENTORY
        c.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY,
            name TEXT,
            sap_number TEXT,
            reference_number TEXT,
            quantity INTEGER,
            location TEXT,
            price NUMERIC DEFAULT 0
        )
        """)

        conn.commit()
        conn.close()

        print("✅ Wszystkie tabele gotowe!")

    except Exception as e:
        print("❌ Błąd tworzenia tabel:")
        print(e)


# --- Użytkownicy ---
def add_user(username, password_hash, salt, hourly_rate=0.0):
    conn = connect()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO users (username, password_hash, salt, hourly_rate) VALUES (%s, %s, %s, %s)",
            (username, password_hash, salt, hourly_rate)
        )
        conn.commit()
        return True
    except IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()


def get_user(username):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash, salt, hourly_rate FROM users WHERE username = %s", (username,))
    user = c.fetchone()
    conn.close()
    return user


def get_user_rate_by_name(username):
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT hourly_rate FROM users WHERE username = %s", (username,))
    res = c.fetchone()
    conn.close()
    return res[0] if res else 0.0


def get_all_users():
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT id, username, COALESCE(hourly_rate, 0.0) FROM users")
    users = c.fetchall()
    conn.close()
    return users


def update_user_rate(user_id, new_rate):
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE users SET hourly_rate = %s WHERE id = %s", (new_rate, user_id))
    conn.commit()
    conn.close()


# --- Awarie ---
def add_failure(data):
    conn = connect()
    c = conn.cursor()

    resolver_name = data.get("osoba_niwelujaca", "")
    c.execute("SELECT hourly_rate FROM users WHERE username = %s", (resolver_name,))
    user_res = c.fetchone()

    hourly_rate = float(user_res[0]) if user_res and user_res[0] else 0.0
    downtime = float(data.get("czas_awarii", 0) or 0)

    labor_cost = (downtime / 60.0) * hourly_rate


    part_name = data.get("uzyta_czesc", "")
    parts_cost = 0.0

    if part_name:
        c.execute("SELECT price FROM inventory WHERE name = %s", (part_name,))
        part_res = c.fetchone()
        if part_res:
            parts_cost = part_res[0]

    total_cost = labor_cost + parts_cost

    c.execute('''
        INSERT INTO failures (
            "user", area, subsystem, functional_subsystem, date,
            shift, time_reported, time_resolved, downtime_minutes,
            department, category, failure_type, failure_description, resolver,
            used_part, labor_cost, parts_cost, total_cost
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
    c = conn.cursor()
    c.execute("""
        SELECT * FROM failures ORDER BY id DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows


# --- TPM ---
def add_tpm_task(date_start, interval, field, type_, desc):
    conn = connect()
    c = conn.cursor()
    c.execute(
        "INSERT INTO tpm_tasks (date, interval, field, type, description, last_done) VALUES (%s, %s, %s, %s, %s, NULL)",
        (date_start, interval, field, type_, desc)
    )
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
    c.execute(
        "UPDATE tpm_tasks SET date=%s, interval=%s, field=%s, type=%s, description=%s WHERE id=%s",
        (date_start, interval, field, type_, desc, task_id)
    )
    conn.commit()
    conn.close()


def mark_task_as_done(task_id):
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE tpm_tasks SET last_done = %s WHERE id = %s", (date.today(), task_id))
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
        t_id, start_date, interval_str, field, type_, desc, last_done = task

        try:
            if not start_date:
                continue

            if last_done == today:
                continue

            val_str, unit = interval_str.split(' ', 1)
            val = int(val_str)

            temp_date = start_date
            latest_due = None

            while temp_date <= today:
                latest_due = temp_date

                if unit == "Dni":
                    temp_date += timedelta(days=val)
                elif unit == "Tygodnie":
                    temp_date += timedelta(weeks=val)
                elif unit == "Miesiące":
                    temp_date += relativedelta(months=val)
                elif unit == "Lata":
                    temp_date += relativedelta(years=val)

            if latest_due and (last_done is None or last_done < latest_due):
                if latest_due == today:
                    status = "NA DZIŚ"
                else:
                    status = f"ZALEGŁE ({(today - latest_due).days} dni)"

                pending_tasks.append((t_id, start_date, interval_str, field, type_, desc, status))

        except Exception:
            continue

    return pending_tasks


# --- Magazyn ---
def get_inventory_items(search_query=""):
    conn = connect()
    c = conn.cursor()

    if search_query:
        search_query = f"%{search_query}%"
        c.execute("""
            SELECT id, name, sap_number, reference_number, quantity, location, price
            FROM inventory
            WHERE name ILIKE %s OR sap_number ILIKE %s
        """, (search_query, search_query))
    else:
        c.execute("SELECT id, name, sap_number, reference_number, quantity, location, price FROM inventory")

    results = c.fetchall()
    conn.close()
    return results


def add_inventory_item(name, sap_number, reference_number, quantity, location, price=0.0):
    conn = connect()
    c = conn.cursor()
    c.execute(
        "INSERT INTO inventory (name, sap_number, reference_number, quantity, location, price) VALUES (%s, %s, %s, %s, %s, %s)",
        (name, sap_number, reference_number, quantity, location, price)
    )
    conn.commit()
    conn.close()