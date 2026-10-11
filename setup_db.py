import psycopg2
import os

DB_CONFIG = {
    "host": "localhost",
    "database": "twoja_baza",
    "user": "twoj_user",
    "password": "twoje_haslo",
    "port": "5432"
}

def create_tables():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Użytkownicy
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'operator'
    )
    """)

    # Zadania dzienne
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_tasks (
        id SERIAL PRIMARY KEY,
        title TEXT,
        description TEXT,
        created_by TEXT,
        created_at TIMESTAMP,
        due_date TIMESTAMP,
        is_completed BOOLEAN DEFAULT FALSE
    )
    """)

    # Rejestr usterek
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS failures (
        id SERIAL PRIMARY KEY,
        title TEXT,
        description TEXT,
        reported_by TEXT,
        status TEXT DEFAULT 'Zgłoszona',
        reported_at TIMESTAMP,
        resolved_at TIMESTAMP
    )
    """)

    # Magazyn części
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id SERIAL PRIMARY KEY,
        part_name TEXT,
        quantity INTEGER,
        location TEXT,
        last_updated TIMESTAMP
    )
    """)

    # Historia pobrań części
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory_logs (
        id SERIAL PRIMARY KEY,
        part_id INTEGER REFERENCES inventory(id),
        used_by TEXT,
        quantity_used INTEGER,
        used_at TIMESTAMP
    )
    """)

    # Historia działań
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS maintenance_logs (
        id SERIAL PRIMARY KEY,
        "user" TEXT,
        action TEXT,
        timestamp TIMESTAMP
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ PostgreSQL baza gotowa!")

if __name__ == "__main__":
    create_tables()
