import os
from datetime import timedelta

# Carrega variáveis do arquivo .env (se existir e se o
# python-dotenv estiver instalado). Em produção, as variáveis
# normalmente vêm do próprio servidor, sem arquivo .env.

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# =========================================================
# AMBIENTE
# =========================================================
#
# APP_ENV=development  -> uso local (debug ligado, cookie sem Secure)
# APP_ENV=production   -> padrão quando a variável NÃO existe
#
# O padrão é "production" de propósito: se alguém esquecer de
# configurar, o sistema sobe no modo mais seguro, não no mais
# permissivo.

APP_ENV = os.environ.get("APP_ENV", "production").strip().lower()

IS_PRODUCTION = APP_ENV == "production"


class Config:

    IS_PRODUCTION = IS_PRODUCTION

    # -----------------------------------------------------
    # CHAVE SECRETA
    # -----------------------------------------------------
    # Vem SEMPRE de variável de ambiente. O app.py se recusa
    # a iniciar se ela não existir ou for curta demais.

    SECRET_KEY = os.environ.get("SECRET_KEY")

    # -----------------------------------------------------
    # CSRF
    # -----------------------------------------------------
    # TIME_LIMIT = None: o token vale enquanto a sessão valer
    # (por padrão expiraria em 1 hora, e um admin com a página
    # aberta tomaria "CSRF token has expired" ao enviar).

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    # -----------------------------------------------------
    # SESSÃO / COOKIES
    # -----------------------------------------------------

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Secure = só trafega por HTTPS. Ligado em produção.
    SESSION_COOKIE_SECURE = IS_PRODUCTION

    # Sessão do admin expira após 60 min SEM atividade
    # (a cada requisição o prazo é renovado).

    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)

    # -----------------------------------------------------
    # LIMITE DE TAMANHO DAS REQUISIÇÕES
    # -----------------------------------------------------

    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB
