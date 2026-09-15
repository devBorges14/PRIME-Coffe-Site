from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import check_password_hash
from database.database import get_connection


auth_bp = Blueprint(
    "auth",
    __name__,
    url_prefix="/admin"
)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

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

        if not user or not check_password_hash(
            user["password_hash"],
            password
        ):

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

        return redirect(
            url_for("admin.dashboard")
        )

    return render_template(
        "admin/login.html"
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return redirect(
        url_for("auth.login")
    )