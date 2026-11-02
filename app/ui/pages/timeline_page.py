import logging
from typing import Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QRadioButton,
    QButtonGroup, QMessageBox, QGridLayout
)

from app.models import ProjectData
from app.constants import TimelineMode, VisualExtendMode
from app.ui.widgets.timeline_editor import TimelineEditorWidget
from app.utils.timecode import seconds_to_display

logger = logging.getLogger("AIDubbingStudio.TimelinePage")


class TimelinePage(QWidget):
    """Tab 5: Dynamic Dubbing Timeline Reconstruction & Conflict Analysis."""

    rebuild_timeline_requested = Signal(str, dict)  # mode, options

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_project: Optional[ProjectData] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Stats & Controls Panel
        header_group = QGroupBox("Cấu hình & Thống kê Timeline Động")
        h_layout = QGridLayout(header_group)
        h_layout.setSpacing(10)

        # Stats Labels
        self.lbl_src_duration = QLabel("Thời lượng Video gốc: --")
        self.lbl_src_duration.setStyleSheet("font-weight: bold; color: #a9b1d6;")
        h_layout.addWidget(self.lbl_src_duration, 0, 0)

        self.lbl_out_duration = QLabel("Thời lượng Video sau lồng tiếng: --")
        self.lbl_out_duration.setStyleSheet("font-weight: bold; color: #7aa2f7; font-size: 14px;")
        h_layout.addWidget(self.lbl_out_duration, 0, 1)

        self.lbl_delta = QLabel("Độ giãn thời gian (Delta): --")
        self.lbl_delta.setStyleSheet("font-weight: bold; color: #ff9e64;")
        h_layout.addWidget(self.lbl_delta, 0, 2)

        # Timeline Mode Selector
        h_layout.addWidget(QLabel("Chế độ Timeline:"), 1, 0)
        mode_box = QHBoxLayout()
        self.radio_dynamic = QRadioButton("Dynamic Duration (Tự tăng/giảm theo TTS - Mặc định)")
        self.radio_dynamic.setChecked(True)
        self.radio_preserve = QRadioButton("Preserve Original Duration (Giữ nguyên thời lượng gốc)")
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.radio_dynamic)
        self.btn_group.addButton(self.radio_preserve)
        mode_box.addWidget(self.radio_dynamic)
        mode_box.addWidget(self.radio_preserve)
        h_layout.addLayout(mode_box, 1, 1, 1, 2)

        # Visual Extension Mode
        h_layout.addWidget(QLabel("Xử lý hình ảnh khi câu thoại dài hơn:"), 2, 0)
        self.combo_extend_mode = QComboBox()
        self.combo_extend_mode.addItem("Đệm khoảng dừng & Chuyển động mượt mà (Hold and Pad - Khuyến nghị, video mượt mà không khựng)", VisualExtendMode.HOLD_AND_PAD)
        self.combo_extend_mode.addItem("Làm chậm mượt chuyển động câu dài (Smooth Slow-Mo - Chuyển động liên tục)", VisualExtendMode.SPEED_ADJUST)
        self.combo_extend_mode.addItem("Đóng băng khung hình cuối (Freeze Last Frame - Đứng hình khi câu thoại dài hơn)", VisualExtendMode.FREEZE_LAST_FRAME)
        self.combo_extend_mode.currentIndexChanged.connect(self._on_extend_mode_changed)
        h_layout.addWidget(self.combo_extend_mode, 2, 1)

        self.btn_rebuild = QPushButton("🔄 Tính toán & Dựng lại Timeline")
        self.btn_rebuild.setObjectName("PrimaryButton")
        self.btn_rebuild.clicked.connect(self._rebuild_timeline)
        h_layout.addWidget(self.btn_rebuild, 2, 2)

        layout.addWidget(header_group)

        # Legend / Guide Banner
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("📌 Chú thích:"))

        lbl_leg1 = QLabel("■ Video thường (Xanh)")
        lbl_leg1.setStyleSheet("color: #7aa2f7; font-weight: bold;")
        legend_layout.addWidget(lbl_leg1)

        lbl_leg2 = QLabel("■ Giãn khung hình (Cam/Vàng)")
        lbl_leg2.setStyleSheet("color: #ff9e64; font-weight: bold;")
        legend_layout.addWidget(lbl_leg2)

        lbl_leg3 = QLabel("■ TTS Tiếng Việt (Xanh ngọc)")
        lbl_leg3.setStyleSheet("color: #73daca; font-weight: bold;")
        legend_layout.addWidget(lbl_leg3)

        legend_layout.addStretch()
        layout.addLayout(legend_layout)

        # Interactive Timeline Visualizer
        self.timeline_editor = TimelineEditorWidget()
        layout.addWidget(self.timeline_editor, stretch=1)

    def set_project(self, project: ProjectData):
        self.current_project = project
        src_dur = project.media_info.duration if project.media_info else 0.0
        out_dur = project.output_duration if project.output_duration > 0 else src_dur

        self.lbl_src_duration.setText(f"Thời lượng Video gốc: {seconds_to_display(src_dur)} ({src_dur:.2f}s)")
        self.lbl_out_duration.setText(f"Thời lượng Sau lồng tiếng: {seconds_to_display(out_dur)} ({out_dur:.2f}s)")

        delta = out_dur - src_dur
        self.lbl_delta.setText(f"Độ giãn thời gian (Delta): {delta:+.2f}s")

        self.timeline_editor.set_data(
            timeline_segments=project.timeline_segments,
            dialogues=project.dialogues,
            source_duration=src_dur,
            output_duration=out_dur
        )

        # Synchronize extend mode dropdown
        ext_mode = getattr(project, "visual_extend_mode", VisualExtendMode.HOLD_AND_PAD)
        idx = self.combo_extend_mode.findData(ext_mode)
        if idx >= 0:
            self.combo_extend_mode.blockSignals(True)
            self.combo_extend_mode.setCurrentIndex(idx)
            self.combo_extend_mode.blockSignals(False)

    def _on_extend_mode_changed(self):
        if self.current_project and self.current_project.dialogues:
            self.current_project.visual_extend_mode = self.combo_extend_mode.currentData()
            self._rebuild_timeline()

    def _rebuild_timeline(self):
        if not self.current_project or not self.current_project.dialogues:
            QMessageBox.warning(self, "Thông báo", "Chưa có lời thoại được xử lý để tính toán timeline.")
            return

        mode = TimelineMode.DYNAMIC_DURATION if self.radio_dynamic.isChecked() else TimelineMode.PRESERVE_DURATION
        opts = {
            "visual_extend_mode": self.combo_extend_mode.currentData(),
            "allow_contraction": False
        }
        self.rebuild_timeline_requested.emit(mode, opts)

