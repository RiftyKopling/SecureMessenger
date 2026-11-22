
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

        # Tabel pengguna
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                username TEXT NOT NULL UNIQUE COLLATE NOCASE,

                password_hash BLOB NOT NULL,

                password_salt BLOB NOT NULL,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP

            )
        """)

        # Migrasi kolom users (dari push teman)
        existing_user_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

        if "role" not in existing_user_columns:

            connection.execute("""
                ALTER TABLE users
                ADD COLUMN role TEXT DEFAULT 'user'
            """)

        if "is_active" not in existing_user_columns:

            connection.execute("""
                ALTER TABLE users
                ADD COLUMN is_active INTEGER DEFAULT 1
            """)

        # ==================================
        # TEXT MESSAGES
        # ==================================

        connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                sender TEXT NOT NULL,

                recipient TEXT NOT NULL,

                ciphertext TEXT NOT NULL,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP

            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON messages (sender, recipient, id)
        """)

        connection.execute("""
            DELETE FROM messages
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM messages
                GROUP BY sender, recipient, ciphertext
            )
        """)

        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_unique
            ON messages (sender, recipient, ciphertext)
        """)

        # ==================================
        # MEDIA MESSAGES
        # ==================================

        connection.execute("""
            CREATE TABLE IF NOT EXISTS media_messages (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                sender TEXT NOT NULL,

                recipient TEXT NOT NULL,

                filename TEXT NOT NULL,

                ciphertext TEXT NOT NULL,

                metadata TEXT,  -- JSON: duration_ms, format, type (voice_note/file)

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP

            )
        """)

        # Migration: add metadata column if not exists
        existing_media_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(media_messages)"
            ).fetchall()
        }

        if "metadata" not in existing_media_columns:
            connection.execute("""
                ALTER TABLE media_messages
                ADD COLUMN metadata TEXT
            """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_media_conversation
            ON media_messages (sender, recipient, id)
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


# ==================================
# SAVE ENCRYPTED MESSAGE
# ==================================

def save_message(sender, recipient, ciphertext):

    if not isinstance(sender, str) or not sender.strip():
        raise ValueError("Invalid sender.")

    if not isinstance(recipient, str) or not recipient.strip():
        raise ValueError("Invalid recipient.")

    if not isinstance(ciphertext, str):
        raise TypeError("Ciphertext must be a string.")

    if not ciphertext.startswith("SM2:"):
        raise ValueError("Invalid encrypted message format.")

    sender = sender.strip()
    recipient = recipient.strip()

    with get_connection() as connection:

        connection.execute("""
            INSERT OR IGNORE INTO messages (
                sender,
                recipient,
                ciphertext
            )
            VALUES (?, ?, ?)
        """, (
            sender,
            recipient,
            ciphertext
        ))

        row = connection.execute("""
            SELECT id
            FROM messages
            WHERE sender = ?
            AND recipient = ?
            AND ciphertext = ?
            LIMIT 1
        """, (
            sender,
            recipient,
            ciphertext
        )).fetchone()

        return row["id"]


# ==================================
# GET CONVERSATION HISTORY
# ==================================

def get_conversation(username, contact, limit=200):

    if not isinstance(limit, int) or limit < 1:
        raise ValueError("Limit must be a positive integer.")

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT
                id,
                sender,
                recipient,
                ciphertext,
                created_at

            FROM messages

            WHERE
                (
                    sender = ?
                    AND recipient = ?
                )
                OR
                (
                    sender = ?
                    AND recipient = ?
                )

            ORDER BY id DESC

            LIMIT ?
        """, (
            username,
            contact,
            contact,
            username,
            limit
        )).fetchall()

    return [
        dict(row)
        for row in reversed(rows)
    ]


# ==================================
# SAVE ENCRYPTED MEDIA
# ==================================

def save_media_message(sender, recipient, filename, ciphertext, metadata=None):

    if not isinstance(sender, str) or not sender.strip():
        raise ValueError("Invalid sender.")

    if not isinstance(recipient, str) or not recipient.strip():
        raise ValueError("Invalid recipient.")

    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("Invalid filename.")

    if not isinstance(ciphertext, str):
        raise TypeError("Ciphertext must be a string.")

    if not ciphertext.startswith("SF1:"):
        raise ValueError("Invalid encrypted file format.")

    sender = sender.strip()
    recipient = recipient.strip()
    filename = Path(filename).name

    import json
    metadata_json = json.dumps(metadata) if metadata else None

    with get_connection() as connection:

        cursor = connection.execute("""
            INSERT INTO media_messages (
                sender,
                recipient,
                filename,
                ciphertext,
                metadata
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            sender,
            recipient,
            filename,
            ciphertext,
            metadata_json
        ))

        connection.commit()

        return cursor.lastrowid


# ==================================
# GET MEDIA CONVERSATION
# ==================================

def get_media_conversation(username, contact, limit=200):

    if not isinstance(limit, int) or limit < 1:
        raise ValueError("Limit must be a positive integer.")

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT
                id,
                sender,
                recipient,
                filename,
                ciphertext,
                metadata,
                created_at

            FROM media_messages

            WHERE
                (
                    sender = ?
                    AND recipient = ?
                )
                OR
                (
                    sender = ?
                    AND recipient = ?
                )

            ORDER BY id DESC

            LIMIT ?
        """, (
            username,
            contact,
            contact,
            username,
            limit
        )).fetchall()

    import json
    result = []
    for row in reversed(rows):
        msg = dict(row)
        if msg.get("metadata"):
            try:
                msg["metadata"] = json.loads(msg["metadata"])
            except Exception:
                msg["metadata"] = None
        result.append(msg)
    return result


# ==================================
# GET LATEST MESSAGE
# ==================================

def get_latest_message(username, contact):

    with get_connection() as connection:

        row = connection.execute("""
            SELECT
                id,
                sender,
                recipient,
                ciphertext,
                created_at

            FROM messages

            WHERE
                (
                    sender = ?
                    AND recipient = ?
                )
                OR
                (
                    sender = ?
                    AND recipient = ?
                )

            ORDER BY id DESC

            LIMIT 1
        """, (
            username,
            contact,
            contact,
            username
        )).fetchone()

    return dict(row) if row else None



