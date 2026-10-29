import logging
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QStyle
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from app.utils.timecode import seconds_to_display

logger = logging.getLogger("AIDubbingStudio.MediaPlayer")


class MediaPlayerWidget(QWidget):
    """Media preview player supporting video/audio playback and seeking."""

    position_changed = Signal(float)  # current time in seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self.media_path: Optional[str] = None
        self.duration_seconds = 0.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Video viewport
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(240)
        self.video_widget.setStyleSheet("background-color: #0f1017; border-radius: 8px;")
        layout.addWidget(self.video_widget, stretch=1)

        # Controls container
        controls = QHBoxLayout()
        controls.setContentsMargins(4, 0, 4, 0)

        self.play_btn = QPushButton("▶ Phát")
        self.play_btn.setFixedWidth(80)
        self.play_btn.clicked.connect(self.toggle_play)
        controls.addWidget(self.play_btn)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setFixedWidth(110)
        controls.addWidget(self.time_label)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderMoved.connect(self._on_slider_moved)
        controls.addWidget(self.slider)

        layout.addLayout(controls)

        # Multimedia Player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)

    def load_media(self, file_path: str | Path):
        """Load video or audio file into player."""
        self.media_path = str(file_path)
        url = QUrl.fromLocalFile(self.media_path)
        self.player.setSource(url)
        self.play_btn.setEnabled(True)
        self.play_btn.setText("▶ Phát")
        logger.info(f"Loaded media in player: {file_path}")

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def play(self):
        self.player.play()

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

    def seek_seconds(self, seconds: float):
        """Seek to target seconds position."""
        if self.duration_seconds > 0:
            target_ms = int(seconds * 1000)
            self.player.setPosition(target_ms)

    def _on_position_changed(self, pos_ms: int):
        pos_sec = pos_ms / 1000.0
        self.position_changed.emit(pos_sec)
        cur_str = seconds_to_display(pos_sec)
        dur_str = seconds_to_display(self.duration_seconds)
        self.time_label.setText(f"{cur_str} / {dur_str}")

        if self.duration_seconds > 0 and not self.slider.isSliderDown():
            val = int((pos_sec / self.duration_seconds) * 1000)
            self.slider.setValue(val)

    def _on_duration_changed(self, dur_ms: int):
        self.duration_seconds = dur_ms / 1000.0
        cur_str = seconds_to_display(self.player.position() / 1000.0)
        dur_str = seconds_to_display(self.duration_seconds)
        self.time_label.setText(f"{cur_str} / {dur_str}")

    def _on_slider_moved(self, val: int):
        if self.duration_seconds > 0:
            target_sec = (val / 1000.0) * self.duration_seconds
            self.player.setPosition(int(target_sec * 1000))

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setText("⏸ Tạm dừng")
        else:
            self.play_btn.setText("▶ Phát")

