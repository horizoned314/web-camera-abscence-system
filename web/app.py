import os
from flask import Flask
from models.attendance import init_db, close_db
from routes.dashboard import dashboard_bp
from routes.api import api_bp


def create_app():
    app = Flask(__name__)

    # ── Database path ────────────────────────────────────
    # Shared dengan core/ (satu level di atas folder web/)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path  = os.path.normpath(os.path.join(base_dir, '..', 'database.db'))
    app.config['DATABASE'] = db_path

    # ── Blueprints ───────────────────────────────────────
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)          # /scan, /api/*

    # ── Teardown ─────────────────────────────────────────
    app.teardown_appcontext(close_db)

    # ── Init database ────────────────────────────────────
    with app.app_context():
        init_db()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
