import os
import logging
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QLineEdit, QComboBox,
    QFileDialog, QMessageBox, QGridLayout
)

from app.models import ProjectData, MediaInfo
from app.ui.widgets.media_player import MediaPlayerWidget
from app.utils.paths import get_disk_free_space_gb
from app.utils.timecode import seconds_to_display

logger = logging.getLogger("AIDubbingStudio.ProjectPage")


class ProjectPage(QWidget):
    """Tab 1: Project & Media Management."""

    project_created = Signal(str, str)  # name, video_path
    video_selected = Signal(str)  # video_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project: Optional[ProjectData] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Left Column: Project Setup & Media Info
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        # 1. Project Management Box
        proj_group = QGroupBox("Quản lý Dự án")
        proj_layout = QGridLayout(proj_group)
        proj_layout.setSpacing(8)

        proj_layout.addWidget(QLabel("Tên dự án:"), 0, 0)
        self.proj_name_input = QLineEdit("Dự án lồng tiếng mới")
        proj_layout.addWidget(self.proj_name_input, 0, 1)

        self.btn_new_proj = QPushButton("✨ Tạo mới")
        self.btn_new_proj.setObjectName("PrimaryButton")
        self.btn_new_proj.clicked.connect(self._create_new_project)
        proj_layout.addWidget(self.btn_new_proj, 0, 2)

        left_col.addWidget(proj_group)

        # 2. Video Import Box
        video_group = QGroupBox("Nhập Tệp Video Gốc")
        video_layout = QGridLayout(video_group)
        video_layout.setSpacing(8)

        video_layout.addWidget(QLabel("Đường dẫn Video:"), 0, 0)
        self.video_path_input = QLineEdit()
        self.video_path_input.setReadOnly(True)
        self.video_path_input.setPlaceholderText("Chọn video từ máy tính (MP4, MKV, MOV, AVI)...")
        video_layout.addWidget(self.video_path_input, 0, 1)

        self.btn_browse_video = QPushButton("📂 Chọn Video")
        self.btn_browse_video.clicked.connect(self._browse_video)
        video_layout.addWidget(self.btn_browse_video, 0, 2)

        # Media specifications display
        self.lbl_specs = QLabel(
            "Thời lượng: -- | Độ phân giải: -- | FPS: --\n"
            "Codec Video: -- | Codec Audio: -- | Dung lượng: --"
        )
        self.lbl_specs.setStyleSheet("color: #7aa2f7; font-weight: 500; padding: 4px;")
        video_layout.addWidget(self.lbl_specs, 1, 0, 1, 3)

        left_col.addWidget(video_group)

        # 3. Language & Storage Box
        lang_group = QGroupBox("Cấu hình Ngôn ngữ & Lưu trữ")
        lang_layout = QGridLayout(lang_group)
        lang_layout.setSpacing(8)

        lang_layout.addWidget(QLabel("Ngôn ngữ nguồn:"), 0, 0)
        self.combo_source_lang = QComboBox()
        self.combo_source_lang.addItems(["Auto Detect", "en (Tiếng Anh)", "ja (Tiếng Nhật)", "zh (Tiếng Trung)", "ko (Tiếng Hàn)", "fr (Tiếng Pháp)"])
        lang_layout.addWidget(self.combo_source_lang, 0, 1)

        lang_layout.addWidget(QLabel("Ngôn ngữ đích:"), 1, 0)
        self.combo_target_lang = QComboBox()
        self.combo_target_lang.addItem("vi (Tiếng Việt)")
        self.combo_target_lang.setEnabled(False)
        lang_layout.addWidget(self.combo_target_lang, 1, 1)

        self.lbl_disk_space = QLabel("Dung lượng ổ đĩa khả dụng: -- GB")
        self.lbl_disk_space.setStyleSheet("color: #9ece6a; font-weight: bold;")
        lang_layout.addWidget(self.lbl_disk_space, 2, 0, 1, 2)

        left_col.addWidget(lang_group)
        left_col.addStretch()

        layout.addLayout(left_col, stretch=1)

        # Right Column: Media Preview Player
        right_col = QVBoxLayout()
        preview_group = QGroupBox("Xem trước Video")
        preview_layout = QVBoxLayout(preview_group)
        self.player_widget = MediaPlayerWidget()
        preview_layout.addWidget(self.player_widget)
        right_col.addWidget(preview_group)

        layout.addLayout(right_col, stretch=1)

    def set_project(self, project: ProjectData):
        """Update view with current project details."""
        self.current_project = project
        self.proj_name_input.setText(project.name)
        if project.video_path:
            self.video_path_input.setText(project.video_path)
            self.player_widget.load_media(project.video_path)

        if project.media_info:
            self.update_media_info(project.media_info)

        # Update disk space
        target_dir = project.project_dir or Path.cwd()
        free_gb = get_disk_free_space_gb(target_dir)
        self.lbl_disk_space.setText(f"Dung lượng ổ đĩa khả dụng: {free_gb} GB")

    def update_media_info(self, info: MediaInfo):
        """Update displayed media specifications."""
        dur_str = seconds_to_display(info.duration)
        size_mb = round(info.file_size_bytes / (1024 * 1024), 2)
        specs_text = (
            f"Thời lượng: {dur_str} ({info.duration:.2f}s) | "
            f"Độ phân giải: {info.width}x{info.height} | FPS: {info.fps}\n"
            f"Codec Video: {info.video_codec or 'Không có'} | "
            f"Codec Audio: {info.audio_codec or 'Không có'} ({info.audio_sample_rate}Hz) | "
            f"Dung lượng: {size_mb} MB"
        )
        self.lbl_specs.setText(specs_text)

        if not info.has_audio:
            QMessageBox.warning(
                self,
                "Cảnh báo",
                "Video đã chọn không chứa track âm thanh (No Audio Stream). "
                "Ứng dụng sẽ không thể nhận diện lời thoại tự động."
            )

    def _browse_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn tệp Video nguồn",
            "",
            "Video Files (*.mp4 *.mkv *.mov *.avi *.webm *.flv);;All Files (*.*)"
        )
        if file_path:
            self.video_path_input.setText(file_path)
            self.player_widget.load_media(file_path)
            self.video_selected.emit(file_path)

    def _create_new_project(self):
        name = self.proj_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên dự án.")
            return
        video_p = self.video_path_input.text().strip()
        self.project_created.emit(name, video_p)

