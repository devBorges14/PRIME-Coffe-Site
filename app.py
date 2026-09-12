from flask import Flask

from config import Config
from routes.main import main
from routes.contact import contact_bp
from routes.admin import admin_bp
from database.database import init_db, migrate_db

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
    migrate_db()

    # =====================================================
    # BLUEPRINTS
    # =====================================================

    app.register_blueprint(main)
    app.register_blueprint(contact_bp)
    app.register_blueprint(admin_bp)

    return app


# =========================================================
# EXECUÇÃO
# =========================================================

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)