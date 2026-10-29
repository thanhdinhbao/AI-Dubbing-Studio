import logging
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QSlider,
    QCheckBox, QGridLayout, QMessageBox
)

from app.models import ProjectData
from app.constants import AudioSeparationMode
from app.ui.widgets.media_player import MediaPlayerWidget

logger = logging.getLogger("AIDubbingStudio.AudioPage")


class AudioPage(QWidget):
    """Tab 4: Audio Separation and Multi-track Audio Mixing."""

    separation_requested = Signal(str)  # separation_mode

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project: Optional[ProjectData] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Left Column: Mixing Controls
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        # 1. Separation Mode Box
        sep_group = QGroupBox("Chế độ Xử lý Âm thanh Nền (Source Separation)")
        sep_layout = QGridLayout(sep_group)
        sep_layout.setSpacing(8)

        sep_layout.addWidget(QLabel("Phương thức giữ nhạc nền:"), 0, 0)
        self.combo_sep_mode = QComboBox()
        self.combo_sep_mode.addItem("Tự động Ducking (Giữ nhạc & giảm nhỏ khi có lời)", AudioSeparationMode.DUCKING_ORIGINAL)
        self.combo_sep_mode.addItem("Tách Vocal AI (Demucs - Yêu cầu cài đặt)", AudioSeparationMode.DEMUCS_SEPARATION)
        self.combo_sep_mode.addItem("Giữ toàn bộ âm thanh gốc ở mức thấp", AudioSeparationMode.KEEP_ORIGINAL_LOW)
        self.combo_sep_mode.addItem("Tắt hoàn toàn âm thanh gốc (Chỉ giữ TTS)", AudioSeparationMode.MUTE_ORIGINAL)
        sep_layout.addWidget(self.combo_sep_mode, 0, 1)

        self.btn_run_sep = QPushButton("🎵 Áp dụng & Chuẩn bị Nhạc nền")
        self.btn_run_sep.setObjectName("PrimaryButton")
        self.btn_run_sep.clicked.connect(self._run_separation)
        sep_layout.addWidget(self.btn_run_sep, 1, 0, 1, 2)

        left_col.addWidget(sep_group)

        # 2. Mixing Parameters Box
        mix_group = QGroupBox("Cân bằng Âm lượng & Ducking")
        mix_layout = QGridLayout(mix_group)
        mix_layout.setSpacing(10)

        # Background Volume
        mix_layout.addWidget(QLabel("Âm lượng Nhạc nền:"), 0, 0)
        self.slider_bg_vol = QSlider(Qt.Horizontal)
        self.slider_bg_vol.setRange(0, 100)
        self.slider_bg_vol.setValue(25)
        self.lbl_bg_vol = QLabel("25%")
        self.slider_bg_vol.valueChanged.connect(lambda v: self.lbl_bg_vol.setText(f"{v}%"))
        mix_layout.addWidget(self.slider_bg_vol, 0, 1)
        mix_layout.addWidget(self.lbl_bg_vol, 0, 2)

        # TTS Volume Gain
        mix_layout.addWidget(QLabel("Âm lượng Lời thoại TTS:"), 1, 0)
        self.slider_tts_vol = QSlider(Qt.Horizontal)
        self.slider_tts_vol.setRange(50, 150)
        self.slider_tts_vol.setValue(100)
        self.lbl_tts_vol = QLabel("100%")
        self.slider_tts_vol.valueChanged.connect(lambda v: self.lbl_tts_vol.setText(f"{v}%"))
        mix_layout.addWidget(self.slider_tts_vol, 1, 1)
        mix_layout.addWidget(self.lbl_tts_vol, 1, 2)

        # Ducking Settings
        self.chk_ducking = QCheckBox("Bật tính năng Auto-Ducking (Tự động hạ nhạc nền khi có lời nói)")
        self.chk_ducking.setChecked(True)
        mix_layout.addWidget(self.chk_ducking, 2, 0, 1, 3)

        left_col.addWidget(mix_group)
        left_col.addStretch()

        layout.addLayout(left_col, stretch=1)

        # Right Column: Audio Preview
        right_col = QVBoxLayout()
        preview_group = QGroupBox("Nghe thử Âm thanh Gốc / Nhạc nền")
        preview_layout = QVBoxLayout(preview_group)
        self.audio_player = MediaPlayerWidget()
        preview_layout.addWidget(self.audio_player)
        right_col.addWidget(preview_group)

        layout.addLayout(right_col, stretch=1)

    def set_project(self, project: ProjectData):
        self.current_project = project
        if project.extracted_audio_path:
            self.audio_player.load_media(project.extracted_audio_path)

    def get_mixing_settings(self) -> dict:
        return {
            "separation_mode": self.combo_sep_mode.currentData(),
            "bg_music_volume": self.slider_bg_vol.value() / 100.0,
            "tts_volume_gain": self.slider_tts_vol.value() / 100.0,
            "enable_ducking": self.chk_ducking.isChecked(),
            "ducking_reduction": 0.20 if self.chk_ducking.isChecked() else 1.0
        }

    def _run_separation(self):
        if not self.current_project or not self.current_project.extracted_audio_path:
            QMessageBox.warning(self, "Thông báo", "Chưa có track âm thanh được trích xuất từ video.")
            return
        mode = self.combo_sep_mode.currentData()
        self.separation_requested.emit(mode)

