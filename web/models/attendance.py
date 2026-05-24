"""
models/attendance.py
Semua operasi database untuk tabel `attendance`.
Berbagi database.db yang sama dengan core/ (users table).
"""

import sqlite3
from datetime import datetime
from flask import g, current_app


# ── Koneksi ──────────────────────────────────────────────────────────────────

def get_db():
    """Kembalikan koneksi SQLite per-request (disimpan di Flask g)."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    """Tutup koneksi di akhir request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ── Inisialisasi ──────────────────────────────────────────────────────────────

def init_db():
    """
    Dipanggil sekali saat app start (app context).
    Buat tabel jika belum ada, lalu sinkron dari tabel users.
    """
    db_path = current_app.config['DATABASE']
    con = sqlite3.connect(db_path)

    # Pastikan tabel users ada (dibuat oleh core/db.py, recreate jika belum)
    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            npm  TEXT UNIQUE NOT NULL,
            nama TEXT NOT NULL
        )
    """)

    # Tabel attendance: satu baris per mahasiswa per sesi
    con.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            npm         TEXT UNIQUE NOT NULL,
            nama        TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'tidak_hadir',
            waktu_hadir TEXT DEFAULT NULL,
            updated_at  TEXT DEFAULT NULL
        )
    """)

    con.commit()
    _sync_users(con)
    con.close()


def _sync_users(con):
    """
    Insert mahasiswa dari tabel users ke attendance jika belum ada.
    Dipanggil saat init dan setiap GET /api/attendance.
    """
    con.execute("""
        INSERT OR IGNORE INTO attendance (npm, nama)
        SELECT npm, nama FROM users
    """)
    con.commit()


# ── Baca ──────────────────────────────────────────────────────────────────────

def get_attendance(search: str = '', status: str = '', page: int = 1, per_page: int = 10):
    """
    Kembalikan (list[dict], total) dengan filter opsional.
    Juga sinkron users → attendance terlebih dahulu.
    """
    db = get_db()
    _sync_users(db)

    where  = "WHERE 1=1"
    params = []

    if search:
        where += " AND (npm LIKE ? OR nama LIKE ?)"
        params += [f'%{search}%', f'%{search}%']

    if status and status != 'semua':
        where += " AND status = ?"
        params.append(status)

    total = db.execute(
        f"SELECT COUNT(*) FROM attendance {where}", params
    ).fetchone()[0]

    order  = "ORDER BY CASE status WHEN 'hadir' THEN 0 ELSE 1 END, nama ASC"
    limit  = "LIMIT ? OFFSET ?"
    rows   = db.execute(
        f"SELECT * FROM attendance {where} {order} {limit}",
        params + [per_page, (page - 1) * per_page],
    ).fetchall()

    return [dict(r) for r in rows], total


def get_stats() -> dict:
    db     = get_db()
    total  = db.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
    hadir  = db.execute("SELECT COUNT(*) FROM attendance WHERE status='hadir'").fetchone()[0]
    return {
        'total'       : total,
        'hadir'       : hadir,
        'tidak_hadir' : total - hadir,
    }


# ── Tulis ─────────────────────────────────────────────────────────────────────

def mark_hadir(npm: str) -> bool:
    """
    Set status mahasiswa menjadi 'hadir'.
    Return True jika NPM ditemukan di attendance, False jika tidak terdaftar.
    """
    db  = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cur = db.execute(
        "UPDATE attendance SET status='hadir', waktu_hadir=?, updated_at=? WHERE npm=?",
        (now, now, npm),
    )
    db.commit()
    return cur.rowcount > 0


def reset_all() -> None:
    """Reset seluruh status ke 'tidak_hadir'."""
    db  = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db.execute(
        "UPDATE attendance SET status='tidak_hadir', waktu_hadir=NULL, updated_at=?",
        (now,),
    )
    db.commit()


def sync_from_users() -> int:
    """
    Public: sinkron ulang users → attendance.
    Kembalikan jumlah baris baru yang ditambahkan.
    """
    db  = get_db()
    cur = db.execute("""
        INSERT OR IGNORE INTO attendance (npm, nama)
        SELECT npm, nama FROM users
    """)
    db.commit()
    return cur.rowcount
