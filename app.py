# app.py
import subprocess
import json
import os
import time
import cv2

DRIVE = "E:"  # ganti sesuai drive flashdisk

# Mapping label → nama user (urut sesuai folder dataset)
NAMA_USER = {0: "user1"}   # kalau ada user2: {0:"user1", 1:"user2"}

# Threshold: semakin KECIL = semakin ketat
# 0-40 = sangat mirip, 40-60 = mirip, >80 = beda orang
THRESHOLD = 60

# ================= CEK DONGLE =================
def get_serial(drive):
    try:
        output = subprocess.check_output(f"vol {drive}", shell=True, text=True)
        for line in output.splitlines():
            if "Serial Number" in line:
                return line.split()[-1]
    except:
        return None

def dongle_valid():
    serial = get_serial(DRIVE)
    if serial is None:
        return False
    with open("config.json") as f:
        config = json.load(f)
    if serial != config["serial"]:
        return False
    if not os.path.exists(f"{DRIVE}/dongle.key"):
        return False
    return True

# ================= LOGIN FACE MATCH =================
def login_biometric():
    # Muat model
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("trainer.yml")

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    cam = cv2.VideoCapture(0)
    print("\n🔐 Arahkan wajah ke kamera. Tekan SPACE untuk verifikasi, ESC untuk batal.")

    hasil_login = False
    while True:
        ret, frame = cam.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        wajah = face_cascade.detectMultiScale(gray, 1.1, 4)

        for (x, y, w, h) in wajah:
            roi = gray[y:y+h, x:x+w]
            roi = cv2.resize(roi, (200, 200))

            label, jarak = recognizer.predict(roi)

            if jarak < THRESHOLD:
                nama = NAMA_USER.get(label, "unknown")
                teks = f"{nama} ({int(jarak)})"
                warna = (0, 255, 0)  # hijau = cocok
            else:
                teks = f"Tidak dikenal ({int(jarak)})"
                warna = (0, 0, 255)  # merah = tidak cocok

            cv2.rectangle(frame, (x, y), (x+w, y+h), warna, 2)
            cv2.putText(frame, teks, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, warna, 2)

        cv2.imshow("Login Biometric", frame)

        key = cv2.waitKey(1)
        if key == 32:  # SPACE → verifikasi
            # Cek ulang frame terakhir
            for (x, y, w, h) in wajah:
                roi = gray[y:y+h, x:x+w]
                roi = cv2.resize(roi, (200, 200))
                label, jarak = recognizer.predict(roi)
                if jarak < THRESHOLD:
                    hasil_login = True
                    break
            break
        elif key == 27:  # ESC → batal
            break

    cam.release()
    cv2.destroyAllWindows()
    return hasil_login

# ================= PROGRAM UTAMA =================
def main():
    print("=== APLIKASI KRIPTOGRAFI ===")

    # 1. Cek dongle
    print("\n[1] Memeriksa dongle flashdisk...")
    if not dongle_valid():
        print("❌ Dongle tidak valid! Aplikasi tidak bisa dijalankan.")
        return
    print("✅ Dongle valid.")

    # 2. Login face match
    print("\n[2] Login biometric.")
    if not login_biometric():
        print("❌ Wajah tidak cocok. Aplikasi ditutup.")
        return
    print("✅ Login berhasil!")

    # 3. Aplikasi jalan
    print("\n🎉 Selamat datang di Aplikasi Kriptografi!")
    print("(isi fitur enkripsi di sini)")

    # 4. Pantau dongle
    print("\n[!] Dongle dipantau. Cabut flashdisk untuk uji.")
    while True:
        if not dongle_valid():
            print("⚠️ Dongle dicabut! Aplikasi dikunci.")
            break
        time.sleep(2)

if __name__ == "__main__":
    main()