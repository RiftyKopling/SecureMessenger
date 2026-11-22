
import sqlite3
import hashlib
import hmac
import secrets

from pathlib import Path

from database.models import User


# ==================================
# DATABASE CONFIGURATION
# ==================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "secure_messenger.db"


def get_connection():

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ==================================
# INITIALIZE DATABASE
# ==================================

def init_db():

    with get_connection() as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                username TEXT NOT NULL UNIQUE COLLATE NOCASE,

                password_hash BLOB NOT NULL,

                password_salt BLOB NOT NULL,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP

            )
        """)

        connection.commit()


# ==================================
# PASSWORD HASHING
# ==================================

def hash_password(password, salt=None):

    if salt is None:
        salt = secrets.token_bytes(16)

    password_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=64
    )

    return password_hash, salt


# ==================================
# REGISTER USER
# ==================================

def create_user(username, password):

    username = username.strip()

    if len(username) < 3:
        raise ValueError(
            "Username minimal 3 karakter."
        )

    if len(password) < 8:
        raise ValueError(
            "Password minimal 8 karakter."
        )

    password_hash, salt = hash_password(password)

    try:

        with get_connection() as connection:

            connection.execute("""
                INSERT INTO users (
                    username,
                    password_hash,
                    password_salt
                )

                VALUES (?, ?, ?)
            """, (
                username,
                password_hash,
                salt
            ))

            connection.commit()

        return True

    except sqlite3.IntegrityError:

        return False


# ==================================
# AUTHENTICATE USER
# ==================================

def authenticate_user(username, password):

    username = username.strip()

    with get_connection() as connection:

        row = connection.execute("""
            SELECT
                id,
                username,
                password_hash,
                password_salt,
                created_at

            FROM users

            WHERE username = ?
        """, (username,)).fetchone()

    if row is None:
        return None

    calculated_hash, _ = hash_password(
        password,
        row["password_salt"]
    )

    if not hmac.compare_digest(
        calculated_hash,
        row["password_hash"]
    ):
        return None

    return User(
        id=row["id"],
        username=row["username"],
        created_at=row["created_at"]
    )
