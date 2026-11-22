
import base64
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ==========================================
# CONFIGURATION
# ==========================================

VIGENERE_KEY = "KRIPTOGRAFI"

AES_KEY_SIZE = 32
NONCE_SIZE = 12

AAD = b"SecureMessenger:Text:v2"
MESSAGE_PREFIX = "SM2:"


class TextEncryption:
    """
    Super Encryption:

    1. Vigenere Cipher (classical cryptography)
    2. AES-256-GCM (modern cryptography)

    AES menggunakan shared key hasil pertukaran
    kunci X25519 antara pengirim dan penerima.
    """

    def __init__(self):
        pass

    # ==========================================
    # KEY VALIDATION
    # ==========================================

    def _validate_key(self, shared_key):

        if not isinstance(shared_key, bytes):
            raise TypeError("Shared key must be bytes.")

        if len(shared_key) != AES_KEY_SIZE:
            raise ValueError("Shared key must contain 32 bytes.")

    # ==========================================
    # CLASSICAL ENCRYPTION
    # ==========================================

    def _vigenere_encrypt(self, plaintext):

        result = []
        key = VIGENERE_KEY.upper()
        key_index = 0

        for char in plaintext:

            if char.isalpha() and char.isascii():

                base = ord("A") if char.isupper() else ord("a")

                shift = ord(key[key_index % len(key)]) - ord("A")

                encrypted = chr(
                    (ord(char) - base + shift) % 26 + base
                )

                result.append(encrypted)
                key_index += 1

            else:
                result.append(char)

        return "".join(result)

    def _vigenere_decrypt(self, ciphertext):

        result = []
        key = VIGENERE_KEY.upper()
        key_index = 0

        for char in ciphertext:

            if char.isalpha() and char.isascii():

                base = ord("A") if char.isupper() else ord("a")

                shift = ord(key[key_index % len(key)]) - ord("A")

                decrypted = chr(
                    (ord(char) - base - shift) % 26 + base
                )

                result.append(decrypted)
                key_index += 1

            else:
                result.append(char)

        return "".join(result)

    # ==========================================
    # TEXT ENCRYPTION
    # ==========================================

    def encrypt(self, plaintext, shared_key):

        if not isinstance(plaintext, str):
            raise TypeError("Message must be a string.")

        if not plaintext:
            raise ValueError("Message cannot be empty.")

        self._validate_key(shared_key)

        # Layer 1: Vigenere encryption
        classical_cipher = self._vigenere_encrypt(plaintext)

        # Layer 2: AES-256-GCM encryption
        aes = AESGCM(shared_key)

        nonce = secrets.token_bytes(NONCE_SIZE)

        ciphertext = aes.encrypt(
            nonce,
            classical_cipher.encode("utf-8"),
            AAD
        )

        # Combine nonce and ciphertext
        payload = nonce + ciphertext

        encoded = base64.b64encode(payload).decode("ascii")

        return MESSAGE_PREFIX + encoded

    # ==========================================
    # TEXT DECRYPTION
    # ==========================================

    def decrypt(self, encrypted_message, shared_key):

        if not isinstance(encrypted_message, str):
            raise TypeError("Encrypted message must be a string.")

        if not encrypted_message.startswith(MESSAGE_PREFIX):
            raise ValueError("Invalid encrypted message format.")

        self._validate_key(shared_key)

        try:

            encoded = encrypted_message[len(MESSAGE_PREFIX):]

            payload = base64.b64decode(
                encoded,
                validate=True
            )

            if len(payload) < NONCE_SIZE + 16:
                raise ValueError("Invalid encrypted payload.")

            nonce = payload[:NONCE_SIZE]
            ciphertext = payload[NONCE_SIZE:]

            # Layer 1 reverse: AES-GCM decryption
            aes = AESGCM(shared_key)

            classical_cipher = aes.decrypt(
                nonce,
                ciphertext,
                AAD
            ).decode("utf-8")

            # Layer 2 reverse: Vigenere decryption
            plaintext = self._vigenere_decrypt(classical_cipher)

            return plaintext

        except Exception as error:

            raise ValueError(
                "Message decryption failed. "
                "Invalid key or corrupted ciphertext."
            ) from error
