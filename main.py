import sys

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMessageBox,
)

from ui.windows.login_window import LoginWindow
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

    while True:
        # ==================================
        # LOGIN WINDOW
        # ==================================

        login_window = LoginWindow()
        login_result = login_window.exec()

        if login_result != QDialog.DialogCode.Accepted:
            # User cancelled login (closed window)
            return 0

        authenticated_user = login_window.authenticated_user
        if not authenticated_user:
            continue

        username = authenticated_user.username

        # ==================================
        # CHECK DEVICE REGISTRATION
        # ==================================

        if not CONFIG_PATH.exists():
            QMessageBox.warning(
                None,
                "Device Not Registered",
                "USB Dongle belum didaftarkan. Silakan daftarkan perangkat terlebih dahulu."
            )
            open_registration()
            continue

        if not MODEL_PATH.exists() or not LABEL_PATH.exists():
            QMessageBox.warning(
                None,
                "Face Model Not Found",
                "Model pengenalan wajah belum tersedia. Silakan daftarkan wajah terlebih dahulu."
            )
            open_registration()
            continue

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
            # Offer to re-register
            ask_registration(str(error))
            continue

        if not dongle_result["valid"]:
            ask_registration(dongle_result["message"])
            continue

        # ==================================
        # FACE VERIFICATION
        # ==================================

        authentication = AuthenticationWindow()

        if authentication.exec() != QDialog.DialogCode.Accepted:
            ask_registration(
                "Face verification failed or was cancelled."
            )
            continue

        # ==================================
        # OPEN MAIN WINDOW
        # ==================================

        # The authenticated_name from face verification should match
        # the display_name on the USB dongle
        display_name = authentication.authenticated_name

        window = MainWindow(username)
        window.show()

        return app.exec()


if __name__ == "__main__":
    sys.exit(main())