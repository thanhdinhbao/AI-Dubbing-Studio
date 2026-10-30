import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QLineEdit,
    QFileDialog, QMessageBox, QGridLayout
)

from app.models import ProjectData
from app.ui.widgets.media_player import MediaPlayerWidget
from app.utils.paths import get_default_output_dir
from app.utils.timecode import seconds_to_display

logger = logging.getLogger("AIDubbingStudio.ExportPage")


class ExportPage(QWidget):
    """Tab 6: Video Export, Render Settings, and Result Verification."""

    render_requested = Signal(str, dict)  # output_path, render_settings

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project: Optional[ProjectData] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Left Column: Export Settings
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        # 1. Output File Configuration
        out_group = QGroupBox("Cấu hình Tệp Xuất bản")
        out_layout = QGridLayout(out_group)
        out_layout.setSpacing(8)

        out_layout.addWidget(QLabel("Tên tệp kết quả:"), 0, 0)
        self.filename_input = QLineEdit("dubbed_video_vi.mp4")
        out_layout.addWidget(self.filename_input, 0, 1)

        out_layout.addWidget(QLabel("Thư mục lưu trữ:"), 1, 0)
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Thư mục output trong dự án...")
        out_layout.addWidget(self.dir_input, 1, 1)

        self.btn_browse_dir = QPushButton("📂 Duyệt...")
        self.btn_browse_dir.clicked.connect(self._browse_output_dir)
        out_layout.addWidget(self.btn_browse_dir, 1, 2)

        left_col.addWidget(out_group)

        # 2. Video & Audio Encoding Specs
        codec_group = QGroupBox("Tham số Mã hóa & Chất lượng Video")
        codec_layout = QGridLayout(codec_group)
        codec_layout.setSpacing(8)

        codec_layout.addWidget(QLabel("Codec Video:"), 0, 0)
        self.combo_vcodec = QComboBox()
        self.combo_vcodec.addItem("H.264 CPU Đa luồng (libx264 - Tương thích tối đa)", "libx264")
        self.combo_vcodec.addItem("H.264 NVIDIA GPU NVENC (Tốc độ cao nhất)", "h264_nvenc")
        self.combo_vcodec.addItem("H.265 / HEVC (libx265)", "libx265")
        codec_layout.addWidget(self.combo_vcodec, 0, 1)

        codec_layout.addWidget(QLabel("Tốc độ mã hóa (Preset):"), 1, 0)
        self.combo_preset = QComboBox()
        self.combo_preset.addItem("⚡ Cực nhanh (Very Fast - Tiết kiệm thời gian)", "veryfast")
        self.combo_preset.addItem("🚀 Nhanh (Faster - Khuyến nghị)", "faster")
        self.combo_preset.addItem("🎯 Cân bằng chuẩn (Medium)", "medium")
        self.combo_preset.setCurrentIndex(1)  # faster
        codec_layout.addWidget(self.combo_preset, 1, 1)

        codec_layout.addWidget(QLabel("Chất lượng Video (CRF/CQ):"), 2, 0)
        self.combo_crf = QComboBox()
        self.combo_crf.addItem("18 (Chất lượng rất cao - Dung lượng lớn)", 18)
        self.combo_crf.addItem("20 (Cân bằng chuẩn - Khuyến nghị)", 20)
        self.combo_crf.addItem("23 (Chất lượng tốt - Dung lượng nhẹ)", 23)
        self.combo_crf.setCurrentIndex(1)
        codec_layout.addWidget(self.combo_crf, 2, 1)

        codec_layout.addWidget(QLabel("Codec Audio:"), 3, 0)
        self.combo_acodec = QComboBox()
        self.combo_acodec.addItem("AAC (192 kbps Stereo - Chuẩn)", "aac")
        self.combo_acodec.addItem("MP3 (Lame 192 kbps)", "libmp3lame")
        codec_layout.addWidget(self.combo_acodec, 3, 1)

        left_col.addWidget(codec_group)

        # 3. Action Buttons
        act_box = QVBoxLayout()
        self.btn_start_render = QPushButton("🚀 BẮT ĐẦU XUẤT VIDEO LỒNG TIẾNG")
        self.btn_start_render.setObjectName("PrimaryButton")
        self.btn_start_render.setFixedHeight(44)
        self.btn_start_render.clicked.connect(self._start_render)
        act_box.addWidget(self.btn_start_render)

        h_btns = QHBoxLayout()
        self.btn_open_folder = QPushButton("📁 Mở thư mục kết quả")
        self.btn_open_folder.clicked.connect(self._open_output_folder)
        h_btns.addWidget(self.btn_open_folder)

        act_box.addLayout(h_btns)
        left_col.addLayout(act_box)
        left_col.addStretch()

        layout.addLayout(left_col, stretch=1)

        # Right Column: Resulting Video Preview
        right_col = QVBoxLayout()
        result_group = QGroupBox("Xem trước Video Kết Quả")
        result_layout = QVBoxLayout(result_group)
        self.result_player = MediaPlayerWidget()
        result_layout.addWidget(self.result_player)

        self.lbl_result_info = QLabel("Chưa xuất bản video.")
        self.lbl_result_info.setStyleSheet("color: #7aa2f7; font-weight: bold; padding: 6px;")
        result_layout.addWidget(self.lbl_result_info)

        right_col.addWidget(result_group)
        layout.addLayout(right_col, stretch=1)

    def set_project(self, project: ProjectData):
        self.current_project = project
        if project:
            if project.project_dir:
                proj_out_dir = Path(project.project_dir) / "output"
                proj_out_dir.mkdir(parents=True, exist_ok=True)
                self.dir_input.setText(str(proj_out_dir))
            if project.video_path:
                stem = Path(project.video_path).stem
                self.filename_input.setText(f"{stem}_dubbed_vi.mp4")

            if project.output_video_path and os.path.exists(project.output_video_path):
                self.show_render_result(project.output_video_path)

    def show_render_result(self, video_path: str):
        if os.path.exists(video_path):
            self.result_player.load_media(video_path)
            size_mb = round(os.path.getsize(video_path) / (1024 * 1024), 2)
            self.lbl_result_info.setText(f"✅ Video đã tạo thành công! Dung lượng: {size_mb} MB")

    def _browse_output_dir(self):
        initial_dir = self.dir_input.text().strip() or (
            str(Path(self.current_project.project_dir) / "output")
            if (self.current_project and self.current_project.project_dir)
            else str(get_default_output_dir())
        )
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu trữ video", initial_dir)
        if folder:
            self.dir_input.setText(folder)

    def _open_output_folder(self):
        target_dir = self.dir_input.text().strip()
        if not target_dir and self.current_project and self.current_project.project_dir:
            target_dir = str(Path(self.current_project.project_dir) / "output")
        if os.path.exists(target_dir):
            if os.name == "nt":
                os.startfile(target_dir)
            else:
                subprocess.Popen(["explorer", target_dir])
        else:
            QMessageBox.warning(self, "Thông báo", "Thư mục không tồn tại.")

    def _start_render(self):
        if not self.current_project or not self.current_project.video_path:
            QMessageBox.warning(self, "Thông báo", "Chưa có dự án hoặc video nguồn hợp lệ.")
            return

        if not self.current_project.timeline_segments:
            QMessageBox.warning(self, "Thông báo", "Chưa tính toán timeline động. Vui lòng qua Tab Timeline để dựng timeline trước.")
            return

        dir_str = self.dir_input.text().strip()
        if dir_str:
            out_dir = Path(dir_str)
        elif self.current_project and self.current_project.project_dir:
            out_dir = Path(self.current_project.project_dir) / "output"
        else:
            out_dir = get_default_output_dir()

        out_dir.mkdir(parents=True, exist_ok=True)
        filename = self.filename_input.text().strip() or "dubbed_video_vi.mp4"
        out_path = str(out_dir / filename)

        settings = {
            "render_video_codec": self.combo_vcodec.currentData(),
            "render_audio_codec": self.combo_acodec.currentData(),
            "render_crf": self.combo_crf.currentData(),
            "render_preset": self.combo_preset.currentData() or "faster",
            "render_audio_bitrate": "192k",
            "bg_music_volume": 0.25,
            "tts_volume_gain": 1.1,
            "ducking_reduction": 0.2
        }

        self.render_requested.emit(out_path, settings)

