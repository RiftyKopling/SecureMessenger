
import uuid
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
    QPushButton,
)
from PySide6.QtCore import Qt

from network.server_config import load_server_config
from security.encryption import TextEncryption
from security.file_encryption import FileEncryption
from network.client import MessengerClient
from database.db import (
    save_message,
    get_conversation,
    get_all_users,
    set_user_role,
    set_user_active,
    save_media_message,
    get_media_conversation,
)
from ui.widgets.chat_widget import ChatWidget


class MainWindow(QMainWindow):

    def __init__(self, username="User", role="user"):
        super().__init__()
        
        self.username = username
        self.role = role

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

        # Admin panel (hanya untuk role admin)

        if self.role == "admin":

            admin_header = QLabel("KELOLA USER")
            admin_header.setObjectName("sectionTitle")

            sidebar_layout.addSpacing(15)
            sidebar_layout.addWidget(admin_header)

            self.admin_user_list = QListWidget()
            self.admin_user_list.setObjectName("adminUserList")

            sidebar_layout.addWidget(self.admin_user_list)

            admin_button_layout = QHBoxLayout()

            self.btn_toggle_active = QPushButton("Nonaktifkan")
            self.btn_toggle_active.setFixedHeight(36)
            self.btn_toggle_active.clicked.connect(
                self.toggle_user_active
            )

            self.btn_change_role = QPushButton("Ubah Role")
            self.btn_change_role.setFixedHeight(36)
            self.btn_change_role.clicked.connect(
                self.change_user_role
            )

            self.btn_refresh_users = QPushButton("Refresh")
            self.btn_refresh_users.setFixedHeight(36)
            self.btn_refresh_users.clicked.connect(
                self.load_admin_users
            )

            admin_button_layout.addWidget(self.btn_toggle_active)
            admin_button_layout.addWidget(self.btn_change_role)
            admin_button_layout.addWidget(self.btn_refresh_users)

            sidebar_layout.addLayout(admin_button_layout)

            self.load_admin_users()

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

    # ==================================
    # ADMIN USER MANAGEMENT
    # ==================================

    def load_admin_users(self):

        if self.role != "admin":

            return

        self.admin_user_list.clear()

        try:

            users = get_all_users()

            for user in users:

                status = "Aktif" if user["is_active"] == 1 else "Nonaktif"

                text = (
                    f"{user['username']} | {user['role']} | {status}"
                )

                item = QListWidgetItem(text)

                item.setData(
                    Qt.ItemDataRole.UserRole,
                    user["username"]
                )

                self.admin_user_list.addItem(item)

        except Exception as error:

            print("[ADMIN ERROR] Gagal memuat daftar user:", error)

    def toggle_user_active(self):

        if self.role != "admin":

            return

        current = self.admin_user_list.currentItem()

        if current is None:

            QMessageBox.warning(
                self,
                "Pilih User",
                "Pilih user dari daftar terlebih dahulu."
            )

            return

        username = current.data(Qt.ItemDataRole.UserRole)

        if username.casefold() == self.username.casefold():

            QMessageBox.warning(
                self,
                "Tidak Diizinkan",
                "Anda tidak dapat menonaktifkan akun sendiri."
            )

            return

        # Cek status saat ini

        is_active = None

        for index in range(self.admin_user_list.count()):

            item = self.admin_user_list.item(index)

            if item.data(Qt.ItemDataRole.UserRole) == username:

                text = item.text()

                is_active = "Aktif" in text

                break

        if is_active is None:

            return

        new_active = 0 if is_active else 1

        try:

            set_user_active(username, new_active)

            status_baru = "diaktifkan" if new_active == 1 else "dinonaktifkan"

            QMessageBox.information(
                self,
                "Berhasil",
                f"User {username} berhasil {status_baru}."
            )

            self.load_admin_users()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Gagal",
                f"Gagal mengubah status user:\n{error}"
            )

    def change_user_role(self):

        if self.role != "admin":

            return

        current = self.admin_user_list.currentItem()

        if current is None:

            QMessageBox.warning(
                self,
                "Pilih User",
                "Pilih user dari daftar terlebih dahulu."
            )

            return

        username = current.data(Qt.ItemDataRole.UserRole)

        if username.casefold() == self.username.casefold():

            QMessageBox.warning(
                self,
                "Tidak Diizinkan",
                "Anda tidak dapat mengubah role akun sendiri."
            )

            return

        # Cek role saat ini dari teks item

        role_saat_ini = "user"

        for index in range(self.admin_user_list.count()):

            item = self.admin_user_list.item(index)

            if item.data(Qt.ItemDataRole.UserRole) == username:

                text = item.text()

                if "| admin |" in text:

                    role_saat_ini = "admin"

                break

        role_baru = "admin" if role_saat_ini == "user" else "user"

        try:

            set_user_role(username, role_baru)

            QMessageBox.information(
                self,
                "Berhasil",
                f"Role user {username} diubah menjadi {role_baru}."
            )

            self.load_admin_users()

        except Exception as error:

            QMessageBox.critical(
                self,
                "Gagal",
                f"Gagal mengubah role user:\n{error}"
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

        try:

            messages = get_media_conversation(
                self.username,
                contact
            )

            shared_key = self.network_client.get_shared_key(
                contact
            )

            if shared_key is None:
                return

            for message in messages:

                file_id = str(message["id"])
                ciphertext = message["ciphertext"]

                # Dekripsi untuk mendapatkan ukuran file.
                # Ciphertext tetap disimpan di database.
                try:

                    file_name, file_data = self.file_encryption.decrypt_file(
                        ciphertext,
                        shared_key
                    )

                    file_name = Path(file_name).name
                    file_size = len(file_data)

                    self.pending_downloads[file_id] = {
                        "ciphertext": ciphertext,
                        "sender": message["sender"],
                        "recipient": message["recipient"],
                        "file_name": file_name
                    }

                    outgoing = (
                        message["sender"].casefold()
                        == self.username.casefold()
                    )

                    self.chat_widget.add_file_message(
                        file_id,
                        file_name,
                        file_size,
                        outgoing=outgoing
                    )

                except Exception as error:

                    print(
                        f"[MEDIA HISTORY ERROR] "
                        f"Media ID {message['id']}: {error}"
                    )

                    self.chat_widget.add_message(
                        "[File tidak dapat dibuka]",
                        outgoing=(
                            message["sender"].casefold()
                            == self.username.casefold()
                        )
                    )

        except Exception as error:

            print("[MEDIA DATABASE ERROR]", error)


    def load_file_messages(self, contact):

        from database.db import get_media_conversation

        messages = get_media_conversation(self.username, contact)

        shared_key = self.network_client.get_shared_key(contact)

        if not shared_key:
            return

        for message in messages:
            try:
                file_id = str(message["id"])
                ciphertext = message["ciphertext"]

                file_name, file_data = FileEncryption.decrypt_file(
                    ciphertext,
                    shared_key
                )

                self.pending_downloads[file_id] = {
                    "sender": message["sender"],
                    "recipient": message["recipient"],
                    "file_name": file_name,
                }

                outgoing = message["sender"] == self.username

                self.chat_widget.add_file_message(
                    file_id,
                    file_name,
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

            # Simpan ciphertext ke database penerima
            media_id = save_media_message(
                sender,
                self.username,
                file_name,
                ciphertext
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

                self.chat_widget.add_file_message(
                    file_id,
                    file_name,
                    len(file_data),
                    outgoing=False
                )

            else:

                QMessageBox.information(
                    self,
                    "File Baru",
                    f"File baru diterima dari {sender}:\n{file_name}"
                )

            print(
                f"[DATABASE] Incoming file saved. ID: {media_id}"
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
    # WINDOW CLOSING
    # ==================================

    def closeEvent(self, event):

        if self.network_client:
            self.network_client.disconnect_from_server()

        event.accept()
