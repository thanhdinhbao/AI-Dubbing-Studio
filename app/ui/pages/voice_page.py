import logging
from typing import Optional, Dict, Any
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QLineEdit,
    QMessageBox, QGridLayout
)

from app.models import ProjectData
from app.constants import EDGE_TTS_VIETNAMESE_VOICES, VIENEU_VIETNAMESE_VOICES, TTS_BACKENDS
from app.ui.widgets.media_player import MediaPlayerWidget

logger = logging.getLogger("AIDubbingStudio.VoicePage")


class VoicePage(QWidget):
    """Tab 3: AI Voice Configuration and Vietnamese Speech Synthesis."""

    tts_generation_requested = Signal(str, str, dict)  # backend, voice_id, options
    test_voice_requested = Signal(str, str, dict)  # backend, voice_id, options

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project: Optional[ProjectData] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Left Column: Configuration Controls
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        # 1. Provider Box
        prov_group = QGroupBox("Cấu hình Động cơ AI Voice")
        prov_layout = QGridLayout(prov_group)
        prov_layout.setSpacing(8)

        prov_layout.addWidget(QLabel("Nhà cung cấp (Provider):"), 0, 0)
        self.combo_backend = QComboBox()
        self.combo_backend.addItem("Microsoft Edge TTS (Tự nhiên, Khuyến nghị)", "edge_tts")
        self.combo_backend.addItem("VieNeu-TTS SDK v3 Turbo (Offline / On-Device AI Voice)", "vieneu")
        self.combo_backend.addItem("VieNeu-TTS SDK v3 Nano (24kHz Siêu nhẹ cho CPU yếu)", "vieneu_nano")
        self.combo_backend.addItem("OpenAI-Compatible Speech API", "openai_compatible")
        self.combo_backend.addItem("Offline TTS Engine (Piper/Local)", "offline_engine")
        self.combo_backend.currentIndexChanged.connect(self._on_backend_changed)
        prov_layout.addWidget(self.combo_backend, 0, 1)

        prov_layout.addWidget(QLabel("Giọng đọc Tiếng Việt:"), 1, 0)
        self.combo_voice = QComboBox()
        self._populate_voices("edge_tts")
        prov_layout.addWidget(self.combo_voice, 1, 1)

        self.btn_open_cloning = QPushButton("✨ Nhân bản Giọng mới (Voice Cloning)...")
        self.btn_open_cloning.setStyleSheet(
            "background-color: #bb9af7; color: #1a1b26; font-weight: bold; padding: 6px;"
        )
        self.btn_open_cloning.setToolTip("Ghi âm trực tiếp từ Mic hoặc import file 3-8s để tạo giọng clone")
        self.btn_open_cloning.clicked.connect(self._open_voice_cloning_dialog)
        prov_layout.addWidget(self.btn_open_cloning, 2, 0, 1, 2)

        left_col.addWidget(prov_group)

        # 2. Voice Parameters Box
        param_group = QGroupBox("Tinh chỉnh Giọng đọc")
        param_layout = QGridLayout(param_group)
        param_layout.setSpacing(8)

        param_layout.addWidget(QLabel("Tốc độ đọc (Speed):"), 0, 0)
        self.combo_rate = QComboBox()
        self.combo_rate.addItems(["-20% (Chậm)", "-10%", "+0% (Mặc định)", "+10%", "+20% (Nhanh)"])
        self.combo_rate.setCurrentText("+0% (Mặc định)")
        param_layout.addWidget(self.combo_rate, 0, 1)

        param_layout.addWidget(QLabel("Cao độ (Pitch):"), 1, 0)
        self.combo_pitch = QComboBox()
        self.combo_pitch.addItems(["-10Hz (Trầm)", "+0Hz (Mặc định)", "+10Hz (Cao)"])
        self.combo_pitch.setCurrentText("+0Hz (Mặc định)")
        param_layout.addWidget(self.combo_pitch, 1, 1)

        param_layout.addWidget(QLabel("Âm lượng (Volume):"), 2, 0)
        self.combo_vol = QComboBox()
        self.combo_vol.addItems(["+0% (Mặc định)", "+10%", "+20%"])
        self.combo_vol.setCurrentText("+0% (Mặc định)")
        param_layout.addWidget(self.combo_vol, 2, 1)

        param_layout.addWidget(QLabel("Phong cách lồng tiếng:"), 3, 0)
        self.combo_style = QComboBox()
        self.combo_style.addItems(["Tự nhiên (Natural)", "Thuyết minh phim", "Kể chuyện (Storytelling)", "Tin tức (News)"])
        param_layout.addWidget(self.combo_style, 3, 1)

        param_layout.addWidget(QLabel("Số luồng song song:"), 4, 0)
        self.combo_threads = QComboBox()
        self.combo_threads.addItem("1 luồng (Tuần tự)", 1)
        self.combo_threads.addItem("3 luồng", 3)
        self.combo_threads.addItem("5 luồng song song (Khuyến nghị)", 5)
        self.combo_threads.addItem("8 luồng song song (Tốc độ cao)", 8)
        self.combo_threads.addItem("10 luồng song song", 10)
        self.combo_threads.setCurrentIndex(2)  # default 5
        param_layout.addWidget(self.combo_threads, 4, 1)

        left_col.addWidget(param_group)

        # Actions Box
        action_layout = QHBoxLayout()
        self.btn_test_voice = QPushButton("🔊 Nghe thử giọng mẫu")
        self.btn_test_voice.clicked.connect(self._test_voice)
        action_layout.addWidget(self.btn_test_voice)

        self.btn_generate_all = QPushButton("⚡ Tạo Giọng đọc cho Toàn bộ Video")
        self.btn_generate_all.setObjectName("PrimaryButton")
        self.btn_generate_all.clicked.connect(self._generate_all_tts)
        action_layout.addWidget(self.btn_generate_all)

        left_col.addLayout(action_layout)
        left_col.addStretch()

        layout.addLayout(left_col, stretch=1)

        # Right Column: Audio Sample Player
        right_col = QVBoxLayout()
        sample_group = QGroupBox("Nghe thử Giọng đọc TTS")
        sample_layout = QVBoxLayout(sample_group)
        self.sample_player = MediaPlayerWidget()
        sample_layout.addWidget(self.sample_player)
        right_col.addWidget(sample_group)

        layout.addLayout(right_col, stretch=1)

    def set_project(self, project: ProjectData):
        self.current_project = project

    def _on_backend_changed(self):
        backend = self.combo_backend.currentData()
        self._populate_voices(backend)

    def _populate_voices(self, backend: str, select_voice: Optional[str] = None):
        self.combo_voice.clear()
        if backend == "edge_tts":
            for v in EDGE_TTS_VIETNAMESE_VOICES:
                self.combo_voice.addItem(f"{v['name']}", v["id"])
        elif backend in ("vieneu", "vieneu_nano"):
            from app.providers.vieneu_tts_provider import VieNeuTTSProvider
            provider = VieNeuTTSProvider()
            for v in provider.get_voices():
                self.combo_voice.addItem(f"{v['name']}", v["id"])
        elif backend == "openai_compatible":
            voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
            for v in voices:
                self.combo_voice.addItem(f"OpenAI {v.capitalize()}", v)
        else:
            self.combo_voice.addItem("Piper Vietnamese (Local Model)", "piper_vi")

        if select_voice:
            idx = self.combo_voice.findData(select_voice)
            if idx >= 0:
                self.combo_voice.setCurrentIndex(idx)

    def _open_voice_cloning_dialog(self):
        from app.ui.dialogs import VoiceCloneDialog
        dlg = VoiceCloneDialog(self)
        dlg.voice_cloned.connect(self._on_voice_cloned)
        dlg.exec()

    def _on_voice_cloned(self, new_voice_name: str):
        # Automatically switch backend to vieneu and select the new cloned voice
        idx = self.combo_backend.findData("vieneu")
        if idx >= 0:
            self.combo_backend.setCurrentIndex(idx)
        self._populate_voices("vieneu", select_voice=new_voice_name)

    def _get_options(self) -> dict:
        rate_str = self.combo_rate.currentText().split()[0]
        pitch_str = self.combo_pitch.currentText().split()[0]
        vol_str = self.combo_vol.currentText().split()[0]
        max_workers = self.combo_threads.currentData() or 5
        return {
            "rate": rate_str,
            "pitch": pitch_str,
            "volume": vol_str,
            "style": self.combo_style.currentText(),
            "max_workers": max_workers
        }

    def _test_voice(self):
        backend = self.combo_backend.currentData()
        voice_id = self.combo_voice.currentData()
        options = self._get_options()
        self.test_voice_requested.emit(backend, voice_id, options)

    def _generate_all_tts(self):
        if not self.current_project or not self.current_project.dialogues:
            QMessageBox.warning(self, "Thông báo", "Chưa có lời thoại dịch. Vui lòng nhận diện và dịch thuật trước.")
            return

        backend = self.combo_backend.currentData()
        voice_id = self.combo_voice.currentData()
        options = self._get_options()
        self.tts_generation_requested.emit(backend, voice_id, options)

