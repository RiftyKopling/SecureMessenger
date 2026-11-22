"""
Voice Recorder Module for Secure Messenger.

Handles audio recording using Qt Multimedia.
Provides recording, playback preview, and audio data management.
"""

import tempfile
import os
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer, QUrl, QBuffer, QIODevice
from PySide6.QtMultimedia import (
    QMediaRecorder,
    QAudioInput,
    QMediaFormat,
    QMediaCaptureSession,
)
from PySide6.QtMultimediaWidgets import QVideoWidget


class VoiceRecorder(QObject):
    """
    Records audio from microphone using Qt Multimedia.
    
    Emits signals for:
    - recording_started: when recording begins
    - recording_stopped: when recording ends (with file path)
    - duration_updated: real-time duration during recording (ms)
    - error_occurred: when an error happens
    """

    recording_started = Signal()
    recording_stopped = Signal(str)  # file path
    duration_updated = Signal(int)   # milliseconds
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._capture_session = QMediaCaptureSession()
        self._audio_input = QAudioInput()
        self._recorder = QMediaRecorder()
        self._capture_session.setAudioInput(self._audio_input)
        self._capture_session.setRecorder(self._recorder)
        
        self._output_file = None
        self._is_recording = False
        self._duration_timer = QTimer()
        self._duration_timer.setInterval(100)  # Update every 100ms
        self._duration_timer.timeout.connect(self._update_duration)
        self._elapsed_ms = 0
        self._max_duration_ms = 5 * 60 * 1000  # 5 minutes max

    def start_recording(self):
        """Start recording audio from microphone."""
        if self._is_recording:
            self.error_occurred.emit("Recording already in progress")
            return False

        # Create temporary file for recording
        try:
            temp_dir = Path(tempfile.gettempdir())
            temp_dir.mkdir(parents=True, exist_ok=True)
            self._output_file = temp_dir / f"voice_note_{os.getpid()}_{id(self)}.wav"
        except Exception as e:
            self.error_occurred.emit(f"Failed to create temp file: {e}")
            return False

        # Configure recorder for WAV format
        media_format = QMediaFormat()
        media_format.setFileFormat(QMediaFormat.FileFormat.Wave)
        self._recorder.setMediaFormat(media_format)
        
        # Set output location
        self._recorder.setOutputLocation(QUrl.fromLocalFile(str(self._output_file)))
        
        # Set quality/encoding
        self._recorder.setQuality(QMediaRecorder.Quality.HighQuality)

        # Start recording
        self._recorder.record()
        
        # Give it a moment to start and check for errors
        from PySide6.QtCore import QTimer
        def check_recorder_error():
            if self._recorder.error() != QMediaRecorder.Error.NoError:
                error_msg = self._recorder.errorString()
                self._is_recording = False
                self.error_occurred.emit(f"Recording failed: {error_msg}")
            else:
                self._is_recording = True
                self._elapsed_ms = 0
                self._duration_timer.start()
                self.recording_started.emit()
        
        QTimer.singleShot(100, check_recorder_error)
        return True

    def stop_recording(self):
        """Stop recording and return the file path."""
        if not self._is_recording:
            return None

        self._recorder.stop()
        self._duration_timer.stop()
        self._is_recording = False
        
        # Wait a bit for file to be written
        QTimer.singleShot(100, self._finalize_recording)
        
    def _finalize_recording(self):
        """Finalize recording after stop."""
        if self._output_file and self._output_file.exists():
            file_size = self._output_file.stat().st_size
            if file_size > 0:
                self.recording_stopped.emit(str(self._output_file))
            else:
                self.error_occurred.emit("Recording produced empty file")
                self._cleanup_temp_file()
        else:
            self.error_occurred.emit("Recording file not found")

    def _update_duration(self):
        """Update elapsed duration during recording."""
        self._elapsed_ms += 100
        self.duration_updated.emit(self._elapsed_ms)
        
        # Auto-stop at max duration
        if self._elapsed_ms >= self._max_duration_ms:
            self.stop_recording()

    def _cleanup_temp_file(self):
        """Clean up temporary recording file."""
        if self._output_file and self._output_file.exists():
            try:
                self._output_file.unlink()
            except Exception:
                pass
        self._output_file = None

    def cancel_recording(self):
        """Cancel recording without saving."""
        if self._is_recording:
            self._recorder.stop()
            self._duration_timer.stop()
            self._is_recording = False
        self._cleanup_temp_file()

    def get_duration_formatted(self, ms=None):
        """Format duration as MM:SS string."""
        if ms is None:
            ms = self._elapsed_ms
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def is_recording(self):
        return self._is_recording

    def get_temp_file_path(self):
        return str(self._output_file) if self._output_file else None

    def set_max_duration(self, minutes: int):
        """Set maximum recording duration in minutes."""
        self._max_duration_ms = minutes * 60 * 1000


class VoicePlayer(QObject):
    """
    Plays voice note audio files.
    
    Uses QMediaPlayer for playback with progress tracking.
    """
    
    playback_started = Signal()
    playback_stopped = Signal()
    playback_paused = Signal()
    playback_finished = Signal()
    position_changed = Signal(int)  # milliseconds
    duration_changed = Signal(int)  # milliseconds
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
        
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.errorOccurred.connect(self._on_error)
        
        self._current_file = None
        self._is_playing = False

    def load_file(self, file_path: str):
        """Load audio file for playback."""
        self._current_file = file_path
        self._player.setSource(QUrl.fromLocalFile(file_path))

    def play(self):
        """Start or resume playback."""
        if not self._current_file:
            self.error_occurred.emit("No file loaded")
            return
        self._player.play()

    def pause(self):
        """Pause playback."""
        self._player.pause()

    def stop(self):
        """Stop playback and reset position."""
        self._player.stop()

    def set_position(self, ms: int):
        """Seek to position in milliseconds."""
        self._player.setPosition(ms)

    def get_position(self):
        return self._player.position()

    def get_duration(self):
        return self._player.duration()

    def is_playing(self):
        return self._is_playing

    def _on_position_changed(self, position):
        self.position_changed.emit(position)

    def _on_duration_changed(self, duration):
        self.duration_changed.emit(duration)

    def _on_state_changed(self, state):
        from PySide6.QtMultimedia import QMediaPlayer
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._is_playing = True
            self.playback_started.emit()
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._is_playing = False
            self.playback_paused.emit()
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self._is_playing = False
            self.playback_stopped.emit()
            # Check if finished naturally
            if self._player.position() >= self._player.duration() - 100:
                self.playback_finished.emit()

    def _on_error(self, error, error_string):
        self.error_occurred.emit(f"Playback error: {error_string}")

    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)."""
        self._audio_output.setVolume(volume)