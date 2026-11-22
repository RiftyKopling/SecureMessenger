
import sys

from PySide6.QtWidgets import QApplication

from ui.windows.main_window import MainWindow


def main():

    app = QApplication(sys.argv)
    app.setApplicationName("Secure Messenger")

    # Langsung membuka halaman utama tanpa autentikasi
    window = MainWindow(username="Test User")
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
