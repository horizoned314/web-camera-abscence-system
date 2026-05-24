"""
routes/api.py
Endpoint:
  POST /scan              ← dipanggil oleh core/face_recognition.py
  GET  /api/attendance    ← polling dari dashboard
  GET  /api/stats
  POST /api/reset
  GET  /api/notifications ← polling toast dari dashboard
  POST /api/sync          ← sinkron users → attendance manual
"""

import threading
from datetime import datetime
from flask import Blueprint, request, jsonify
from models.attendance import (
    get_attendance,
    get_stats,
    mark_hadir,
    reset_all,
    sync_from_users,
)

api_bp = Blueprint('api', __name__)

# ── Antrian notifikasi in-memory (thread-safe) ────────────────────────────────
_notifications      : list  = []
_notifications_lock         = threading.Lock()


def _push_notification(message: str, ntype: str) -> None:
    with _notifications_lock:
        _notifications.append({
            'type'     : ntype,
            'message'  : message,
            'timestamp': datetime.now().isoformat(),
        })


# ── /scan ─────────────────────────────────────────────────────────────────────

@api_bp.route('/scan', methods=['POST'])
def scan():
    """
    Dipanggil oleh core/face_recognition.py setiap kali wajah diproses.

    Payload JSON:
      { "npm": "...", "nama": "...", "status": "hadir" | "tidak_dikenal" }

    Response:
      200 – berhasil diabsen
      404 – npm tidak terdaftar di sistem
      400 – payload tidak valid
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Payload JSON tidak valid'}), 400

    npm    = str(data.get('npm',    '')).strip()
    nama   = str(data.get('nama',  '')).strip()
    status = str(data.get('status', '')).strip().lower()

    if not npm:
        return jsonify({'error': 'Field npm wajib diisi'}), 400

    # ── Wajah dikenal ──────────────────────────────────────
    if status == 'hadir':
        found = mark_hadir(npm)
        if found:
            label = nama or npm
            _push_notification(f'{label} berhasil diabsen', 'success')
            return jsonify({
                'status': 'hadir',
                'pesan' : f'{label} berhasil diabsen',
            })
        else:
            # NPM ada di face_recognition tapi belum di-register via web
            _push_notification(f'NPM {npm} tidak terdaftar di database', 'warning')
            return jsonify({
                'status': 'tidak_dikenal',
                'pesan' : 'NPM tidak ditemukan di database sistem',
            }), 404

    # ── Wajah tidak dikenal ────────────────────────────────
    else:
        _push_notification('Wajah tidak dikenal terdeteksi', 'warning')
        return jsonify({
            'status': 'tidak_dikenal',
            'pesan' : 'Wajah tidak dapat diidentifikasi',
        })


# ── /api/attendance ───────────────────────────────────────────────────────────

@api_bp.route('/api/attendance', methods=['GET'])
def attendance():
    search   = request.args.get('search',   '').strip()
    status   = request.args.get('status',   '').strip()
    page     = max(1, int(request.args.get('page',     1)))
    per_page = max(1, min(100, int(request.args.get('per_page', 10))))

    rows, total = get_attendance(search, status, page, per_page)
    stats       = get_stats()
    total_pages = max(1, (total + per_page - 1) // per_page)

    return jsonify({
        'data'       : rows,
        'total'      : total,
        'page'       : page,
        'per_page'   : per_page,
        'total_pages': total_pages,
        'stats'      : stats,
    })


# ── /api/stats ────────────────────────────────────────────────────────────────

@api_bp.route('/api/stats', methods=['GET'])
def stats():
    return jsonify(get_stats())


# ── /api/reset ────────────────────────────────────────────────────────────────

@api_bp.route('/api/reset', methods=['POST'])
def reset():
    reset_all()
    _push_notification('Semua absensi telah direset', 'info')
    return jsonify({'status': 'ok', 'pesan': 'Absensi berhasil direset'})


# ── /api/notifications ────────────────────────────────────────────────────────

@api_bp.route('/api/notifications', methods=['GET'])
def notifications():
    """Kembalikan antrian notifikasi lalu kosongkan (consume once)."""
    with _notifications_lock:
        items = _notifications.copy()
        _notifications.clear()
    return jsonify(items)


# ── /api/sync ─────────────────────────────────────────────────────────────────

@api_bp.route('/api/sync', methods=['POST'])
def sync():
    """Sinkron manual users → attendance (berguna setelah register.py dijalankan)."""
    added = sync_from_users()
    msg   = f'{added} mahasiswa baru ditambahkan' if added else 'Tidak ada mahasiswa baru'
    _push_notification(msg, 'success' if added else 'info')
    return jsonify({'status': 'ok', 'added': added, 'pesan': msg})
