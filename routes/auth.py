from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from database.database import get_connection
from extensions import limiter


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/admin"
)


# Hash "falso" usado quando o usuário digitado não existe.
# Sem isso, login com usuário inexistente responderia mais
# rápido que login com usuário existente e senha errada, e
# um atacante poderia descobrir quais usuários existem
# medindo o tempo de resposta.

DUMMY_PASSWORD_HASH = generate_password_hash(
    "senha-falsa-apenas-para-igualar-o-tempo"
)


def _login_failed(response):
    """
    Só tentativas que NÃO terminaram em redirecionamento
    (ou seja, logins que falharam) contam para o limite.
    Um admin que acerta a senha nunca é penalizado.
    """

    return response.status_code != 302


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit(
    "5 per minute; 30 per hour",
    methods=["POST"],
    deduct_when=_login_failed
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()[:150]

        password = request.form.get(
            "password",
            ""
        )[:1000]

        if not username or not password:

            flash(
                "Preencha usuário e senha.",
                "error"
            )

            return render_template(
                "admin/login.html"
            )

        connection = get_connection()

        user = connection.execute("""
            SELECT *
            FROM users
            WHERE username = ?
            AND is_active = 1
        """, (username,)).fetchone()

        connection.close()

        # A verificação de senha SEMPRE roda (com hash falso
        # se o usuário não existe), para igualar o tempo.

        password_ok = check_password_hash(
            user["password_hash"] if user else DUMMY_PASSWORD_HASH,
            password
        )

        if not user or not password_ok:

            current_app.logger.warning(
                "Login falhou: usuario=%r ip=%s",
                username[:64],
                request.remote_addr
            )

            flash(
                "Usuário ou senha inválidos.",
                "error"
            )

            return render_template(
                "admin/login.html"
            )

        session.clear()

        session["user_id"] = user["id"]
        session["username"] = user["username"]

        # Sessão "permanente" = expira por inatividade conforme
        # PERMANENT_SESSION_LIFETIME (60 min), renovada a cada
        # requisição.

        session.permanent = True

        current_app.logger.info(
            "Login ok: usuario=%r ip=%s",
            user["username"],
            request.remote_addr
        )

        return redirect(
            url_for("admin.dashboard")
        )

    return render_template(
        "admin/login.html"
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():

    username = session.get("username")

    session.clear()

    if username:

        current_app.logger.info(
            "Logout: usuario=%r ip=%s",
            username,
            request.remote_addr
        )

    return redirect(
        url_for("auth.login")
    )
