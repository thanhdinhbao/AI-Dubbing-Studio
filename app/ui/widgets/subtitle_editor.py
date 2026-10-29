import logging
from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QPushButton,
    QLabel, QFileDialog, QMessageBox
)

from app.models import DialogueSegment
from app.constants import DialogueStatus
from app.utils.timecode import seconds_to_srt_time, srt_time_to_seconds

logger = logging.getLogger("AIDubbingStudio.SubtitleEditor")


class SubtitleEditorWidget(QWidget):
    """Interactive table for viewing and editing subtitles and translations."""

    dialogues_changed = Signal()  # Emitted when text or timing is edited
    play_dialogue_requested = Signal(DialogueSegment)

    COL_ID = 0
    COL_START = 1
    COL_END = 2
    COL_SOURCE = 3
    COL_TARGET = 4
    COL_TTS_DUR = 5
    COL_STATUS = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dialogues: List[DialogueSegment] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Tìm kiếm nội dung câu thoại...")
        self.search_input.textChanged.connect(self._filter_rows)
        toolbar.addWidget(self.search_input)

        self.btn_play_row = QPushButton("🔊 Nghe câu chọn")
        self.btn_play_row.clicked.connect(self._on_play_selected)
        toolbar.addWidget(self.btn_play_row)

        self.btn_import_srt = QPushButton("📥 Nhập SRT")
        self.btn_import_srt.clicked.connect(self._import_srt)
        toolbar.addWidget(self.btn_import_srt)

        self.btn_export_srt = QPushButton("📤 Xuất SRT")
        self.btn_export_srt.clicked.connect(self._export_srt)
        toolbar.addWidget(self.btn_export_srt)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Bắt đầu", "Kết thúc", "Lời thoại gốc",
            "Bản dịch Tiếng Việt", "Thời lượng TTS", "Trạng thái"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_ID, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_START, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_END, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_SOURCE, QHeaderView.Stretch)
        header.setSectionResizeMode(self.COL_TARGET, QHeaderView.Stretch)
        header.setSectionResizeMode(self.COL_TTS_DUR, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_STATUS, QHeaderView.ResizeToContents)

        self.table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self.table)

        self._updating = False

    def load_dialogues(self, dialogues: List[DialogueSegment]):
        """Populate table with dialogue segments."""
        self._updating = True
        self.dialogues = dialogues
        self.table.setRowCount(len(dialogues))

        for row, dlg in enumerate(dialogues):
            # ID (read-only)
            item_id = QTableWidgetItem(dlg.id)
            item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, self.COL_ID, item_id)

            # Start time (editable)
            item_start = QTableWidgetItem(seconds_to_srt_time(dlg.start))
            self.table.setItem(row, self.COL_START, item_start)

            # End time (editable)
            item_end = QTableWidgetItem(seconds_to_srt_time(dlg.end))
            self.table.setItem(row, self.COL_END, item_end)

            # Source text (editable)
            item_source = QTableWidgetItem(dlg.source_text)
            self.table.setItem(row, self.COL_SOURCE, item_source)

            # Vietnamese text (editable)
            item_target = QTableWidgetItem(dlg.target_text)
            self.table.setItem(row, self.COL_TARGET, item_target)

            # TTS Duration (read-only)
            dur_str = f"{dlg.tts_duration:.2f}s" if dlg.tts_duration > 0 else "-"
            item_dur = QTableWidgetItem(dur_str)
            item_dur.setFlags(item_dur.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, self.COL_TTS_DUR, item_dur)

            # Status badge (read-only)
            status_text = {
                DialogueStatus.PENDING: "Chờ xử lý",
                DialogueStatus.TRANSCRIBED: "Đã nhận diện",
                DialogueStatus.TRANSLATED: "Đã dịch",
                DialogueStatus.SYNTHESIZED: "Đã tạo TTS",
                DialogueStatus.MODIFIED: "Đã chỉnh sửa",
                DialogueStatus.ERROR: "Lỗi"
            }.get(dlg.status, dlg.status)
            item_status = QTableWidgetItem(status_text)
            item_status.setFlags(item_status.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, self.COL_STATUS, item_status)

        self._updating = False

    def get_dialogues(self) -> List[DialogueSegment]:
        return self.dialogues

    def get_selected_index(self) -> int:
        """Return index of currently selected row in table, or -1 if none selected."""
        return self.table.currentRow()

    def update_dialogue_target_at(self, index: int, target_text: str):
        """Update Vietnamese text for a specific row in the table."""
        if 0 <= index < len(self.dialogues):
            self.dialogues[index].target_text = target_text
            self.dialogues[index].status = DialogueStatus.TRANSLATED
            self._updating = True
            item_target = self.table.item(index, self.COL_TARGET)
            if item_target:
                item_target.setText(target_text)
            item_status = self.table.item(index, self.COL_STATUS)
            if item_status:
                item_status.setText("Đã dịch")
            self._updating = False

    def _on_cell_changed(self, row: int, col: int):
        if self._updating or row >= len(self.dialogues):
            return

        dlg = self.dialogues[row]
        item = self.table.item(row, col)
        if not item:
            return

        text = item.text().strip()

        if col == self.COL_START:
            try:
                dlg.start = srt_time_to_seconds(text)
                dlg.status = DialogueStatus.MODIFIED
            except Exception:
                pass
        elif col == self.COL_END:
            try:
                dlg.end = srt_time_to_seconds(text)
                dlg.status = DialogueStatus.MODIFIED
            except Exception:
                pass
        elif col == self.COL_SOURCE:
            dlg.source_text = text
            dlg.status = DialogueStatus.MODIFIED
        elif col == self.COL_TARGET:
            if dlg.target_text != text:
                dlg.target_text = text
                dlg.status = DialogueStatus.MODIFIED
                # When translation text changes, reset tts_duration to mark for re-synthesis
                dlg.tts_duration = 0.0
                dlg.tts_audio_path = None
                self._updating = True
                self.table.item(row, self.COL_TTS_DUR).setText("-")
                self.table.item(row, self.COL_STATUS).setText("Đã chỉnh sửa")
                self._updating = False

        self.dialogues_changed.emit()

    def _filter_rows(self, query: str):
        query = query.lower()
        for row in range(self.table.rowCount()):
            src = self.table.item(row, self.COL_SOURCE).text().lower()
            tgt = self.table.item(row, self.COL_TARGET).text().lower()
            match = query in src or query in tgt
            self.table.setRowHidden(row, not match)

    def _on_play_selected(self):
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if row < len(self.dialogues):
            dlg = self.dialogues[row]
            self.play_dialogue_requested.emit(dlg)

    def _export_srt(self):
        if not self.dialogues:
            QMessageBox.warning(self, "Thông báo", "Không có phụ đề nào để xuất.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Xuất file phụ đề SRT", "subtitles_vi.srt", "SRT Subtitles (*.srt)")
        if file_path:
            from app.services.audio_alignment import AudioAlignmentService
            AudioAlignmentService.export_srt(self.dialogues, file_path, use_vietnamese=True)
            QMessageBox.information(self, "Thành công", f"Đã xuất phụ đề thành công vào:\n{file_path}")

    def _import_srt(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Nhập file phụ đề SRT", "", "SRT Subtitles (*.srt)")
        if file_path:
            from app.services.audio_alignment import AudioAlignmentService
            try:
                imported = AudioAlignmentService.import_srt(file_path)
                self.load_dialogues(imported)
                self.dialogues_changed.emit()
                QMessageBox.information(self, "Thành công", f"Đã nhập {len(imported)} dòng phụ đề từ SRT.")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể đọc file SRT: {e}")

