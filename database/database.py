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

       # LEADS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        event_type TEXT NOT NULL,
        event_date TEXT,
        event_time TEXT,
        event_location TEXT,
        guest_count INTEGER,
        details TEXT,
        status TEXT NOT NULL DEFAULT 'NOVO',
        notes TEXT,
        availability_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # DISPONIBILIDADE / AGENDA
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'AVAILABLE',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # USUÁRIOS / ADMINISTRADORES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # HISTÓRICO DE ALTERAÇÕES DA AGENDA
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS availability_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        availability_id INTEGER,

        date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,

        action TEXT NOT NULL,

        old_status TEXT,
        new_status TEXT,

        affected_lead_id INTEGER,
        affected_client_name TEXT,
        affected_event_type TEXT,

        admin_username TEXT NOT NULL,

        description TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    connection.commit()
    connection.close()

def migrate_db():
    connection = get_connection()
    cursor = connection.cursor()

    # Verifica colunas existentes em leads
    cursor.execute("PRAGMA table_info(leads)")
    columns = [column["name"] for column in cursor.fetchall()]

    if "notes" not in columns:
        cursor.execute("""
            ALTER TABLE leads
            ADD COLUMN notes TEXT
        """)

    if "event_time" not in columns:
        cursor.execute("""
            ALTER TABLE leads
            ADD COLUMN event_time TEXT
        """)
        
    if "availability_id" not in columns:
        cursor.execute("""
        ALTER TABLE leads
        ADD COLUMN availability_id INTEGER
    """)

    connection.commit()
    connection.close()