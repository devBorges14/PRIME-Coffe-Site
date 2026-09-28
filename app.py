from flask import Flask

from flask_wtf.csrf import CSRFProtect

from config import Config
from database.database import init_db, migrate_db

from extensions import limiter
from logging_config import configure_logging
from security import (
    register_security_headers,
    register_error_handlers
)

from routes.main import main
from routes.contact import contact_bp
from routes.admin import admin_bp
from routes.agenda import agenda_bp
from routes.reports import reports_bp
from routes.auth import auth_bp


app = Flask(__name__)

app.config.from_object(Config)


# =====================================================
# CHAVE SECRETA OBRIGATÓRIA
# =====================================================
#
# Sem uma chave forte, qualquer pessoa que descubra (ou
# adivinhe) a chave consegue forjar uma sessão de admin.
# Por isso o app se recusa a iniciar sem ela.

secret_key = app.config.get("SECRET_KEY")

if not secret_key or len(secret_key) < 32:

    raise RuntimeError(
        "SECRET_KEY ausente ou curta demais (mínimo 32 caracteres). "
        "Gere uma com:\n"
        "    python -c \"import secrets; print(secrets.token_hex(32))\"\n"
        "e coloque no arquivo .env (SECRET_KEY=...) "
        "ou na variável de ambiente do servidor."
    )


# =====================================================
# LOGS
# =====================================================

configure_logging(app)


# =====================================================
# CSRF
# =====================================================

csrf = CSRFProtect(app)


# =====================================================
# LIMITE DE REQUISIÇÕES (anti força bruta / spam)
# =====================================================

limiter.init_app(app)


# =====================================================
# HEADERS DE SEGURANÇA E PÁGINAS DE ERRO
# =====================================================

register_security_headers(app)
register_error_handlers(app)


# =====================================================
# BANCO
# =====================================================

init_db()
migrate_db()


# =====================================================
# BLUEPRINTS
# =====================================================

app.register_blueprint(main)
app.register_blueprint(contact_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(agenda_bp)
app.register_blueprint(reports_bp)


if __name__ == "__main__":

    # debug só fora de produção (APP_ENV=development no .env)
    app.run(debug=not app.config["IS_PRODUCTION"])
