
import socket
import threading
import json
import base64
import hashlib

from security.identity_keys import load_or_create_private_key
from PySide6.QtCore import QObject, Signal

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)

from cryptography.hazmat.primitives import serialization

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


class MessengerClient(QObject):

    connected = Signal()
    registered = Signal(str)

    message_received = Signal(str, str)
    message_sent = Signal(str)

    file_received = Signal(str, str)
    file_sent = Signal(str)

    public_key_received = Signal(str, str)
    key_established = Signal(str)

    users_updated = Signal(list)

    error_occurred = Signal(str)
    disconnected = Signal()

    def __init__(self, parent=None, username=None):
        super().__init__(parent)

        self.socket = None
        self.username = username

        self.running = False

        self.send_lock = threading.Lock()
        self.socket_lock = threading.Lock()

        self.receive_thread = None

        # ==================================
        # X25519 PERSISTENT KEY PAIR
        # ==================================

        if username:

            self.private_key = load_or_create_private_key(
                username
            )

        else:

            # Mode sementara untuk pengujian tanpa identitas permanen
            self.private_key = X25519PrivateKey.generate()

            print(
                "[WARNING] Using temporary X25519 identity."
            )

        self.public_key = self.private_key.public_key()

        self.public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

        self.public_key_base64 = base64.b64encode(
            self.public_key_bytes
        ).decode("ascii")

        # Public key pengguna lain
        self.peer_public_keys = {}

        # Kunci AES hasil pertukaran
        self.shared_keys = {}

        self.key_lock = threading.Lock()

    # ==================================
    # CONNECTION
    # ==================================

    def connect_to_server(
        self,
        host="127.0.0.1",
        port=5000,
        username=None
    ):

        if self.running:
            self.error_occurred.emit(
                "Client is already connected."
            )
            return False

        if (
            self.username is not None
            and self.username.casefold() != username.casefold()
        ):
            self.error_occurred.emit(
                "Username tidak sesuai dengan identitas kunci."
            )
            return False

        self.username = username

        try:

            new_socket = socket.create_connection(
                (host, port),
                timeout=5
            )

            new_socket.settimeout(None)

            self.socket = new_socket
            self.username = username
            self.running = True

            self.receive_thread = threading.Thread(
                target=self.receive_messages,
                daemon=True
            )

            self.receive_thread.start()

            self.connected.emit()

            success = self.send_json({
                "type": "register",
                "username": username
            })

            return success

        except OSError as error:

            self.running = False

            self.socket = None

            self.error_occurred.emit(
                f"Connection failed: {error}"
            )

            return False

    # ==================================
    # SEND JSON
    # ==================================

    def send_json(self, data):

        with self.socket_lock:

            if not self.running or self.socket is None:

                self.error_occurred.emit(
                    "Not connected to server."
                )

                return False

            try:

                message = json.dumps(data) + "\n"

                encoded_message = message.encode("utf-8")

                with self.send_lock:

                    self.socket.sendall(encoded_message)

                return True

            except OSError as error:

                self.error_occurred.emit(
                    f"Failed to send data: {error}"
                )

                return False

    # ==================================
    # SEND PUBLIC KEY
    # ==================================

    def send_public_key(self):

        return self.send_json({
            "type": "public_key",
            "public_key": self.public_key_base64
        })

    # ==================================
    # RECEIVE PEER PUBLIC KEY
    # ==================================

    def process_public_key(self, username, public_key_base64):

        if username == self.username:
            return

        try:

            public_key_bytes = base64.b64decode(
                public_key_base64,
                validate=True
            )

            if len(public_key_bytes) != 32:
                raise ValueError("Invalid X25519 public key length.")

            peer_public_key = X25519PublicKey.from_public_bytes(
                public_key_bytes
            )

            # ==================================
            # X25519 SHARED SECRET
            # ==================================

            shared_secret = self.private_key.exchange(
                peer_public_key
            )

            if shared_secret == b"\x00" * 32:
                raise ValueError("Invalid shared secret.")

            # ==================================
            # HKDF KEY DERIVATION
            # ==================================

            # Urutkan username agar kedua pihak
            # menghasilkan salt yang sama.
            participants = sorted([
                self.username,
                username
            ])

            salt_data = (
                participants[0] + "|" + participants[1]
            ).encode("utf-8")

            salt = hashlib.sha256(salt_data).digest()

            info = b"SecureMessenger:Text:v2"

            derived_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                info=info
            ).derive(shared_secret)

            with self.key_lock:

                self.peer_public_keys[username] = peer_public_key
                self.shared_keys[username] = derived_key

            print(
                f"[KEY EXCHANGE] Shared key established with {username}"
            )

            self.key_established.emit(username)

            self.public_key_received.emit(
                username,
                public_key_base64
            )

        except Exception as error:

            self.error_occurred.emit(
                f"Key exchange failed with {username}: {error}"
            )

    # ==================================
    # GET SHARED KEY
    # ==================================

    def get_shared_key(self, username):

        with self.key_lock:

            return self.shared_keys.get(username)

    # ==================================
    # SEND ENCRYPTED MESSAGE
    # ==================================

    def send_message(self, recipient, ciphertext):

        if not isinstance(recipient, str) or not recipient.strip():

            self.error_occurred.emit(
                "Invalid recipient."
            )

            return False

        if (
            not isinstance(ciphertext, str)
            or not ciphertext.startswith("SM2:")
        ):

            self.error_occurred.emit(
                "Invalid encrypted message."
            )

            return False

        return self.send_json({
            "type": "message",
            "recipient": recipient,
            "ciphertext": ciphertext
        })

    # ==================================
    # SEND ENCRYPTED FILE
    # ==================================

    def send_file(self, recipient, encrypted_file):

        if not isinstance(recipient, str) or not recipient.strip():
            self.error_occurred.emit("Invalid recipient.")
            return False

        if (
            not isinstance(encrypted_file, str)
            or not encrypted_file.startswith("SF1:")
            or len(encrypted_file) > 1_000_000
        ):
            self.error_occurred.emit("Invalid encrypted file.")
            return False

        return self.send_json({
            "type": "file",
            "recipient": recipient,
            "ciphertext": encrypted_file
        })

    # ==================================
    # RECEIVE MESSAGES
    # ==================================

    def receive_messages(self):

        buffer = ""

        try:

            while self.running:

                current_socket = self.socket

                if current_socket is None:
                    break

                data = current_socket.recv(4096)

                if not data:
                    break

                buffer += data.decode("utf-8")

                while "\n" in buffer:

                    line, buffer = buffer.split("\n", 1)

                    if not line.strip():
                        continue

                    try:

                        response = json.loads(line)

                    except json.JSONDecodeError:

                        self.error_occurred.emit(
                            "Received invalid JSON from server."
                        )

                        continue

                    self.handle_response(response)

        except (OSError, UnicodeDecodeError) as error:

            if self.running:

                self.error_occurred.emit(
                    f"Connection error: {error}"
                )

        finally:

            was_running = self.running

            self.running = False

            with self.socket_lock:

                if self.socket is not None:

                    try:
                        self.socket.close()
                    except OSError:
                        pass

                    self.socket = None

            if was_running:
                self.disconnected.emit()

    # ==================================
    # HANDLE SERVER RESPONSE
    # ==================================

    def handle_response(self, response):

        response_type = response.get("type")

        if response_type == "registered":

            username = response.get("username", "")

            self.registered.emit(username)

            # Kirim public key setelah registrasi berhasil
            self.send_public_key()

        elif response_type == "public_key":

            username = response.get("username", "")
            public_key = response.get("public_key", "")

            self.process_public_key(
                username,
                public_key
            )

        elif response_type == "message":

            sender = response.get("sender", "")
            ciphertext = response.get("ciphertext", "")

            self.message_received.emit(
                sender,
                ciphertext
            )

        elif response_type == "sent":

            recipient = response.get("recipient", "")

            self.message_sent.emit(recipient)

        elif response_type == "file":

            sender = response.get("sender", "")
            ciphertext = response.get("ciphertext", "")

            if isinstance(sender, str) and isinstance(ciphertext, str):
                self.file_received.emit(sender, ciphertext)

        elif response_type == "file_sent":

            recipient = response.get("recipient", "")
            self.file_sent.emit(recipient)

        elif response_type == "users":

            users = response.get("users", [])

            print("[DEBUG CLIENT] Received users:", users)

            if isinstance(users, list):

                valid_users = [
                    user
                    for user in users
                    if isinstance(user, str)
                ]

                print("[DEBUG CLIENT] Emitting users:", valid_users)

                self.users_updated.emit(valid_users)

        elif response_type == "error":

            self.error_occurred.emit(
                response.get(
                    "message",
                    "Unknown server error"
                )
            )

    # ==================================
    # DISCONNECT
    # ==================================

    def disconnect_from_server(self):

        with self.socket_lock:

            if not self.running and self.socket is None:
                return

            self.running = False

            if self.socket is not None:

                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

                try:
                    self.socket.close()
                except OSError:
                    pass

                self.socket = None

