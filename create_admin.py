from getpass import getpass

from werkzeug.security import generate_password_hash

from database.database import get_connection
from database.database import init_db, migrate_db


MIN_PASSWORD_LENGTH = 10


init_db()
migrate_db()


username = input("Usuário administrador: ").strip()

password = getpass(
    "Senha: "
)

password_confirmation = getpass(
    "Confirme a senha: "
)


if not username:
    raise SystemExit(
        "O usuário não pode ficar vazio."
    )


if len(password) < MIN_PASSWORD_LENGTH:
    raise SystemExit(
        f"A senha precisa ter pelo menos {MIN_PASSWORD_LENGTH} caracteres."
    )


if password != password_confirmation:
    raise SystemExit(
        "As senhas não coincidem."
    )


password_hash = generate_password_hash(
    password
)


connection = get_connection()

try:

    connection.execute("""
        INSERT INTO users (
            username,
            password_hash
        )
        VALUES (?, ?)
    """, (
        username,
        password_hash
    ))

    connection.commit()

    print(
        "Administrador criado com sucesso."
    )

except Exception as error:

    connection.rollback()

    print(
        f"Erro ao criar administrador: {error}"
    )

finally:

    connection.close()
