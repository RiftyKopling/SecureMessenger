"""
Steganography Module - LSB (Least Significant Bit) embedding with AES-256-GCM encryption.

Format:
- Carrier: PNG only (lossless)
- Payload: Encrypted message bytes
- Header: 4-byte big-endian length prefix
- Encryption: AES-256-GCM with Scrypt key derivation from password
"""

import base64
import secrets
import struct
from pathlib import Path

import numpy as np
from PIL import Image

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives import hashes


# ==========================================
# CONFIGURATION
# ==========================================

SCRYPT_N = 32768      # CPU/memory cost
SCRYPT_R = 8          # Block size
SCRYPT_P = 1          # Parallelization
SCRYPT_KEY_LEN = 32   # 256-bit key
NONCE_SIZE = 12       # AES-GCM nonce
SALT_SIZE = 16        # Scrypt salt
LENGTH_HEADER_SIZE = 4  # 32-bit length prefix
AAD = b"SecureMessenger:Stego:v1"
PREFIX = "STG1:"


class SteganographyError(Exception):
    """Base exception for steganography errors."""
    pass


class CapacityError(SteganographyError):
    """Raised when image capacity is insufficient."""
    pass


class NoMessageError(SteganographyError):
    """Raised when no hidden message found."""
    pass


class DecryptionError(SteganographyError):
    """Raised when decryption fails (wrong password/corrupted)."""
    pass


class FormatError(SteganographyError):
    """Raised when image format is invalid."""
    pass


# ==========================================
# KEY DERIVATION
# ==========================================

def derive_key(password: str, salt: bytes) -> bytes:
    """Derive AES-256 key from password using Scrypt."""
    if not isinstance(password, str):
        raise TypeError("Password must be string.")
    if not salt or len(salt) != SALT_SIZE:
        raise ValueError(f"Salt must be {SALT_SIZE} bytes.")

    kdf = Scrypt(
        salt=salt,
        length=SCRYPT_KEY_LEN,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    )
    return kdf.derive(password.encode("utf-8"))


# ==========================================
# ENCRYPTION / DECRYPTION
# ==========================================

def encrypt_payload(plaintext: str, password: str) -> bytes:
    """
    Encrypt plaintext with AES-256-GCM using password-derived key.
    Returns: salt || nonce || ciphertext+tag
    """
    if not plaintext:
        raise ValueError("Message cannot be empty.")
    if not password:
        raise ValueError("Password cannot be empty.")

    salt = secrets.token_bytes(SALT_SIZE)
    key = derive_key(password, salt)
    nonce = secrets.token_bytes(NONCE_SIZE)

    aes = AESGCM(key)
    ciphertext = aes.encrypt(nonce, plaintext.encode("utf-8"), AAD)

    return salt + nonce + ciphertext


def decrypt_payload(encrypted_data: bytes, password: str) -> str:
    """
    Decrypt payload with AES-256-GCM.
    Expects: salt || nonce || ciphertext+tag
    """
    if not encrypted_data:
        raise ValueError("No data to decrypt.")
    if not password:
        raise ValueError("Password cannot be empty.")

    min_size = SALT_SIZE + NONCE_SIZE + 16  # salt + nonce + tag
    if len(encrypted_data) < min_size:
        raise DecryptionError("Encrypted data too short.")

    salt = encrypted_data[:SALT_SIZE]
    nonce = encrypted_data[SALT_SIZE:SALT_SIZE + NONCE_SIZE]
    ciphertext = encrypted_data[SALT_SIZE + NONCE_SIZE:]

    try:
        key = derive_key(password, salt)
        aes = AESGCM(key)
        plaintext = aes.decrypt(nonce, ciphertext, AAD)
        return plaintext.decode("utf-8")
    except Exception as e:
        raise DecryptionError("Decryption failed. Wrong password or corrupted data.") from e


# ==========================================
# CAPACITY CALCULATION
# ==========================================

def calculate_capacity(image_path: Path) -> int:
    """
    Calculate maximum payload capacity in bytes for a PNG image.
    Each pixel has 3 channels (RGB), 1 bit per channel = 3 bits per pixel.
    Header uses 32 bits (4 bytes).
    """
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            width, height = img.size
            total_bits = width * height * 3
            payload_bits = total_bits - 32  # Reserve 32 bits for length header
            return payload_bits // 8
    except Exception as e:
        raise FormatError(f"Cannot read image: {e}") from e


def check_capacity(image_path: Path, payload_bytes: int) -> bool:
    """Check if image can hold payload."""
    capacity = calculate_capacity(image_path)
    return payload_bytes <= capacity


# ==========================================
# LSB EMBEDDING / EXTRACTION
# ==========================================

def _embed_bits(pixels: np.ndarray, bitstream: str) -> np.ndarray:
    """Embed bitstream into LSB of pixel array."""
    flat = pixels.flatten()
    if len(bitstream) > len(flat):
        raise CapacityError("Payload too large for image.")

    # Convert bitstream to array of 0/1
    bits = np.array([int(b) for b in bitstream], dtype=np.uint8)
    # Clear LSB and set new bits
    flat[:len(bits)] = (flat[:len(bits)] & 0xFE) | bits
    return flat.reshape(pixels.shape)


def _extract_bits(pixels: np.ndarray, num_bits: int) -> str:
    """Extract num_bits from LSB of pixel array."""
    flat = pixels.flatten()
    if num_bits > len(flat):
        raise ValueError("Not enough pixels to extract.")
    bits = (flat[:num_bits] & 1).astype(np.uint8)
    return ''.join(str(b) for b in bits)


# ==========================================
# PUBLIC API
# ==========================================

def encode_image(
    carrier_path: Path,
    message: str,
    password: str,
    output_path: Path
) -> None:
    """
    Embed encrypted message into PNG image using LSB.

    Args:
        carrier_path: Source PNG image path
        message: Plaintext message to hide
        password: Encryption password
        output_path: Output PNG path (will not overwrite carrier)
    """
    carrier_path = Path(carrier_path)
    output_path = Path(output_path)

    if carrier_path.suffix.lower() != ".png":
        raise FormatError("Carrier must be PNG format.")
    if output_path.suffix.lower() != ".png":
        raise FormatError("Output must be PNG format.")
    if carrier_path.resolve() == output_path.resolve():
        raise ValueError("Output path cannot be same as carrier.")

    # Encrypt message
    encrypted_payload = encrypt_payload(message, password)

    # Prepare bitstream: 32-bit length + payload
    payload_len = len(encrypted_payload)
    length_bits = format(payload_len, '032b')  # 4 bytes big-endian
    payload_bits = ''.join(f"{b:08b}" for b in encrypted_payload)
    bitstream = length_bits + payload_bits

    # Load carrier image
    try:
        with Image.open(carrier_path) as img:
            img = img.convert("RGB")
            pixels = np.array(img, dtype=np.uint8)
    except Exception as e:
        raise FormatError(f"Failed to load carrier image: {e}") from e

    # Check capacity
    max_payload_bytes = calculate_capacity(carrier_path)
    if payload_len > max_payload_bytes:
        raise CapacityError(
            f"Message too large. Max capacity: {max_payload_bytes} bytes, "
            f"required: {payload_len} bytes."
        )

    # Embed
    stego_pixels = _embed_bits(pixels, bitstream)

    # Save as PNG (lossless)
    try:
        stego_img = Image.fromarray(stego_pixels, "RGB")
        stego_img.save(output_path, "PNG", optimize=False)
    except Exception as e:
        raise FormatError(f"Failed to save stego image: {e}") from e


def decode_image(stego_path: Path, password: str) -> str:
    """
    Extract and decrypt message from stego PNG image.

    Args:
        stego_path: Path to PNG image with hidden message
        password: Decryption password

    Returns:
        Decrypted plaintext message

    Raises:
        NoMessageError: No hidden message found
        DecryptionError: Wrong password or corrupted data
        FormatError: Invalid image format
    """
    stego_path = Path(stego_path)

    if stego_path.suffix.lower() != ".png":
        raise FormatError("Stego image must be PNG format.")

    try:
        with Image.open(stego_path) as img:
            img = img.convert("RGB")
            pixels = np.array(img, dtype=np.uint8)
    except Exception as e:
        raise FormatError(f"Failed to load stego image: {e}") from e

    # Extract 32-bit length header
    try:
        length_bits = _extract_bits(pixels, 32)
        payload_len = int(length_bits, 2)
    except Exception as e:
        raise NoMessageError("Cannot read message length header.") from e

    # Validate length
    if payload_len == 0:
        raise NoMessageError("No hidden message found (length is zero).")

    max_capacity = calculate_capacity(stego_path)
    if payload_len > max_capacity:
        raise NoMessageError(
            f"Invalid message length ({payload_len} bytes). "
            f"Image capacity: {max_capacity} bytes. Image may be corrupted."
        )

    # Extract payload bits
    payload_bit_count = payload_len * 8
    try:
        payload_bits = _extract_bits(pixels, 32 + payload_bit_count)[32:]
    except Exception as e:
        raise NoMessageError("Failed to extract message payload.") from e

    # Convert bits to bytes
    try:
        encrypted_payload = bytes(
            int(payload_bits[i:i+8], 2)
            for i in range(0, len(payload_bits), 8)
        )
    except Exception as e:
        raise NoMessageError("Corrupted message payload.") from e

    # Decrypt
    try:
        return decrypt_payload(encrypted_payload, password)
    except DecryptionError:
        raise
    except Exception as e:
        raise DecryptionError("Decryption failed.") from e


def get_image_info(image_path: Path) -> dict:
    """Get basic info about carrier image."""
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            mode = img.mode
            capacity = calculate_capacity(image_path)
            return {
                "width": width,
                "height": height,
                "mode": mode,
                "capacity_bytes": capacity,
                "capacity_kb": round(capacity / 1024, 2),
            }
    except Exception as e:
        raise FormatError(f"Cannot read image info: {e}") from e