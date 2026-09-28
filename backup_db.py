"""
Backup do banco SQLite.

Uso:
    python backup_db.py

Cria backups/site-AAAAMMDD-HHMMSS.db usando a API de backup do
próprio SQLite (seguro mesmo com o site rodando) e mantém só os
KEEP backups mais recentes.
"""

import datetime
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DATABASE = BASE_DIR / "database" / "site.db"

BACKUP_DIR = BASE_DIR / "backups"

KEEP = 14


def main():

    if not DATABASE.exists():
        raise SystemExit(f"Banco não encontrado: {DATABASE}")

    BACKUP_DIR.mkdir(exist_ok=True)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    destination = BACKUP_DIR / f"site-{stamp}.db"

    source = sqlite3.connect(DATABASE)
    target = sqlite3.connect(destination)

    try:

        source.backup(target)

        # Confere se a cópia está íntegra
        result = target.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

    finally:

        target.close()
        source.close()

    if result != "ok":

        destination.unlink(missing_ok=True)

        raise SystemExit(
            f"Backup corrompido ({result}); descartado."
        )

    print(f"Backup criado: {destination}")

    # Rotação: apaga os mais antigos além do limite
    backups = sorted(BACKUP_DIR.glob("site-*.db"))

    for old in backups[:-KEEP]:
        old.unlink()
        print(f"Removido backup antigo: {old.name}")


if __name__ == "__main__":
    main()
