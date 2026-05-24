"""
face_recognition.py — Pengenalan wajah realtime menggunakan model LBPH.

Prasyarat:
  - trainer/model.yml      (hasil train.py)
  - trainer/label_map.json (hasil train.py)
  - db.json                (hasil register.py)

Output:
  - Tampil nama + NPM di layar jika wajah dikenali
  - Confidence ditampilkan (makin kecil = makin yakin)
"""

import cv2
import json
import os
from db import get_name

# Konfigurasi
MODEL_PATH     = os.path.join("trainer", "model.yml")
LABEL_MAP_PATH = os.path.join("trainer", "label_map.json")

# Threshold confidence LBPH:
# nilai < CONFIDENCE_THRESHOLD → dianggap dikenali
# nilai >= threshold → "Tidak Dikenal"
CONFIDENCE_THRESHOLD = 70

# Validasi file model
if not os.path.exists(MODEL_PATH):
    print(f"[ERROR] Model tidak ditemukan: {MODEL_PATH}")
    print("[INFO] Jalankan train.py terlebih dahulu.")
    exit(1)

if not os.path.exists(LABEL_MAP_PATH):
    print(f"[ERROR] Label map tidak ditemukan: {LABEL_MAP_PATH}")
    print("[INFO] Jalankan train.py terlebih dahulu.")
    exit(1)

# Load model & label map
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read(MODEL_PATH)

with open(LABEL_MAP_PATH, "r", encoding="utf-8") as f:
    label_map: dict = json.load(f)  # {"0": "npm123", ...}

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

print("[INFO] Model dimuat. Kamera aktif. Tekan ESC untuk keluar.")

# Helper: label int → info teks
def resolve_identity(label: int, confidence: float) -> tuple[str, str, tuple]:
    """
    Kembalikan (display_name, npm, warna_kotak).
    Warna: hijau = dikenali, merah = tidak dikenal.
    """
    if confidence < CONFIDENCE_THRESHOLD:
        npm  = label_map.get(str(label), "?")
        nama = get_name(npm)
        text = f"{nama}  [{npm}]"
        color = (0, 220, 0)   # hijau
    else:
        npm   = "-"
        text  = "Tidak Dikenal"
        color = (0, 0, 220)   # merah
    return text, npm, color

# Loop kamera
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
        face_roi = gray[y : y + h, x : x + w]
        face_roi = cv2.resize(face_roi, (200, 200))

        label, confidence = recognizer.predict(face_roi)
        display_text, npm, color = resolve_identity(label, confidence)

        # Kotak wajah
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

        # Label nama & NPM
        cv2.rectangle(frame, (x, y - 30), (x + w, y), color, -1)
        cv2.putText(
            frame,
            display_text,
            (x + 4, y - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        # Confidence (debug)
        cv2.putText(
            frame,
            f"conf: {confidence:.1f}",
            (x, y + h + 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
        )

    cv2.putText(
        frame,
        "ESC: Keluar",
        (10, frame.shape[0] - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (180, 180, 180),
        1,
    )

    cv2.imshow("Face Recognition", frame)

    if cv2.waitKey(1) == 27:
        break

cam.release()
cv2.destroyAllWindows()
print("[INFO] Kamera ditutup.")