
import hashlib
import secrets

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
)

from security.dongle import (
    get_dongle_secret,
    PROJECT_DIR,
)


# ==================================
# CONFIGURATION
# ==================================

IDENTITY_DIR = PROJECT_DIR / "config" / "identity_keys"

NONCE_SIZE = 12

KEY_INFO = b"SecureMessenger:IdentityStorage:v1"


# ==================================
# DERIVE STORAGE KEY
# ==================================

def derive_storage_key(dongle_secret, username):

    normalized_username = username.strip().casefold()

    salt = hashlib.sha256(
        normalized_username.encode("utf-8")
    ).digest()

    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=KEY_INFO
    ).derive(dongle_secret)


# ==================================
# GET IDENTITY FILE PATH
# ==================================

def get_identity_path(username):

    normalized_username = username.strip().casefold()

    username_hash = hashlib.sha256(
        normalized_username.encode("utf-8")
    ).hexdigest()

    return IDENTITY_DIR / f"{username_hash}.key"


# ==================================
# CREATE NEW PRIVATE KEY
# ==================================

def create_identity_key(username, storage_key):

    private_key = X25519PrivateKey.generate()

    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )

    nonce = secrets.token_bytes(NONCE_SIZE)

    aad = username.strip().casefold().encode("utf-8")

    encrypted_private_key = AESGCM(
        storage_key
    ).encrypt(
        nonce,
        private_key_bytes,
        aad
    )

    IDENTITY_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    identity_path = get_identity_path(username)

    temporary_path = identity_path.with_suffix(".tmp")

    temporary_path.write_bytes(
        nonce + encrypted_private_key
    )

    temporary_path.replace(identity_path)

    return private_key


# ==================================
# LOAD EXISTING PRIVATE KEY
# ==================================

def load_identity_key(username, storage_key):

    identity_path = get_identity_path(username)

    encrypted_data = identity_path.read_bytes()

    if len(encrypted_data) < NONCE_SIZE + 32 + 16:
        raise ValueError(
            "File identity key tidak valid."
        )

    nonce = encrypted_data[:NONCE_SIZE]

    encrypted_private_key = encrypted_data[NONCE_SIZE:]

    aad = username.strip().casefold().encode("utf-8")

    private_key_bytes = AESGCM(
        storage_key
    ).decrypt(
        nonce,
        encrypted_private_key,
        aad
    )

    if len(private_key_bytes) != 32:
        raise ValueError(
            "Private key X25519 tidak valid."
        )

    return X25519PrivateKey.from_private_bytes(
        private_key_bytes
    )


# ==================================
# LOAD OR CREATE IDENTITY
# ==================================

def load_or_create_private_key(username):

    if not isinstance(username, str) or not username.strip():
        raise ValueError(
            "Username tidak valid."
        )

    dongle_secret = get_dongle_secret()

    storage_key = derive_storage_key(
        dongle_secret,
        username
    )

    identity_path = get_identity_path(username)

    if identity_path.exists():

        print(
            f"[IDENTITY] Loading existing identity for {username}"
        )

        return load_identity_key(
            username,
            storage_key
        )

    print(
        f"[IDENTITY] Creating new identity for {username}"
    )

    return create_identity_key(
        username,
        storage_key
    )
