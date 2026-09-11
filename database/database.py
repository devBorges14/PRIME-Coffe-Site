import sqlite3
from pathlib import Path


# Caminho do banco de dados
BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "site.db"


def get_connection():
    """
    Cria uma conexão com o banco de dados.
    """
    connection = sqlite3.connect(DATABASE)

    # Permite acessar as colunas pelo nome
    connection.row_factory = sqlite3.Row

    return connection


def init_db():
    """
    Cria as tabelas necessárias caso ainda não existam.
    """

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