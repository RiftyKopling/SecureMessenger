
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QMessageBox,
    QFrame,
)
from PySide6.QtCore import Qt

from ui.widgets.camera_widget import CameraWidget

from security.dongle import (
    get_removable_drives,
    register_dongle,
    reset_dongle,
    verify_dongle,
    update_display_name,
)

class RegisterWindow(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Register Device")
        self.resize(550, 650)
        self.setMinimumSize(480, 580)

        self.init_ui()
        self.refresh_usb()

    def init_ui(self):

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 30, 35, 30)
        main_layout.setSpacing(18)

        # HEADER

        title = QLabel("Register Device")
        title.setObjectName("title")

        subtitle = QLabel(
            "Set up your identity and security device."
        )
        subtitle.setObjectName("subtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # USER INFORMATION

        user_card = QFrame()
        user_card.setObjectName("card")

        user_layout = QVBoxLayout(user_card)
        user_layout.setContentsMargins(18, 18, 18, 18)
        user_layout.setSpacing(12)

        user_title = QLabel("USER INFORMATION")
        user_title.setObjectName("sectionTitle")

        self.username = QLineEdit()
        self.username.setPlaceholderText(
            "Enter your display name"
        )
        self.username.setFixedHeight(44)

        user_layout.addWidget(user_title)
        user_layout.addWidget(QLabel("Display Name"))
        user_layout.addWidget(self.username)

        main_layout.addWidget(user_card)

        # USB DONGLE SECTION

        usb_card = QFrame()
        usb_card.setObjectName("card")

        usb_layout = QVBoxLayout(usb_card)
        usb_layout.setContentsMargins(18, 18, 18, 18)
        usb_layout.setSpacing(12)

        usb_title = QLabel("USB DONGLE SETUP")
        usb_title.setObjectName("sectionTitle")

        usb_description = QLabel(
            "Connect your USB flash drive to register it."
        )
        usb_description.setObjectName("subtitle")

        self.usb_combo = QComboBox()
        self.usb_combo.setFixedHeight(44)

        refresh_layout = QHBoxLayout()

        self.usb_status = QLabel(
            "Searching for USB devices..."
        )
        self.usb_status.setObjectName("status")

        refresh_button = QPushButton("Refresh")
        refresh_button.setFixedHeight(36)
        refresh_button.clicked.connect(self.refresh_usb)

        self.reset_button = QPushButton("Reset Existing Device")
        self.reset_button.setFixedHeight(36)
        self.reset_button.clicked.connect(self.reset_device)

        refresh_layout.addWidget(self.usb_status, 1)
        refresh_layout.addWidget(refresh_button)

        usb_layout.addWidget(usb_title)
        usb_layout.addWidget(usb_description)
        usb_layout.addWidget(self.usb_combo)
        usb_layout.addLayout(refresh_layout)

        main_layout.addWidget(usb_card)
        usb_layout.addWidget(self.reset_button)

        # REGISTRATION BUTTON

        self.register_button = QPushButton(
            "Register USB Dongle"
        )
        self.register_button.setObjectName("registerButton")
        self.register_button.setFixedHeight(48)
        self.register_button.clicked.connect(
            self.register_usb
        )

        main_layout.addSpacing(8)
        main_layout.addWidget(self.register_button)

        self.face_button = QPushButton("Register Face")
        self.face_button.setFixedHeight(48)
        self.face_button.setEnabled(False)
        self.face_button.clicked.connect(
            self.open_face_enrollment
        )

        main_layout.addWidget(self.face_button)

        main_layout.addStretch()

        footer = QLabel(
            "SECURE MESSENGER • DEVICE ENROLLMENT"
        )
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setObjectName("footer")

        main_layout.addWidget(footer)

        # STYLESHEET

        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
            }

            QLabel {
                color: #cbd5e1;
                font-size: 12px;
            }

            QLabel#title {
                color: #f1f5f9;
                font-size: 26px;
                font-weight: bold;
            }

            QLabel#subtitle {
                color: #94a3b8;
                font-size: 12px;
            }

            QLabel#sectionTitle {
                color: #60a5fa;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1px;
            }

            QLabel#status {
                color: #94a3b8;
                font-size: 11px;
            }

            QLabel#footer {
                color: #64748b;
                font-size: 10px;
                letter-spacing: 1px;
            }

            QFrame#card {
                background-color: #111c30;
                border: 1px solid #24334d;
                border-radius: 12px;
            }

            QLineEdit, QComboBox {
                background-color: #0b1528;
                color: white;
                border: 1px solid #293a56;
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
            }

            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #3b82f6;
            }

            QComboBox QAbstractItemView {
                background-color: #111c30;
                color: white;
                selection-background-color: #2563eb;
            }

            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 14px;
            }

            QPushButton:hover {
                background-color: #334155;
            }

            QPushButton#registerButton {
                background-color: #2563eb;
                color: white;
                border: none;
                font-size: 13px;
                font-weight: bold;
            }

            QPushButton#registerButton:hover {
                background-color: #3b82f6;
            }

            QPushButton#registerButton:disabled {
                background-color: #334155;
                color: #94a3b8;
            }
        """)

    # ==================================
    # REFRESH USB DEVICES
    # ==================================

    def refresh_usb(self):

        self.usb_combo.clear()

        try:
            drives = get_removable_drives()

        except Exception as error:

            self.usb_status.setText(
                "USB detection failed."
            )

            QMessageBox.critical(
                self,
                "USB Error",
                str(error)
            )

            return

        if not drives:

            self.usb_combo.addItem(
                "No USB device found"
            )

            self.usb_status.setText(
                "No removable drive detected."
            )

            self.register_button.setEnabled(False)

            return

        for drive in drives:

            label = (
                f"{drive['root']} "
                f"— Serial: {drive['serial']}"
            )

            self.usb_combo.addItem(
                label,
                drive["root"]
            )

        self.usb_status.setText(
            f"{len(drives)} USB device(s) detected."
        )

        self.register_button.setEnabled(True)

    # ==================================
    # REGISTER USB
    # ==================================

    def register_usb(self):

        username = self.username.text().strip()

        if len(username) < 3:

            QMessageBox.warning(
                self,
                "Invalid Name",
                "Display name must contain at least 3 characters."
            )

            return

        drive_root = self.usb_combo.currentData()

        if not drive_root:

            QMessageBox.warning(
                self,
                "USB Not Selected",
                "Please select a USB device."
            )

            return

        confirmation = QMessageBox.question(
            self,
            "Confirm Registration",
            f"Register {drive_root} as your USB Dongle?",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No
        )

        if confirmation != QMessageBox.StandardButton.Yes:
            return

        try:
            verification = verify_dongle()

            if verification["valid"]:
                registered_drive = verification["drive"]

                if registered_drive != drive_root:
                    raise RuntimeError(
                        "USB yang dipilih berbeda dari USB yang terdaftar."
                    )

                update_display_name(username)

                message = (
                    f"Nama pengguna berhasil disimpan: {username}\n"
                    "USB Dongle lama berhasil diverifikasi."
                )

            else:
                register_dongle(drive_root, username)

                message = (
                    f"USB Dongle berhasil didaftarkan!\n"
                    f"Display Name: {username}"
                )
            self.face_button.setEnabled(True)
            QMessageBox.information(
                self,
                "Registration Successful",
                message
            )

            self.register_button.setEnabled(False)
            self.usb_status.setText(
                "Device registered successfully."
            )

        except (ValueError, RuntimeError, OSError, FileExistsError) as error:
            QMessageBox.critical(
                self,
                "Registration Failed",
                str(error)
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Unexpected Error",
                str(error)
            )

    def reset_device(self):
        confirmation = QMessageBox.question(
            self,
            "Reset Device",
            (
                "PERINGATAN!\n\n"
                "Konfigurasi USB Dongle lama akan dihapus dari komputer.\n"
                "Tindakan ini diperlukan jika USB lama sudah diformat "
                "atau tidak lagi tersedia.\n\n"
                "Lanjutkan reset?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if confirmation != QMessageBox.StandardButton.Yes:
            return

        result = reset_dongle(force=True)

        if result["valid"]:
            QMessageBox.information(
                self,
                "Reset Berhasil",
                result["message"]
            )
            self.refresh_usb()
        else:
            QMessageBox.warning(
                self,
                "Reset Gagal",
                result["message"]
            )

    def open_face_enrollment(self):

        username = self.username.text().strip()

        if len(username) < 3:
            QMessageBox.warning(
                self,
                "Invalid Name",
                "Display name must contain at least 3 characters."
            )
            return

        self.camera_window = CameraWidget(username)
        self.camera_window.setWindowTitle("Face Enrollment")
        self.camera_window.resize(650, 550)
        self.camera_window.show()