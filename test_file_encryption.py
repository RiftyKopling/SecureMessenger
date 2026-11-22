
from pathlib import Path

from security.file_encryption import FileEncryption


def main():

    encryption = FileEncryption()

    # Kunci simulasi untuk pengujian.
    # Nantinya diganti dengan shared key X25519.
    shared_key = b"A" * 32

    test_file = Path("test_document.txt")

    test_file.write_text(
        "Ini adalah dokumen rahasia Secure Messenger.",
        encoding="utf-8"
    )

    print("[TEST] Original file:", test_file.name)

    # Enkripsi

    encrypted_data = encryption.encrypt_file(
        test_file,
        shared_key
    )

    print("[TEST] Encryption successful.")
    print("[TEST] Prefix:", encrypted_data[:4])

    # Dekripsi

    filename, decrypted_data = encryption.decrypt_file(
        encrypted_data,
        shared_key
    )

    output_file = Path("decrypted_" + filename)

    output_file.write_bytes(decrypted_data)

    print("[TEST] Decryption successful.")
    print("[TEST] Output file:", output_file)

    # Verifikasi

    original_data = test_file.read_bytes()

    if original_data == decrypted_data:

        print("[SUCCESS] Original and decrypted files match.")

    else:

        print("[FAILED] File contents do not match.")


if __name__ == "__main__":
    main()
