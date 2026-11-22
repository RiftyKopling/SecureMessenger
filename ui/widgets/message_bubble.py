
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt


class MessageBubble(QWidget):

    def __init__(self, message, outgoing=False, parent=None):
        super().__init__(parent)

        self.message = message
        self.outgoing = outgoing

        self.init_ui()

    def init_ui(self):

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        bubble = QLabel(self.message)
        bubble.setWordWrap(True)
        bubble.setMaximumWidth(450)
        bubble.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum
        )

        bubble.setObjectName(
            "outgoingMessage" if self.outgoing
            else "incomingMessage"
        )

        bubble_layout = QVBoxLayout()
        bubble_layout.setContentsMargins(0, 0, 0, 0)
        bubble_layout.addWidget(bubble)

        if self.outgoing:
            main_layout.addStretch()
            main_layout.addLayout(bubble_layout)
        else:
            main_layout.addLayout(bubble_layout)
            main_layout.addStretch()

