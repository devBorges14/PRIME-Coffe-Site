import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "site.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_date TEXT,
            event_location TEXT,
            guest_count INTEGER,
            details TEXT,
            status TEXT NOT NULL DEFAULT 'NOVO',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


def migrate_db():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        PRAGMA table_info(leads)
    """)

    columns = [column["name"] for column in cursor.fetchall()]

    if "notes" not in columns:

        cursor.execute("""
            ALTER TABLE leads
            ADD COLUMN notes TEXT
        """)

    connection.commit()
    connection.close()