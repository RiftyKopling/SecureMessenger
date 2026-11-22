import base64
import secrets
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


class FileEncryption:
    """
    Enkripsi file menggunakan ChaCha20-Poly1305.

    Format ciphertext:
        SF1:Base64(salt || nonce || ciphertext+tag)

    Nama file disimpan di dalam plaintext terenkripsi.
    """

    PREFIX = "SF1:"
    SALT_SIZE = 16
    NONCE_SIZE = 12
    KEY_SIZE = 32

    # Batas sementara karena server menerima JSON line maksimal 1.000.000 karakter.
    # Ukuran ini memberi ruang untuk Base64, metadata nama file, dan tag autentikasi.
    MAX_FILE_SIZE = 700 * 1024

    KEY_INFO = b"SecureMessenger:File:v1"
    AAD = b"SecureMessenger:File:v1"

    def derive_file_key(self, shared_key, salt):

        if not isinstance(shared_key, bytes) or len(shared_key) != 32:
            raise ValueError("Shared key harus berupa 32 byte.")

        return HKDF(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=salt,
            info=self.KEY_INFO
        ).derive(shared_key)

    def encrypt_file(self, file_path, shared_key):

        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError("File yang dipilih tidak ditemukan.")

        file_size = path.stat().st_size

        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"Ukuran file maksimal sementara adalah "
                f"{self.MAX_FILE_SIZE // 1024} KB."
            )

        file_data = path.read_bytes()
        filename = path.name.encode("utf-8")

        if not filename or len(filename) > 65535:
            raise ValueError("Nama file tidak valid atau terlalu panjang.")

        # Panjang nama file (2 byte) + nama file + isi file.
        plaintext = (
            len(filename).to_bytes(2, "big")
            + filename
            + file_data
        )

        salt = secrets.token_bytes(self.SALT_SIZE)
        nonce = secrets.token_bytes(self.NONCE_SIZE)

        file_key = self.derive_file_key(shared_key, salt)

        encrypted_data = ChaCha20Poly1305(file_key).encrypt(
            nonce,
            plaintext,
            self.AAD
        )

        payload = salt + nonce + encrypted_data

        return self.PREFIX + base64.b64encode(payload).decode("ascii")

    def decrypt_file(self, encrypted_data, shared_key):

        if (
            not isinstance(encrypted_data, str)
            or not encrypted_data.startswith(self.PREFIX)
        ):
            raise ValueError("Format file terenkripsi tidak valid.")

        encoded_payload = encrypted_data[len(self.PREFIX):]

        try:
            payload = base64.b64decode(
                encoded_payload,
                validate=True
            )
        except Exception as error:
            raise ValueError("Data Base64 file tidak valid.") from error

        minimum_size = (
            self.SALT_SIZE
            + self.NONCE_SIZE
            + 16  # Tag autentikasi Poly1305
            + 2   # Panjang nama file
        )

        if len(payload) < minimum_size:
            raise ValueError("Data file terenkripsi terlalu pendek.")

        salt_end = self.SALT_SIZE
        nonce_end = salt_end + self.NONCE_SIZE

        salt = payload[:salt_end]
        nonce = payload[salt_end:nonce_end]
        encrypted_content = payload[nonce_end:]

        file_key = self.derive_file_key(shared_key, salt)

        try:
            plaintext = ChaCha20Poly1305(file_key).decrypt(
                nonce,
                encrypted_content,
                self.AAD
            )
        except Exception as error:
            raise ValueError(
                "Dekripsi file gagal. Data rusak atau kunci tidak cocok."
            ) from error

        if len(plaintext) < 2:
            raise ValueError("Metadata file tidak lengkap.")

        filename_length = int.from_bytes(plaintext[:2], "big")
        filename_end = 2 + filename_length

        if filename_length == 0 or filename_end > len(plaintext):
            raise ValueError("Metadata nama file tidak valid.")

        try:
            filename = plaintext[2:filename_end].decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("Nama file tidak valid.") from error

        # Cegah nama file membawa direktori/path dari pengirim.
        filename = filename.replace("\\", "/").split("/")[-1]

        if filename in ("", ".", ".."):
            filename = "received_file"

        file_data = plaintext[filename_end:]

        if len(file_data) > self.MAX_FILE_SIZE:
            raise ValueError("Ukuran file hasil dekripsi melewati batas.")

        return filename, file_data
