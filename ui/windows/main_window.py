
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
)
from PySide6.QtCore import Qt

from ui.widgets.chat_widget import ChatWidget


class MainWindow(QMainWindow):

    def __init__(self, username="User"):
        super().__init__()

        self.username = username

        self.setWindowTitle("Secure Messenger")
        self.resize(1250, 800)
        self.setMinimumSize(900, 600)

        self.init_ui()
        self.load_contacts()

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

        # Branding

        brand = QLabel("⬡  SECURE MESSENGER")
        brand.setObjectName("brand")

        sidebar_layout.addWidget(brand)

        subtitle = QLabel("Private communication")
        subtitle.setObjectName("sidebarSubtitle")

        sidebar_layout.addWidget(subtitle)

        # Profile

        profile = QFrame()
        profile.setObjectName("profileCard")

        profile_layout = QHBoxLayout(profile)
        profile_layout.setContentsMargins(12, 12, 12, 12)

        avatar = QLabel(self.username[:1].upper())
        avatar.setObjectName("avatar")

        profile_info = QVBoxLayout()

        username_label = QLabel(self.username)
        username_label.setObjectName("profileName")

        status_label = QLabel("●  Online")
        status_label.setObjectName("onlineStatus")

        profile_info.addWidget(username_label)
        profile_info.addWidget(status_label)

        profile_layout.addWidget(avatar)
        profile_layout.addLayout(profile_info)
        profile_layout.addStretch()

        sidebar_layout.addSpacing(15)
        sidebar_layout.addWidget(profile)

        # Search

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

        # Conversation title

        conversation_header = QLabel("MESSAGES")
        conversation_header.setObjectName("sectionTitle")

        sidebar_layout.addSpacing(15)
        sidebar_layout.addWidget(conversation_header)

        # Contact list

        self.contact_list = QListWidget()
        self.contact_list.setObjectName("contactList")

        self.contact_list.currentItemChanged.connect(
            self.select_contact
        )

        sidebar_layout.addWidget(self.contact_list)

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

        contacts = [
            "Alice",
            "Bob",
            "Charlie",
            "David",
            "Emily",
        ]

        for name in contacts:

            item = QListWidgetItem(f"●   {name}")
            item.setData(
                Qt.ItemDataRole.UserRole,
                name
            )

            self.contact_list.addItem(item)

        self.contact_list.setCurrentRow(0)

    def filter_contacts(self, text):

        for index in range(self.contact_list.count()):

            item = self.contact_list.item(index)

            name = item.data(
                Qt.ItemDataRole.UserRole
            )

            item.setHidden(
                text.lower() not in name.lower()
            )

    def select_contact(self, current, previous):

        if current is None:
            return

        name = current.data(
            Qt.ItemDataRole.UserRole
        )

        self.chat_widget.set_contact(name)

    # ==================================
    # MESSAGE EVENT
    # ==================================

    def handle_message_sent(self, text):

        print(
            f"[MESSAGE] "
            f"To: {self.chat_widget.current_contact} "
            f"| Content: {text}"
        )
