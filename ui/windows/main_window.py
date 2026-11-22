
import uuid
import json
import tempfile
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QMessageBox,
    QFileDialog,
)
from PySide6.QtCore import Qt

from network.server_config import load_server_config
from security.encryption import TextEncryption
from security.file_encryption import FileEncryption
from network.client import MessengerClient
from database.db import (
    save_message,
    get_conversation,
    save_media_message,
    get_media_conversation,
)
from ui.widgets.chat_widget import ChatWidget
from ui.windows.steganography_window import SteganographyWindow


class MainWindow(QMainWindow):

    def __init__(self, username="User"):
        super().__init__()

        self.username = username

        self.text_encryption = TextEncryption()
        self.file_encryption = FileEncryption()

        # Penyimpanan sementara pesan
        self.encrypted_messages = []
        self.received_messages = []

        # File masuk yang belum diunduh
        self.pending_downloads = {}

        # Network client
        self.network_client = MessengerClient(
            self,
            username=self.username
        )

        # ==================================
        # NETWORK SIGNALS
        # ==================================

        self.network_client.users_updated.connect(
            self.handle_users_updated
        )

        self.network_client.connected.connect(
            self.handle_connected
        )

        self.network_client.registered.connect(
            self.handle_registered
        )

        self.network_client.message_received.connect(
            self.handle_message_received
        )

        self.network_client.file_received.connect(
            self.handle_file_received
        )

        self.network_client.file_sent.connect(
            self.handle_file_delivered
        )

        self.network_client.message_sent.connect(
            self.handle_message_delivered
        )

        self.network_client.error_occurred.connect(
            self.handle_network_error
        )

        self.network_client.disconnected.connect(
            self.handle_disconnected
        )

        self.network_client.key_established.connect(
            self.handle_key_established
        )

        # ==================================
        # WINDOW
        # ==================================

        self.setWindowTitle("Secure Messenger")
        self.resize(1250, 800)
        self.setMinimumSize(900, 600)

        self.init_ui()
        self.load_contacts()

        self.connect_to_server()

    # ==================================
    # NETWORK CONNECTION
    # ==================================

    def connect_to_server(self):

        try:

            host, port = load_server_config()

            print(f"[NETWORK] Connecting to {host}:{port}")

            success = self.network_client.connect_to_server(
                host=host,
                port=port,
                username=self.username
            )

            if not success:
                print("[NETWORK] Failed to connect to server.")

        except Exception as error:

            QMessageBox.critical(
                self,
                "Connection Error",
                f"Gagal terhubung ke server:\n{error}"
            )

    def handle_connected(self):

        print(
            f"[NETWORK] {self.username} connected to server"
        )

        self.connection_status_label.setText(
            "●  Connected to server"
        )

    def handle_registered(self, username):

        print(
            f"[NETWORK] Registered as {username}"
        )

        self.connection_status_label.setText(
            "●  Online"
        )

        self.update_contact_status()

    def handle_disconnected(self):

        print("[NETWORK] Disconnected from server")

        self.connection_status_label.setText(
            "●  Disconnected"
        )

        self.chat_widget.contact_status.setText(
            "●  Server disconnected"
        )

    def handle_network_error(self, error):

        print("[NETWORK ERROR]", error)

        self.connection_status_label.setText(
            "●  Connection error"
        )

        QMessageBox.warning(
            self,
            "Network Error",
            str(error)
        )

    # ==================================
    # KEY EXCHANGE
    # ==================================

    def handle_key_established(self, username):

        print(
            f"[KEY EXCHANGE] Shared key established with {username}"
        )

        if username == self.chat_widget.current_contact:

            self.update_contact_status()

            self.load_conversation_history(username)

    def update_contact_status(self):

        recipient = self.chat_widget.current_contact

        if not recipient:
            return

        if not self.network_client.running:

            self.chat_widget.contact_status.setText(
                "●  Server disconnected"
            )

            return

        shared_key = self.network_client.get_shared_key(
            recipient
        )

        if shared_key is not None:

            self.chat_widget.contact_status.setText(
                "●  Encrypted connection established"
            )

        else:

            self.chat_widget.contact_status.setText(
                "●  Waiting for key exchange..."
            )

    # ==================================
    # USER INTERFACE
    # ==================================

    def init_ui(self):

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==================================
        # SIDEBAR
        # ==================================

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(300)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 25, 20, 20)
        sidebar_layout.setSpacing(15)

        brand = QLabel("⬡  SECURE MESSENGER")
        brand.setObjectName("brand")
        sidebar_layout.addWidget(brand)

        subtitle = QLabel("Private communication")
        subtitle.setObjectName("sidebarSubtitle")
        sidebar_layout.addWidget(subtitle)

        # PROFILE

        profile = QFrame()
        profile.setObjectName("profileCard")

        profile_layout = QHBoxLayout(profile)
        profile_layout.setContentsMargins(12, 12, 12, 12)

        avatar = QLabel(self.username[:1].upper())
        avatar.setObjectName("avatar")

        profile_info = QVBoxLayout()

        username_label = QLabel(self.username)
        username_label.setObjectName("profileName")

        self.connection_status_label = QLabel(
            "●  Connecting..."
        )
        self.connection_status_label.setObjectName(
            "onlineStatus"
        )

        profile_info.addWidget(username_label)
        profile_info.addWidget(self.connection_status_label)

        profile_layout.addWidget(avatar)
        profile_layout.addLayout(profile_info)
        profile_layout.addStretch()

        sidebar_layout.addSpacing(15)
        sidebar_layout.addWidget(profile)

        # SEARCH

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText(
            "Search conversations..."
        )

        self.search_input.textChanged.connect(
            self.filter_contacts
        )

        sidebar_layout.addSpacing(10)
        sidebar_layout.addWidget(self.search_input)

        # CONVERSATION TITLE

        conversation_header = QLabel("MESSAGES")
        conversation_header.setObjectName("sectionTitle")

        sidebar_layout.addSpacing(15)
        sidebar_layout.addWidget(conversation_header)

        # CONTACT LIST

        self.contact_list = QListWidget()
        self.contact_list.setObjectName("contactList")

        self.contact_list.currentItemChanged.connect(
            self.select_contact
        )

        sidebar_layout.addWidget(self.contact_list)

        # Footer

        sidebar_footer = QLabel("END-TO-END SECURITY")
        sidebar_footer.setObjectName("sidebarFooter")
        sidebar_footer.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        sidebar_layout.addWidget(sidebar_footer)

        # ==================================
        # CHAT WIDGET
        # ==================================

        self.chat_widget = ChatWidget()

        self.chat_widget.message_sent.connect(
            self.handle_message_sent
        )

        self.chat_widget.file_selected.connect(
            self.handle_file_selected
        )

        self.chat_widget.file_download_requested.connect(
            self.handle_file_download
        )

        self.chat_widget.steganography_requested.connect(
            self.open_steganography
        )

        # Voice Note signals
        self.chat_widget.voice_note_send_requested.connect(
            self.handle_voice_note_send
        )
        self.chat_widget.voice_note_play_requested.connect(
            self.handle_voice_note_play
        )
        self.chat_widget.voice_note_download_requested.connect(
            self.handle_voice_note_download
        )

        # ==================================
        # MAIN LAYOUT
        # ==================================

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.chat_widget, 1)

        # ==================================
        # STYLING
        # ==================================

        self.setStyleSheet("""

            QMainWindow {
                background-color: #0b1120;
            }

            QWidget#central {
                background-color: #0b1120;
            }

            QFrame#sidebar {
                background-color: #111c30;
                border-right: 1px solid #24334d;
            }

            QLabel#brand {
                color: #60a5fa;
                font-size: 15px;
                font-weight: bold;
                letter-spacing: 1px;
            }

            QLabel#sidebarSubtitle {
                color: #64748b;
                font-size: 11px;
            }

            QFrame#profileCard {
                background-color: #1a2940;
                border: 1px solid #293a56;
                border-radius: 10px;
            }

            QLabel#avatar {
                background-color: #2563eb;
                color: white;
                min-width: 40px;
                max-width: 40px;
                min-height: 40px;
                max-height: 40px;
                border-radius: 20px;
                font-size: 17px;
                font-weight: bold;
                qproperty-alignment: AlignCenter;
            }

            QLabel#profileName {
                color: #f1f5f9;
                font-size: 13px;
                font-weight: bold;
            }

            QLabel#onlineStatus {
                color: #34d399;
                font-size: 10px;
            }

            QLineEdit#searchInput {
                background-color: #0b1528;
                color: white;
                border: 1px solid #293a56;
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
                min-height: 22px;
            }

            QLineEdit#searchInput:focus {
                border: 1px solid #3b82f6;
            }

            QLabel#sectionTitle {
                color: #64748b;
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 2px;
            }

            QListWidget#contactList {
                background-color: transparent;
                border: none;
                outline: none;
                color: #cbd5e1;
                font-size: 13px;
            }

            QListWidget#contactList::item {
                padding: 16px 12px;
                border-radius: 8px;
                margin-bottom: 5px;
            }

            QListWidget#contactList::item:hover {
                background-color: #1a2940;
            }

            QListWidget#contactList::item:selected {
                background-color: #1d3558;
                color: #60a5fa;
                border-left: 3px solid #3b82f6;
            }

            QLabel#sidebarFooter {
                color: #475569;
                font-size: 9px;
                letter-spacing: 1px;
                padding: 10px;
            }

        """)

    # ==================================
    # CONTACT MANAGEMENT
    # ==================================

    def load_contacts(self):

        self.contact_list.clear()

    def handle_users_updated(self, users):

        print("[DEBUG MAIN WINDOW] Users received:", users)

        current_contact = self.chat_widget.current_contact

        self.contact_list.blockSignals(True)
        self.contact_list.clear()

        selected_item = None

        for name in users:

            if name.casefold() == self.username.casefold():
                continue

            item = QListWidgetItem(
                f"●   {name}"
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                name
            )

            self.contact_list.addItem(item)

            if (
                current_contact
                and name.casefold() == current_contact.casefold()
            ):
                selected_item = item

        print(
            "[DEBUG MAIN WINDOW] Contact list count:",
            self.contact_list.count()
        )

        self.contact_list.blockSignals(False)

        if selected_item is not None:

            self.contact_list.setCurrentItem(selected_item)

        elif self.contact_list.count() > 0:

            self.contact_list.setCurrentRow(0)

        else:

            self.chat_widget.set_contact(None)
            self.chat_widget.clear_messages()

            self.chat_widget.add_message(
                "Belum ada pengguna lain yang online.",
                outgoing=False
            )

    def filter_contacts(self, text):

        for index in range(self.contact_list.count()):

            item = self.contact_list.item(index)

            name = item.data(
                Qt.ItemDataRole.UserRole
            )

            item.setHidden(
                text.lower() not in name.lower()
            )

    def select_contact(self, current, previous):

        if current is None:
            return

        name = current.data(
            Qt.ItemDataRole.UserRole
        )

        self.chat_widget.set_contact(name)

        self.update_contact_status()

        self.load_conversation_history(name)

    # ==================================
    # LOAD CONVERSATION HISTORY
    # ==================================

    
    def load_conversation_history(self, contact):

        try:

            messages = get_conversation(
                self.username,
                contact
            )

            self.chat_widget.clear_messages()

            shared_key = self.network_client.get_shared_key(
                contact
            )

            if shared_key is None:

                self.chat_widget.add_message(
                    "Menunggu pertukaran kunci untuk membuka riwayat pesan.",
                    outgoing=False
                )

                return

            # ==================================
            # LOAD TEXT MESSAGES
            # ==================================

            for message in messages:

                try:

                    plaintext = self.text_encryption.decrypt(
                        message["ciphertext"],
                        shared_key
                    )

                    outgoing = (
                        message["sender"].casefold()
                        == self.username.casefold()
                    )

                    self.chat_widget.add_message(
                        plaintext,
                        outgoing=outgoing
                    )

                except Exception as error:

                    print(
                        f"[HISTORY DECRYPTION ERROR] "
                        f"Message ID {message['id']}: {error}"
                    )

                    self.chat_widget.add_message(
                        "[Pesan tidak dapat didekripsi]",
                        outgoing=(
                            message["sender"].casefold()
                            == self.username.casefold()
                        )
                    )

            # ==================================
            # LOAD FILE MESSAGES
            # ==================================

            self.load_file_messages(contact)

            if not messages and not get_media_conversation(
                self.username,
                contact
            ):

                self.chat_widget.add_message(
                    f"Percakapan dengan {contact} dimulai.",
                    outgoing=False
                )

        except Exception as error:

            print("[DATABASE ERROR]", error)

            QMessageBox.warning(
                self,
                "Database Error",
                f"Gagal memuat riwayat percakapan:\n{error}"
            )


    def load_file_messages(self, contact):

        from database.db import get_media_conversation
        import json

        messages = get_media_conversation(self.username, contact)

        shared_key = self.network_client.get_shared_key(contact)

        if not shared_key:
            return

        for message in messages:
            try:
                file_id = str(message["id"])
                ciphertext = message["ciphertext"]
                file_name = message["filename"]
                
                # Check if it's a voice note
                metadata = message.get("metadata")
                is_voice_note = False
                
                if metadata:
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata)
                    if metadata.get("type") == "voice_note":
                        is_voice_note = True
                
                # Also check filename for voice note pattern
                if not is_voice_note:
                    fname = file_name.lower()
                    if fname.startswith("voice_note") or fname.endswith(".wav"):
                        is_voice_note = True

                file_name_dec, file_data = self.file_encryption.decrypt_file(
                    ciphertext,
                    shared_key
                )

                self.pending_downloads[file_id] = {
                    "sender": message["sender"],
                    "recipient": message["recipient"],
                    "file_name": file_name_dec,
                    "ciphertext": ciphertext
                }

                outgoing = message["sender"] == self.username

                if is_voice_note:
                    # Get duration from metadata if available
                    duration_ms = 0
                    if metadata and isinstance(metadata, dict):
                        duration_ms = metadata.get("duration_ms", 0)
                    
                    self.chat_widget.add_voice_note_message(
                        file_id,
                        file_name_dec,
                        duration_ms,
                        outgoing=outgoing,
                        metadata=metadata
                    )
                else:
                    self.chat_widget.add_file_message(
                        file_id,
                        file_name_dec,
                        len(file_data),
                        outgoing=outgoing
                    )

            except Exception as e:
                print(f"Gagal memuat file {message.get('id')}: {e}")

    # ==================================
    # MESSAGE SENDING
    # ==================================

    def handle_message_sent(self, message):

        recipient = self.chat_widget.current_contact

        if not recipient:
            return

        try:

            if not self.network_client.running:
                raise ConnectionError(
                    "Belum terhubung ke server."
                )

            shared_key = self.network_client.get_shared_key(
                recipient
            )

            if shared_key is None:

                raise ConnectionError(
                    f"Shared key dengan {recipient} "
                    "belum tersedia. Tunggu pertukaran kunci selesai."
                )

            encrypted_message = self.text_encryption.encrypt(
                message,
                shared_key
            )

            success = self.network_client.send_message(
                recipient,
                encrypted_message
            )

            if not success:
                raise ConnectionError(
                    "Server gagal menerima pesan."
                )

            self.encrypted_messages.append({
                "sender": self.username,
                "recipient": recipient,
                "ciphertext": encrypted_message,
            })

            try:

                save_message(
                    self.username,
                    recipient,
                    encrypted_message
                )

                print(
                    "[DATABASE] Outgoing message saved."
                )

            except Exception as database_error:

                print(
                    "[DATABASE ERROR]",
                    database_error
                )

                QMessageBox.warning(
                    self,
                    "Storage Warning",
                    "Pesan sudah dikirim ke server, "
                    "tetapi gagal disimpan ke database."
                )

            print("\n========== SECURE MESSAGE ==========")
            print(f"Sender    : {self.username}")
            print(f"Recipient : {recipient}")
            print(f"Original  : {message}")
            print(f"Ciphertext: {encrypted_message}")
            print("Status    : Encrypted and sent")
            print("====================================\n")

        except Exception as error:

            QMessageBox.warning(
                self,
                "Message Error",
                f"Gagal mengirim pesan:\n{error}"
            )

    # ==================================
    # MESSAGE RECEIVING
    # ==================================

    def handle_message_received(self, sender, ciphertext):

        print("\n========== INCOMING MESSAGE ==========")
        print(f"Sender    : {sender}")
        print(f"Ciphertext: {ciphertext}")
        print("======================================\n")

        try:

            shared_key = self.network_client.get_shared_key(
                sender
            )

            if shared_key is None:

                raise ValueError(
                    f"Shared key dengan {sender} belum tersedia."
                )

            plaintext = self.text_encryption.decrypt(
                ciphertext,
                shared_key
            )

            self.received_messages.append({
                "sender": sender,
                "recipient": self.username,
                "ciphertext": ciphertext,
                "plaintext": plaintext,
            })

            try:

                save_message(
                    sender,
                    self.username,
                    ciphertext
                )

                print(
                    "[DATABASE] Incoming message saved."
                )

            except Exception as database_error:

                print(
                    "[DATABASE ERROR]",
                    database_error
                )

                QMessageBox.warning(
                    self,
                    "Storage Warning",
                    "Pesan berhasil diterima, "
                    "tetapi gagal disimpan ke database."
                )

            print(
                f"[DECRYPTED] Message from {sender}: {plaintext}"
            )

            if sender == self.chat_widget.current_contact:

                self.chat_widget.add_message(
                    plaintext,
                    outgoing=False
                )

            else:

                QMessageBox.information(
                    self,
                    "New Message",
                    f"Pesan baru dari {sender}:\n\n{plaintext}"
                )

        except Exception as error:

            print(
                f"[DECRYPTION ERROR] {error}"
            )

            QMessageBox.warning(
                self,
                "Decryption Error",
                f"Gagal mendekripsi pesan dari {sender}:\n{error}"
            )

    # ==================================
    # MESSAGE DELIVERY
    # ==================================

    def handle_message_delivered(self, recipient):

        print(
            f"[NETWORK] Message successfully forwarded to {recipient}"
        )

    # ==================================
    # FILE SENDING
    # ==================================

    
    def handle_file_selected(self, file_path):

        recipient = self.chat_widget.current_contact

        if not recipient:

            QMessageBox.warning(
                self,
                "Pilih Kontak",
                "Pilih kontak terlebih dahulu sebelum mengirim file."
            )

            return

        try:

            if not self.network_client.running:

                raise ConnectionError(
                    "Belum terhubung ke server."
                )

            shared_key = self.network_client.get_shared_key(
                recipient
            )

            if shared_key is None:

                raise ConnectionError(
                    f"Shared key dengan {recipient} belum tersedia."
                )

            path = Path(file_path)

            file_name = path.name
            file_size = path.stat().st_size

            # Enkripsi file
            encrypted_file = self.file_encryption.encrypt_file(
                file_path,
                shared_key
            )

            # Kirim ke penerima
            success = self.network_client.send_file(
                recipient,
                encrypted_file
            )

            if not success:

                raise ConnectionError(
                    "File gagal dikirim ke server."
                )

            # Simpan ciphertext ke database lokal pengirim
            media_id = save_media_message(
                self.username,
                recipient,
                file_name,
                encrypted_file
            )

            print(
                f"[DATABASE] Outgoing file saved. ID: {media_id}"
            )

            # Tampilkan file di chat
            self.chat_widget.add_file_message(
                str(media_id),
                file_name,
                file_size,
                outgoing=True
            )

            print(
                f"[FILE] Encrypted file sent to {recipient}: {file_name}"
            )

        except Exception as error:

            QMessageBox.warning(
                self,
                "File Error",
                f"Gagal mengirim atau menyimpan file:\n{error}"
            )


    # ==================================
    # FILE RECEIVING
    # ==================================

    
    def handle_file_received(self, sender, ciphertext):

        try:

            shared_key = self.network_client.get_shared_key(
                sender
            )

            if shared_key is None:

                raise ValueError(
                    f"Shared key dengan {sender} belum tersedia."
                )

            # Verifikasi ciphertext dengan mendekripsi file
            file_name, file_data = self.file_encryption.decrypt_file(
                ciphertext,
                shared_key
            )

            file_name = Path(file_name).name

            # Check if it's a voice note based on filename
            fname = file_name.lower()
            is_voice_note = fname.startswith("voice_note") or fname.endswith(".wav")
            
            # Prepare metadata for voice notes
            metadata = None
            if is_voice_note:
                metadata = {
                    "type": "voice_note",
                    "format": "wav",
                    "size_bytes": len(file_data),
                }

            # Simpan ciphertext ke database penerima (with metadata for voice notes)
            media_id = save_media_message(
                sender,
                self.username,
                file_name,
                ciphertext,
                metadata
            )

            file_id = str(media_id)

            # Simpan referensi ciphertext untuk tombol download
            self.pending_downloads[file_id] = {
                "ciphertext": ciphertext,
                "sender": sender,
                "recipient": self.username,
                "file_name": file_name
            }

            # Tampilkan bubble jika kontak sedang dibuka
            if (
                self.chat_widget.current_contact
                and sender.casefold()
                == self.chat_widget.current_contact.casefold()
            ):

                if is_voice_note:
                    self.chat_widget.add_voice_note_message(
                        file_id,
                        file_name,
                        0,  # Duration will be determined on playback
                        outgoing=False,
                        metadata=metadata
                    )
                else:
                    self.chat_widget.add_file_message(
                        file_id,
                        file_name,
                        len(file_data),
                        outgoing=False
                    )

            else:

                notification_text = f"Voice note baru dari {sender}" if is_voice_note else f"File baru diterima dari {sender}:\n{file_name}"
                
                QMessageBox.information(
                    self,
                    "Voice Note Baru" if is_voice_note else "File Baru",
                    notification_text
                )

            print(
                f"[DATABASE] Incoming {'voice note' if is_voice_note else 'file'} saved. ID: {media_id}"
            )

        except Exception as error:

            print(
                f"[FILE RECEIVING ERROR] {error}"
            )

            QMessageBox.warning(
                self,
                "File Error",
                f"Gagal menerima atau menyimpan file:\n{error}"
            )


    # ==================================
    # FILE DOWNLOAD
    # ==================================

    
    def handle_file_download(self, file_id):

        file_info = self.pending_downloads.get(str(file_id))

        if not file_info:

            QMessageBox.warning(
                self,
                "File Tidak Tersedia",
                "Data file tidak ditemukan."
            )

            return

        try:

            sender = file_info["sender"]
            recipient = file_info["recipient"]

            # Tentukan kontak untuk mengambil shared key
            if sender.casefold() == self.username.casefold():

                contact = recipient

            else:

                contact = sender

            shared_key = self.network_client.get_shared_key(
                contact
            )

            if shared_key is None:

                raise ValueError(
                    "Shared key belum tersedia."
                )

            # Dekripsi ciphertext
            file_name, file_data = self.file_encryption.decrypt_file(
                file_info["ciphertext"],
                shared_key
            )

            file_name = Path(file_name).name

            # Dialog Save As
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Simpan File",
                file_name,
                "All Files (*.*)"
            )

            if not save_path:
                return

            Path(save_path).write_bytes(file_data)

            QMessageBox.information(
                self,
                "Download Berhasil",
                f"File berhasil disimpan:\n{save_path}"
            )

            print(
                f"[FILE] Downloaded: {save_path}"
            )

        except Exception as error:

            QMessageBox.warning(
                self,
                "Download Error",
                f"Gagal mengunduh file:\n{error}"
            )


    # ==================================
    # FILE DELIVERY
    # ==================================

    def handle_file_delivered(self, recipient):

        print(
            f"[NETWORK] Encrypted file successfully forwarded to {recipient}"
        )

    # ==================================
    # VOICE NOTES
    # ==================================

    def handle_voice_note_send(self, temp_file_path: str):
        """Handle sending a recorded voice note."""
        recipient = self.chat_widget.current_contact

        if not recipient:
            QMessageBox.warning(
                self,
                "Pilih Kontak",
                "Pilih kontak terlebih dahulu sebelum mengirim voice note."
            )
            # Clean up temp file
            try:
                Path(temp_file_path).unlink(missing_ok=True)
            except Exception:
                pass
            return

        try:
            if not self.network_client.running:
                raise ConnectionError("Belum terhubung ke server.")

            shared_key = self.network_client.get_shared_key(recipient)

            if shared_key is None:
                raise ConnectionError(
                    f"Shared key dengan {recipient} belum tersedia. "
                    "Tunggu pertukaran kunci selesai."
                )

            # Encrypt the voice note file using existing FileEncryption
            encrypted_file = self.file_encryption.encrypt_file(
                temp_file_path,
                shared_key
            )

            # Send to recipient
            success = self.network_client.send_file(
                recipient,
                encrypted_file
            )

            if not success:
                raise ConnectionError("Voice note gagal dikirim ke server.")

            # Get file info for metadata
            file_size = Path(temp_file_path).stat().st_size
            file_name = Path(temp_file_path).name
            
            # Extract duration from metadata if available
            # For now, we'll estimate from file size (rough approximation)
            # WAV: ~176 KB/s for 44.1kHz 16-bit mono
            # Better: we could use a proper audio library to read duration
            metadata = {
                "type": "voice_note",
                "format": "wav",
                "size_bytes": file_size,
            }

            # Save to local database with metadata
            media_id = save_media_message(
                self.username,
                recipient,
                file_name,
                encrypted_file,
                metadata
            )

            print(f"[DATABASE] Outgoing voice note saved. ID: {media_id}")

            # Show in chat
            # For duration, we'll use a placeholder and update when played
            # Actual duration should be read from audio file
            self.chat_widget.add_voice_note_message(
                str(media_id),
                file_name,
                0,  # Duration will be updated on playback
                outgoing=True
            )

            # Clean up temp file
            try:
                Path(temp_file_path).unlink(missing_ok=True)
            except Exception:
                pass

            QMessageBox.information(
                self,
                "Terkirim",
                f"Voice note berhasil dikirim ke {recipient}."
            )
            self.status_label.setText(f"✓ Voice note terkirim ke {recipient}")

        except Exception as error:
            # Clean up temp file on error
            try:
                Path(temp_file_path).unlink(missing_ok=True)
            except Exception:
                pass
            
            QMessageBox.warning(
                self,
                "Kirim Gagal",
                f"Gagal mengirim voice note:\n{error}"
            )
            self.status_label.setText("Gagal kirim voice note")

    def handle_voice_note_play(self, file_id: str):
        """Handle play/pause request for a voice note."""
        file_info = self.pending_downloads.get(str(file_id))
        
        if not file_info:
            # Try to load from database
            self._load_voice_note_for_playback(file_id)
            return

        # We have the ciphertext, need to decrypt and play
        self._play_voice_note(file_id, file_info)

    def _load_voice_note_for_playback(self, file_id: str):
        """Load voice note from database for playback."""
        try:
            from database.db import get_media_conversation
            
            # We need to find the message by ID
            # Since we don't have a direct get by ID, search in conversation
            contact = self.chat_widget.current_contact
            if not contact:
                return
                
            messages = get_media_conversation(self.username, contact)
            
            for msg in messages:
                if str(msg["id"]) == str(file_id):
                    # Found it, decrypt and play
                    shared_key = self.network_client.get_shared_key(
                        msg["sender"] if msg["sender"] != self.username else msg["recipient"]
                    )
                    
                    if not shared_key:
                        self.chat_widget.update_voice_note_bubble(
                            file_id, status="Shared key not available"
                        )
                        return
                    
                    file_name, file_data = self.file_encryption.decrypt_file(
                        msg["ciphertext"],
                        shared_key
                    )
                    
                    # Save decrypted to temp file for playback
                    import tempfile
                    temp_dir = Path(tempfile.gettempdir())
                    temp_file = temp_dir / f"vn_play_{file_id}_{file_name}"
                    temp_file.write_bytes(file_data)
                    
                    self.pending_downloads[file_id] = {
                        "sender": msg["sender"],
                        "recipient": msg["recipient"],
                        "file_name": file_name,
                        "decrypted_path": str(temp_file),
                        "ciphertext": msg["ciphertext"]
                    }
                    
                    self._play_voice_note(file_id, self.pending_downloads[file_id])
                    return
            
            self.chat_widget.update_voice_note_bubble(
                file_id, status="Voice note not found"
            )
            
        except Exception as e:
            print(f"[VOICE NOTE LOAD ERROR] {e}")
            self.chat_widget.update_voice_note_bubble(
                file_id, status=f"Error: {e}"
            )

    def _play_voice_note(self, file_id: str, file_info: dict):
        """Play a voice note using Qt Multimedia."""
        from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
        from PySide6.QtCore import QUrl
        
        decrypted_path = file_info.get("decrypted_path")
        if not decrypted_path or not Path(decrypted_path).exists():
            self.chat_widget.update_voice_note_bubble(
                file_id, status="File not available"
            )
            return
        
        # Create player for this voice note
        player = QMediaPlayer()
        audio_output = QAudioOutput()
        player.setAudioOutput(audio_output)
        player.setSource(QUrl.fromLocalFile(decrypted_path))
        
        # Store player reference
        if not hasattr(self, '_voice_players'):
            self._voice_players = {}
        
        # Stop any currently playing voice note
        for pid, p in self._voice_players.items():
            if pid != file_id and p["player"].playbackState() == 1:  # PlayingState
                p["player"].pause()
                self.chat_widget.update_voice_note_bubble(pid, playing=False)
        
        self._voice_players[file_id] = {
            "player": player,
            "audio_output": audio_output,
            "file_info": file_info
        }
        
        # Connect signals
        def on_position_changed(pos):
            self.chat_widget.update_voice_note_bubble(
                file_id, position_ms=pos
            )
        
        def on_duration_changed(dur):
            self.chat_widget.update_voice_note_bubble(
                file_id, duration_ms=dur
            )
        
        def on_state_changed(state):
            from PySide6.QtMultimedia import QMediaPlayer
            is_playing = state == QMediaPlayer.PlaybackState.PlayingState
            self.chat_widget.update_voice_note_bubble(
                file_id, playing=is_playing
            )
            if state == QMediaPlayer.PlaybackState.StoppedState:
                if player.position() >= player.duration() - 500:
                    # Finished playing
                    self.chat_widget.update_voice_note_bubble(
                        file_id, playing=False, position_ms=0
                    )
        
        player.positionChanged.connect(on_position_changed)
        player.durationChanged.connect(on_duration_changed)
        player.playbackStateChanged.connect(on_state_changed)
        
        # Check current state and toggle
        if player.playbackState() == 1:  # PlayingState
            player.pause()
        else:
            player.play()

    def handle_voice_note_download(self, file_id: str):
        """Handle voice note download request - same as file download."""
        self.handle_file_download(file_id)

    def load_voice_note_messages(self, contact: str):
        """Load voice note messages from history for a contact."""
        from database.db import get_media_conversation
        
        messages = get_media_conversation(self.username, contact)
        
        shared_key = self.network_client.get_shared_key(contact)
        if not shared_key:
            return
        
        for message in messages:
            try:
                metadata = message.get("metadata")
                is_voice_note = False
                
                if metadata:
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata)
                    if metadata.get("type") == "voice_note":
                        is_voice_note = True
                
                # Also check filename for voice note pattern
                if not is_voice_note:
                    fname = message["filename"].lower()
                    if fname.startswith("voice_note") or fname.endswith(".wav"):
                        is_voice_note = True
                
                if not is_voice_note:
                    continue  # Skip regular files
                
                file_id = str(message["id"])
                ciphertext = message["ciphertext"]
                file_name = message["filename"]
                
                # Decrypt to get duration
                file_name_dec, file_data = self.file_encryption.decrypt_file(
                    ciphertext,
                    shared_key
                )
                
                # Try to get duration from metadata or estimate
                duration_ms = 0
                if metadata and isinstance(metadata, dict):
                    # If we stored duration in metadata
                    pass
                # For WAV files, we could parse the header, but for now use placeholder
                
                self.pending_downloads[file_id] = {
                    "sender": message["sender"],
                    "recipient": message["recipient"],
                    "file_name": file_name,
                    "ciphertext": ciphertext
                }
                
                outgoing = message["sender"] == self.username
                
                self.chat_widget.add_voice_note_message(
                    file_id,
                    file_name,
                    duration_ms,
                    outgoing=outgoing,
                    metadata=metadata
                )
                
            except Exception as e:
                print(f"Gagal memuat voice note {message.get('id')}: {e}")

    # ==================================
    # STEGANOGRAPHY
    # ==================================

    def open_steganography(self):
        """Open the Steganography Window."""
        self.stego_window = SteganographyWindow(self)
        self.stego_window.stego_image_ready.connect(
            self._on_stego_image_ready
        )
        self.stego_window.show()

    def _on_stego_image_ready(self, stego_path: str):
        """Handle stego image ready to send - show contact selection."""
        self._show_contact_selection_for_stego(stego_path)

    def _show_contact_selection_for_stego(self, stego_path: str):
        """Show dialog to select contact for sending stego image."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QLineEdit
        from PySide6.QtCore import Qt

        dialog = QDialog(self)
        dialog.setWindowTitle("Kirim ke Kontak")
        dialog.setFixedSize(400, 500)
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Title
        title = QLabel("Pilih Penerima")
        title.setObjectName("dialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Description
        desc = QLabel(
            f"Kirim gambar steganography ke percakapan:\n"
            f"<b>{Path(stego_path).name}</b>"
        )
        desc.setObjectName("dialogDesc")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        # Search
        search_input = QLineEdit()
        search_input.setPlaceholderText("Cari kontak...")
        search_input.setFixedHeight(36)
        layout.addWidget(search_input)

        # Contact list
        contact_list = QListWidget()
        contact_list.setObjectName("contactSelectionList")

        # Get current online users from chat widget
        current_users = []
        for i in range(self.chat_widget.contact_list.count()):
            item = self.chat_widget.contact_list.item(i)
            username = item.data(Qt.ItemDataRole.UserRole)
            if username and username.casefold() != self.username.casefold():
                current_users.append(username)

        for user in current_users:
            item = QListWidgetItem(f"●  {user}")
            item.setData(Qt.ItemDataRole.UserRole, user)
            contact_list.addItem(item)

        if not current_users:
            item = QListWidgetItem("Tidak ada kontak online")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            contact_list.addItem(item)

        layout.addWidget(contact_list, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        cancel_btn = QPushButton("Batal")
        cancel_btn.setObjectName("cancelButton")
        cancel_btn.setFixedHeight(40)
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        send_btn = QPushButton("Kirim")
        send_btn.setObjectName("sendContactButton")
        send_btn.setFixedHeight(40)
        send_btn.setEnabled(bool(current_users))
        btn_layout.addWidget(send_btn)

        layout.addLayout(btn_layout)

        # Search filter
        def filter_contacts(text):
            for i in range(contact_list.count()):
                item = contact_list.item(i)
                username = item.data(Qt.ItemDataRole.UserRole)
                if username:
                    item.setHidden(text.lower() not in username.lower())

        search_input.textChanged.connect(filter_contacts)

        # Handle send
        def on_send():
            current = contact_list.currentItem()
            if not current:
                return
            recipient = current.data(Qt.ItemDataRole.UserRole)
            if not recipient:
                return
            dialog.accept()
            self._send_stego_image(stego_path, recipient)

        send_btn.clicked.connect(on_send)
        contact_list.itemDoubleClicked.connect(lambda _: on_send())

        dialog.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
            }
            QLabel#dialogTitle {
                color: #f1f5f9;
                font-size: 18px;
                font-weight: bold;
            }
            QLabel#dialogDesc {
                color: #94a3b8;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #0b1528;
                color: white;
                border: 1px solid #293a56;
                border-radius: 8px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
            }
            QListWidget#contactSelectionList {
                background-color: #111c30;
                border: 1px solid #24334d;
                border-radius: 8px;
                color: #cbd5e1;
                font-size: 13px;
            }
            QListWidget#contactSelectionList::item {
                padding: 12px 16px;
                border-bottom: 1px solid #24334d;
            }
            QListWidget#contactSelectionList::item:hover {
                background-color: #1a2940;
            }
            QListWidget#contactSelectionList::item:selected {
                background-color: #1d3558;
                color: #60a5fa;
            }
            QPushButton#cancelButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#cancelButton:hover {
                background-color: #334155;
            }
            QPushButton#sendContactButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#sendContactButton:hover {
                background-color: #34d399;
            }
            QPushButton#sendContactButton:disabled {
                background-color: #334155;
                color: #64748b;
            }
        """)

        dialog.exec()

    def _send_stego_image(self, stego_path: str, recipient: str):
        """Send stego image as file attachment using existing file encryption."""
        try:
            if not self.network_client.running:
                raise ConnectionError("Belum terhubung ke server.")

            shared_key = self.network_client.get_shared_key(recipient)
            if shared_key is None:
                raise ConnectionError(
                    f"Shared key dengan {recipient} belum tersedia. "
                    "Tunggu pertukaran kunci selesai."
                )

            # Encrypt the stego image file using existing FileEncryption
            encrypted_file = self.file_encryption.encrypt_file(
                stego_path,
                shared_key
            )

            # Send to recipient
            success = self.network_client.send_file(
                recipient,
                encrypted_file
            )

            if not success:
                raise ConnectionError("File gagal dikirim ke server.")

            # Save to local database
            file_name = Path(stego_path).name
            media_id = save_media_message(
                self.username,
                recipient,
                file_name,
                encrypted_file
            )

            print(f"[DATABASE] Outgoing stego image saved. ID: {media_id}")

            # Show in chat
            file_size = Path(stego_path).stat().st_size
            self.chat_widget.add_file_message(
                str(media_id),
                file_name,
                file_size,
                outgoing=True
            )

            QMessageBox.information(
                self,
                "Terkirim",
                f"Gambar steganography berhasil dikirim ke {recipient}."
            )
            self.status_label.setText(f"✓ Stego image terkirim ke {recipient}")

        except Exception as error:
            QMessageBox.warning(
                self,
                "Kirim Gagal",
                f"Gagal mengirim gambar steganography:\n{error}"
            )
            self.status_label.setText("Gagal kirim stego image")

    # ==================================
    # WINDOW CLOSING
    # ==================================

    def closeEvent(self, event):

        if self.network_client:
            self.network_client.disconnect_from_server()

        event.accept()
