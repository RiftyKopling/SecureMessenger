"""
Voice Note Bubble Widget for Secure Messenger.

Displays a voice note with play/pause, progress bar, and duration.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
    QLabel, QSlider, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer


class VoiceNoteBubble(QWidget):
    """
    Widget for displaying a voice note in chat.
    
    Features:
    - Play/Pause button
    - Progress slider with seeking support
    - Current time / total duration
    - Waveform visualization (optional)
    - Download button for incoming (if not decrypted yet)
    """
    
    # Signals
    play_requested = Signal(str)            # file_id - request to play/pause
    seek_requested = Signal(str, int)       # file_id, position_ms - seek to position
    download_requested = Signal(str)        # file_id - request to download file

    def __init__(self, file_id: str, file_name: str, duration_ms: int, 
                 outgoing: bool, parent=None):
        super().__init__(parent)
        
        self.file_id = file_id
        self.file_name = file_name
        self.duration_ms = duration_ms
        self.outgoing = outgoing
        self._is_playing = False
        self._is_seeking = False
        self._position_ms = 0
        self._decrypted_file_path = None
        
        self.init_ui()
        self.setup_styles()
    
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Align bubble based on outgoing/incoming
        if self.outgoing:
            main_layout.addStretch()
        
        # Bubble container
        self.bubble = QFrame()
        self.bubble.setObjectName("voiceNoteBubble")
        self.bubble.setMaximumWidth(340)
        self.bubble.setMinimumWidth(260)
        
        bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout.setContentsMargins(14, 12, 14, 12)
        bubble_layout.setSpacing(8)
        
        # Top row: Play button + progress + duration
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        
        # Play/Pause button
        self.play_button = QPushButton("▶")
        self.play_button.setObjectName("voicePlayButton")
        self.play_button.setFixedSize(38, 38)
        self.play_button.clicked.connect(self._on_play_clicked)
        top_row.addWidget(self.play_button)
        
        # Progress slider
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setObjectName("voiceProgressSlider")
        self.progress_slider.setRange(0, max(1, self.duration_ms))
        self.progress_slider.setValue(0)
        self.progress_slider.setFixedHeight(20)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        top_row.addWidget(self.progress_slider, 1)
        
        # Duration layout (current / total)
        time_layout = QHBoxLayout()
        time_layout.setSpacing(2)
        
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setObjectName("voiceTimeLabel")
        self.current_time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        time_layout.addWidget(self.current_time_label)
        
        self.time_divider = QLabel("/")
        self.time_divider.setObjectName("voiceTimeDivider")
        self.time_divider.setAlignment(Qt.AlignCenter)
        time_layout.addWidget(self.time_divider)
        
        self.total_time_label = QLabel(self._format_time(self.duration_ms))
        self.total_time_label.setObjectName("voiceTimeLabel")
        self.total_time_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        time_layout.addWidget(self.total_time_label)
        
        top_row.addLayout(time_layout)
        bubble_layout.addLayout(top_row)
        
        # Status label (for incoming: "Tap to play" / "Playing..." / "Sent")
        self.status_label = QLabel("Sent" if self.outgoing else "Tap to play")
        self.status_label.setObjectName("voiceStatusLabel")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        bubble_layout.addWidget(self.status_label)
        
        # Download button for incoming (only if not yet decrypted/available)
        if not self.outgoing:
            self.download_button = QPushButton("⬇  Download")
            self.download_button.setObjectName("voiceDownloadButton")
            self.download_button.setFixedHeight(30)
            self.download_button.clicked.connect(
                lambda: self.download_requested.emit(self.file_id)
            )
            self.download_button.hide()  # Show only when needed
            bubble_layout.addWidget(self.download_button)
        
        main_layout.addWidget(self.bubble)
        
        if not self.outgoing:
            main_layout.addStretch()
    
    def setup_styles(self):
        """Apply styling based on outgoing/incoming."""
        if self.outgoing:
            bubble_bg = "#1d4ed8"
            text_color = "white"
            time_color = "rgba(255,255,255,0.8)"
            status_color = "rgba(255,255,255,0.7)"
            play_bg = "rgba(255,255,255,0.2)"
            play_hover = "rgba(255,255,255,0.3)"
            play_pressed = "rgba(255,255,255,0.4)"
            slider_handle = "#60a5fa"
            slider_groove = "rgba(255,255,255,0.3)"
            download_bg = "rgba(255,255,255,0.15)"
            download_hover = "rgba(255,255,255,0.25)"
        else:
            bubble_bg = "#1a2940"
            text_color = "#f1f5f9"
            time_color = "#94a3b8"
            status_color = "#64748b"
            play_bg = "#2563eb"
            play_hover = "#3b82f6"
            play_pressed = "#1d4ed8"
            slider_handle = "#60a5fa"
            slider_groove = "#293a56"
            download_bg = "#1e293b"
            download_hover = "#334155"
        
        self.setStyleSheet(f"""
            QFrame#voiceNoteBubble {{
                background-color: {bubble_bg};
                border: 1px solid {slider_groove};
                border-radius: 16px;
            }}
            
            QPushButton#voicePlayButton {{
                background-color: {play_bg};
                color: {text_color};
                border: none;
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton#voicePlayButton:hover {{
                background-color: {play_hover};
            }}
            QPushButton#voicePlayButton:pressed {{
                background-color: {play_pressed};
            }}
            
            QSlider#voiceProgressSlider::groove:horizontal {{
                background: {slider_groove};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider#voiceProgressSlider::handle:horizontal {{
                background: {slider_handle};
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider#voiceProgressSlider::sub-page:horizontal {{
                background: {slider_handle};
                border-radius: 2px;
            }}
            
            QLabel#voiceTimeLabel {
                color: {time_color};
                font-size: 11px;
                font-family: "Consolas", monospace;
            }
            QLabel#voiceTimeDivider {
                color: {time_color};
                font-size: 11px;
                font-family: "Consolas", monospace;
            }
            
            QLabel#voiceStatusLabel {
                color: {status_color};
                font-size: 11px;
            }
            
            QPushButton#voiceDownloadButton {
                background-color: {download_bg};
                color: {text_color};
                border: 1px solid {slider_groove};
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#voiceDownloadButton:hover {
                background-color: {download_hover};
            }
        """)
    
    def _format_time(self, ms: int) -> str:
        """Format milliseconds as M:SS or MM:SS."""
        seconds = max(0, ms // 1000)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def _on_play_clicked(self):
        """Handle play/pause button click."""
        if not self._decrypted_file_path and not self.outgoing and not self._is_playing:
            self.status_label.setText("Decrypting...")
        self.play_requested.emit(self.file_id)
    
    def set_decrypted_file(self, file_path: str):
        """Set the decrypted file path for playback."""
        self._decrypted_file_path = file_path
        if not self._is_playing:
            self.status_label.setText("Sent" if self.outgoing else "Ready to play")
    
    def set_playing(self, playing: bool):
        """Update play/pause button state."""
        self._is_playing = playing
        self.play_button.setText("⏸" if playing else "▶")
        if playing:
            self.status_label.setText("Playing...")
        else:
            if self.outgoing:
                self.status_label.setText("Sent")
            else:
                self.status_label.setText("Ready to play" if self._decrypted_file_path else "Tap to play")
    
    def set_position(self, position_ms: int):
        """Update playback position."""
        self._position_ms = position_ms
        if not self._is_seeking:
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(position_ms)
            self.progress_slider.blockSignals(False)
            self.current_time_label.setText(self._format_time(position_ms))
    
    def set_duration(self, duration_ms: int):
        """Update total duration."""
        self.duration_ms = duration_ms
        self.progress_slider.setRange(0, max(1, duration_ms))
        self.total_time_label.setText(self._format_time(duration_ms))
    
    def _on_slider_pressed(self):
        """User started dragging slider."""
        self._is_seeking = True
    
    def _on_slider_released(self):
        """User released slider - seek to position."""
        self._is_seeking = False
        position = self.progress_slider.value()
        self.seek_requested.emit(self.file_id, position)
    
    def _on_slider_moved(self, position):
        """Slider moved - update time label."""
        self.current_time_label.setText(self._format_time(position))
    
    def show_download_button(self, show: bool):
        """Show/hide download button for incoming messages."""
        if not self.outgoing:
            self.download_button.setVisible(show)
    
    def set_status(self, text: str):
        """Set status label text."""
        self.status_label.setText(text)


class VoiceNoteRecorderWidget(QWidget):
    """
    Widget for recording voice notes.
    
    Shows recording indicator, duration, and cancel/send buttons.
    """
    
    recording_finished = Signal(str)  # file_path
    recording_cancelled = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._recorder = None
        self._temp_file = None
        self.init_ui()
    
    def init_ui(self):
        self.setObjectName("voiceRecorderWidget")
        self.setFixedHeight(120)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        # Recording indicator
        indicator_layout = QHBoxLayout()
        indicator_layout.setSpacing(12)
        
        # Animated recording dot
        self.recording_dot = QLabel("●")
        self.recording_dot.setObjectName("recordingDot")
        self.recording_dot.setFixedSize(24, 24)
        indicator_layout.addWidget(self.recording_dot)
        
        # Status text
        self.status_label = QLabel("Recording...")
        self.status_label.setObjectName("recordingStatus")
        indicator_layout.addWidget(self.status_label)
        
        indicator_layout.addStretch()
        
        # Duration
        self.duration_label = QLabel("00:00")
        self.duration_label.setObjectName("recordingDuration")
        self.duration_label.setFixedWidth(60)
        indicator_layout.addWidget(self.duration_label)
        
        layout.addLayout(indicator_layout)
        
        # Waveform placeholder (visual feedback)
        self.waveform_label = QLabel()
        self.waveform_label.setObjectName("recordingWaveform")
        self.waveform_label.setFixedHeight(30)
        self.waveform_label.setStyleSheet("""
            QLabel#recordingWaveform {
                background-color: #0b1528;
                border: 1px solid #293a56;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.waveform_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("recorderCancelButton")
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("recorderStopButton")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setFixedWidth(100)
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(True)
        btn_layout.addWidget(self.stop_btn)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("recorderSendButton")
        self.send_btn.setFixedHeight(36)
        self.send_btn.setFixedWidth(100)
        self.send_btn.clicked.connect(self._on_send)
        self.send_btn.setEnabled(False)  # Enable after recording stops
        self.send_btn.hide()  # Hidden until recording stops
        btn_layout.addWidget(self.send_btn)
        
        layout.addLayout(btn_layout)
        
        # Animation timer for recording dot
        self._blink_timer = QTimer()
        self._blink_timer.setInterval(500)
        self._blink_timer.timeout.connect(self._blink_dot)
        self._dot_visible = True
        
        self.setStyleSheet("""
            QWidget#voiceRecorderWidget {
                background-color: #1a1f2e;
                border: 2px solid #ef4444;
                border-radius: 12px;
            }
            QLabel#recordingDot {
                color: #ef4444;
                font-size: 20px;
                font-weight: bold;
            }
            QLabel#recordingStatus {
                color: #f1f5f9;
                font-size: 14px;
                font-weight: bold;
            }
            QLabel#recordingDuration {
                color: #ef4444;
                font-size: 16px;
                font-weight: bold;
                font-family: "Consolas", "Monospace";
            }
            QPushButton#recorderCancelButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#recorderCancelButton:hover {
                background-color: #334155;
            }
            QPushButton#recorderStopButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#recorderStopButton:hover {
                background-color: #f87171;
            }
            QPushButton#recorderSendButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#recorderSendButton:hover {
                background-color: #34d399;
            }
            QPushButton#recorderSendButton:disabled {
                background-color: #334155;
                color: #64748b;
            }
        """)
    
    def start_recording(self, recorder):
        """Start recording with given VoiceRecorder instance."""
        self._recorder = recorder
        try:
            self._recorder.duration_updated.connect(self._on_duration_update)
            self._recorder.recording_stopped.connect(self._on_recording_stopped)
            self._recorder.error_occurred.connect(self._on_error)
        except Exception:
            pass
        
        # Reset UI state
        self._dot_visible = True
        self.recording_dot.setText("●")
        self.recording_dot.setStyleSheet("color: #ef4444; font-size: 20px; font-weight: bold;")
        self.duration_label.setText("00:00")
        self.status_label.setText("Recording...")
        self.stop_btn.show()
        self.send_btn.hide()
        self.send_btn.setEnabled(False)
        self._temp_file = None
        
        if self._recorder.start_recording():
            self._blink_timer.start()
        else:
            self._on_error("Failed to start recording")
    
    def stop_recording(self):
        """Stop recording."""
        if self._recorder:
            self._recorder.stop_recording()
    
    def cancel_recording(self):
        """Cancel recording."""
        if self._recorder:
            self._recorder.cancel_recording()
        self._cleanup()
        self.recording_cancelled.emit()
    
    def _on_duration_update(self, ms: int):
        """Update duration display."""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        self.duration_label.setText(f"{minutes:02d}:{seconds:02d}")
    
    def _on_recording_stopped(self, file_path: str):
        """Recording finished."""
        self._blink_timer.stop()
        self.recording_dot.setText("✓")
        self.recording_dot.setStyleSheet("color: #10b981; font-size: 20px; font-weight: bold;")
        self.status_label.setText("Recording complete - ready to send")
        self._temp_file = file_path
        # Swap Stop button for Send button
        self.stop_btn.hide()
        self.send_btn.show()
        self.send_btn.setEnabled(True)
    
    def _on_stop(self):
        """Stop button clicked - stop recording."""
        self.stop_recording()
    
    def _on_error(self, error_msg: str):
        """Handle recording error."""
        self._blink_timer.stop()
        self.recording_dot.setText("✗")
        self.recording_dot.setStyleSheet("color: #ef4444; font-size: 20px; font-weight: bold;")
        self.status_label.setText(f"Error: {error_msg}")
        self.send_btn.setEnabled(False)
    
    def _blink_dot(self):
        """Blink recording indicator."""
        self._dot_visible = not self._dot_visible
        self.recording_dot.setVisible(self._dot_visible)
    
    def _on_cancel(self):
        """Cancel button clicked."""
        self.cancel_recording()
    
    def _on_send(self):
        """Send button clicked."""
        if self._temp_file:
            self.recording_finished.emit(self._temp_file)
            self._cleanup()
    
    def _cleanup(self):
        """Clean up recorder."""
        if self._recorder:
            try:
                self._recorder.duration_updated.disconnect(self._on_duration_update)
            except (RuntimeError, TypeError):
                pass
            try:
                self._recorder.recording_stopped.disconnect(self._on_recording_stopped)
            except (RuntimeError, TypeError):
                pass
            try:
                self._recorder.error_occurred.disconnect(self._on_error)
            except (RuntimeError, TypeError):
                pass
            self._recorder = None
        self._blink_timer.stop()
        # Reset buttons and state
        self.stop_btn.show()
        self.send_btn.hide()
        self.send_btn.setEnabled(False)
        self._temp_file = None
        self._dot_visible = True
        self.recording_dot.setText("●")
        self.recording_dot.setStyleSheet("color: #ef4444; font-size: 20px; font-weight: bold;")
        self.duration_label.setText("00:00")
        self.status_label.setText("Ready")