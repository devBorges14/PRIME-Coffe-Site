from flask import Flask

from flask_wtf.csrf import CSRFProtect

from config import Config
from database.database import init_db, migrate_db

from routes.main import main
from routes.contact import contact_bp
from routes.admin import admin_bp
from routes.agenda import agenda_bp
from routes.reports import reports_bp
from routes.auth import auth_bp


app = Flask(__name__)

app.config.from_object(Config)


# =====================================================
# CSRF
# =====================================================

csrf = CSRFProtect(app)


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
    app.run(debug=True)