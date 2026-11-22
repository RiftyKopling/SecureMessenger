# Mini Secure Chat — Aplikasi Chat Terenkripsi Berbasis Kriptografi

## 1. Latar Belakang & Tujuan

Proyek ini dibuat untuk memenuhi **Tugas Akhir mata kuliah Kriptografi**. Tujuannya adalah membangun aplikasi chat desktop yang **benar-benar berjalan antar komputer** dalam jaringan lokal (LAN), sekaligus mendemonstrasikan berbagai teknik kriptografi klasik dan modern dalam satu sistem terpadu.

Setiap komponen dirancang untuk menunjukkan **satu teknik kriptografi spesifik**: autentikasi dongle, biometrik wajah, hashing password, enkripsi pesan (klasik + modern), enkripsi file, enkripsi kolom database, steganografi gambar, dan integritas data berbasis hash chain (blockchain sederhana).

## 2. Persyaratan Tugas & Pemenuhannya

| Persyaratan Tugas | Implementasi pada Proyek |
| :--- | :--- |
| Login biometrik + hanya bisa dihidupkan dengan dongle | Verifikasi wajah LBPH (OpenCV) + validasi serial flashdisk & file `dongle.key`. Kunci enkripsi (`keys.enc`) hanya bisa dibuka dengan isi dongle |
| Login aplikasi menggunakan algoritma kriptografi | Password di-hash dengan **PBKDF2-HMAC-SHA256 + salt acak** (berbasis SHA-256) |
| Pesan teks dienkripsi (algoritma modern & klasik) | **Super enkripsi**: Vigenère (klasik) lalu Fernet/AES (modern). Ciphertext ditampilkan di UI |
| Pesan file dienkripsi berbeda dari teks | File dienkripsi dengan AES-GCM, kunci terpisah dari pesan teks |
| Pesan penting dienkripsi di database | Kolom `isi_pesan` di SQLite selalu berisi ciphertext |
| Pesan gambar diamankan dengan steganografi | Teks dienkripsi dulu, lalu disisipkan ke piksel gambar PNG (LSB) |
| Aset penting diamankan dengan blockchain sederhana | Log aktivitas (pengirim, waktu, hash pesan) dirantai dengan SHA-256 dan dapat diverifikasi |
| Laporan & presentasi | Dokumen ini + demo aplikasi pada 4 pertemuan terakhir |

## 3. Arsitektur Sistem

Arsitektur **client–server terpusat** pada **jaringan lokal (LAN)**.

```
+----------------+        WebSocket (LAN)        +----------------------+
|  Client A      | <--------------------------> |  Server (Ubuntu VM)  |
|  (PySide6)     |                              |  - WebSocket server  |
+----------------+                              |  - SQLite (cipher)   |
                                                |  - Hash chain log    |
+----------------+        WebSocket (LAN)        |                      |
|  Client B      | <--------------------------> |                      |
|  (PySide6)     |                              +----------------------+
+----------------+
```

- **Server**: Ubuntu Server di **VirtualBox** (Bridged Adapter) lewat **hotspot HP**, sehingga punya IP sendiri di jaringan.
- **Client**: aplikasi desktop PySide6 di Windows (serial dongle dibaca dengan perintah `vol`).
- **Enkripsi dilakukan di sisi client**. Server hanya menerima, menyimpan, dan meneruskan **ciphertext**. Kunci tidak pernah ada di server.

## 4. Teknologi yang Digunakan

| Komponen | Teknologi |
| :--- | :--- |
| Antarmuka desktop | PySide6 |
| Verifikasi wajah | OpenCV contrib (LBPH Face Recognizer) |
| Enkripsi pesan & file | `cryptography` (Fernet, AES-GCM) |
| Cipher klasik | Vigenère (implementasi mandiri) |
| Hash password & derivasi kunci | `hashlib.pbkdf2_hmac` (SHA-256) |
| Steganografi | Pillow + NumPy (LSB) |
| Hash chain | SHA-256 (implementasi mandiri) |
| Database | SQLite |
| Komunikasi jaringan | WebSocket (`websockets`) |
| Server | Ubuntu Server di VirtualBox (Bridged Adapter) |
| Jaringan | Hotspot HP |

## 5. Alur Penggunaan Aplikasi

1. Pengguna mencolokkan flashdisk dongle.
2. Aplikasi memeriksa **serial number** flashdisk dan file `dongle.key`.
3. Kamera aktif dan meminta verifikasi wajah. Pengguna menekan SPACE.
4. Jika wajah cocok (jarak di bawah threshold) dan dongle valid, pengguna memasukkan password.
5. Password diverifikasi (PBKDF2 + salt). Jika benar, `keys.enc` dibuka dengan kunci turunan dari dongle, dan jendela chat terbuka.
6. Pengguna menghubungkan client ke server dengan memasukkan IP (`192.168.x.x:8765`).
7. Pesan dienkripsi di client (Vigenère lalu Fernet), ciphertext dikirim ke server, lalu diteruskan ke client lain.
8. Client penerima mendekripsi dan menampilkan pesan asli.
9. Selama aplikasi berjalan, sistem memeriksa dongle setiap beberapa detik. Jika dicabut, kunci dihapus dari memori dan aplikasi terkunci.

## 6. Modul Kriptografi & Cara Kerjanya

### 6.1 Verifikasi Dongle & Pengunci Kunci
- Serial number flashdisk dibaca dengan `vol` dan dicocokkan dengan `config.json`. File `dongle.key` harus ada.
- Kunci enkripsi disimpan di `keys.enc` (terenkripsi), **bukan** file teks biasa. Kunci pembukanya diturunkan (PBKDF2) dari isi `dongle.key` + serial flashdisk.
- Akibatnya, tanpa dongle yang benar, aplikasi secara kriptografis tidak bisa mendekripsi apa pun, bukan sekadar "dicek lalu diizinkan".

### 6.2 Login Biometrik
**LBPH Face Recognizer** (OpenCV). Model dilatih dari dataset wajah pengguna (`trainer.yml`). Jarak di bawah threshold (disarankan 45–50, disesuaikan dengan pencahayaan) dianggap cocok.

### 6.3 Login Password
Password tidak disimpan asli. Disimpan `salt` acak (16 byte) dan `hash = PBKDF2-HMAC-SHA256(password, salt, 200000 iterasi)` di `user.json`. Verifikasi dilakukan dengan membandingkan hash (`hmac.compare_digest`).

### 6.4 Enkripsi Pesan Teks (Super Enkripsi)
1. **Vigenère** (klasik): huruf pada teks digeser sesuai kunci. Karakter non-huruf dibiarkan.
2. **Fernet** (modern, AES-128-CBC + HMAC): hasil Vigenère dienkripsi lagi, menghasilkan ciphertext Base64.

Dekripsi dilakukan terbalik (Fernet lalu Vigenère). UI menampilkan ciphertext di bawah bubble chat sebagai bukti.

### 6.5 Enkripsi File
File dibaca biner dan dienkripsi dengan **AES-GCM** (kunci terpisah dari pesan teks, nonce acak 12 byte di depan data). Dikirim lewat WebSocket sebagai Base64. Penerima mendekripsi sebelum menyimpan. Batas ukuran file demo: 5 MB.

### 6.6 Enkripsi Kolom Database
Kolom `isi_pesan` di SQLite selalu berisi ciphertext. Saat demo, tunjukkan isi tabel di server: tidak ada teks asli. Dekripsi hanya terjadi di client.

### 6.7 Steganografi Gambar
Teks dienkripsi (6.4), diubah menjadi bit, lalu disisipkan ke bit paling rendah (LSB) kanal piksel gambar. Aturan:
- Gambar harus disimpan/dikirim sebagai **PNG** (JPEG merusak LSB).
- Payload diawali **header panjang 32-bit** agar ekstraksi tahu kapan berhenti.
- Penerima mengekstrak bit, lalu mendekripsi.

### 6.8 Hash Chain (Blockchain Sederhana)
Setiap aktivitas (kirim pesan/file/gambar) dicatat sebagai blok:
`{index, timestamp, data, prev_hash, hash}`
- `data` berisi `{type, sender, msg_hash}` dengan `msg_hash = SHA-256(ciphertext)`.
- `hash = SHA-256(index + timestamp + data + prev_hash)`.
- Verifikasi: hitung ulang hash tiap blok dan cek `prev_hash`-nya.
- Client menyimpan **hash blok terakhir** secara lokal. Jika rantai di server diubah lalu dihitung ulang seluruhnya, hash akhir akan berbeda dan terdeteksi.

## 7. Struktur Proyek

```
proyek-kriptografi/
├── AGENTS.md              # Aturan untuk AI agent
├── PROTOCOL.md            # Format pesan, tabel DB, format blok
├── penjelasan_proyek.md   # Dokumen ini
├── requirements.txt
├── client/
│   ├── main.py            # Entry point PySide6
│   ├── auth.py            # Verifikasi dongle + wajah + password
│   ├── crypto_utils.py    # Vigenere, Fernet, AES-GCM, PBKDF2, steganografi
│   ├── network.py         # WebSocket client (QThread)
│   └── ui_main.py         # Jendela utama chat
├── server/
│   ├── server.py          # WebSocket server
│   ├── blockchain.py      # Hash chain
│   └── db_server.py       # SQLite server
├── tools/
│   ├── make_keys.py       # Buat keys.enc dari dongle (sekali jalan)
│   ├── make_user.py       # Buat user.json (salt + hash password)
│   └── train_face.py      # Latih trainer.yml dari dataset/
├── dataset/               # Foto wajah pengguna
├── trainer.yml            # Model wajah
├── config.json            # Serial dongle, threshold, dev_mode
├── user.json              # username, salt, hash
├── keys.enc               # Kunci terenkripsi (dibuka dengan dongle)
└── dongle.key             # File kunci pada flashdisk
```

## 8. Alur Demo Presentasi

1. Nyalakan **hotspot HP**.
2. Nyalakan laptop server, jalankan VirtualBox Ubuntu Server (Bridged Adapter).
3. Catat IP Ubuntu (`ip a`), jalankan `server.py`.
4. Nyalakan laptop client, buka aplikasi.
5. **Dongle**: coba tanpa flashdisk, aplikasi menolak.
6. **Wajah**: coba wajah lain, ditolak.
7. Login dengan password (PBKDF2 + salt).
8. Hubungkan client ke IP server.
9. Kirim pesan, tunjukkan **ciphertext** di UI dan di database.
10. Kirim file, tunjukkan file terenkripsi.
11. Sisipkan pesan ke gambar, buka gambar hasil, ekstrak pesan.
12. Buka panel **hash chain**, tunjukkan verifikasi berhasil.
13. Ubah satu blok secara manual, verifikasi gagal.
14. Cabut dongle saat aplikasi berjalan, aplikasi terkunci.

**Persiapan demo**: uji hotspot jauh hari (beberapa HP mengaktifkan *client isolation*), latih ulang dataset wajah di ruangan demo, dan siapkan video rekaman sebagai cadangan.

## 9. Rencana Pengerjaan (Checklist)

- [ ] 0. Kerangka proyek: semua file sesuai struktur, fungsi kosong
- [ ] 1. Verifikasi dongle + wajah + `keys.enc` ke PySide6
- [ ] 2. Jendela chat statis (UI)
- [ ] 3. Server WebSocket di Ubuntu (VirtualBox Bridged)
- [ ] 4. Enkripsi teks (Vigenère + Fernet) + database terenkripsi
- [ ] 5. Enkripsi file (AES-GCM)
- [ ] 6. Steganografi gambar
- [ ] 7. Hash chain log aktivitas
- [ ] 8. Login password (PBKDF2 + salt)
- [ ] 9. Pengujian end-to-end antar komputer
- [ ] 10. Laporan & persiapan presentasi

## 10. Catatan, Penyederhanaan & Keterbatasan

Bagian ini sengaja ditulis jujur agar batas sistem jelas.

- **Kunci bersama**: semua client memakai kunci simetris yang sama, dibagikan manual lewat `keys.enc` pada dongle. Ini bukan *end-to-end encryption* seperti Signal (tidak ada pertukaran kunci per pengguna).
- **Server tidak tahu isi pesan** karena kunci tidak pernah ada di server. Namun server tetap melihat metadata (pengirim, waktu, ukuran).
- **Transport `ws://` tanpa TLS**: ciphertext aman, tetapi metadata terlihat di jaringan, dan belum ada perlindungan replay penuh.
- **Hash chain bersifat terpusat**: berfungsi sebagai *tamper-evidence*, bukan konsensus terdistribusi seperti blockchain publik. Pengecekan hash terakhir di client mengurangi risiko, tetapi tidak menghilangkannya.
- **LBPH tanpa liveness detection**: foto wajah berpotensi lolos. Threshold perlu disesuaikan dengan pencahayaan.
- **Serial dongle** (`vol`) bisa berubah saat flashdisk diformat. Karena itu keamanan utama bertumpu pada `keys.enc`, bukan sekadar pengecekan serial.
- **Vigenère** sangat lemah jika berdiri sendiri. Dipakai hanya sebagai lapisan klasik di bawah Fernet untuk memenuhi persyaratan tugas.
- **Enkripsi kolom database** berarti database menyimpan ciphertext yang dikirim client. Server tidak memiliki kunci untuk membukanya.