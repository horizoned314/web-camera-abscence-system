import cv2
import json
import os
import threading
import requests
import time
from db import get_name

# ──────────────────────────────────────────────
# Konfigurasi
# ──────────────────────────────────────────────
MODEL_PATH          = os.path.join("trainer", "model.yml")
LABEL_MAP_PATH      = os.path.join("trainer", "label_map.json")
CONFIDENCE_THRESHOLD = 70
DASHBOARD_URL       = "http://localhost:5000/scan"
SEND_TO_DASHBOARD   = True

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay"

# ──────────────────────────────────────────────
# Validasi file
# ──────────────────────────────────────────────
if not os.path.exists(MODEL_PATH):
    print(f"[ERROR] Model tidak ditemukan: {MODEL_PATH}")
    # Jangan exit() agar server Flask tidak mati, cukup print error
if not os.path.exists(LABEL_MAP_PATH):
    print(f"[ERROR] Label map tidak ditemukan: {LABEL_MAP_PATH}")

# ──────────────────────────────────────────────
# Load model (Hanya dijalankan sekali saat server nyala)
# ──────────────────────────────────────────────
recognizer = cv2.face.LBPHFaceRecognizer_create()
if os.path.exists(MODEL_PATH):
    recognizer.read(MODEL_PATH)

label_map = {}
if os.path.exists(LABEL_MAP_PATH):
    with open(LABEL_MAP_PATH, "r", encoding="utf-8") as f:
        label_map = json.load(f)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

print("[INFO] Model Face Recognition siap digunakan.")

# ──────────────────────────────────────────────
# Dashboard sender
# ──────────────────────────────────────────────
_last_sent = {}
COOLDOWN_SECONDS = 10

def send_to_dashboard(npm, nama, status):
    if not SEND_TO_DASHBOARD:
        return

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
        except:
            pass

    threading.Thread(target=_post, daemon=True).start()

def resolve_identity(label, confidence):
    if confidence < CONFIDENCE_THRESHOLD:
        npm   = label_map.get(str(label), "?")
        nama  = get_name(npm)
        return f"{nama} [{npm}]", npm, nama, (0,220,0), "hadir"
    else:
        return "Tidak Dikenal", "", "", (0,0,220), "tidak_dikenal"

# ──────────────────────────────────────────────
# Generator Stream untuk Web
# ──────────────────────────────────────────────
def gen_frames():
    ESP_URL = "http://192.168.1.26/stream?buffer_size=1024&fifo_size=100000&overrun_nonfatal=1"

    cam = cv2.VideoCapture(ESP_URL, cv2.CAP_FFMPEG)
    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cam.set(cv2.CAP_PROP_FPS, 10)

    while True:
        cam.grab()
        ret, frame = cam.read()

        if not ret or frame is None or frame.size == 0:
            cam.release()
            time.sleep(1)
            cam = cv2.VideoCapture(ESP_URL, cv2.CAP_FFMPEG)
            cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )

        display = frame.copy()

        for (x, y, w, h) in faces:
            face_roi = cv2.resize(gray[y:y+h, x:x+w], (200, 200))
            label, confidence = recognizer.predict(face_roi)
            text, npm, nama, color, status = resolve_identity(label, confidence)

            send_to_dashboard(npm, nama, status)

            cv2.rectangle(display, (x,y), (x+w,y+h), color, 2)
            cv2.rectangle(display, (x,y-30), (x+w,y), color, -1)
            cv2.putText(display, text, (x+4, y-8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 1)
            cv2.putText(display, f"conf: {confidence:.1f}", (x, y+h+18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

        # Ubah gambar OpenCV menjadi JPEG byte format agar bisa dibaca di HTML
        ret, buffer = cv2.imencode('.jpg', display)
        frame_bytes = buffer.tobytes()

        # Yield frame ke Flask
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        time.sleep(0.03)