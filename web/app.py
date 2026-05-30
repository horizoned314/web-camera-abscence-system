import os
import sys
from flask import Flask, Response
from models.attendance import init_db, close_db
from routes.dashboard import dashboard_bp
from routes.api import api_bp

# Import fungsi stream kamera dari file face_recognition.py
base_dir = os.path.dirname(os.path.abspath(__file__))
core_dir = os.path.abspath(os.path.join(base_dir, '..', 'core'))

sys.path.append(core_dir)

from recognize import gen_frames

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

    # ── Route untuk Video Streaming di Web ───────────────
    @app.route('/video_feed')
    def video_feed():
        # Memanggil fungsi generator frame dari face_recognition.py
        return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

    # ── Teardown ─────────────────────────────────────────
    app.teardown_appcontext(close_db)

    # ── Init database ────────────────────────────────────
    with app.app_context():
        init_db()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)