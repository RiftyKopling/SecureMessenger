
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
from ui.widgets.voice_note_bubble import VoiceNoteBubble, VoiceNoteRecorderWidget


class ChatWidget(QWidget):

    file_selected = Signal(str)
    file_download_requested = Signal(str)
    message_sent = Signal(str)
    steganography_requested = Signal()
    voice_note_record_requested = Signal()      # Start recording
    voice_note_send_requested = Signal(str)     # Send recorded voice note (temp file path)
    voice_note_cancel_requested = Signal()      # Cancel recording
    voice_note_play_requested = Signal(str)     # Play voice note (file_id)
    voice_note_seek_requested = Signal(str, int)# Seek voice note (file_id, position_ms)
    voice_note_download_requested = Signal(str) # Download voice note (file_id)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_contact = None
        self._recorder_widget = None

        self.init_ui()

    # ==================================
    # USER INTERFACE
    # ==================================

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

        self.contact_status = QLabel(
            "●  Waiting for connection"
        )
        self.contact_status.setObjectName("contactStatus")

        contact_info.addWidget(self.contact_name)
        contact_info.addWidget(self.contact_status)

        header_layout.addLayout(contact_info)
        header_layout.addStretch()

        self.security_button = QPushButton("♢  Security")
        self.security_button.setObjectName("securityButton")

        self.steganography_button = QPushButton("[Steganography]")
        self.steganography_button.setObjectName("steganographyButton")
        self.steganography_button.clicked.connect(
            lambda: self.steganography_requested.emit()
        )

        header_layout.addWidget(self.security_button)
        header_layout.addWidget(self.steganography_button)

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

        # ATTACH BUTTON

        attach_button = QPushButton("📎 Attach")
        attach_button.setObjectName("attachButton")
        attach_button.setFixedSize(90, 48)

        attach_button.clicked.connect(
            self.select_file
        )

        # MICROPHONE BUTTON (Voice Note)

        self.mic_button = QPushButton("🎤")
        self.mic_button.setObjectName("micButton")
        self.mic_button.setFixedSize(48, 48)
        self.mic_button.setToolTip("Record Voice Note")
        self.mic_button.clicked.connect(self._on_mic_clicked)

        # MESSAGE INPUT

        self.message_input = QLineEdit()
        self.message_input.setObjectName("messageInput")
        self.message_input.setPlaceholderText(
            "Write a secure message..."
        )
        self.message_input.setFixedHeight(48)

        self.message_input.returnPressed.connect(
            self.send_message
        )

        # SEND BUTTON

        send_button = QPushButton("Send  ➤")
        send_button.setObjectName("sendButton")
        send_button.setFixedSize(105, 48)

        send_button.clicked.connect(
            self.send_message
        )

        input_layout.addWidget(attach_button)
        input_layout.addWidget(self.mic_button)
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_button)

        main_layout.addWidget(input_container)

        # ==================================
        # VOICE RECORDER WIDGET (hidden by default)
        # ==================================

        self.recorder_widget = VoiceNoteRecorderWidget()
        self.recorder_widget.recording_finished.connect(
            self._on_recording_finished
        )
        self.recorder_widget.recording_cancelled.connect(
            self._on_recording_cancelled
        )
        self.recorder_widget.hide()
        main_layout.addWidget(self.recorder_widget)

        # ==================================
        # STYLING
        # ==================================

        self.setStyleSheet("""

            QWidget {
                background-color: #0b1120;
            }

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

            QPushButton#steganographyButton {
                background-color: #172c45;
                color: #60a5fa;
                border: 1px solid #29466b;
                border-radius: 8px;
                padding: 9px 15px;
                font-size: 11px;
                font-weight: bold;
            }

            QPushButton#steganographyButton:hover {
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

            QPushButton#micButton {
                background-color: #172c45;
                color: #60a5fa;
                border: 1px solid #29466b;
                border-radius: 9px;
                font-size: 18px;
            }

            QPushButton#micButton:hover {
                background-color: #203b5c;
            }

            QPushButton#micButton:pressed {
                background-color: #ef4444;
                color: white;
                border: 1px solid #ef4444;
            }

            QPushButton#micButton.recording {
                background-color: #ef4444;
                color: white;
                border: 1px solid #ef4444;
            }

            QFrame#fileBubble {
                background-color: #1a2940;
                border: 1px solid #304563;
                border-radius: 12px;
            }

            QLabel#fileName {
                color: #f1f5f9;
                font-size: 13px;
                font-weight: bold;
            }

            QLabel#fileSize {
                color: #94a3b8;
                font-size: 11px;
            }

            QPushButton#downloadButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 7px;
                padding: 8px 14px;
                font-size: 11px;
                font-weight: bold;
            }

            QPushButton#downloadButton:hover {
                background-color: #3b82f6;
            }

            QLabel#fileStatus {
                color: #93c5fd;
                font-size: 10px;
            }

        """)

    # ==================================
    # CONTACT MANAGEMENT
    # ==================================

    def set_contact(self, name):

        self.current_contact = name

        if name:
            self.contact_name.setText(name)
            self.contact_status.setText(
                "●  Waiting for connection"
            )
        else:
            self.contact_name.setText("Select a contact")
            self.contact_status.setText(
                "●  Waiting for connection"
            )

        self.clear_messages()

        if name:
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

    def scroll_to_bottom(self):

        scrollbar = self.chat_scroll.verticalScrollBar()

        scrollbar.setValue(
            scrollbar.maximum()
        )

    def add_message(self, text, outgoing=False):

        bubble = MessageBubble(
            message=text,
            outgoing=outgoing
        )

        self.message_layout.insertWidget(
            self.message_layout.count() - 1,
            bubble
        )

        self.scroll_to_bottom()

    # ==================================
    # FILE MESSAGE BUBBLE
    # ==================================

    def add_file_message(
        self,
        file_id,
        file_name,
        file_size,
        outgoing=False
    ):

        container = QWidget()

        outer_layout = QHBoxLayout(container)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # Pengirim di kanan
        if outgoing:
            outer_layout.addStretch()

        # Bubble file
        bubble = QFrame()
        bubble.setObjectName("fileBubble")
        bubble.setMaximumWidth(340)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(14, 12, 14, 12)
        bubble_layout.setSpacing(9)

        # Informasi file
        info_layout = QHBoxLayout()
        info_layout.setSpacing(10)

        extension = file_name.rsplit(".", 1)[-1].upper()

        if "." not in file_name:
            extension = "FILE"

        icon = QLabel("📄")
        icon.setStyleSheet("font-size: 28px;")

        details = QVBoxLayout()
        details.setSpacing(4)

        name_label = QLabel(file_name)
        name_label.setObjectName("fileName")
        name_label.setWordWrap(True)

        size_label = QLabel(
            self.format_file_size(file_size)
        )
        size_label.setObjectName("fileSize")

        details.addWidget(name_label)
        details.addWidget(size_label)

        info_layout.addWidget(icon)
        info_layout.addLayout(details, 1)

        bubble_layout.addLayout(info_layout)

        # Tombol download hanya untuk file masuk
        if not outgoing and file_id:

            download_button = QPushButton(
                "⬇  Download"
            )
            download_button.setObjectName(
                "downloadButton"
            )

            download_button.clicked.connect(
                lambda checked=False, fid=file_id:
                    self.file_download_requested.emit(fid)
            )

            bubble_layout.addWidget(download_button)

            status = QLabel("File diterima")

        else:

            status = QLabel("File terkirim")

        status.setObjectName("fileStatus")

        bubble_layout.addWidget(status)

        outer_layout.addWidget(bubble)

        # Penerima di kiri
        if not outgoing:
            outer_layout.addStretch()

        self.message_layout.insertWidget(
            self.message_layout.count() - 1,
            container
        )

        self.scroll_to_bottom()

    # ==================================
    # FILE SIZE FORMAT
    # ==================================

    @staticmethod
    def format_file_size(size):

        if size < 1024:
            return f"{size} B"

        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"

        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"

        return f"{size / (1024 * 1024 * 1024):.1f} GB"

    # ==================================
    # SEND MESSAGE
    # ==================================

    def send_message(self):

        text = self.message_input.text().strip()

        if not text or not self.current_contact:
            return

        self.add_message(
            text,
            outgoing=True
        )

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

    # ==================================
    # VOICE NOTE RECORDING
    # ==================================

    def _on_mic_clicked(self):
        """Handle microphone button click - start recording."""
        if not self.current_contact:
            return
        
        # Hide input, show recorder
        self.message_input.hide()
        self.mic_button.hide()
        self.recorder_widget.show()
        
        # Import and create recorder
        from security.voice_recorder import VoiceRecorder
        recorder = VoiceRecorder(self)
        recorder.set_max_duration(5)  # 5 minutes max
        self.recorder_widget.start_recording(recorder)
        
        # Update mic button state
        self.mic_button.setProperty("recording", True)
        self.mic_button.style().unpolish(self.mic_button)
        self.mic_button.style().polish(self.mic_button)

    def _on_recording_cancelled(self):
        """Handle recording cancelled."""
        self._reset_input_ui()

    def _on_recording_finished(self, path):
        """Handle recording finished and send."""
        self._reset_input_ui()
        self.voice_note_send_requested.emit(path)

    def _reset_input_ui(self):
        """Reset UI to normal input state."""
        self.recorder_widget.hide()
        self.message_input.show()
        self.mic_button.show()
        self.mic_button.setProperty("recording", False)
        self.mic_button.style().unpolish(self.mic_button)
        self.mic_button.style().polish(self.mic_button)

    # ==================================
    # VOICE NOTE DISPLAY
    # ==================================

    def add_voice_note_message(
        self,
        file_id: str,
        file_name: str,
        duration_ms: int,
        outgoing: bool,
        metadata: dict = None
    ):
        """Add a voice note bubble to the chat."""
        container = QWidget()
        outer_layout = QHBoxLayout(container)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # Align based on outgoing/incoming
        if outgoing:
            outer_layout.addStretch()

        bubble = VoiceNoteBubble(file_id, file_name, duration_ms, outgoing)
        
        # Connect signals
        bubble.play_requested.connect(self.voice_note_play_requested.emit)
        bubble.seek_requested.connect(self.voice_note_seek_requested.emit)
        bubble.download_requested.connect(self.voice_note_download_requested.emit)

        outer_layout.addWidget(bubble)

        if not outgoing:
            outer_layout.addStretch()

        self.message_layout.insertWidget(
            self.message_layout.count() - 1,
            container
        )

        self.scroll_to_bottom()
        
        return bubble

    def update_voice_note_bubble(self, file_id: str, decrypted_path: str = None, 
                                  playing: bool = None, position_ms: int = None,
                                  duration_ms: int = None, status: str = None):
        """Update an existing voice note bubble."""
        # Find the bubble widget
        for i in range(self.message_layout.count()):
            widget = self.message_layout.itemAt(i).widget()
            if widget:
                # Check if it's a voice note container
                for child in widget.findChildren(VoiceNoteBubble):
                    if child.file_id == file_id:
                        if decrypted_path:
                            child.set_decrypted_file(decrypted_path)
                        if playing is not None:
                            child.set_playing(playing)
                        if position_ms is not None:
                            child.set_position(position_ms)
                        if duration_ms is not None:
                            child.set_duration(duration_ms)
                        if status is not None:
                            child.set_status(status)
                        return
