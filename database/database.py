import re
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

    # HISTÓRICO DE ALTERAÇÕES DO LEAD (FUNIL COMERCIAL)
    #
    # Guarda cada mudança de status de um lead, desde a
    # criação (old_status = NULL, new_status = 'NOVO')
    # até o fechamento ou perda. "changed_by" fica NULL
    # quando a mudança vem do formulário público (criação);
    # nas demais, guarda o username do administrador.

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        lead_id INTEGER NOT NULL,

        old_status TEXT,
        new_status TEXT NOT NULL,

        changed_by TEXT,

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

    # Data/horário que o CLIENTE escolheu no formulário.
    # event_date/event_time passam a ser a data atual (que muda
    # quando o admin reagenda); estas guardam a original.
    # Ficam NULL enquanto o lead nunca foi reagendado.

    if "original_event_date" not in columns:
        cursor.execute("""
            ALTER TABLE leads
            ADD COLUMN original_event_date TEXT
        """)

    if "original_event_time" not in columns:
        cursor.execute("""
            ALTER TABLE leads
            ADD COLUMN original_event_time TEXT
        """)

    backfill_original_dates(cursor)

    connection.commit()
    connection.close()


def backfill_original_dates(cursor):
    """
    Leads reagendados ANTES de existirem as colunas original_*
    perderam a data escolhida pelo cliente. Ela é recuperada do
    primeiro registro "Reagendado de AAAA-MM-DD HH:MM para ..."
    do histórico do lead.
    """

    rows = cursor.execute("""
        SELECT h.lead_id, h.description
        FROM leads_history h
        JOIN leads l ON l.id = h.lead_id
        WHERE l.original_event_date IS NULL
          AND h.description LIKE 'Reagendado de %'
        ORDER BY h.lead_id, h.created_at ASC, h.id ASC
    """).fetchall()

    done = set()

    for row in rows:

        lead_id = row["lead_id"]

        if lead_id in done:
            continue

        done.add(lead_id)

        match = re.match(
            r"Reagendado de (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})",
            row["description"] or ""
        )

        # "Reagendado de nenhum horário ..." -> não há o que recuperar
        if not match:
            continue

        cursor.execute("""
            UPDATE leads
            SET original_event_date = ?,
                original_event_time = ?
            WHERE id = ?
              AND original_event_date IS NULL
        """, (match.group(1), match.group(2), lead_id))