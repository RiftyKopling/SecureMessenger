# SecureMessenger

Aplikasi pesan rahasia dengan autentikasi dongle flashdisk dan login biometrik (wajah).

Proyek tugas mata kuliah Kriptografi, Semester 5.

---

## Fitur

- Flashdisk sebagai dongle (kunci fisik)
- Login wajah menggunakan kamera
- Aplikasi terkunci otomatis jika dongle dicabut

---

## Persyaratan

- Windows 10/11
- Python 3.11 (jangan 3.13+)
- Webcam
- Flashdisk

---

## Instalasi
py -3.11 -m venv env
.\env\Scripts\Activate.ps1
pip install numpy==1.26.4 --only-binary :all:
pip install opencv-contrib-python==4.9.0.80 --only-binary :all:

Cek instalasi:
powershell
python -c "import cv2; print(hasattr(cv2, 'face'))"
Harus output True.

Struktur Folder
text
ProyekKripto/
├── dataset/user1/        # foto wajah kamu (5-10 foto)
├── setup_dongle.py       # daftarkan flashdisk (sekali saja)
├── train_wajah.py        # latih model wajah (sekali saja)
├── app.py                # aplikasi utama
├── config.json           # dibuat otomatis
└── trainer.yml           # dibuat otomatis

🧪 Cara Uji Coba
1. Siapkan foto di dataset/user1/ (5-10 foto)
2. Jalankan python train_wajah.py → hasilkan trainer.yml
3. Colok flashdisk, jalankan python setup_dongle.py (dari sebelumnya)
4. Jalankan python app.py:
5. Dongle dicek ✅
6. Kamera terbuka → wajah kamu dikasih kotak hijau + nama
7. Wajah orang lain → kotak merah + "Tidak dikenal"
8. Tekan SPACE → verifikasi → masuk aplikasi
9. Coba pakai wajah orang lain → login gagal ❌

Mata Kuliah Kriptografi, Semester 5
Dosen: [Nama Dosen]
