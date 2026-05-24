"""
face_recognition.py — Pengenalan wajah realtime + integrasi dashboard web.

Prasyarat:
  - trainer/model.yml
  - trainer/label_map.json
  - db.json / database.db
  - pip install requests

Saat wajah dikenali → POST ke http://localhost:5000/scan
"""

import cv2
import json
import os
import threading
import requests
from db import get_name

# ──────────────────────────────────────────────
# Konfigurasi
# ──────────────────────────────────────────────
MODEL_PATH          = os.path.join("trainer", "model.yml")
LABEL_MAP_PATH      = os.path.join("trainer", "label_map.json")
CONFIDENCE_THRESHOLD = 70
DASHBOARD_URL       = "http://localhost:5000/scan"
SEND_TO_DASHBOARD   = True   # Set False untuk nonaktifkan integrasi web


# ──────────────────────────────────────────────
# Validasi file model
# ──────────────────────────────────────────────
if not os.path.exists(MODEL_PATH):
    print(f"[ERROR] Model tidak ditemukan: {MODEL_PATH}")
    print("[INFO] Jalankan train.py terlebih dahulu.")
    exit(1)

if not os.path.exists(LABEL_MAP_PATH):
    print(f"[ERROR] Label map tidak ditemukan: {LABEL_MAP_PATH}")
    exit(1)


# ──────────────────────────────────────────────
# Load model & label map
# ──────────────────────────────────────────────
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(MODEL_PATH)

with open(LABEL_MAP_PATH, "r", encoding="utf-8") as f:
    label_map: dict = json.load(f)   # {"0": "npm123", ...}

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

print("[INFO] Model dimuat. Kamera aktif. Tekan ESC untuk keluar.")


# ──────────────────────────────────────────────
# Kirim data ke dashboard (non-blocking)
# ──────────────────────────────────────────────
# Cooldown: hindari spam POST untuk wajah yang sama
_last_sent: dict = {}   # {npm: timestamp}
COOLDOWN_SECONDS = 10


def send_to_dashboard(npm: str, nama: str, status: str) -> None:
    """
    Kirim payload ke POST /scan di Flask dashboard.
    Dijalankan di thread terpisah agar tidak memblokir kamera.
    """
    if not SEND_TO_DASHBOARD:
        return

    import time
    now = time.time()
    last = _last_sent.get(npm or "unknown", 0)
    if now - last < COOLDOWN_SECONDS:
        return
    _last_sent[npm or "unknown"] = now

    def _post():
        try:
            requests.post(
                DASHBOARD_URL,
                json={"npm": npm, "nama": nama, "status": status},
                timeout=2,
            )
        except requests.exceptions.ConnectionError:
            pass   # Dashboard belum dijalankan — abaikan
        except Exception as e:
            print(f"[WARN] Gagal kirim ke dashboard: {e}")

    threading.Thread(target=_post, daemon=True).start()


# ──────────────────────────────────────────────
# Helper: label int → info
# ──────────────────────────────────────────────

def resolve_identity(label: int, confidence: float):
    """Return (display_text, npm, nama, warna_kotak, status_api)."""
    if confidence < CONFIDENCE_THRESHOLD:
        npm   = label_map.get(str(label), "?")
        nama  = get_name(npm)
        text  = f"{nama}  [{npm}]"
        color = (0, 220, 0)    # hijau
        return text, npm, nama, color, "hadir"
    else:
        return "Tidak Dikenal", "", "", (0, 0, 220), "tidak_dikenal"


# ──────────────────────────────────────────────
# Loop kamera
# ──────────────────────────────────────────────
cam = cv2.VideoCapture(0)
if not cam.isOpened():
    print("[ERROR] Kamera tidak dapat dibuka.")
    exit(1)

while True:
    ret, frame = cam.read()
    if not ret:
        break

    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80),
    )

    for (x, y, w, h) in faces:
        face_roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
        label, confidence = recognizer.predict(face_roi)
        display_text, npm, nama, color, api_status = resolve_identity(label, confidence)

        # ── Kirim ke dashboard ──
        send_to_dashboard(npm, nama, api_status)

        # ── Tampilan ──
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        cv2.rectangle(frame, (x, y-30), (x+w, y), color, -1)
        cv2.putText(frame, display_text, (x+4, y-8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"conf: {confidence:.1f}", (x, y+h+18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

    cv2.putText(frame, "ESC: Keluar", (10, frame.shape[0]-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180,180,180), 1)

    cv2.imshow("Face Recognition", frame)
    if cv2.waitKey(1) == 27:
        break

cam.release()
cv2.destroyAllWindows()
print("[INFO] Kamera ditutup.")
