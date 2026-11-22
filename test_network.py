
import sys

from PySide6.QtCore import QCoreApplication, QTimer

from network.client import MessengerClient
from security.encryption import TextEncryption


app = QCoreApplication(sys.argv)

alice = MessengerClient()
bob = MessengerClient()

encryption = TextEncryption()

alice_registered = False
bob_registered = False
message_received = False


def on_alice_registered(username):

    global alice_registered

    alice_registered = True

    print(f"[ALICE] Registered as {username}")

    send_test_message()


def on_bob_registered(username):

    global bob_registered

    bob_registered = True

    print(f"[BOB] Registered as {username}")

    send_test_message()


def send_test_message():

    if not alice_registered or not bob_registered:
        return

    if getattr(send_test_message, "sent", False):
        return

    send_test_message.sent = True

    plaintext = "Halo Bob, ini pesan rahasia!"

    ciphertext = encryption.encrypt(plaintext)

    print("\n[ALICE] Sending encrypted message...")
    print("[ALICE] Plaintext :", plaintext)
    print("[ALICE] Ciphertext:", ciphertext)

    alice.send_message(
        "Bob",
        ciphertext
    )


def on_message_received(sender, ciphertext):

    global message_received

    message_received = True

    print("\n[BOB] Message received!")
    print("[BOB] Sender    :", sender)
    print("[BOB] Ciphertext:", ciphertext)

    # Pengujian ini hanya menguji pengiriman ciphertext.
    # Dekripsi lintas pengguna belum dilakukan karena
    # mekanisme pertukaran kunci belum dibuat.

    print("\n[NETWORK TEST] MESSAGE DELIVERED")

    QTimer.singleShot(500, app.quit)


def on_error(error):

    print("[ERROR]", error)


def on_disconnected():

    print("[NETWORK] Client disconnected")


alice.registered.connect(on_alice_registered)
bob.registered.connect(on_bob_registered)

bob.message_received.connect(on_message_received)

alice.error_occurred.connect(on_error)
bob.error_occurred.connect(on_error)

alice.disconnected.connect(on_disconnected)
bob.disconnected.connect(on_disconnected)


# Hubungkan kedua pengguna ke server.

alice.connect_to_server(
    host="127.0.0.1",
    port=5000,
    username="Alice"
)

bob.connect_to_server(
    host="127.0.0.1",
    port=5000,
    username="Bob"
)


def finish_test():

    if not message_received:
        print("\n[NETWORK TEST] Timeout: message not received")

    alice.disconnect_from_server()
    bob.disconnect_from_server()


QTimer.singleShot(10000, finish_test)

sys.exit(app.exec())
