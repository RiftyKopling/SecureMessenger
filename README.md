# SecureMessenger

Aplikasi pesan rahasia dengan autentikasi **dongle flashdisk** dan **login biometrik (wajah)**.

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

Jalankan perintah berikut di PowerShell:

```powershell
py -3.11 -m venv env
.\env\Scripts\Activate.ps1
pip install numpy==1.26.4 --only-binary :all:
pip install opencv-contrib-python==4.9.0.80 --only-binary :all:
```

Cek instalasi:

```powershell
python -c "import cv2; print(hasattr(cv2, 'face'))"
```

Output harus `True`.

---

## Struktur Folder

```text
ProyekKripto/
├── dataset/user1/        # foto wajah kamu (5-10 foto)
├── setup_dongle.py       # daftarkan flashdisk (sekali saja)
├── train_wajah.py        # latih model wajah (sekali saja)
├── app.py                # aplikasi utama
├── config.json           # dibuat otomatis
└── trainer.yml           # dibuat otomatis
```

---

## Cara Penggunaan

1. Siapkan 5-10 foto wajah di folder `dataset/user1/`.
2. Latih model wajah (sekali saja), hasilnya `trainer.yml`:
   ```powershell
   python train_wajah.py
   ```
3. Colok flashdisk, lalu daftarkan sebagai dongle (sekali saja):
   ```powershell
   python setup_dongle.py
   ```
4. Jalankan aplikasi:
   ```powershell
   python app.py
   ```

---

## Cara Uji Coba

Setelah `python app.py` dijalankan:

1. Dongle dicek ✅
2. Kamera terbuka. Wajah terdaftar ditandai **kotak hijau + nama**.
3. Wajah orang lain ditandai **kotak merah + "Tidak dikenal"**.
4. Tekan `SPACE` untuk verifikasi, lalu masuk ke aplikasi.
5. Coba dengan wajah orang lain, login harus gagal ❌
6. Cabut flashdisk, aplikasi harus terkunci otomatis.

---
