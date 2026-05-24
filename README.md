# Attendify — Face Recognition Attendance System

Sistem absensi mahasiswa berbasis pengenalan wajah menggunakan Python OpenCV dan dashboard web realtime dengan Flask.

---

## Struktur Project

```
web-camera-absence-system/
│
├── database.db                  # SQLite database (dibagi antara core & web)
│
├── core/                        # Sistem face recognition (Python)
│   ├── db.py                    # Operasi database (SQLite)
│   ├── register.py              # Registrasi wajah mahasiswa
│   ├── train.py                 # Training model LBPH
│   ├── face_recognition.py      # Pengenalan wajah realtime
│   ├── dataset/                 # Foto wajah hasil registrasi
│   │   └── {npm}/               # Folder per mahasiswa
│   │       └── 001.jpg ... 040.jpg
│   └── trainer/                 # Output model training
│       ├── model.yml
│       └── label_map.json
│
└── web/                         # Dashboard web (Flask)
    ├── app.py
    ├── requirements.txt
    ├── routes/
    │   ├── dashboard.py         # Halaman utama
    │   └── api.py               # REST API endpoints
    ├── models/
    │   └── attendance.py        # Model database absensi
    ├── templates/
    │   ├── base.html
    │   └── dashboard.html
    └── static/
        ├── css/style.css
        └── js/dashboard.js
```

---

## Cara Penggunaan

### 1. Registrasi Mahasiswa

```bash
cd core/
python register.py
```

Masukkan nama dan NPM, lalu hadapkan wajah ke kamera. Sistem akan mengambil **80 foto** secara otomatis dan menyimpannya di `dataset/{npm}/`.

### 2. Training Model

```bash
python train.py
```

Melatih model LBPH dari semua foto di `dataset/`. Hasil disimpan di `trainer/model.yml` dan `trainer/label_map.json`.

### 3. Jalankan Dashboard Web

```bash
cd web/
python app.py
```

Buka browser di `http://localhost:5000`.

### 4. Jalankan Face Recognition

```bash
cd core/
pip install requests
python face_recognition.py
```

Setiap wajah yang dikenali akan otomatis memperbarui status absensi di dashboard.

---

## Teknologi

| Komponen | Teknologi |
|---|---|
| Face detection | OpenCV Haar Cascade |
| Face recognition | OpenCV LBPH (`opencv-contrib-python`) |
| Database | SQLite |
| Backend web | Flask |
| Frontend | Tailwind CSS, Vanilla JavaScript |
| Integrasi | HTTP REST (POST `/scan`) |

---

## API Endpoint

| Method | Endpoint | Keterangan |
|---|---|---|
| `POST` | `/scan` | Terima data dari face recognition |
| `GET` | `/api/attendance` | Data absensi (search, filter, pagination) |
| `GET` | `/api/stats` | Statistik kehadiran |
| `POST` | `/api/reset` | Reset semua absensi |
| `GET` | `/api/notifications` | Antrian notifikasi realtime |
| `POST` | `/api/sync` | Sinkron mahasiswa dari tabel `users` |

Contoh payload `/scan`:

```json
{
  "npm": "250007",
  "nama": "Rafif Phratama",
  "status": "hadir"
}
```

---

## Instalasi Dependency

```bash
pip install -r requirements.txt
```

> **Pastikan menggunakan `opencv-contrib-python`**, bukan `opencv-python`, karena modul `cv2.face` hanya tersedia di paket contrib.

---

## Alur Sistem

```
register.py → dataset/{npm}/ → train.py → trainer/model.yml
                                                    ↓
                               face_recognition.py (kamera)
                                                    ↓
                                          POST /scan (HTTP)
                                                    ↓
                                        Dashboard (realtime polling)
```