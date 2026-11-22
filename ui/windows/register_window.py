"""
Registration Window for Secure Messenger.

Handles new user account creation, USB dongle registration,
and face enrollment in a sequential flow.
"""

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

from database.db import create_user, init_db


class RegisterWindow(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Secure Messenger - Register")
        self.resize(550, 750)
        self.setMinimumSize(480, 680)

        self.step = 1  # 1: account, 2: usb, 3: face
        self.created_username = None
        self.created_display_name = None  # disimpan dari step 1 sebelum widget dihancurkan
        self.usb_registered = False
        self.face_enrolled = False

        self.init_ui()
        # refresh_usb() will be called when step 2 is shown

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 30, 35, 30)
        main_layout.setSpacing(18)

        # HEADER
        title = QLabel("Create Account")
        title.setObjectName("title")

        self.subtitle = QLabel(
            "Step 1 of 3: Create your user account"
        )
        self.subtitle.setObjectName("subtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(self.subtitle)

        # STEP INDICATOR
        self.step_layout = QHBoxLayout()
        self.step_layout.setSpacing(8)

        self.step1_indicator = self.create_step_indicator(1, "Account", True)
        self.step2_indicator = self.create_step_indicator(2, "USB Dongle", False)
        self.step3_indicator = self.create_step_indicator(3, "Face", False)

        self.step_layout.addStretch()
        self.step_layout.addWidget(self.step1_indicator)
        self.step_layout.addWidget(self.step2_indicator)
        self.step_layout.addWidget(self.step3_indicator)
        self.step_layout.addStretch()

        main_layout.addLayout(self.step_layout)

        # STACKED CONTENT AREA
        self.content_card = QFrame()
        self.content_card.setObjectName("card")
        self.content_layout = QVBoxLayout(self.content_card)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(16)

        main_layout.addWidget(self.content_card, 1)

        # NAVIGATION BUTTONS
        self.nav_layout = QHBoxLayout()
        self.nav_layout.setSpacing(12)

        self.back_button = QPushButton("Back")
        self.back_button.setFixedHeight(44)
        self.back_button.clicked.connect(self.go_back)
        self.back_button.setVisible(False)

        self.next_button = QPushButton("Create Account")
        self.next_button.setObjectName("nextButton")
        self.next_button.setFixedHeight(48)
        self.next_button.clicked.connect(self.on_next_clicked)

        self.nav_layout.addWidget(self.back_button)
        self.nav_layout.addStretch()
        self.nav_layout.addWidget(self.next_button)

        main_layout.addLayout(self.nav_layout)

        # FOOTER
        footer = QLabel(
            "SECURE MESSENGER • ACCOUNT REGISTRATION"
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

            QLabel#stepIndicator {
                color: #64748b;
                font-size: 11px;
                font-weight: bold;
            }

            QLabel#stepIndicatorActive {
                color: #60a5fa;
                font-size: 11px;
                font-weight: bold;
            }

            QLabel#stepIndicatorComplete {
                color: #10b981;
                font-size: 11px;
                font-weight: bold;
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
                font-size: 12px;
            }

            QPushButton:hover {
                background-color: #334155;
            }

            QPushButton:disabled {
                background-color: #1e293b;
                color: #64748b;
                border: 1px solid #24334d;
            }

            QPushButton#nextButton {
                background-color: #2563eb;
                color: white;
                border: none;
                font-size: 13px;
                font-weight: bold;
            }

            QPushButton#nextButton:hover {
                background-color: #3b82f6;
            }

            QPushButton#nextButton:disabled {
                background-color: #334155;
                color: #94a3b8;
            }
        """)

        # Initialize with step 1 content
        self.show_step_content()

    def create_step_indicator(self, number, label, active):
        """Create a step indicator widget."""
        widget = QFrame()
        widget.setObjectName(f"step{number}Indicator")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        circle = QLabel(str(number))
        circle.setObjectName("stepCircle")
        circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circle.setFixedSize(28, 28)
        circle.setStyleSheet("""
            QLabel#stepCircle {
                border: 2px solid #334155;
                border-radius: 14px;
                background-color: #0b1528;
                color: #64748b;
                font-size: 12px;
                font-weight: bold;
            }
        """)

        text = QLabel(label)
        text.setObjectName("stepText")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setStyleSheet("color: #64748b; font-size: 10px;")

        layout.addWidget(circle, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text)

        self.update_step_indicator(widget, number, active, False)
        return widget

    def update_step_indicator(self, widget, number, active, complete):
        """Update step indicator appearance."""
        circle = widget.findChild(QLabel, "stepCircle")
        text = widget.findChild(QLabel, "stepText")

        if complete:
            circle.setStyleSheet("""
                QLabel#stepCircle {
                    border: 2px solid #10b981;
                    border-radius: 14px;
                    background-color: #10b981;
                    color: white;
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
            text.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")
        elif active:
            circle.setStyleSheet("""
                QLabel#stepCircle {
                    border: 2px solid #60a5fa;
                    border-radius: 14px;
                    background-color: #1e3a5f;
                    color: #60a5fa;
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
            text.setStyleSheet("color: #60a5fa; font-size: 10px; font-weight: bold;")
        else:
            circle.setStyleSheet("""
                QLabel#stepCircle {
                    border: 2px solid #334155;
                    border-radius: 14px;
                    background-color: #0b1528;
                    color: #64748b;
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
            text.setStyleSheet("color: #64748b; font-size: 10px;")

    def show_step_content(self):
        """Show content for current step."""
        # Clear existing content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.step == 1:
            self.show_account_step()
        elif self.step == 2:
            self.show_usb_step()
        elif self.step == 3:
            self.show_face_step()

        self.update_navigation()

    def show_account_step(self):
        """Step 1: Create user account."""
        self.subtitle.setText("Step 1 of 3: Create your user account")

        # Account info
        account_title = QLabel("ACCOUNT INFORMATION")
        account_title.setObjectName("sectionTitle")
        self.content_layout.addWidget(account_title)

        # Username
        self.content_layout.addWidget(QLabel("Username"))
        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("Enter username (min 3 characters)")
        self.reg_username.setFixedHeight(44)
        self.reg_username.setClearButtonEnabled(True)
        self.reg_username.textChanged.connect(self.validate_account_form)
        self.content_layout.addWidget(self.reg_username)

        # Password
        self.content_layout.addWidget(QLabel("Password"))
        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Enter password (min 8 characters)")
        self.reg_password.setFixedHeight(44)
        self.reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_password.setClearButtonEnabled(True)
        self.reg_password.textChanged.connect(self.validate_account_form)
        self.content_layout.addWidget(self.reg_password)

        # Confirm Password
        self.content_layout.addWidget(QLabel("Confirm Password"))
        self.reg_confirm_password = QLineEdit()
        self.reg_confirm_password.setPlaceholderText("Confirm your password")
        self.reg_confirm_password.setFixedHeight(44)
        self.reg_confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_confirm_password.setClearButtonEnabled(True)
        self.reg_confirm_password.textChanged.connect(self.validate_account_form)
        self.content_layout.addWidget(self.reg_confirm_password)

        # Display Name (for USB dongle)
        self.content_layout.addWidget(QLabel("Display Name"))
        self.reg_display_name = QLineEdit()
        self.reg_display_name.setPlaceholderText("Enter display name for USB dongle (min 3 characters)")
        self.reg_display_name.setFixedHeight(44)
        self.reg_display_name.setClearButtonEnabled(True)
        self.reg_display_name.textChanged.connect(self.validate_account_form)
        self.content_layout.addWidget(self.reg_display_name)

        self.content_layout.addStretch()

    def show_usb_step(self):
        """Step 2: Register USB dongle."""
        self.subtitle.setText("Step 2 of 3: Register your USB dongle")

        usb_title = QLabel("USB DONGLE SETUP")
        usb_title.setObjectName("sectionTitle")
        self.content_layout.addWidget(usb_title)

        usb_description = QLabel(
            "Connect your USB flash drive to register it as your security key."
        )
        usb_description.setObjectName("subtitle")
        usb_description.setWordWrap(True)
        self.content_layout.addWidget(usb_description)

        self.usb_combo = QComboBox()
        self.usb_combo.setFixedHeight(44)
        self.content_layout.addWidget(self.usb_combo)

        refresh_layout = QHBoxLayout()
        self.usb_status = QLabel("Searching for USB devices...")
        self.usb_status.setObjectName("status")
        refresh_button = QPushButton("Refresh")
        refresh_button.setFixedHeight(36)
        refresh_button.clicked.connect(self.refresh_usb)
        refresh_layout.addWidget(self.usb_status, 1)
        refresh_layout.addWidget(refresh_button)
        self.content_layout.addLayout(refresh_layout)

        self.reset_button = QPushButton("Reset Existing Device")
        self.reset_button.setFixedHeight(36)
        self.reset_button.clicked.connect(self.reset_device)
        self.content_layout.addWidget(self.reset_button)

        self.register_usb_button = QPushButton("Register USB Dongle")
        self.register_usb_button.setObjectName("registerButton")
        self.register_usb_button.setFixedHeight(48)
        self.register_usb_button.clicked.connect(self.register_usb)
        self.register_usb_button.setEnabled(False)
        self.content_layout.addWidget(self.register_usb_button)

        self.content_layout.addStretch()

        # Refresh USB devices when entering this step (after all UI elements created)
        self.refresh_usb()

    def show_face_step(self):
        """Step 3: Face enrollment."""
        self.subtitle.setText("Step 3 of 3: Enroll your face for authentication")

        face_title = QLabel("FACE ENROLLMENT")
        face_title.setObjectName("sectionTitle")
        self.content_layout.addWidget(face_title)

        face_description = QLabel(
            "Register your face for biometric authentication. "
            "You will need to capture 10 face samples from different angles."
        )
        face_description.setObjectName("subtitle")
        face_description.setWordWrap(True)
        self.content_layout.addWidget(face_description)

        self.face_button = QPushButton("Start Face Enrollment")
        self.face_button.setFixedHeight(48)
        self.face_button.clicked.connect(self.open_face_enrollment)
        self.content_layout.addWidget(self.face_button)

        self.face_status = QLabel("")
        self.face_status.setObjectName("status")
        self.face_status.setWordWrap(True)
        self.content_layout.addWidget(self.face_status)

        self.content_layout.addStretch()

    def validate_account_form(self):
        """Validate account creation form."""
        username = self.reg_username.text().strip()
        password = self.reg_password.text()
        confirm = self.reg_confirm_password.text()
        display_name = self.reg_display_name.text().strip()

        valid = (
            len(username) >= 3 and
            len(password) >= 8 and
            password == confirm and
            len(display_name) >= 3
        )
        self.next_button.setEnabled(valid)

    def update_navigation(self):
        """Update navigation button states."""
        if self.step == 1:
            self.back_button.setVisible(False)
            self.next_button.setText("Create Account")
            self.next_button.setEnabled(self.validate_account_form_check())
        elif self.step == 2:
            self.back_button.setVisible(True)
            self.next_button.setText("Next: Face Enrollment")
            self.next_button.setEnabled(self.usb_registered)
        elif self.step == 3:
            self.back_button.setVisible(True)
            self.next_button.setText("Finish Registration")
            self.next_button.setEnabled(self.face_enrolled)

    def validate_account_form_check(self):
        """Check if account form is valid.

        Gunakan atribut Python (bukan widget) agar aman dipanggil
        kapan saja, termasuk setelah widget step 1 sudah dihapus.
        """
        # Jika sudah masuk step 2+, berarti akun sudah dibuat dan valid
        if self.step > 1:
            return True

        # Widget step 1 masih aktif — baca nilainya langsung
        try:
            username = self.reg_username.text().strip()
            password = self.reg_password.text()
            confirm = self.reg_confirm_password.text()
            display_name = self.reg_display_name.text().strip()
        except RuntimeError:
            # Widget sudah dihapus (C++ object deleted) — anggap valid
            return True

        return (
            len(username) >= 3 and
            len(password) >= 8 and
            password == confirm and
            len(display_name) >= 3
        )

    def on_next_clicked(self):
        """Handle next/finish button click."""
        if self.step == 1:
            self.create_account()
        elif self.step == 2:
            self.go_to_step(3)
        elif self.step == 3:
            self.finish_registration()

    def go_back(self):
        """Go to previous step."""
        if self.step > 1:
            self.go_to_step(self.step - 1)

    def go_to_step(self, step):
        """Navigate to a specific step."""
        self.step = step
        self.update_step_indicators()
        self.show_step_content()

    def update_step_indicators(self):
        """Update all step indicator states."""
        for i, indicator in enumerate([
            self.step1_indicator, self.step2_indicator, self.step3_indicator
        ], 1):
            active = (i == self.step)
            complete = (i < self.step)
            self.update_step_indicator(indicator, i, active, complete)

    def create_account(self):
        """Create user account in database."""
        username = self.reg_username.text().strip()
        password = self.reg_password.text()
        display_name = self.reg_display_name.text().strip()

        init_db()

        try:
            success = create_user(username, password)
            if not success:
                QMessageBox.warning(
                    self,
                    "Account Exists",
                    "Username already taken. Please choose another."
                )
                return

            self.created_username = username
            self.created_display_name = display_name

            QMessageBox.information(
                self,
                "Account Created",
                f"Account created successfully for: {username}\n"
                f"Display Name: {display_name}\n\n"
                "Now register your USB dongle."
            )

            self.go_to_step(2)

        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create account: {e}")

    # ==================================
    # USB REGISTRATION (Step 2)
    # ==================================

    def refresh_usb(self):
        self.usb_combo.clear()

        try:
            drives = get_removable_drives()
        except Exception as error:
            self.usb_status.setText("USB detection failed.")
            QMessageBox.critical(self, "USB Error", str(error))
            return

        if not drives:
            self.usb_combo.addItem("No USB device found")
            self.usb_status.setText("No removable drive detected.")
            self.register_usb_button.setEnabled(False)
            return

        for drive in drives:
            label = f"{drive['root']} — Serial: {drive['serial']}"
            self.usb_combo.addItem(label, drive["root"])

        self.usb_status.setText(f"{len(drives)} USB device(s) detected.")
        self.register_usb_button.setEnabled(True)

    def register_usb(self):
        display_name = self.created_display_name
        drive_root = self.usb_combo.currentData()

        if not drive_root:
            QMessageBox.warning(self, "USB Not Selected", "Please select a USB device.")
            return

        confirmation = QMessageBox.question(
            self,
            "Confirm Registration",
            f"Register {drive_root} as your USB Dongle?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirmation != QMessageBox.StandardButton.Yes:
            return

        try:
            verification = verify_dongle()

            if verification["valid"]:
                registered_drive = verification["drive"]
                if registered_drive != drive_root:
                    raise RuntimeError("USB yang dipilih berbeda dari USB yang terdaftar.")

                update_display_name(display_name)
                message = (
                    f"Display Name updated: {display_name}\n"
                    "Existing USB Dongle verified."
                )
            else:
                register_dongle(drive_root, display_name)
                message = (
                    f"USB Dongle successfully registered!\n"
                    f"Display Name: {display_name}"
                )

            self.usb_registered = True
            self.register_usb_button.setEnabled(False)
            self.usb_status.setText("Device registered successfully.")

            QMessageBox.information(self, "Registration Successful", message)
            self.go_to_step(3)

        except (ValueError, RuntimeError, OSError, FileExistsError) as error:
            QMessageBox.critical(self, "Registration Failed", str(error))
        except Exception as error:
            QMessageBox.critical(self, "Unexpected Error", str(error))

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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if confirmation != QMessageBox.StandardButton.Yes:
            return

        result = reset_dongle(force=True)

        if result["valid"]:
            QMessageBox.information(self, "Reset Berhasil", result["message"])
            self.refresh_usb()
        else:
            QMessageBox.warning(self, "Reset Gagal", result["message"])

    # ==================================
    # FACE ENROLLMENT (Step 3)
    # ==================================

    def open_face_enrollment(self):
        # Sembunyikan RegisterWindow saat Face Enrollment berjalan agar tidak
        # menutupi atau mengganggu tampilan kamera.
        self.hide()

        # Buat CameraWidget tanpa parent agar menjadi top-level window
        # mandiri, bukan child dari RegisterWindow/LoginWindow.
        self.camera_window = CameraWidget(self.created_display_name, None)
        self.camera_window.setWindowTitle("Face Enrollment")
        self.camera_window.resize(1000, 720)

        # Hubungkan sinyal enrollment_completed SATU KALI saja.
        self.camera_window.enrollment_completed.connect(self.on_face_enrollment_completed)

        # Jalankan sebagai modal dialog independen
        result = self.camera_window.exec()

        # Tampilkan kembali RegisterWindow setelah Face Enrollment selesai
        self.show()
        self.raise_()
        self.activateWindow()

        # Panggil callback hanya jika belum di-trigger oleh sinyal
        if result == QDialog.DialogCode.Accepted and not self.face_enrolled:
            self.on_face_enrollment_completed()

    def on_face_enrollment_completed(self):
        """Called when face enrollment training is completed."""
        self.face_enrolled = True
        self.face_status.setText("Face enrollment completed successfully!")
        self.face_status.setStyleSheet("color: #10b981; font-size: 11px;")
        self.update_navigation()

    def on_face_enrollment_closed(self):
        """Called when camera window is closed (legacy - kept for safety)."""
        pass

    def finish_registration(self):
        """Complete the registration process."""
        # Use stored display_name (created_display_name is set in create_account())
        # Don't access reg_display_name widget as it was deleted when switching steps
        display_name = getattr(self, 'created_display_name', 'N/A')
        QMessageBox.information(
            self,
            "Registration Complete",
            "Your account has been fully registered!\n\n"
            f"Username: {self.created_username}\n"
            f"Display Name: {display_name}\n\n"
            "You can now login with your credentials."
        )
        self.accept()