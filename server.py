
import socket
import threading
import json
import base64


HOST = "0.0.0.0"
PORT = 5000

# Struktur:
# clients = {
#     "Alice": {
#         "socket": socket,
#         "send_lock": threading.Lock(),
#         "public_key": None
#     }
# }

clients = {}
clients_lock = threading.Lock()

# ==================================
# ONLINE USER MANAGEMENT
# ==================================

def get_online_users():

    with clients_lock:
        return sorted(clients.keys(), key=str.casefold)


def broadcast_online_users():

    with clients_lock:

        online_users = sorted(
            clients.keys(),
            key=str.casefold
        )

        connected_clients = list(clients.values())

    data = {
        "type": "users",
        "users": online_users
    }

    for client in connected_clients:

        try:

            send_json(client, data)

        except OSError:

            print("[ONLINE USERS] Failed to update a client.")

# ==================================
# SEND JSON
# ==================================

def send_json(client, data):

    message = json.dumps(data) + "\n"
    encoded_message = message.encode("utf-8")

    with client["send_lock"]:
        client["socket"].sendall(encoded_message)


# ==================================
# VALIDATE PUBLIC KEY
# ==================================

def validate_public_key(public_key):

    if not isinstance(public_key, str):
        return False

    try:

        decoded = base64.b64decode(
            public_key,
            validate=True
        )

        # Public key X25519 memiliki panjang 32 byte
        return len(decoded) == 32

    except Exception:
        return False


# ==================================
# HANDLE CLIENT
# ==================================

def handle_client(client_socket, address):

    username = None

    client = {
        "socket": client_socket,
        "send_lock": threading.Lock(),
        "public_key": None
    }

    buffer = ""

    print(f"[CONNECTED] {address}")

    try:

        while True:

            data = client_socket.recv(4096)

            if not data:
                break

            buffer += data.decode("utf-8")

            while "\n" in buffer:

                line, buffer = buffer.split("\n", 1)

                if not line.strip():
                    continue

                try:

                    request = json.loads(line)

                except json.JSONDecodeError:

                    send_json(client, {
                        "type": "error",
                        "message": "Invalid JSON format"
                    })

                    continue

                request_type = request.get("type")

                # ==================================
                # REGISTER USER
                # ==================================

                if request_type == "register":

                    requested_username = request.get("username")

                    if not isinstance(requested_username, str):

                        send_json(client, {
                            "type": "error",
                            "message": "Invalid username"
                        })

                        continue

                    requested_username = requested_username.strip()

                    if (
                        not requested_username
                        or len(requested_username) > 32
                    ):

                        send_json(client, {
                            "type": "error",
                            "message": "Username must contain 1-32 characters"
                        })

                        continue

                    if username is not None:

                        send_json(client, {
                            "type": "error",
                            "message": "Already registered"
                        })

                        continue

                    with clients_lock:

                        if requested_username in clients:

                            send_json(client, {
                                "type": "error",
                                "message": "Username already in use"
                            })

                            continue

                        username = requested_username
                        clients[username] = client

                        # Ambil public key pengguna yang sudah online
                        existing_users = [
                            {
                                "username": name,
                                "public_key": data["public_key"]
                            }
                            for name, data in clients.items()
                            if name != username
                            and data["public_key"] is not None
                        ]

                    print(f"[REGISTERED] {username}")

                    send_json(client, {
                        "type": "registered",
                        "username": username
                    })

                    # Perbarui daftar pengguna online untuk semua client
                    broadcast_online_users()

                    # Kirim public key pengguna lain ke client baru
                    for user in existing_users:

                        try:

                            send_json(client, {
                                "type": "public_key",
                                "username": user["username"],
                                "public_key": user["public_key"]
                            })

                        except OSError:
                            pass

                # ==================================
                # PUBLIC KEY EXCHANGE
                # ==================================

                elif request_type == "public_key":

                    if username is None:

                        send_json(client, {
                            "type": "error",
                            "message": "Register before sending public key"
                        })

                        continue

                    public_key = request.get("public_key")

                    if not validate_public_key(public_key):

                        send_json(client, {
                            "type": "error",
                            "message": "Invalid X25519 public key"
                        })

                        continue

                    with clients_lock:

                        client["public_key"] = public_key

                        # Ambil semua pengguna lain yang sedang online
                        other_clients = [
                            (name, data)
                            for name, data in clients.items()
                            if name != username
                        ]

                    print(f"[PUBLIC KEY] Received from {username}")

                    # Teruskan public key ke pengguna lain
                    for other_username, other_client in other_clients:

                        try:

                            send_json(other_client, {
                                "type": "public_key",
                                "username": username,
                                "public_key": public_key
                            })

                            print(
                                f"[PUBLIC KEY] {username} -> {other_username}"
                            )

                        except OSError:

                            print(
                                f"[PUBLIC KEY ERROR] "
                                f"Could not send to {other_username}"
                            )

                # ==================================
                # SEND ENCRYPTED MESSAGE
                # ==================================

                elif request_type == "message":

                    if username is None:

                        send_json(client, {
                            "type": "error",
                            "message": "Register before sending messages"
                        })

                        continue

                    recipient = request.get("recipient")
                    ciphertext = request.get("ciphertext")

                    if (
                        not isinstance(recipient, str)
                        or not recipient.strip()
                    ):

                        send_json(client, {
                            "type": "error",
                            "message": "Invalid recipient"
                        })

                        continue

                    if (
                        not isinstance(ciphertext, str)
                        or not ciphertext.startswith("SM2:")
                        or len(ciphertext) > 1_000_000
                    ):

                        send_json(client, {
                            "type": "error",
                            "message": "Invalid encrypted message"
                        })

                        continue

                    with clients_lock:

                        recipient_client = clients.get(recipient)

                    if recipient_client is None:

                        send_json(client, {
                            "type": "error",
                            "message": f"{recipient} is offline"
                        })

                        continue

                    try:

                        send_json(recipient_client, {
                            "type": "message",
                            "sender": username,
                            "ciphertext": ciphertext
                        })

                        send_json(client, {
                            "type": "sent",
                            "recipient": recipient
                        })

                        print(
                            f"[MESSAGE] {username} -> {recipient}"
                        )

                    except OSError:

                        send_json(client, {
                            "type": "error",
                            "message": "Failed to deliver message"
                        })

                # ==================================
                # SEND ENCRYPTED FILE
                # ==================================

                elif request_type == "file":

                    if username is None:
                        send_json(client, {
                            "type": "error",
                            "message": "Register before sending files"
                        })
                        continue

                    recipient = request.get("recipient")
                    ciphertext = request.get("ciphertext")

                    if (
                        not isinstance(recipient, str)
                        or not recipient.strip()
                    ):
                        send_json(client, {
                            "type": "error",
                            "message": "Invalid file recipient"
                        })
                        continue

                    if (
                        not isinstance(ciphertext, str)
                        or not ciphertext.startswith("SF1:")
                        or len(ciphertext) > 1_000_000
                    ):
                        send_json(client, {
                            "type": "error",
                            "message": "Invalid encrypted file"
                        })
                        continue

                    with clients_lock:
                        recipient_client = clients.get(recipient)

                    if recipient_client is None:
                        send_json(client, {
                            "type": "error",
                            "message": f"{recipient} is offline"
                        })
                        continue

                    try:
                        send_json(recipient_client, {
                            "type": "file",
                            "sender": username,
                            "ciphertext": ciphertext
                        })

                        send_json(client, {
                            "type": "file_sent",
                            "recipient": recipient
                        })

                        print(
                            f"[FILE] {username} -> {recipient} "
                            f"({len(ciphertext)} encrypted characters)"
                        )

                    except OSError:
                        send_json(client, {
                            "type": "error",
                            "message": "Failed to deliver file"
                        })

                # ==================================
                # UNKNOWN REQUEST
                # ==================================

                else:

                    send_json(client, {
                        "type": "error",
                        "message": "Unknown request type"
                    })

    except (ConnectionError, OSError, UnicodeDecodeError) as error:

        print(f"[CONNECTION ERROR] {error}")

    finally:

        if username is not None:

            removed = False

            with clients_lock:

                if clients.get(username) is client:

                    del clients[username]
                    removed = True

            print(f"[DISCONNECTED] {username}")

            if removed:
                broadcast_online_users()

        else:

            print(f"[DISCONNECTED] {address}")

        try:
            client_socket.close()
        except OSError:
            pass


# ==================================
# START SERVER
# ==================================

def start_server():

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind((HOST, PORT))
    server.listen()

    print("===================================")
    print("       SECURE MESSENGER SERVER     ")
    print("===================================")
    print(f"Server running on port {PORT}")
    print("Waiting for connections...\n")

    try:

        while True:

            client_socket, address = server.accept()

            thread = threading.Thread(
                target=handle_client,
                args=(client_socket, address),
                daemon=True
            )

            thread.start()

    except KeyboardInterrupt:

        print("\n[SERVER] Shutting down...")

    finally:

        server.close()


if __name__ == "__main__":
    start_server()
