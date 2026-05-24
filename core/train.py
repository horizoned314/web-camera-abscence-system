"""
train.py — Melatih model LBPH Face Recognizer.

Alur:
  dataset/{npm}/001.jpg ... 040.jpg
        ↓
  LBPH training
        ↓
  trainer/model.yml  (model siap pakai)
  trainer/label_map.json  (index → npm mapping)
"""

import cv2
import os
import json
import numpy as np
from db import get_all_users

# Konfigurasi path
DATASET_DIR    = "dataset"
TRAINER_DIR    = "trainer"
MODEL_PATH     = os.path.join(TRAINER_DIR, "model.yml")
LABEL_MAP_PATH = os.path.join(TRAINER_DIR, "label_map.json")

os.makedirs(TRAINER_DIR, exist_ok=True)

# Load semua foto dari dataset/
def load_dataset() -> tuple[list, list, dict]:
    """
    Baca semua gambar dari dataset/{npm}/*.jpg.
    Kembalikan:
      - faces      : list numpy array gambar grayscale
      - labels     : list integer label
      - label_map  : {int_label: npm}
    """
    faces      : list = []
    labels     : list = []
    label_map  : dict = {}  # int → npm

    registered = get_all_users()  # {npm: nama}

    if not os.path.isdir(DATASET_DIR):
        raise FileNotFoundError(f"[ERROR] Folder '{DATASET_DIR}' tidak ditemukan.")

    label_index = 0

    for npm in sorted(os.listdir(DATASET_DIR)):
        person_dir = os.path.join(DATASET_DIR, npm)

        if not os.path.isdir(person_dir):
            continue

        if npm not in registered:
            print(f"[SKIP] NPM {npm} tidak ada di database, dilewati.")
            continue

        img_files = [
            f for f in sorted(os.listdir(person_dir))
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        if not img_files:
            print(f"[SKIP] Folder {npm}/ kosong, dilewati.")
            continue

        label_map[label_index] = npm
        nama = registered[npm]

        for img_file in img_files:
            img_path = os.path.join(person_dir, img_file)
            img      = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

            if img is None:
                print(f"  [WARN] Gagal baca: {img_path}")
                continue

            img = cv2.resize(img, (200, 200))
            faces.append(img)
            labels.append(label_index)

        print(f"  [OK] {nama} (NPM: {npm}) — {len(img_files)} foto dimuat, label={label_index}")
        label_index += 1

    return faces, labels, label_map

# Training
def train():
    print("=" * 45)
    print("  TRAINING MODEL FACE RECOGNITION")
    print("=" * 45)

    print("\n[INFO] Memuat dataset...")
    faces, labels, label_map = load_dataset()

    if len(faces) == 0:
        print("[ERROR] Tidak ada data wajah ditemukan. Jalankan register.py terlebih dahulu.")
        return

    print(f"\n[INFO] Total sampel : {len(faces)} foto")
    print(f"[INFO] Total orang  : {len(label_map)} mahasiswa")

    # Konversi ke numpy array
    faces_np  = [np.array(f) for f in faces]
    labels_np = np.array(labels, dtype=np.int32)

    # Buat & latih LBPH recognizer
    print("\n[INFO] Melatih model LBPH...")
    recognizer = cv2.face.LBPHFaceRecognizer_create(
        radius=1,
        neighbors=8,
        grid_x=8,
        grid_y=8,
    )
    recognizer.train(faces_np, labels_np)

    # Simpan model
    recognizer.save(MODEL_PATH)
    print(f"[OK] Model disimpan: {MODEL_PATH}")

    # Simpan label_map
    # JSON key harus string, simpan sebagai {"0": "npm123", ...}
    label_map_str = {str(k): v for k, v in label_map.items()}
    with open(LABEL_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(label_map_str, f, ensure_ascii=False, indent=2)
    print(f"[OK] Label map disimpan: {LABEL_MAP_PATH}")

    print("\n[SELESAI] Model siap digunakan oleh face_recognition.py\n")

# Entry point
if __name__ == "__main__":
    train()