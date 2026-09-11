from flask import Flask

from config import Config
from database.database import init_db
from routes.main import main
from routes.contact import contact_bp


def create_app():
    app = Flask(__name__)

    # =====================================================
    # CONFIGURAÇÕES
    # =====================================================

    app.config.from_object(Config)

    # =====================================================
    # BANCO DE DADOS
    # =====================================================

    init_db()

    # =====================================================
    # BLUEPRINTS
    # =====================================================

    app.register_blueprint(main)
    app.register_blueprint(contact_bp)

    return app


# =========================================================
# EXECUÇÃO
# =========================================================

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)