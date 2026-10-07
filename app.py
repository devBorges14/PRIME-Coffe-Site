import os

from flask import Flask

from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

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
# PROXY (PythonAnywhere e similares)
# =====================================================
#
# Atrás de um proxy, request.remote_addr seria o IP do proxy
# para TODOS os visitantes (e o limite anti-spam valeria para
# todo mundo junto). Com BEHIND_PROXY=1 no .env, o Flask passa
# a usar o IP real enviado pelo proxy. Não ligar localmente:
# sem proxy, qualquer um poderia forjar esse cabeçalho.

if os.environ.get("BEHIND_PROXY") == "1":
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)


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
