
import sys

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMessageBox,
)

from ui.windows.register_window import RegisterWindow
from ui.windows.authentication_window import AuthenticationWindow
from ui.windows.main_window import MainWindow
from database.db import init_db

from security.dongle import (
    CONFIG_PATH,
    verify_dongle,
    reset_dongle,
)

from security.face_recognition import (
    MODEL_PATH,
    LABEL_PATH,
)


def open_registration():
    window = RegisterWindow()
    window.exec()


def ask_registration(reason):

    answer = QMessageBox.question(
        None,
        "Authentication Failed",
        (
            f"{reason}\n\n"
            "Apakah kamu ingin mendaftarkan USB Dongle "
            "dan wajah yang baru?"
        ),
        QMessageBox.StandardButton.Yes
        | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
    )

    if answer != QMessageBox.StandardButton.Yes:
        return False

    # Hapus konfigurasi USB lama sebelum registrasi baru.
    result = reset_dongle(force=True)

    if not result["valid"]:
        QMessageBox.critical(
            None,
            "Reset Failed",
            result["message"]
        )
        return False

    open_registration()
    return True


def main():
    init_db()
    app = QApplication(sys.argv)
    app.setApplicationName("Secure Messenger")

    # ==================================
    # CHECK REGISTRATION
    # ==================================

    if not CONFIG_PATH.exists():
        open_registration()
        return 0

    if not MODEL_PATH.exists() or not LABEL_PATH.exists():
        open_registration()
        return 0

    # ==================================
    # USB VERIFICATION
    # ==================================

    try:
        dongle_result = verify_dongle()

    except Exception as error:
        QMessageBox.critical(
            None,
            "USB Verification Error",
            str(error)
        )
        return 1

    if not dongle_result["valid"]:

        ask_registration(dongle_result["message"])
        return 0

    # ==================================
    # FACE VERIFICATION
    # ==================================

    authentication = AuthenticationWindow()

    if authentication.exec() != QDialog.DialogCode.Accepted:

        ask_registration(
            "Face verification failed or was cancelled."
        )
        return 0

    # ==================================
    # OPEN MAIN WINDOW
    # ==================================

    username = authentication.authenticated_name
    role = authentication.authenticated_role

    window = MainWindow(username, role=role)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
