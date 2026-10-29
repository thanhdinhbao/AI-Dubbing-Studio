import logging
from typing import List, Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QMessageBox
)

from app.models import DialogueSegment, ProjectData
from app.ui.widgets.subtitle_editor import SubtitleEditorWidget
from app.constants import WHISPER_MODELS

logger = logging.getLogger("AIDubbingStudio.TranscriptionPage")


class TranscriptionPage(QWidget):
    """Tab 2: Speech-to-Text Transcription & Vietnamese Translation Subtitle Editor."""

    transcription_requested = Signal(str, str, int)  # model_size, device, beam_size
    translation_requested = Signal(str, dict)  # backend, options
    translate_single_requested = Signal(int, str, dict)  # row_idx, backend, options
    config_requested = Signal()  # request opening settings dialog

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project: Optional[ProjectData] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Control Panel Box
        controls_group = QGroupBox("Điều khiển Nhận diện & Dịch thuật Tiếng Việt")
        ctrl_grid = QGridLayout(controls_group)
        ctrl_grid.setSpacing(10)
        ctrl_grid.setContentsMargins(12, 12, 12, 12)

        # --- Row 0: ASR Speech-to-Text ---
        lbl_asr_header = QLabel("<b>🎙 Nhận diện giọng nói (ASR):</b>")
        ctrl_grid.addWidget(lbl_asr_header, 0, 0)

        asr_box = QHBoxLayout()
        asr_box.setSpacing(8)
        asr_box.addWidget(QLabel("Mô hình:"))
        self.combo_model = QComboBox()
        self.combo_model.addItems(WHISPER_MODELS)
        self.combo_model.setCurrentText("base")
        asr_box.addWidget(self.combo_model)

        asr_box.addWidget(QLabel("Thiết bị:"))
        self.combo_device = QComboBox()
        self.combo_device.addItems(["cpu", "cuda"])
        asr_box.addWidget(self.combo_device)

        asr_box.addWidget(QLabel("Tốc độ:"))
        self.combo_speed_mode = QComboBox()
        self.combo_speed_mode.addItem("⚡ Siêu tốc (Greedy beam=1, Nhanh 3-5x)", 1)
        self.combo_speed_mode.addItem("🎯 Tiêu chuẩn (Beam=5, Chuẩn xác)", 5)
        self.combo_speed_mode.setCurrentIndex(0)
        asr_box.addWidget(self.combo_speed_mode)

        self.btn_transcribe = QPushButton("🎙 Bắt đầu Nhận diện ASR")
        self.btn_transcribe.setObjectName("PrimaryButton")
        self.btn_transcribe.clicked.connect(self._on_transcribe_clicked)
        asr_box.addWidget(self.btn_transcribe)
        asr_box.addStretch()

        ctrl_grid.addLayout(asr_box, 0, 1)

        # --- Row 1: Translation Controls ---
        lbl_trans_header = QLabel("<b>🌐 Dịch sang Tiếng Việt:</b>")
        ctrl_grid.addWidget(lbl_trans_header, 1, 0)

        trans_box = QHBoxLayout()
        trans_box.setSpacing(8)

        trans_box.addWidget(QLabel("Bộ máy dịch:"))
        self.combo_trans_engine = QComboBox()
        self.combo_trans_engine.addItem("Google Translate (Miễn phí / Không cần Key)", "google_free")
        self.combo_trans_engine.addItem("Cloud API (OpenAI / DeepSeek / Gemini)", "openai_compatible")
        self.combo_trans_engine.addItem("Local Offline LLM (Ollama / LM Studio)", "local_llm")
        trans_box.addWidget(self.combo_trans_engine)

        self.btn_config_trans = QPushButton("⚙ Cấu hình API")
        self.btn_config_trans.setToolTip("Cấu hình API Key, Base URL hoặc Mô hình Ollama")
        self.btn_config_trans.clicked.connect(self.config_requested.emit)
        trans_box.addWidget(self.btn_config_trans)

        self.btn_translate_selected = QPushButton("📝 Dịch câu đang chọn")
        self.btn_translate_selected.setToolTip("Dịch lại duy nhất câu thoại đang được bôi chọn trên bảng")
        self.btn_translate_selected.clicked.connect(self._on_translate_selected_clicked)
        trans_box.addWidget(self.btn_translate_selected)

        self.btn_translate = QPushButton("🌐 Dịch toàn bộ sang Tiếng Việt")
        self.btn_translate.setStyleSheet("background-color: #9ece6a; color: #15161e; font-weight: bold;")
        self.btn_translate.clicked.connect(self._on_translate_clicked)
        trans_box.addWidget(self.btn_translate)
        trans_box.addStretch()

        ctrl_grid.addLayout(trans_box, 1, 1)

        layout.addWidget(controls_group)

        # Subtitle Editor Table
        self.subtitle_editor = SubtitleEditorWidget()
        layout.addWidget(self.subtitle_editor, stretch=1)

    def set_project(self, project: ProjectData):
        self.current_project = project
        self.subtitle_editor.load_dialogues(project.dialogues)

    def get_dialogues(self) -> List[DialogueSegment]:
        return self.subtitle_editor.get_dialogues()

    def update_dialogue_target_at(self, index: int, text: str):
        self.subtitle_editor.update_dialogue_target_at(index, text)

    def _get_selected_backend(self) -> str:
        return self.combo_trans_engine.currentData() or "google_free"

    def _on_transcribe_clicked(self):
        if not self.current_project or not self.current_project.video_path:
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn video nguồn trước khi nhận diện giọng nói.")
            return
        model = self.combo_model.currentText()
        device = self.combo_device.currentText()
        beam_size = int(self.combo_speed_mode.currentData() or 1)
        self.transcription_requested.emit(model, device, beam_size)

    def _on_translate_clicked(self):
        dialogues = self.subtitle_editor.get_dialogues()
        if not dialogues:
            QMessageBox.warning(self, "Thông báo", "Chưa có lời thoại nào để dịch. Hãy chạy nhận diện ASR trước.")
            return
        backend = self._get_selected_backend()
        self.translation_requested.emit(backend, {})

    def _on_translate_selected_clicked(self):
        row = self.subtitle_editor.get_selected_index()
        if row < 0:
            QMessageBox.warning(self, "Thông báo", "Vui lòng bấm chọn một dòng trên bảng phụ đề để dịch.")
            return
        backend = self._get_selected_backend()
        self.translate_single_requested.emit(row, backend, {})


