import os

class Config:

    SECRET_KEY = "troque-esta-chave-depois"

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"