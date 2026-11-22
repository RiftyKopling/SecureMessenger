
import json

from pathlib import Path

import cv2

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap

from security.dongle import verify_dongle
from security.face_recognition import FaceVerification


PROJECT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_DIR / "config" / "device_config.json"


class AuthenticationWindow(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Secure Messenger - Authentication")
        self.resize(650, 550)
        self.setMinimumSize(550, 450)

        self.verifier = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        self.display_name = None
        self.success_count = 0
        self.required_matches = 5
        self.authenticated_name = None

        self.init_ui()
        self.authenticate_device()

    def init_ui(self):

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        title = QLabel("Secure Messenger")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size: 25px; font-weight: bold; color: #f1f5f9;"
        )

        subtitle = QLabel("Device and Face Authentication")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #94a3b8;")

        self.camera_label = QLabel("Waiting for authentication...")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setMinimumSize(480, 320)
        self.camera_label.setStyleSheet("""
            QLabel {
                background-color: #020617;
                color: #64748b;
                border: 1px solid #334155;
                border-radius: 10px;
            }
        """)

        self.status_label = QLabel("Checking USB Dongle...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(
            "color: #cbd5e1; font-size: 13px;"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.camera_label)
        layout.addWidget(self.status_label)

        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
            }
        """)

    def authenticate_device(self):

        # 1. Verifikasi USB Dongle

        try:
            result = verify_dongle()

            if not result["valid"]:
                self.reject_authentication(result["message"])
                return

            if not CONFIG_PATH.exists():
                self.reject_authentication(
                    "Device configuration tidak ditemukan."
                )
                return

            config = json.loads(
                CONFIG_PATH.read_text(encoding="utf-8")
            )

            self.display_name = config.get("display_name")

            if not self.display_name:
                self.reject_authentication(
                    "Display name tidak ditemukan."
                )
                return

            self.status_label.setText(
                f"USB verified. Welcome, {self.display_name}. "
                "Starting face verification..."
            )

        except Exception as error:
            self.reject_authentication(str(error))
            return

        # 2. Persiapkan Face Verification

        try:
            self.verifier = FaceVerification(threshold=70)
            self.verifier.start_camera()

            self.status_label.setText(
                "Camera active. Please look at the camera."
            )

            self.timer.start(30)

        except Exception as error:
            self.reject_authentication(str(error))

    def update_frame(self):

        try:
            success, frame = self.verifier.camera.read()

            if not success:
                raise RuntimeError("Gagal membaca kamera.")

            result = self.verifier.verify_frame(frame)

            if result["recognized"]:

                recognized_name = result["name"]

                if recognized_name == self.display_name:
                    self.success_count += 1

                    self.status_label.setText(
                        f"Face recognized: {recognized_name} "
                        f"({self.success_count}/{self.required_matches})"
                    )

                    if self.success_count >= self.required_matches:
                        self.authenticated_name = recognized_name
                        self.complete_authentication()

                else:
                    self.success_count = 0
                    self.status_label.setText(
                        "Face identity does not match device owner."
                    )

            else:
                self.success_count = 0
                self.status_label.setText(result["message"])

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            height, width, channel = rgb.shape

            image = QImage(
                rgb.data,
                width,
                height,
                channel * width,
                QImage.Format.Format_RGB888
            ).copy()

            pixmap = QPixmap.fromImage(image)

            self.camera_label.setPixmap(
                pixmap.scaled(
                    self.camera_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )

        except Exception as error:
            self.reject_authentication(str(error))

    def complete_authentication(self):

        self.timer.stop()

        if self.verifier:
            self.verifier.stop_camera()

        self.status_label.setText(
            f"Authentication successful. Welcome, {self.display_name}!"
        )

        self.accept()

    def reject_authentication(self, message):

        self.timer.stop()

        if self.verifier:
            self.verifier.stop_camera()

        self.status_label.setText(
            "Authentication failed."
        )

        QMessageBox.critical(
            self,
            "Authentication Failed",
            message
        )

        self.reject()

    def closeEvent(self, event):

        self.timer.stop()

        if self.verifier:
            self.verifier.stop_camera()

        event.accept()
