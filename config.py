import os

class Config:

    SECRET_KEY = "troque-esta-chave-depois"

    WTF_CSRF_ENABLED = True

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = "Lax"