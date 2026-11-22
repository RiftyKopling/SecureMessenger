"""
Login Window for Secure Messenger.

Handles username/password authentication against local database.
After successful login, proceeds to USB dongle and face verification.
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
    QCheckBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from database.db import authenticate_user, init_db


class LoginWindow(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Secure Messenger - Login")
        self.resize(450, 500)
        self.setMinimumSize(400, 450)

        self.authenticated_user = None

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(35, 30, 35, 30)
        main_layout.setSpacing(18)

        # HEADER
        title = QLabel("Secure Messenger")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Enter your credentials to continue")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # LOGIN FORM CARD
        login_card = QFrame()
        login_card.setObjectName("card")

        login_layout = QVBoxLayout(login_card)
        login_layout.setContentsMargins(24, 24, 24, 24)
        login_layout.setSpacing(16)

        # Username field
        login_layout.addWidget(QLabel("Username"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setFixedHeight(44)
        self.username_input.setClearButtonEnabled(True)
        self.username_input.returnPressed.connect(self.on_login_clicked)
        login_layout.addWidget(self.username_input)

        # Password field
        login_layout.addWidget(QLabel("Password"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setFixedHeight(44)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setClearButtonEnabled(True)
        self.password_input.returnPressed.connect(self.on_login_clicked)
        login_layout.addWidget(self.password_input)

        # Remember me (optional)
        self.remember_checkbox = QCheckBox("Remember me")
        self.remember_checkbox.setObjectName("rememberCheckbox")
        login_layout.addWidget(self.remember_checkbox)

        # Error label (hidden by default)
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        login_layout.addWidget(self.error_label)

        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.setObjectName("loginButton")
        self.login_button.setFixedHeight(48)
        self.login_button.clicked.connect(self.on_login_clicked)
        login_layout.addWidget(self.login_button)

        main_layout.addWidget(login_card)

        # REGISTER LINK
        register_layout = QHBoxLayout()
        register_layout.addStretch()

        register_label = QLabel("Don't have an account?")
        register_label.setObjectName("linkLabel")

        self.register_button = QPushButton("Register")
        self.register_button.setObjectName("linkButton")
        self.register_button.setFlat(True)
        self.register_button.clicked.connect(self.open_registration)

        register_layout.addWidget(register_label)
        register_layout.addWidget(self.register_button)
        register_layout.addStretch()

        main_layout.addLayout(register_layout)

        main_layout.addStretch()

        # FOOTER
        footer = QLabel("SECURE MESSENGER • ENCRYPTED COMMUNICATION")
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
                font-size: 28px;
                font-weight: bold;
            }

            QLabel#subtitle {
                color: #94a3b8;
                font-size: 13px;
            }

            QLabel#linkLabel {
                color: #94a3b8;
            }

            QPushButton#linkButton {
                color: #60a5fa;
                background: transparent;
                border: none;
                font-size: 12px;
                font-weight: bold;
            }

            QPushButton#linkButton:hover {
                color: #93c5fd;
                text-decoration: underline;
            }

            QLabel#errorLabel {
                color: #f87171;
                font-size: 11px;
                background-color: #450a0a;
                border: 1px solid #991b1b;
                border-radius: 6px;
                padding: 8px 12px;
            }

            QLabel#footer {
                color: #64748b;
                font-size: 10px;
                letter-spacing: 1px;
            }

            QFrame#card {
                background-color: #111c30;
                border: 1px solid #24334d;
                border-radius: 16px;
            }

            QLineEdit {
                background-color: #0b1528;
                color: white;
                border: 1px solid #293a56;
                border-radius: 10px;
                padding: 12px;
                font-size: 13px;
            }

            QLineEdit:focus {
                border: 1px solid #3b82f6;
            }

            QCheckBox#rememberCheckbox {
                color: #94a3b8;
                font-size: 12px;
                spacing: 8px;
            }

            QCheckBox#rememberCheckbox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #334155;
                border-radius: 4px;
                background-color: #0b1528;
            }

            QCheckBox#rememberCheckbox::indicator:checked {
                background-color: #2563eb;
                border: 1px solid #2563eb;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEwLjUgMUwyLjUgOS41IDEgNyIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz48L3N2Zz4=);
            }

            QPushButton#loginButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
            }

            QPushButton#loginButton:hover {
                background-color: #3b82f6;
            }

            QPushButton#loginButton:pressed {
                background-color: #1d4ed8;
            }

            QPushButton#loginButton:disabled {
                background-color: #334155;
                color: #94a3b8;
            }
        """)

    def on_login_clicked(self):
        """Handle login button click."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username:
            self.show_error("Username tidak boleh kosong.")
            self.username_input.setFocus()
            return

        if not password:
            self.show_error("Password tidak boleh kosong.")
            self.password_input.setFocus()
            return

        self.login_button.setEnabled(False)
        self.login_button.setText("Memverifikasi...")
        self.hide_error()

        # Authenticate against database
        init_db()  # Ensure database exists
        user = authenticate_user(username, password)

        if user is None:
            self.show_error("Username atau password salah.")
            self.login_button.setEnabled(True)
            self.login_button.setText("Login")
            self.password_input.clear()
            self.password_input.setFocus()
            return

        # Login successful
        self.authenticated_user = user
        self.accept()

    def show_error(self, message):
        """Show error message."""
        self.error_label.setText(message)
        self.error_label.show()

    def hide_error(self):
        """Hide error message."""
        self.error_label.hide()
        self.error_label.setText("")

    def open_registration(self):
        """Open registration window."""
        from ui.windows.register_window import RegisterWindow

        reg_window = RegisterWindow(self)
        if reg_window.exec() == QDialog.DialogCode.Accepted:
            # Registration successful, clear form for login
            self.username_input.clear()
            self.password_input.clear()
            self.username_input.setFocus()