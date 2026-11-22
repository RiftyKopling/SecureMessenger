"""
Steganography Window - Encode/Decode hidden messages in PNG images.

Features:
- Tab-based navigation: Encode and Decode modes
- LSB steganography with AES-256-GCM encryption
- PNG lossless carrier format
- Capacity validation
- QMessageBox error handling
- Consistent Secure Messenger dark UI
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QFrame,
    QFileDialog,
    QTabWidget,
    QWidget,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
)
from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QPixmap, QImage

from pathlib import Path
import tempfile
import shutil

from security.steganography import (
    encode_image,
    decode_image,
    calculate_capacity,
    get_image_info,
    CapacityError,
    NoMessageError,
    DecryptionError,
    FormatError,
)


class SteganographyWindow(QDialog):
    """
    Main window for image steganography operations.

    Two modes:
    - Encode: Hide a secret message inside a PNG image
    - Decode: Extract and decrypt a hidden message from a PNG image
    """

    # Signals for communication with parent
    stego_image_ready = Signal(str)  # Emits path to stego image for sending
    encode_finished = None
    decode_finished = None

    # ==================================
    # CONSTRUCTOR
    # ==================================

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Image Steganography")
        self.resize(900, 700)
        self.setMinimumSize(800, 600)

        self._encode_path = None
        self._decode_path = None
        self._current_mode = "encode"  # "encode" or "decode"
        self._last_stego_path = None  # Path to last encoded image

        self.init_ui()
        self._update_mode_ui("encode")

    # ==================================
    # UI SETUP
    # ==================================

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        # --- HEADER ---
        header = QFrame()
        header.setObjectName("windowHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Image Steganography")
        title.setObjectName("windowTitle")
        subtitle = QLabel("Sembunyikan atau ekstrak pesan rahasia di gambar PNG")
        subtitle.setObjectName("windowSubtitle")

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(subtitle)
        main_layout.addWidget(header)

        # --- TABS ---
        self.tabs = QTabWidget()
        self.tabs.setObjectName("stegoTabs")
        self.tabs.setMinimumHeight(400)

        # Encode tab
        self.encode_widget = self._create_encode_widget()
        self.tabs.addTab(self.encode_widget, "Encode Message")

        # Decode tab
        self.decode_widget = self._create_decode_widget()
        self.tabs.addTab(self.decode_widget, "Decode Message")

        main_layout.addWidget(self.tabs, 1)

        # --- FOOTER / STATUS ---
        self.status_label = QLabel("Siap — pilih gambar untuk memulai")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label, 0)

        # --- STYLESHEET ---
        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
            }

            QTabWidget::pane {
                border: 1px solid #24334d;
                background-color: #0b1120;
            }

            QTabBar::tab {
                background-color: #111c30;
                color: #cbd5e1;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }

            QTabBar::tab:selected {
                background-color: #1a2940;
                color: #60a5fa;
            }

            QTabBar::tab:hover:!selected {
                background-color: #16213e;
                color: #64748b;
            }

            #windowHeader {
                background-color: #111c30;
                border-bottom: 1px solid #24334d;
                padding: 8px 12px;
            }

            #windowTitle {
                color: #f1f5f9;
                font-size: 20px;
                font-weight: bold;
                letter-spacing: 1px;
            }

            #windowSubtitle {
                color: #64748b;
                font-size: 11px;
            }

            #statusLabel {
                color: #64748b;
                font-size: 11px;
                padding: 8px;
                background-color: #0b1528;
                border-radius: 6px;
                margin-top: 4px;
            }

            QFrame#card {
                background-color: #111c30;
                border: 1px solid #24334d;
                border-radius: 12px;
            }

            QLabel {
                color: #cbd5e1;
                font-size: 12px;
            }

            QLineEdit {
                background-color: #0b1528;
                color: white;
                border: 1px solid #293a56;
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
            }

            QLineEdit:focus {
                border: 1px solid #3b82f6;
            }

            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #334155;
                color: #f1f5f9;
            }

            QPushButton#encodeButton {
                background-color: #2563eb;
                color: white;
                border: none;
            }

            QPushButton#encodeButton:hover {
                background-color: #3b82f6;
            }

            QPushButton#decodeButton {
                background-color: #10b981;
                color: white;
                border: none;
            }

            QPushButton#decodeButton:hover {
                background-color: #34d399;
            }

            QPushButton#browseButton {
                background-color: #172c45;
                color: #60a5fa;
                border: 1px solid #29466b;
            }

            QPushButton#browseButton:hover {
                background-color: #203b5c;
            }

            QLabel#sectionTitle {
                color: #60a5fa;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1px;
                margin-top: 8px;
            }
        """)

    # ==================================
    # ENCODE WIDGET
    # ==================================

    def _create_encode_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Carrier selection
        carrier_card = QFrame()
        carrier_card.setObjectName("card")
        carrier_layout = QVBoxLayout(carrier_card)
        carrier_layout.setContentsMargins(16, 16, 16, 16)
        carrier_layout.setSpacing(8)

        carrier_header = QLabel("Pilih Gambar Carrier")
        carrier_header.setObjectName("sectionTitle")
        carrier_layout.addWidget(carrier_header)

        self.encode_path_label = QLabel("Belum ada gambar dipilih")
        self.encode_path_label.setObjectName("pathLabel")
        self.encode_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        carrier_layout.addWidget(self.encode_path_label)

        browse_btn = QPushButton("Browse PNG...")
        browse_btn.setObjectName("browseButton")
        browse_btn.clicked.connect(self._browse_encode_carrier)
        carrier_layout.addWidget(browse_btn)

        # Info card
        info_card = QFrame()
        info_card.setObjectName("card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(6)

        self.encode_info_label = QLabel(
            "Format: PNG | Kapasitas: belum dicek"
        )
        self.encode_info_label.setObjectName("infoLabel")
        info_layout.addWidget(self.encode_info_label)

        layout.addWidget(carrier_card)
        layout.addWidget(info_card, 1)

        # Message + Password
        form_card = QFrame()
        form_card.setObjectName("card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(12)

        # Message
        msg_layout = QHBoxLayout()
        msg_label = QLabel("Pesan rahasia:")
        msg_label.setFixedWidth(100)
        form_layout.addWidget(msg_label)
        self.encode_message = QLineEdit()
        self.encode_message.setPlaceholderText("Masukkan pesan yang akan disembunyikan...")
        form_layout.addWidget(self.encode_message)

        # Password
        pwd_layout = QHBoxLayout()
        pwd_label = QLabel("Password:")
        pwd_label.setFixedWidth(100)
        form_layout.addWidget(pwd_label)
        self.encode_password = QLineEdit()
        self.encode_password.setPlaceholderText("Kata sandi untuk enkripsi")
        self.encode_password.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addWidget(self.encode_password)

        layout.addWidget(form_card, 1)

        # Encode button
        btn_card = QFrame()
        btn_card.setObjectName("card")
        btn_layout = QHBoxLayout(btn_card)
        btn_layout.setContentsMargins(16, 16, 16, 16)
        btn_layout.setSpacing(12)

        self.encode_btn = QPushButton("Encode Message")
        self.encode_btn.setObjectName("encodeButton")
        self.encode_btn.setFixedHeight(44)
        self.encode_btn.clicked.connect(self._on_encode)
        btn_layout.addStretch()
        btn_layout.addWidget(self.encode_btn)
        btn_layout.addStretch()

        layout.addWidget(btn_card)

        # Result
        result_card = QFrame()
        result_card.setObjectName("card")
        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(16, 16, 16, 16)
        result_layout.setSpacing(8)

        self.encode_result = QLabel("")
        self.encode_result.setObjectName("resultLabel")
        self.encode_result.setAlignment(Qt.AlignCenter)
        result_layout.addWidget(self.encode_result)

        self.copy_encode_btn = QPushButton("Copy Pesan")
        self.copy_encode_btn.setFixedHeight(32)
        self.copy_encode_btn.clicked.connect(self._copy_encode_text)
        self.copy_encode_btn.setEnabled(False)
        result_layout.addWidget(self.copy_encode_btn)

        layout.addWidget(result_card, 0)

        return widget

    # ==================================
    # DECODE WIDGET
    # ==================================

    def _create_decode_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Carrier selection
        carrier_card = QFrame()
        carrier_card.setObjectName("card")
        carrier_layout = QVBoxLayout(carrier_card)
        carrier_layout.setContentsMargins(16, 16, 16, 16)
        carrier_layout.setSpacing(8)

        carrier_header = QLabel("Pilih Gambar Steganography")
        carrier_header.setObjectName("sectionTitle")
        carrier_layout.addWidget(carrier_header)

        self.decode_path_label = QLabel("Belum ada gambar dipilih")
        self.decode_path_label.setObjectName("pathLabel")
        self.decode_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        carrier_layout.addWidget(self.decode_path_label)

        browse_btn = QPushButton("Browse PNG...")
        browse_btn.setObjectName("browseButton")
        browse_btn.clicked.connect(self._browse_decode_stego)
        carrier_layout.addWidget(browse_btn)

        # Info card
        info_card = QFrame()
        info_card.setObjectName("card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(6)

        self.decode_info_label = QLabel("")
        self.decode_info_label.setObjectName("infoLabel")
        info_layout.addWidget(self.decode_info_label)

        layout.addWidget(carrier_card)
        layout.addWidget(info_card, 1)

        # Password
        pwd_card = QFrame()
        pwd_card.setObjectName("card")
        pwd_layout = QVBoxLayout(pwd_card)
        pwd_layout.setContentsMargins(16, 16, 16, 16)
        pwd_layout.setSpacing(8)

        pwd_label = QLabel("Password:")
        pwd_label.setFixedHeight(30)
        pwd_layout.addWidget(pwd_label)

        self.decode_password = QLineEdit()
        self.decode_password.setPlaceholderText("Masukkan password gambar...")
        self.decode_password.setEchoMode(QLineEdit.EchoMode.Password)
        pwd_layout.addWidget(self.decode_password)

        layout.addWidget(pwd_card)

        # Decode button
        btn_card = QFrame()
        btn_card.setObjectName("card")
        btn_layout = QHBoxLayout(btn_card)
        btn_layout.setContentsMargins(16, 16, 16, 16)
        btn_layout.setSpacing(12)

        self.decode_btn = QPushButton("Decode Message")
        self.decode_btn.setObjectName("decodeButton")
        self.decode_btn.setFixedHeight(44)
        self.decode_btn.clicked.connect(self._on_decode)
        btn_layout.addStretch()
        btn_layout.addWidget(self.decode_btn)
        btn_layout.addStretch()

        layout.addWidget(btn_card)

        # Result
        result_card = QFrame()
        result_card.setObjectName("card")
        result_layout = QVBoxLayout(result_card)
        result_layout.setContentsMargins(16, 16, 16, 16)
        result_layout.setSpacing(8)

        self.decode_result = QLabel("")
        self.decode_result.setObjectName("resultLabel")
        self.decode_result.setAlignment(Qt.AlignCenter)
        result_layout.addWidget(self.decode_result)

        self.copy_decode_btn = QPushButton("Copy Pesan")
        self.copy_decode_btn.setFixedHeight(32)
        self.copy_decode_btn.clicked.connect(self._copy_decode_text)
        self.copy_decode_btn.setEnabled(False)
        result_layout.addWidget(self.copy_decode_btn)

        layout.addWidget(result_card, 0)

        # Capacity note
        cap_label = QLabel(
            "⚠ Jika pesan tidak bisa diekstrak, cek password dan pastikan gambar valid PNG."
        )
        cap_label.setObjectName("infoLabel")
        cap_label.setWordWrap(True)
        layout.addWidget(cap_label, 0)

        return widget

    # ==================================
    # NAVIGATION / MODE SWITCH
    # ==================================

    def _update_mode_ui(self, mode: str):
        """Update UI based on selected tab (encode/decode)."""
        self._current_mode = mode

        if mode == "encode":
            self.tabs.setCurrentIndex(0)
            self.encode_btn.setDefault(True)
            self.decode_btn.setDefault(False)
            self.status_label.setText("Mode: Encode — Sisipkan pesan ke gambar PNG")
        else:
            self.tabs.setCurrentIndex(1)
            self.decode_btn.setDefault(True)
            self.encode_btn.setDefault(False)
            self.status_label.setText("Mode: Decode — Ekstrak pesan dari gambar PNG")

    def switch_to_encode(self):
        self._update_mode_ui("encode")

    def switch_to_decode(self):
        self._update_mode_ui("decode")

    # ==================================
    # BROWSE FUNCTIONS
    # ==================================

    def _browse_encode_carrier(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Gambar Carrier (PNG)",
            "",
            "PNG Image (*.png);;All Files (*.*)",
        )
        if not file_path:
            return

        self._encode_path = file_path
        self.encode_path_label.setText(Path(file_path).name)

        # Show info
        try:
            info = get_image_info(Path(file_path))
            cap_kb = info["capacity_kb"]
            self.encode_info_label.setText(
                f"✓ {info['width']}×{info['height']} px | Kapasitas: ~{cap_kb} KB"
            )
        except FormatError:
            self.encode_info_label.setText("✗ Format gambar tidak valid")

    def _browse_decode_stego(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Gambar Terenkripsi (PNG)",
            "",
            "PNG Image (*.png);;All Files (*.*)",
        )
        if not file_path:
            return

        self._decode_path = file_path
        self.decode_path_label.setText(Path(file_path).name)

        # Show info
        try:
            info = get_image_info(Path(file_path))
            cap_kb = info["capacity_kb"]
            self.decode_info_label.setText(
                f"✓ {info['width']}×{info['height']} px | Kapasitas: ~{cap_kb} KB"
            )
        except FormatError:
            self.decode_info_label.setText("✗ Format gambar tidak valid")

    # ==================================
    # PROCESS HANDLERS
    # ==================================

    def _on_encode(self):
        """Handle Encode button click."""
        carrier_path = Path(self._encode_path) if self._encode_path else None
        message = self.encode_message.text().strip()
        password = self.encode_password.text().strip()

        # Validation
        if not carrier_path:
            QMessageBox.warning(
                self,
                "Gambar Tidak Dipilih",
                "Silakan pilih gambar carrier terlebih dahulu."
            )
            return

        if not message:
            QMessageBox.warning(
                self,
                "Pesan Kosong",
                "Masukkan pesan rahasia yang akan disembunyikan."
            )
            return

        if not password:
            QMessageBox.warning(
                self,
                "Password Kosong",
                "Masukkan kata sandi untuk mengenkripsi pesan."
            )
            return

        # Check capacity
        try:
            capacity = calculate_capacity(carrier_path)
            msg_size = len(message.encode("utf-8"))
            if msg_size > capacity:
                QMessageBox.warning(
                    self,
                    "Kapasitas Tidak Cukup",
                    f"Pesan terlalu besar untuk gambar ini.\n"
                    f"Kapasitas maksimal: {capacity} byte\n"
                    f"Ukuran pesan: {msg_size} byte.\n"
                    f"Gunakan gambar yang lebih besar atau pesan yang lebih pendek."
                )
                return
        except FormatError as e:
            QMessageBox.critical(self, "Error Gambar", str(e))
            return

        # Perform encode
        output_path = carrier_path.parent / f"stego_{Path(carrier_path).name}"
        self.status_label.setText("⏳ Sedang menyisipkan pesan ke gambar...")

        try:
            encode_image(carrier_path, message, password, output_path)
            self._last_stego_path = str(output_path)
            self._show_encode_success_dialog(output_path, password)

        except CapacityError as e:
            QMessageBox.critical(self, "Kapasitas Melebihi", str(e))
            self.status_label.setText("Gagal — kapasitas gambar tidak mencukupi")
        except FormatError as e:
            QMessageBox.critical(self, "Format Error", str(e))
            self.status_label.setText("Gagal — format gambar tidak valid")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Encode Error",
                f"Terjadi kesalahan tak terduga:\n{str(e)}"
            )
            self.status_label.setText("Gagal — error selama encode")

    def _show_encode_success_dialog(self, stego_path: Path, password: str):
        """Show dialog with Save Image / Send to Chat options after successful encode."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle("Encoding Completed!")
        dialog.setFixedSize(500, 400)
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("Encoding Completed!")
        title.setObjectName("dialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Your secret message has been successfully embedded into the image.\n"
            "Choose what to do with the steganography image:"
        )
        desc.setObjectName("dialogDesc")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        # Preview
        preview_label = QLabel()
        preview_label.setObjectName("previewLabel")
        preview_label.setAlignment(Qt.AlignCenter)
        preview_label.setFixedSize(300, 200)
        preview_label.setScaledContents(False)
        layout.addWidget(preview_label, alignment=Qt.AlignCenter)

        # Load preview
        try:
            pixmap = QPixmap(str(stego_path))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                preview_label.setPixmap(pixmap)
        except Exception:
            preview_label.setText("[Preview tidak tersedia]")

        # Info
        info = QLabel(
            f"File: {stego_path.name}\n"
            f"Ukuran: {stego_path.stat().st_size / 1024:.1f} KB\n"
            f"Password: {password[:3]}{'*' * (len(password) - 3)}"
        )
        info.setObjectName("dialogInfo")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

        # Warning
        warning = QLabel(
            "⚠ Penerima memerlukan password yang sama untuk mendekripsi pesan tersembunyi."
        )
        warning.setObjectName("dialogWarning")
        warning.setWordWrap(True)
        warning.setAlignment(Qt.AlignCenter)
        layout.addWidget(warning)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        save_btn = QPushButton("Save Image")
        save_btn.setObjectName("saveButton")
        save_btn.setFixedHeight(44)
        save_btn.clicked.connect(lambda: self._handle_save_image(dialog, stego_path))
        btn_layout.addWidget(save_btn)

        send_btn = QPushButton("Send to Chat")
        send_btn.setObjectName("sendButton")
        send_btn.setFixedHeight(44)
        send_btn.clicked.connect(lambda: self._handle_send_to_chat(dialog, stego_path))
        btn_layout.addWidget(send_btn)

        layout.addLayout(btn_layout)

        # Add stylesheet for dialog
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
            }
            QLabel#dialogTitle {
                color: #f1f5f9;
                font-size: 20px;
                font-weight: bold;
            }
            QLabel#dialogDesc {
                color: #94a3b8;
                font-size: 12px;
            }
            QLabel#previewLabel {
                background-color: #111c30;
                border: 1px solid #24334d;
                border-radius: 8px;
            }
            QLabel#dialogInfo {
                color: #64748b;
                font-size: 11px;
                background-color: #0b1528;
                border-radius: 6px;
                padding: 8px;
            }
            QLabel#dialogWarning {
                color: #fbbf24;
                font-size: 11px;
                background-color: #1f2a1a;
                border: 1px solid #3d4a2d;
                border-radius: 6px;
                padding: 8px;
            }
            QPushButton#saveButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#saveButton:hover {
                background-color: #3b82f6;
            }
            QPushButton#sendButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#sendButton:hover {
                background-color: #34d399;
            }
        """)

        dialog.exec()

    def _handle_save_image(self, dialog, stego_path: Path):
        """Handle Save Image option."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Gambar Steganography",
            str(Path.home() / "Desktop" / "secret_message.png"),
            "PNG Image (*.png)"
        )

        if not save_path:
            return

        try:
            shutil.copy2(stego_path, save_path)
            QMessageBox.information(
                self,
                "Berhasil Disimpan",
                f"Gambar steganography berhasil disimpan ke:\n{save_path}"
            )
            self.status_label.setText(f"✓ Disimpan: {Path(save_path).name}")
            self.encode_result.setText(
                f"✓ Pesan berhasil disembunyikan!\n"
                f"Disimpan ke: {Path(save_path).name}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Gagal Menyimpan",
                f"Tidak dapat menyimpan file:\n{str(e)}"
            )
            self.status_label.setText("Gagal menyimpan file")

        dialog.accept()

    def _handle_send_to_chat(self, dialog, stego_path: Path):
        """Handle Send to Chat option - emit signal for parent to handle."""
        dialog.accept()
        self.status_label.setText("⏳ Membuka pemilihan kontak...")
        self.stego_image_ready.emit(str(stego_path))

    def _on_decode(self):
        """Handle Decode button click."""
        stego_path = Path(self._decode_path) if self._decode_path else None
        password = self.decode_password.text().strip()

        # Validation
        if not stego_path:
            QMessageBox.warning(
                self,
                "Gambar Tidak Dipilih",
                "Silakan pilih gambar steganography terlebih dahulu."
            )
            return

        if not password:
            QMessageBox.warning(
                self,
                "Password Kosong",
                "Masukkan kata sandi untuk mendekripsi pesan."
            )
            return

        # Perform decode
        self.status_label.setText("⏳ Sedang mengekstrak dan mendekripsi...")

        try:
            plaintext = decode_image(stego_path, password)
            self.decode_result.setText(f"🔓 Pesan: {plaintext}")
            self.decode_result.setStyleSheet("color: #f1f5f9; font-size: 13px;")
            self.copy_decode_btn.setEnabled(True)

            self.status_label.setText("✓ Decode selesai — pesan berhasil diekstrak")

        except NoMessageError as e:
            QMessageBox.warning(
                self,
                "Tidak Ada Pesan",
                str(e)
            )
            self.decode_result.setText("✗ Tidak ditemukan pesan tersembunyi")
            self.decode_result.setStyleSheet("color: #f87171; font-size: 12px;")
            self.copy_decode_btn.setEnabled(False)
            self.status_label.setText("Decode selesai — tidak ada pesan")

        except DecryptionError as e:
            QMessageBox.critical(
                self,
                "Password Salah / Data Rusak",
                str(e)
            )
            self.decode_result.setText("✗ Dekripsi gagal — password salah atau gambar rusak")
            self.decode_result.setStyleSheet("color: #f87171; font-size: 12px;")
            self.copy_decode_btn.setEnabled(False)
            self.status_label.setText("Gagal — password salah atau data rusak")

        except FormatError as e:
            QMessageBox.critical(self, "Format Error", str(e))
            self.decode_result.setText("✗ Gambar tidak valid")
            self.decode_result.setStyleSheet("color: #f87171; font-size: 12px;")
            self.copy_decode_btn.setEnabled(False)
            self.status_label.setText("Gagal — format gambar salah")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Decode Error",
                f"Terjadi kesalahan tak terduga:\n{str(e)}"
            )
            self.decode_result.setText("✗ Error tidak terduga")
            self.decode_result.setStyleSheet("color: #f87171; font-size: 12px;")
            self.copy_decode_btn.setEnabled(False)
            self.status_label.setText("Gagal — error tidak terduga")

    # ==================================
    # COPY HELPERS
    # ==================================

    def _copy_encode_text(self):
        text = self.encode_result.text()
        if not text or "✓" not in text:
            return

        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        # Extract just the message part
        msg_line = text.split("Disimpan ke:")[0] if "Disimpan ke:" in text else text
        clipboard.setText(msg_line)
        QMessageBox.information(self, "Disalin", "Pesan berhasil disalin ke clipboard.")

    def _copy_decode_text(self):
        text = self.decode_result.text()
        if not text or "🔓 Pesan:" not in text:
            return

        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        # Extract just the plaintext after ": "
        msg = text.split("🔓 Pesan: ", 1)[1] if "🔓 Pesan: " in text else text
        clipboard.setText(msg)
        QMessageBox.information(self, "Disalin", "Pesan berhasil disalin ke clipboard.")