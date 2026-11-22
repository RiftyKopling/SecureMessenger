
import cv2

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QMessageBox,
    QProgressBar,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap

from security.face_recognition import FaceEnrollment


class CameraWidget(QDialog):

    # Signal emitted when face enrollment training is completed
    enrollment_completed = Signal()

    def __init__(self, display_name, parent=None):
        super().__init__(parent)

        self.enrollment = FaceEnrollment(display_name)
        self.current_gray = None
        self.current_faces = []
        self.display_name = display_name
        self.camera_active = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        self.init_ui()

    def init_ui(self):

        self.setWindowTitle("Secure Messenger - Face Enrollment")
        self.resize(1000, 720)
        self.setMinimumSize(850, 650)

        self.setStyleSheet("""
            QWidget {
                background-color: #0b1120;
                color: #e2e8f0;
                font-family: "Segoe UI", sans-serif;
                font-size: 12px;
            }

            QFrame#header {
                background-color: #111c32;
                border: 1px solid #263650;
                border-radius: 16px;
            }

            QFrame#camera_card {
                background-color: #111c32;
                border: 1px solid #263650;
                border-radius: 16px;
            }

            QFrame#info_card {
                background-color: #111c32;
                border: 1px solid #263650;
                border-radius: 16px;
            }

            QLabel#main_title {
                font-size: 25px;
                font-weight: 700;
                color: #f8fafc;
            }

            QLabel#subtitle {
                font-size: 12px;
                color: #94a3b8;
            }

            QLabel#section_title {
                font-size: 15px;
                font-weight: 700;
                color: #f1f5f9;
            }

            QLabel#camera_preview {
                background-color: #020617;
                color: #64748b;
                border: 2px dashed #334155;
                border-radius: 12px;
                font-size: 14px;
            }

            QLabel#status_label {
                background-color: #172554;
                color: #93c5fd;
                border: 1px solid #1e40af;
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
            }

            QLabel#user_label {
                background-color: #172554;
                color: #93c5fd;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 600;
            }

            QLabel#info_text {
                color: #94a3b8;
                font-size: 12px;
            }

            QProgressBar {
                background-color: #1e293b;
                border: none;
                border-radius: 6px;
                height: 12px;
                text-align: center;
            }

            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 6px;
            }

            QPushButton {
                border: none;
                border-radius: 9px;
                padding: 12px 18px;
                font-size: 12px;
                font-weight: 700;
            }

            QPushButton:disabled {
                background-color: #263449;
                color: #64748b;
            }

            QPushButton#start_button {
                background-color: #2563eb;
                color: white;
            }

            QPushButton#start_button:hover {
                background-color: #3b82f6;
            }

            QPushButton#capture_button {
                background-color: #0891b2;
                color: white;
            }

            QPushButton#capture_button:hover {
                background-color: #06b6d4;
            }

            QPushButton#train_button {
                background-color: #059669;
                color: white;
            }

            QPushButton#train_button:hover {
                background-color: #10b981;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        # =========================
        # HEADER
        # =========================

        header = QFrame()
        header.setObjectName("header")

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)

        title = QLabel("Face Recognition Setup")
        title.setObjectName("main_title")

        subtitle = QLabel(
            "Register your facial identity to secure your account."
        )
        subtitle.setObjectName("subtitle")

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        self.user_label = QLabel(f"USER  •  {self.display_name}")
        self.user_label.setObjectName("user_label")
        self.user_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addWidget(self.user_label)

        main_layout.addWidget(header)

        # =========================
        # CAMERA CARD
        # =========================

        camera_card = QFrame()
        camera_card.setObjectName("camera_card")

        camera_layout = QVBoxLayout(camera_card)
        camera_layout.setContentsMargins(20, 18, 20, 20)
        camera_layout.setSpacing(14)

        camera_header = QHBoxLayout()

        camera_title = QLabel("Camera Preview")
        camera_title.setObjectName("section_title")

        self.camera_indicator = QLabel("● CAMERA OFF")
        self.camera_indicator.setStyleSheet(
            "color: #f87171; font-size: 11px; font-weight: 700;"
        )

        camera_header.addWidget(camera_title)
        camera_header.addStretch()
        camera_header.addWidget(self.camera_indicator)

        self.camera_label = QLabel("CAMERA PREVIEW")
        self.camera_label.setObjectName("camera_preview")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setMinimumHeight(320)
        self.camera_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        camera_layout.addLayout(camera_header)
        camera_layout.addWidget(self.camera_label)

        # Status
        self.status_label = QLabel(
            "● Camera is not active. Start the camera to begin."
        )
        self.status_label.setObjectName("status_label")
        self.status_label.setWordWrap(True)

        camera_layout.addWidget(self.status_label)

        main_layout.addWidget(camera_card, stretch=1)

        # =========================
        # PROGRESS CARD
        # =========================

        info_card = QFrame()
        info_card.setObjectName("info_card")

        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 16, 20, 16)
        info_layout.setSpacing(12)

        progress_header = QHBoxLayout()

        progress_title = QLabel("Face Enrollment Progress")
        progress_title.setObjectName("section_title")

        self.sample_label = QLabel("0 / 10 Samples")
        self.sample_label.setStyleSheet(
            "color: #60a5fa; font-weight: 700; font-size: 12px;"
        )

        progress_header.addWidget(progress_title)
        progress_header.addStretch()
        progress_header.addWidget(self.sample_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 10)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

        info_text = QLabel(
            "Capture 10 face samples. Slightly change your head position "
            "for each capture to improve recognition."
        )
        info_text.setObjectName("info_text")
        info_text.setWordWrap(True)

        info_layout.addLayout(progress_header)
        info_layout.addWidget(self.progress_bar)
        info_layout.addWidget(info_text)

        main_layout.addWidget(info_card)

        # =========================
        # BUTTONS
        # =========================

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.start_button = QPushButton("▶  Start Camera")
        self.start_button.setObjectName("start_button")

        self.capture_button = QPushButton("◎  Capture Face")
        self.capture_button.setObjectName("capture_button")

        self.train_button = QPushButton("✓  Train Face Model")
        self.train_button.setObjectName("train_button")

        self.capture_button.setEnabled(False)
        self.train_button.setEnabled(False)

        self.start_button.clicked.connect(self.start_camera)
        self.capture_button.clicked.connect(self.capture_face)
        self.train_button.clicked.connect(self.train_model)

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.capture_button)
        button_layout.addWidget(self.train_button)

        main_layout.addLayout(button_layout)

    # =========================
    # CAMERA
    # =========================

    def start_camera(self):

        try:
            self.enrollment.start_camera()

            self.camera_active = True
            self.timer.start(30)

            self.start_button.setEnabled(False)
            self.capture_button.setEnabled(True)

            self.camera_indicator.setText("● CAMERA ACTIVE")
            self.camera_indicator.setStyleSheet(
                "color: #4ade80; font-size: 11px; font-weight: 700;"
            )

            self.set_status(
                "Camera is active. Position your face inside the camera.",
                "blue"
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Camera Error",
                str(error)
            )

    def update_frame(self):

        try:
            frame, gray, faces = self.enrollment.get_frame()

            self.current_gray = gray
            self.current_faces = faces

            for (x, y, w, h) in faces:
                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    (34, 197, 94),
                    2
                )

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

            if len(faces) == 1:
                self.set_status(
                    "Face detected. You can capture a sample.",
                    "green"
                )

            elif len(faces) == 0:
                self.set_status(
                    "No face detected. Move closer to the camera.",
                    "blue"
                )

            else:
                self.set_status(
                    "Multiple faces detected. Only one person should be visible.",
                    "red"
                )

        except Exception as error:
            self.timer.stop()

            self.set_status(
                f"Camera error: {error}",
                "red"
            )

            self.stop_camera()

    # =========================
    # FACE CAPTURE
    # =========================

    def capture_face(self):

        if self.current_gray is None:
            return

        if len(self.current_faces) != 1:
            QMessageBox.warning(
                self,
                "Face Detection",
                "Ensure exactly one face is visible."
            )
            return

        try:
            count = self.enrollment.capture_sample(
                self.current_gray,
                self.current_faces[0]
            )

            self.sample_label.setText(
                f"{count} / 10 Samples"
            )

            self.progress_bar.setValue(count)

            if count >= 10:
                self.capture_button.setEnabled(False)
                self.train_button.setEnabled(True)

                self.set_status(
                    "All samples collected. You can now train your face model.",
                    "green"
                )

            else:
                self.set_status(
                    f"Sample {count} captured successfully. Change your face position slightly.",
                    "green"
                )

        except Exception as error:
            QMessageBox.warning(
                self,
                "Capture Failed",
                str(error)
            )

    # =========================
    # MODEL TRAINING
    # =========================

    def train_model(self):

        try:
            self.enrollment.train_model()

            self.timer.stop()
            self.enrollment.stop_camera()
            self.camera_active = False

            self.camera_indicator.setText("● ENROLLMENT COMPLETED")
            self.camera_indicator.setStyleSheet(
                "color: #4ade80; font-size: 11px; font-weight: 700;"
            )

            self.start_button.setEnabled(False)
            self.capture_button.setEnabled(False)
            self.train_button.setEnabled(False)

            self.set_status(
                "Face enrollment completed successfully.",
                "green"
            )

            QMessageBox.information(
                self,
                "Training Successful",
                "Face recognition model saved successfully."
            )

            # Emit signal to notify that enrollment is completed
            self.enrollment_completed.emit()
            # Accept the dialog to close it
            self.accept()

        except Exception as error:
            QMessageBox.critical(
                self,
                "Training Failed",
                str(error)
            )

    # =========================
    # HELPERS
    # =========================

    def set_status(self, message, color="blue"):

        colors = {
            "blue": ("#172554", "#93c5fd", "#1e40af"),
            "green": ("#052e16", "#86efac", "#166534"),
            "red": ("#450a0a", "#fca5a5", "#991b1b"),
        }

        background, foreground, border = colors.get(
            color,
            colors["blue"]
        )

        self.status_label.setText(f"●  {message}")

        self.status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {background};
                color: {foreground};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
            }}
        """)

    def stop_camera(self):

        self.timer.stop()
        self.enrollment.stop_camera()
        self.camera_active = False

        self.start_button.setEnabled(True)
        self.capture_button.setEnabled(False)

        self.camera_indicator.setText("● CAMERA OFF")
        self.camera_indicator.setStyleSheet(
            "color: #f87171; font-size: 11px; font-weight: 700;"
        )

        self.camera_label.clear()
        self.camera_label.setText("CAMERA PREVIEW")

    def closeEvent(self, event):

        self.stop_camera()
        event.accept()
