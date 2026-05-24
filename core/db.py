"""
db.py — database SQLite (database.db)

Tabel: users
  id    INTEGER PRIMARY KEY AUTOINCREMENT
  npm   TEXT UNIQUE NOT NULL
  nama  TEXT NOT NULL
"""

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_FILE = os.path.abspath(
    os.path.join(BASE_DIR, "..", "database.db")
)

# Inisialisasi
def init_db() -> None:
    with sqlite3.connect(DB_FILE) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                npm  TEXT UNIQUE NOT NULL,
                nama TEXT NOT NULL
            )
        """)
        con.commit()


# Panggil saat modul diimport
init_db()

# API publik
def save_user(npm: str, nama: str) -> None:
    """Tambah pengguna baru. Raise sqlite3.IntegrityError jika NPM sudah ada."""
    with sqlite3.connect(DB_FILE) as con:
        con.execute(
            "INSERT INTO users (npm, nama) VALUES (?, ?)",
            (npm, nama)
        )
        con.commit()

def get_name(npm: str) -> str:
    """Kembalikan nama berdasarkan NPM, atau 'Unknown' jika tidak ada."""
    with sqlite3.connect(DB_FILE) as con:
        row = con.execute(
            "SELECT nama FROM users WHERE npm = ?", (npm,)
        ).fetchone()
    return row[0] if row else "Unknown"

def npm_exists(npm: str) -> bool:
    """Cek apakah NPM sudah terdaftar."""
    with sqlite3.connect(DB_FILE) as con:
        row = con.execute(
            "SELECT 1 FROM users WHERE npm = ?", (npm,)
        ).fetchone()
    return row is not None

def get_all_users() -> dict:
    """Kembalikan semua data sebagai dict {npm: nama}."""
    with sqlite3.connect(DB_FILE) as con:
        rows = con.execute("SELECT npm, nama FROM users").fetchall()
    return {npm: nama for npm, nama in rows}

def delete_user(npm: str) -> bool:
    """Hapus pengguna berdasarkan NPM. Kembalikan True jika berhasil."""
    with sqlite3.connect(DB_FILE) as con:
        cursor = con.execute(
            "DELETE FROM users WHERE npm = ?", (npm,)
        )
        con.commit()
    return cursor.rowcount > 0


def list_users() -> None:
    """Print semua pengguna terdaftar ke terminal (untuk debugging)."""
    data = get_all_users()
    if not data:
        print("[DB] Belum ada pengguna terdaftar.")
        return
    print(f"[DB] Total pengguna: {len(data)}")
    for npm, nama in data.items():
        print(f"  {npm} → {nama}")

# Jalankan langsung → tampilkan isi database

if __name__ == "__main__":
    list_users()