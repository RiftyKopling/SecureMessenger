# AGENTS.md — Mini Secure Chat

Baca file ini di awal setiap sesi. Detail lengkap ada di `penjelasan_proyek.md` (apa & mengapa) dan `PROTOCOL.md` (format pesan, tabel DB, blok).

## Ringkasan
Aplikasi chat desktop terenkripsi untuk Tugas Akhir Kriptografi. Client PySide6 (Windows) terhubung lewat WebSocket ke server (Ubuntu). Enkripsi di sisi client; server hanya menyimpan dan meneruskan ciphertext.

## Stack (jangan diganti)
Python 3.11+, PySide6, websockets, cryptography, opencv-contrib-python (LBPH), Pillow, numpy, sqlite3 bawaan.
Tidak boleh menambah framework atau library lain tanpa izin.

## Prinsip: SIMPLE
- Ini tugas kuliah dan akan dipresentasikan. Kode harus **mudah dibaca dan dijelaskan**.
- Satu file satu tanggung jawab sesuai struktur di `penjelasan_proyek.md`. Jangan membuat file/folder di luar struktur.
- Hindari abstraksi berlebihan (tanpa class hierarchy, plugin, dependency injection). Fungsi biasa sudah cukup.
- Komentar singkat dalam bahasa Indonesia pada bagian kriptografi.
- Jangan menambah fitur di luar daftar persyaratan.

## Aturan kriptografi (penting)
- Teks: Vigenère (klasik) lalu Fernet. Dekripsi urutan terbalik.
- File: AES-GCM, kunci terpisah dari teks, nonce 12 byte acak di depan ciphertext.
- Password: `hashlib.pbkdf2_hmac('sha256', ..., salt, 200000)` dengan salt acak 16 byte. Bandingkan dengan `hmac.compare_digest`.
- Kunci disimpan di `keys.enc`, dibuka dengan kunci turunan dari `dongle.key` + serial flashdisk. **Jangan** menyimpan kunci sebagai teks biasa dan **jangan** pernah menaruh kunci di server.
- Steganografi: hanya PNG, payload diawali header panjang 32-bit, teks dienkripsi sebelum disisipkan.
- Jangan membuat algoritma kripto sendiri selain Vigenère dan hash chain. Pakai `cryptography` dan `hashlib`.
- Jangan pernah mencetak kunci atau password ke log.

## Perintah
```
pip install -r requirements.txt
python tools/make_keys.py        # sekali, buat keys.enc dari dongle
python tools/make_user.py        # sekali, buat user.json
python tools/train_face.py       # latih trainer.yml dari dataset/
python server/server.py          # di Ubuntu, port 8765
python client/main.py            # di Windows
```

## Cara kerja per sesi
1. Baca `TODO` (checklist di bagian 9 `penjelasan_proyek.md`). Kerjakan **satu tahap saja** per sesi.
2. Jangan mengubah `PROTOCOL.md` tanpa memberi tahu saya. Jika format perlu berubah, usulkan dulu.
3. Setelah selesai: jelaskan apa yang dibuat, cara mengujinya, lalu centang tahap tersebut.
4. Tulis unit test kecil (`pytest`) untuk fungsi murni di `crypto_utils.py` dan `blockchain.py` (Vigenère, Fernet round-trip, AES-GCM round-trip, stego round-trip, verifikasi chain).
5. Bagian yang butuh perangkat fisik (dongle, kamera, VirtualBox/hotspot) tidak bisa kamu tes. Buat agar bisa dijalankan dengan `dev_mode` dan beri saya langkah tes manual.

## dev_mode
`config.json` punya `"dev_mode": true/false`. Jika `true`, lewati cek dongle dan wajah (untuk pengembangan di mesin tanpa flashdisk/kamera). Harus `false` saat demo.

## Jangan sentuh
`dongle.key`, `keys.enc`, `user.json`, `trainer.yml`, dan folder `dataset/` (jangan hapus, timpa, atau commit ke repo publik).