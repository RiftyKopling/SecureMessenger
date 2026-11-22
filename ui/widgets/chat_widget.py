
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QFrame,
    QScrollArea,
    QFileDialog,
)
from PySide6.QtCore import Qt, Signal

from ui.widgets.message_bubble import MessageBubble


class ChatWidget(QWidget):
    file_selected = Signal(str)
    message_sent = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_contact = None

        self.init_ui()

    def init_ui(self):

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ==================================
        # CHAT HEADER
        # ==================================

        header = QFrame()
        header.setObjectName("chatHeader")
        header.setFixedHeight(85)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(30, 15, 30, 15)

        contact_info = QVBoxLayout()
        contact_info.setSpacing(5)

        self.contact_name = QLabel("Select a contact")
        self.contact_name.setObjectName("contactName")

        self.contact_status = QLabel("●  Waiting for connection")
        self.contact_status.setObjectName("contactStatus")

        contact_info.addWidget(self.contact_name)
        contact_info.addWidget(self.contact_status)

        header_layout.addLayout(contact_info)
        header_layout.addStretch()

        self.security_button = QPushButton("♢  Security")
        self.security_button.setObjectName("securityButton")

        header_layout.addWidget(self.security_button)

        main_layout.addWidget(header)

        # ==================================
        # MESSAGE AREA
        # ==================================

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setObjectName("chatScroll")
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.chat_content = QWidget()

        self.message_layout = QVBoxLayout(self.chat_content)
        self.message_layout.setContentsMargins(30, 25, 30, 25)
        self.message_layout.setSpacing(15)
        self.message_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_content)

        main_layout.addWidget(self.chat_scroll)

        # ==================================
        # MESSAGE INPUT
        # ==================================

        input_container = QFrame()
        input_container.setObjectName("inputContainer")

        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(25, 18, 25, 18)
        input_layout.setSpacing(12)

        # Attach File Button

        attach_button = QPushButton("📎 Attach")
        attach_button.setObjectName("attachButton")
        attach_button.setFixedSize(90, 48)

        attach_button.clicked.connect(
            self.select_file
        )

        # Message Input

        self.message_input = QLineEdit()
        self.message_input.setObjectName("messageInput")
        self.message_input.setPlaceholderText(
            "Write a secure message..."
        )
        self.message_input.setFixedHeight(48)

        self.message_input.returnPressed.connect(
            self.send_message
        )

        # Send Button

        send_button = QPushButton("Send  ➤")
        send_button.setObjectName("sendButton")
        send_button.setFixedSize(105, 48)

        send_button.clicked.connect(
            self.send_message
        )

        input_layout.addWidget(attach_button)
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_button)

        main_layout.addWidget(input_container)

        # ==================================
        # STYLING
        # ==================================

        self.setStyleSheet("""
            
            QPushButton#attachButton {
                background-color: #172c45;
                color: #60a5fa;
                border: 1px solid #29466b;
                border-radius: 9px;
                font-size: 11px;
                font-weight: bold;
            }

            QPushButton#attachButton:hover {
                background-color: #203b5c;
            }

            QWidget {
                background-color: #0b1120;
            }

            QFrame#chatHeader {
                background-color: #111c30;
                border-bottom: 1px solid #24334d;
            }

            QLabel#contactName {
                color: #f1f5f9;
                font-size: 16px;
                font-weight: bold;
            }

            QLabel#contactStatus {
                color: #34d399;
                font-size: 11px;
            }

            QPushButton#securityButton {
                background-color: #172c45;
                color: #60a5fa;
                border: 1px solid #29466b;
                border-radius: 8px;
                padding: 9px 15px;
                font-size: 11px;
                font-weight: bold;
            }

            QPushButton#securityButton:hover {
                background-color: #203b5c;
            }

            QScrollArea#chatScroll {
                background-color: #0b1120;
                border: none;
            }

            QLabel#incomingMessage {
                background-color: #1a2940;
                color: #e2e8f0;
                border: 1px solid #293a56;
                border-radius: 12px;
                padding: 12px 16px;
                font-size: 13px;
            }

            QLabel#outgoingMessage {
                background-color: #1d4ed8;
                color: white;
                border-radius: 12px;
                padding: 12px 16px;
                font-size: 13px;
            }

            QFrame#inputContainer {
                background-color: #111c30;
                border-top: 1px solid #24334d;
            }

            QLineEdit#messageInput {
                background-color: #0b1528;
                color: white;
                border: 1px solid #293a56;
                border-radius: 9px;
                padding: 0px 15px;
                font-size: 13px;
            }

            QLineEdit#messageInput:focus {
                border: 1px solid #3b82f6;
            }

            QPushButton#sendButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 9px;
                font-size: 12px;
                font-weight: bold;
            }

            QPushButton#sendButton:hover {
                background-color: #3b82f6;
            }

        """)

    # ==================================
    # CONTACT MANAGEMENT
    # ==================================

    def set_contact(self, name):

        self.current_contact = name
        self.contact_name.setText(name)
        self.contact_status.setText("●  Demo conversation")

        self.clear_messages()

        self.add_message(
            f"Percakapan dengan {name} dimulai.",
            outgoing=False
        )

    # ==================================
    # MESSAGE MANAGEMENT
    # ==================================

    def clear_messages(self):

        while self.message_layout.count():

            item = self.message_layout.takeAt(0)
            widget = item.widget()

            if widget:
                widget.deleteLater()

        self.message_layout.addStretch()

    def add_message(self, text, outgoing=False):

        bubble = MessageBubble(
            message=text,
            outgoing=outgoing
        )

        self.message_layout.insertWidget(
            self.message_layout.count() - 1,
            bubble
        )

        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def send_message(self):

        text = self.message_input.text().strip()

        if not text or not self.current_contact:
            return

        self.add_message(text, outgoing=True)

        self.message_input.clear()

        self.message_sent.emit(text)

    # ==================================
    # FILE SELECTION
    # ==================================

    def select_file(self):

        if not self.current_contact:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Send",
            "",
            "All Files (*.*)"
        )

        if not file_path:
            return

        self.file_selected.emit(file_path)
