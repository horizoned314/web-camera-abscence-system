import cv2
import os
import json
from db import save_user, npm_exists

# Konfigurasi
DATASET_DIR   = "dataset"
SAMPLE_TARGET = 100          # jumlah foto yang diambil per orang
SAMPLE_DELAY  = 5           # ambil foto setiap N frame (hindari duplikat)

# Input data mahasiswa
print("=" * 40)
print("  REGISTRASI WAJAH MAHASISWA")
print("=" * 40)

nama = input("Nama lengkap : ").strip()
npm  = input("NPM          : ").strip()

if not nama or not npm:
    print("[ERROR] Nama dan NPM tidak boleh kosong.")
    exit(1)

if npm_exists(npm):
    print(f"[ERROR] NPM {npm} sudah terdaftar. Gunakan NPM lain atau hapus data lama.")
    exit(1)

# Buat folder dataset/{npm}/
user_dir = os.path.join(DATASET_DIR, npm)
os.makedirs(user_dir, exist_ok=True)

# Setup kamera & detektor
cam = cv2.VideoCapture(0)
if not cam.isOpened():
    print("[ERROR] Kamera tidak dapat dibuka.")
    exit(1)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

sample_count = 0
frame_count  = 0

print(f"\n[INFO] Kamera aktif. Hadapkan wajah ke kamera.")
print(f"[INFO] Akan mengambil {SAMPLE_TARGET} foto. Tekan ESC untuk batal.\n")

# Loop pengambilan foto
while True:
    ret, frame = cam.read()
    if not ret:
        print("[ERROR] Gagal membaca frame kamera.")
        break

    frame_count += 1
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80),
    )

    display = frame.copy()

    for (x, y, w, h) in faces:
        # Simpan foto hanya setiap SAMPLE_DELAY frame agar tidak terlalu mirip
        if frame_count % SAMPLE_DELAY == 0 and sample_count < SAMPLE_TARGET:
            face_img  = gray[y : y + h, x : x + w]
            face_img  = cv2.resize(face_img, (200, 200))
            file_path = os.path.join(user_dir, f"{sample_count + 1:03d}.jpg")
            cv2.imwrite(file_path, face_img)
            sample_count += 1

        # Tampilan kotak & progress
        color = (0, 255, 0) if sample_count < SAMPLE_TARGET else (0, 200, 255)
        cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)
        cv2.putText(
            display,
            f"Sample: {sample_count}/{SAMPLE_TARGET}",
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
        )

    # HUD info
    cv2.putText(
        display,
        f"Nama: {nama}  |  NPM: {npm}",
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )

    # Progress bar sederhana
    bar_x, bar_y, bar_w, bar_h = 10, 40, 300, 14
    filled = int(bar_w * sample_count / SAMPLE_TARGET)
    cv2.rectangle(display, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (80, 80, 80), -1)
    cv2.rectangle(display, (bar_x, bar_y), (bar_x + filled, bar_y + bar_h), (0, 220, 0), -1)
    cv2.putText(
        display,
        f"{int(sample_count / SAMPLE_TARGET * 100)}%",
        (bar_x + bar_w + 8, bar_y + bar_h - 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1,
    )

    cv2.imshow("Registrasi Wajah - ESC untuk batal", display)

    key = cv2.waitKey(1)
    if key == 27:  # ESC → batal
        print("\n[INFO] Registrasi dibatalkan oleh pengguna.")
        # Hapus foto yang sudah terlanjur tersimpan
        import shutil
        shutil.rmtree(user_dir, ignore_errors=True)
        cam.release()
        cv2.destroyAllWindows()
        exit(0)

    if sample_count >= SAMPLE_TARGET:
        print(f"\n[OK] {SAMPLE_TARGET} foto berhasil disimpan di: {user_dir}")
        break

cam.release()
cv2.destroyAllWindows()

# Simpan data ke database
save_user(npm, nama)
print(f"[OK] Data '{nama}' (NPM: {npm}) berhasil disimpan ke database.")
print("[INFO] Jalankan train.py untuk melatih model.\n")