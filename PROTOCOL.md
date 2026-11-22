# PROTOCOL.md — Format Komunikasi & Data

Semua pesan WebSocket berupa **JSON teks (UTF-8)**. Semua data biner dikirim sebagai **Base64**. Server: `ws://<ip>:8765`.

Prinsip: **client yang mengenkripsi/mendekripsi**. Server tidak pernah memegang kunci, hanya menyimpan dan meneruskan.

## 1. Pesan Client → Server

### hello (pertama kali terhubung)
```json
{"type": "hello", "sender": "rifty"}
```

### text
`cipher` = Base64 hasil `Fernet(Vigenère(plaintext))`.
```json
{"type": "text", "sender": "rifty", "ts": 1700000000, "cipher": "gAAAAAB..."}
```

### file
`cipher` = Base64 dari `nonce(12 byte) + AES-GCM(ciphertext+tag)`. Maksimal 5 MB sebelum enkripsi.
```json
{"type": "file", "sender": "rifty", "ts": 1700000000, "filename": "laporan.pdf", "cipher": "..."}
```

### image
`data` = Base64 file PNG yang sudah disisipi pesan (steganografi). Payload di dalam piksel adalah ciphertext teks (sama seperti `text`).
```json
{"type": "image", "sender": "rifty", "ts": 1700000000, "filename": "stego.png", "data": "..."}
```

### history_request
Minta N pesan terakhir.
```json
{"type": "history_request", "limit": 50}
```

### chain_request
Minta seluruh hash chain (untuk panel verifikasi).
```json
{"type": "chain_request"}
```

## 2. Pesan Server → Client

### broadcast
Pesan dari client lain, diteruskan apa adanya dengan tambahan `id` dan `block_hash`. Pengirim juga menerima `ack`.
```json
{"type": "text", "id": 12, "sender": "rifty", "ts": 1700000000, "cipher": "...", "block_hash": "ab12..."}
```
(Untuk `file`/`image` bentuknya sama dengan pesan dari client, ditambah `id` dan `block_hash`.)

### ack
```json
{"type": "ack", "id": 12, "block_hash": "ab12..."}
```

### history
```json
{"type": "history", "messages": [ { "...": "bentuk sama seperti broadcast" } ]}
```

### chain
```json
{"type": "chain", "blocks": [ { "index": 0, "timestamp": 0, "data": {}, "prev_hash": "0", "hash": "..." } ]}
```

### error
```json
{"type": "error", "message": "ukuran file melebihi batas"}
```

## 3. Database SQLite (server)

File: `server/chat.db`

```sql
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sender      TEXT    NOT NULL,
    ts          INTEGER NOT NULL,
    type        TEXT    NOT NULL,   -- text | file | image
    isi_pesan   TEXT    NOT NULL,   -- SELALU ciphertext (Base64), tidak pernah plaintext
    filename    TEXT,               -- untuk file/image
    block_hash  TEXT    NOT NULL
);
```
Untuk `type = image`, `isi_pesan` berisi Base64 PNG stego. Untuk `file`, berisi Base64 ciphertext AES-GCM.

## 4. Hash Chain (Blockchain Sederhana)

Disimpan di tabel:
```sql
CREATE TABLE IF NOT EXISTS chain (
    idx        INTEGER PRIMARY KEY,
    timestamp  INTEGER NOT NULL,
    data       TEXT    NOT NULL,   -- JSON kanonik (sort_keys=True, tanpa spasi)
    prev_hash  TEXT    NOT NULL,
    hash       TEXT    NOT NULL
);
```

Aturan:
- Blok 0 (genesis): `data = {}`, `prev_hash = "0"`.
- Setiap pesan masuk membuat satu blok baru dengan
  `data = {"type": ..., "sender": ..., "msg_hash": sha256_hex(isi_pesan)}`.
- `hash = sha256_hex(f"{idx}{timestamp}{data}{prev_hash}")` dengan `data` dalam JSON kanonik.
- Verifikasi: untuk setiap blok, hitung ulang `hash` dan cek `prev_hash == hash blok sebelumnya`.
- Client menyimpan `hash` blok terakhir yang ia ketahui di file lokal `head.txt`. Saat verifikasi, hash terakhir dari server harus sama dengan (atau merupakan kelanjutan dari) yang tersimpan.

## 5. Kunci (di `keys.enc`)

Setelah didekripsi dengan kunci turunan dari `dongle.key` + serial, isinya JSON:
```json
{"text_fernet_key": "<base64>", "file_aesgcm_key": "<base64>", "vigenere_key": "KATAKUNCI"}
```
`vigenere_key` hanya huruf A–Z. Kunci tidak pernah dikirim lewat jaringan.

## 6. Urutan Kerja Enkripsi

| Jenis | Kirim | Terima |
| :--- | :--- | :--- |
| text | Vigenère → Fernet → Base64 | Base64 decode → Fernet decrypt → Vigenère decrypt |
| file | AES-GCM (nonce acak) → Base64 | Base64 decode → AES-GCM decrypt → simpan file |
| image | text dienkripsi seperti `text` → sisipkan ke PNG (LSB, header panjang 32-bit) → Base64 | Base64 decode → ekstrak bit → dekripsi seperti `text` |