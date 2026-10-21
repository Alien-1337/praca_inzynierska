import psycopg2
from psycopg2 import IntegrityError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import os

import permissions

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "cmms"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "port":     os.getenv("DB_PORT", "5432")
}

# statusy awarii
STATUS_REPORTED = "Zgłoszona"
STATUS_IN_REPAIR = "W naprawie"
STATUS_RESOLVED = "Rozwiązana"


def _connection_error(server_message):
    # w komunikacie nie ma hasła
    return RuntimeError(
        "Nie udało się połączyć z PostgreSQL "
        f"(serwer {DB_CONFIG['host']}:{DB_CONFIG['port']}, baza '{DB_CONFIG['database']}', "
        f"użytkownik '{DB_CONFIG['user']}').\n"
        f"Komunikat serwera: {server_message}\n"
        "Sprawdź plik data.env (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD). "
        "Przy kilku zainstalowanych wersjach PostgreSQL każda ma własny port i hasło "
        "(pgAdmin: prawy przycisk na serwerze, Properties, zakładka Connection)."
    )


def connect():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except UnicodeDecodeError as e:
        # polskie Windows: serwer wysyła komunikat w cp1250, a psycopg2 czyta go jako UTF-8,
        # więc zamiast przyczyny widać błąd dekodowania; odczytujemy oryginał z wyjątku
        raw = e.object if isinstance(e.object, (bytes, bytearray)) else b""
        raise _connection_error(bytes(raw).decode("cp1250", errors="replace").strip()) from None
    except psycopg2.OperationalError as e:
        raise _connection_error(str(e).strip()) from None


def _column_exists(cursor, table, column):
    cursor.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s",
        (table, column)
    )
    return cursor.fetchone() is not None


def create_tables():
    conn = None
    try:
        conn = connect()
        c = conn.cursor()
        print("Tworzenie tabel PostgreSQL...")

        # role użytkowników (taki sam schemat jak w sql/001_add_roles.sql)
        c.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            name VARCHAR(30) PRIMARY KEY,
            description TEXT NOT NULL
        )
        """)

        for role_name in permissions.ALL_ROLES:
            c.execute(
                """
                INSERT INTO roles (name, description) VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
                WHERE roles.description IS DISTINCT FROM EXCLUDED.description
                """,
                (role_name, permissions.ROLE_DESCRIPTIONS[role_name])
            )

        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            hourly_rate NUMERIC DEFAULT 0
        )
        """)

        # kolumna roli (istniejące konta dostają rolę domyślną)
        if not _column_exists(c, "users", "role"):
            c.execute(f"""
            ALTER TABLE users
            ADD COLUMN role VARCHAR(30) NOT NULL DEFAULT '{permissions.DEFAULT_ROLE}'
                CONSTRAINT users_role_fkey REFERENCES roles (name) ON UPDATE CASCADE
            """)

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

        # status awarii; dotychczasowe wpisy były już naprawione, więc dostają 'Rozwiązana'
        if not _column_exists(c, "failures", "status"):
            c.execute(f"""
            ALTER TABLE failures
            ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT '{STATUS_RESOLVED}'
                CONSTRAINT failures_status_check
                CHECK (status IN ('{STATUS_REPORTED}', '{STATUS_IN_REPAIR}', '{STATUS_RESOLVED}'))
            """)
            c.execute(f"ALTER TABLE failures ALTER COLUMN status SET DEFAULT '{STATUS_REPORTED}'")

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
        print("Wszystkie tabele gotowe!")

    except Exception as e:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


# --- Użytkownicy ---

def add_user(username, password_hash, salt, hourly_rate=0.0):
    # pierwsze konto w pustej bazie dostaje Administratora, kolejne rolę domyślną
    conn = connect()
    try:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO users (username, password_hash, salt, hourly_rate, role)
            VALUES (%s, %s, %s, %s,
                    CASE WHEN EXISTS (SELECT 1 FROM users) THEN %s ELSE %s END)
            """,
            (username, password_hash, salt, hourly_rate,
             permissions.DEFAULT_ROLE, permissions.ROLE_ADMIN)
        )
        conn.commit()
        return True
    except IntegrityError:
        conn.rollback()
        return False
    except Exception as e:
        conn.rollback()
        print(f"Błąd dodawania użytkownika: {e}")
        return False
    finally:
        conn.close()


def get_user(username):
    conn = connect()
    try:
        c = conn.cursor()
        c.execute(
            "SELECT id, username, password_hash, salt, hourly_rate FROM users WHERE username = %s",
            (username,)
        )
        return c.fetchone()
    except Exception as e:
        print(f"Błąd pobierania użytkownika: {e}")
        return None
    finally:
        conn.close()


def get_user_rate_by_name(username):
    conn = connect()
    try:
        c = conn.cursor()
        c.execute("SELECT hourly_rate FROM users WHERE username = %s", (username,))
        res = c.fetchone()
        return float(res[0]) if res else 0.0
    except Exception as e:
        print(f"Błąd pobierania stawki: {e}")
        return 0.0
    finally:
        conn.close()


def get_all_users():
    conn = connect()
    try:
        c = conn.cursor()
        c.execute("SELECT id, username, COALESCE(hourly_rate, 0.0) FROM users")
        return c.fetchall()
    except Exception as e:
        print(f"Błąd pobierania użytkowników: {e}")
        return []
    finally:
        conn.close()


def update_user_rate(user_id, new_rate):
    conn = connect()
    try:
        c = conn.cursor()
        c.execute("UPDATE users SET hourly_rate = %s WHERE id = %s", (new_rate, user_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Błąd aktualizacji stawki: {e}")
    finally:
        conn.close()


# --- Role i uprawnienia ---

def get_user_role(username):
    """Rola użytkownika albo None (brak konta / błąd bazy)."""
    conn = connect()
    try:
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE username = %s", (username,))
        res = c.fetchone()
        return res[0] if res else None
    except Exception as e:
        print(f"Błąd pobierania roli: {e}")
        return None
    finally:
        conn.close()


def _user_can(cursor, username, feature):
    cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()
    return row is not None and permissions.can(row[0], feature)


def user_can(username, feature):
    """True, jeśli aktualna rola użytkownika (z bazy) ma dostęp do funkcji."""
    return permissions.can(get_user_role(username), feature)


def get_all_users_with_roles():
    """[(id, login, rola, stawka_godzinowa), ...] - dla okna zarządzania użytkownikami."""
    conn = connect()
    try:
        c = conn.cursor()
        c.execute("SELECT id, username, role, COALESCE(hourly_rate, 0.0) FROM users ORDER BY id")
        return c.fetchall()
    except Exception as e:
        print(f"Błąd pobierania użytkowników: {e}")
        return []
    finally:
        conn.close()


def get_role_counts():
    """{rola: liczba kont} - np. do sprawdzenia, czy w bazie jest Administrator."""
    conn = connect()
    try:
        c = conn.cursor()
        c.execute("SELECT role, count(*) FROM users GROUP BY role")
        return {role: int(n) for role, n in c.fetchall()}
    except Exception as e:
        print(f"Błąd liczenia ról: {e}")
        return {}
    finally:
        conn.close()


def set_user_role(user_id, new_role, acting_username):
    """Zmiana roli użytkownika (tylko Administrator; ostatniemu Administratorowi nie można
    odebrać roli). Zwraca (ok, komunikat)."""
    if new_role not in permissions.ALL_ROLES:
        return False, f"Nieznana rola: {new_role}"

    conn = connect()
    try:
        c = conn.cursor()

        if not _user_can(c, acting_username, permissions.FEATURE_USERS):
            return False, "Brak uprawnień do zmiany ról."

        c.execute("SELECT username, role FROM users WHERE id = %s FOR UPDATE", (user_id,))
        row = c.fetchone()
        if row is None:
            return False, "Nie znaleziono takiego użytkownika."
        target_name, old_role = row

        if old_role == new_role:
            return True, f"{target_name} ma już rolę {new_role}."

        if old_role == permissions.ROLE_ADMIN:
            c.execute("SELECT count(*) FROM users WHERE role = %s", (permissions.ROLE_ADMIN,))
            if c.fetchone()[0] <= 1:
                return False, "Nie można odebrać roli ostatniemu Administratorowi."

        c.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        conn.commit()
        return True, f"{target_name}: zmieniono rolę z {old_role} na {new_role}"

    except Exception as e:
        conn.rollback()
        print(f"Błąd zmiany roli: {e}")
        return False, f"Błąd bazy danych: {e}"
    finally:
        conn.close()


# --- Awarie ---

def add_failure(data):
    """Zapis awarii już naprawionej. Wymaga prawa do rozwiązywania awarii,
    samo zgłoszenie robi report_failure()."""
    conn = connect()
    try:
        c = conn.cursor()

        if not _user_can(c, data.get("username", ""), permissions.FEATURE_FAILURE_RESOLVE):
            print("Brak uprawnień do zapisu rozwiązanej awarii")
            return False

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
                parts_cost = float(part_res[0]) if part_res[0] else 0.0

        total_cost = labor_cost + parts_cost

        c.execute('''
            INSERT INTO failures (
                "user", area, subsystem, functional_subsystem, date,
                shift, time_reported, time_resolved, downtime_minutes,
                department, category, failure_type, failure_description, resolver,
                used_part, labor_cost, parts_cost, total_cost, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      'Rozwiązana')
        ''', (
            data["username"], data["obszar_system"], data["podsystem"],
            data["podsystem_funkcjonalny"], data["data_zgloszenia"],
            data["zmiana"], data["godzina_zgloszenia"], data["godzina_zakonczenia"],
            downtime, data["dzial"], data["kategoria_awarii"], data["awaria_jaka"],
            data["opis_awarii"], resolver_name,
            part_name, round(labor_cost, 2), round(parts_cost, 2), round(total_cost, 2)
        ))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        print(f"Błąd dodawania awarii: {e}")
        return False
    finally:
        conn.close()


# kolejność kolumn jest stała, bo okno historii i Analytics odwołują się do nich po indeksie
FAILURE_COLUMNS = (
    'id, "user", area, subsystem, functional_subsystem, date, shift, '
    'time_reported, time_resolved, downtime_minutes, department, category, '
    'failure_type, failure_description, resolver, used_part, '
    'labor_cost, parts_cost, total_cost, status'
)


def get_failure_history(reported_by=None):
    """Awarie (najnowsze pierwsze): wszystkie albo tylko zgłoszone przez podanego użytkownika."""
    conn = connect()
    try:
        c = conn.cursor()
        sql = f"SELECT {FAILURE_COLUMNS} FROM failures"
        params = None
        if reported_by is not None:
            sql += ' WHERE "user" = %s'
            params = (reported_by,)
        c.execute(sql + " ORDER BY id DESC", params)
        return c.fetchall()
    except Exception as e:
        print(f"Błąd pobierania historii awarii: {e}")
        return []
    finally:
        conn.close()


def get_open_failures(include_resolved=False):
    """Kolejka dla Technika: awarie 'Zgłoszona' i 'W naprawie' (opcjonalnie także rozwiązane)."""
    conn = connect()
    try:
        c = conn.cursor()
        sql = f"SELECT {FAILURE_COLUMNS} FROM failures"
        params = None
        if not include_resolved:
            sql += " WHERE status <> %s"
            params = (STATUS_RESOLVED,)
        c.execute(sql + " ORDER BY id DESC", params)
        return c.fetchall()
    except Exception as e:
        print(f"Błąd pobierania otwartych awarii: {e}")
        return []
    finally:
        conn.close()


# indeksy kolumn w wierszach zwracanych przez funkcje z FAILURE_COLUMNS
(F_ID, F_USER, F_AREA, F_SUBSYSTEM, F_FUNCTIONAL, F_DATE, F_SHIFT, F_TIME_REPORTED,
 F_TIME_RESOLVED, F_DOWNTIME, F_DEPARTMENT, F_CATEGORY, F_TYPE, F_DESCRIPTION,
 F_RESOLVER, F_PART, F_LABOR, F_PARTS, F_TOTAL, F_STATUS) = range(20)


def get_failure_months():
    """Miesiące z awariami jako [(rok, miesiąc), ...], od najnowszego."""
    conn = connect()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT EXTRACT(YEAR FROM date)::int, EXTRACT(MONTH FROM date)::int
            FROM failures
            WHERE date IS NOT NULL
            ORDER BY 1 DESC, 2 DESC
        """)
        return c.fetchall()
    except Exception as e:
        print(f"Błąd pobierania miesięcy z awariami: {e}")
        return []
    finally:
        conn.close()


def get_failure_areas(start_date, end_date):
    """Maszyny (obszary systemu) z awariami w okresie od start_date do end_date (bez końca)."""
    conn = connect()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT area FROM failures
            WHERE date >= %s AND date < %s AND area IS NOT NULL AND area <> ''
            ORDER BY area
        """, (start_date, end_date))
        return [row[0] for row in c.fetchall()]
    except Exception as e:
        print(f"Błąd pobierania maszyn: {e}")
        return []
    finally:
        conn.close()


def get_failures_for_report(start_date, end_date, area=None):
    """Awarie z okresu od start_date do end_date (bez końca), opcjonalnie jednej maszyny."""
    conn = connect()
    try:
        c = conn.cursor()
        sql = f"SELECT {FAILURE_COLUMNS} FROM failures WHERE date >= %s AND date < %s"
        params = [start_date, end_date]
        if area:
            sql += " AND area = %s"
            params.append(area)
        c.execute(sql + " ORDER BY date, time_reported, id", params)
        return c.fetchall()
    except Exception as e:
        print(f"Błąd pobierania awarii do raportu: {e}")
        return []
    finally:
        conn.close()


def report_failure(data):
    """Zgłoszenie awarii (status Zgłoszona), bez danych o naprawie."""
    conn = connect()
    try:
        c = conn.cursor()

        if not _user_can(c, data.get("username", ""), permissions.FEATURE_FAILURE_REPORT):
            print("Brak uprawnień do zgłaszania awarii")
            return False

        c.execute('''
            INSERT INTO failures (
                "user", area, subsystem, functional_subsystem, date, shift,
                time_reported, department, category, failure_type,
                failure_description, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data["username"], data["obszar_system"], data["podsystem"],
            data["podsystem_funkcjonalny"], data["data_zgloszenia"], data["zmiana"],
            data["godzina_zgloszenia"], data["dzial"], data["kategoria_awarii"],
            data["awaria_jaka"], data["opis_awarii"], STATUS_REPORTED
        ))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        print(f"Błąd zgłaszania awarii: {e}")
        return False
    finally:
        conn.close()


def compute_downtime_minutes(start_date, start_time, end_date, end_time):
    """Przestój w minutach między zgłoszeniem a końcem naprawy.
    Daty to date albo 'YYYY-MM-DD', godziny 'HH:MM'. Zły format albo koniec przed
    początkiem daje ValueError."""
    try:
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date.strip(), "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Niepoprawny format daty. Użyj formatu: YYYY-MM-DD")

    try:
        start_t = datetime.strptime(str(start_time).strip(), "%H:%M").time()
    except ValueError:
        raise ValueError("Zgłoszenie ma niepoprawną godzinę zgłoszenia (oczekiwano HH:MM).")
    try:
        end_t = datetime.strptime(str(end_time).strip(), "%H:%M").time()
    except ValueError:
        raise ValueError("Niepoprawny format godziny zakończenia. Użyj formatu: HH:MM")

    start_dt = datetime.combine(start_date, start_t)
    end_dt = datetime.combine(end_date, end_t)
    if end_dt < start_dt:
        raise ValueError("Zakończenie naprawy nie może być wcześniejsze niż zgłoszenie awarii.")
    return int((end_dt - start_dt).total_seconds() // 60)


def start_repair(failure_id, username):
    """Technik przejmuje awarię (status W naprawie). Zwraca (ok, komunikat)."""
    conn = connect()
    try:
        c = conn.cursor()

        if not _user_can(c, username, permissions.FEATURE_FAILURE_RESOLVE):
            return False, "Brak uprawnień do rozwiązywania awarii."

        c.execute(
            "UPDATE failures SET status = %s, resolver = %s WHERE id = %s AND status = %s",
            (STATUS_IN_REPAIR, username, failure_id, STATUS_REPORTED)
        )
        if c.rowcount == 0:
            conn.rollback()
            return False, "Ta awaria nie czeka już na naprawę (jest w naprawie albo została zamknięta)."

        conn.commit()
        return True, "Awaria przekazana do naprawy."

    except Exception as e:
        conn.rollback()
        print(f"Błąd rozpoczynania naprawy: {e}")
        return False, f"Błąd bazy danych: {e}"
    finally:
        conn.close()


def resolve_failure(failure_id, username, end_date, end_time, used_part=""):
    """Technik kończy naprawę: liczy przestój i koszty, status Rozwiązana.
    Koszt robocizny liczy się ze stawki osoby naprawiającej (username). Zwraca (ok, komunikat)."""
    conn = connect()
    try:
        c = conn.cursor()

        if not _user_can(c, username, permissions.FEATURE_FAILURE_RESOLVE):
            return False, "Brak uprawnień do rozwiązywania awarii."

        c.execute("SELECT date, time_reported, status FROM failures WHERE id = %s FOR UPDATE", (failure_id,))
        row = c.fetchone()
        if row is None:
            return False, "Nie znaleziono takiej awarii."
        failure_date, time_reported, status = row
        if status == STATUS_RESOLVED:
            return False, "Ta awaria jest już rozwiązana."

        try:
            downtime = compute_downtime_minutes(failure_date, time_reported, end_date, end_time)
        except ValueError as e:
            return False, str(e)
        end_time_norm = datetime.strptime(str(end_time).strip(), "%H:%M").strftime("%H:%M")

        c.execute("SELECT hourly_rate FROM users WHERE username = %s", (username,))
        rate_row = c.fetchone()
        hourly_rate = float(rate_row[0]) if rate_row and rate_row[0] else 0.0
        labor_cost = (downtime / 60.0) * hourly_rate

        part_name = (used_part or "").strip()
        parts_cost = 0.0
        if part_name:
            c.execute("SELECT price FROM inventory WHERE name = %s", (part_name,))
            part_row = c.fetchone()
            if part_row and part_row[0]:
                parts_cost = float(part_row[0])

        total_cost = labor_cost + parts_cost

        c.execute('''
            UPDATE failures
            SET status = %s, resolver = %s, time_resolved = %s, downtime_minutes = %s,
                used_part = %s, labor_cost = %s, parts_cost = %s, total_cost = %s
            WHERE id = %s
        ''', (
            STATUS_RESOLVED, username, end_time_norm, downtime, part_name,
            round(labor_cost, 2), round(parts_cost, 2), round(total_cost, 2), failure_id
        ))

        conn.commit()
        return True, (f"Awaria #{failure_id} rozwiązana.\n"
                      f"Przestój: {downtime} min, koszt całkowity: {total_cost:.2f} PLN.")

    except Exception as e:
        conn.rollback()
        print(f"Błąd rozwiązywania awarii: {e}")
        return False, f"Błąd bazy danych: {e}"
    finally:
        conn.close()


# --- TPM ---

def add_tpm_task(date_start, interval, field, type_, desc):
    conn = connect()
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO tpm_tasks (date, interval, field, type, description, last_done) VALUES (%s, %s, %s, %s, %s, NULL)",
            (date_start, interval, field, type_, desc)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Błąd dodawania zadania TPM: {e}")
    finally:
        conn.close()


def get_tpm_tasks():
    conn = connect()
    try:
        c = conn.cursor()
        c.execute("SELECT id, date, interval, field, type, description FROM tpm_tasks")
        return c.fetchall()
    except Exception as e:
        print(f"Błąd pobierania zadań TPM: {e}")
        return []
    finally:
        conn.close()


def update_tpm_task(task_id, date_start, interval, field, type_, desc):
    conn = connect()
    try:
        c = conn.cursor()
        c.execute(
            "UPDATE tpm_tasks SET date=%s, interval=%s, field=%s, type=%s, description=%s WHERE id=%s",
            (date_start, interval, field, type_, desc, task_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Błąd aktualizacji zadania TPM: {e}")
    finally:
        conn.close()


def mark_task_as_done(task_id):
    conn = connect()
    try:
        c = conn.cursor()
        c.execute("UPDATE tpm_tasks SET last_done = %s WHERE id = %s", (date.today(), task_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Błąd zatwierdzania zadania: {e}")
    finally:
        conn.close()


def get_pending_tpm_tasks():
    today = date.today()
    conn = connect()
    try:
        c = conn.cursor()
        c.execute("SELECT id, date, interval, field, type, description, last_done FROM tpm_tasks")
        all_tasks = c.fetchall()
    except Exception as e:
        print(f"Błąd pobierania zaległych zadań: {e}")
        return []
    finally:
        conn.close()

    pending_tasks = []

    for task in all_tasks:
        t_id, start_date, interval_str, field, type_, desc, last_done = task

        try:
            if not start_date or not interval_str:
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
                else:
                    break

            if latest_due and (last_done is None or last_done < latest_due):
                if latest_due == today:
                    status = "NA DZIŚ"
                else:
                    status = f"ZALEGŁE ({(today - latest_due).days} dni)"

                pending_tasks.append((t_id, start_date, interval_str, field, type_, desc, status))

        except Exception as e:
            print(f"Pominięto zadanie {t_id}: {e}")
            continue

    return pending_tasks


# --- Magazyn ---

def get_inventory_items(search_query=""):
    conn = connect()
    try:
        c = conn.cursor()
        if search_query:
            like = f"%{search_query}%"
            c.execute("""
                SELECT id, name, sap_number, reference_number, quantity, location, price
                FROM inventory
                WHERE name ILIKE %s OR sap_number ILIKE %s
            """, (like, like))
        else:
            c.execute("""
                SELECT id, name, sap_number, reference_number, quantity, location, price
                FROM inventory
            """)
        return c.fetchall()
    except Exception as e:
        print(f"Błąd pobierania magazynu: {e}")
        return []
    finally:
        conn.close()


def add_inventory_item(name, sap_number, reference_number, quantity, location, price=0.0):
    conn = connect()
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO inventory (name, sap_number, reference_number, quantity, location, price) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, sap_number, reference_number, quantity, location, price)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Błąd dodawania do magazynu: {e}")
    finally:
        conn.close()