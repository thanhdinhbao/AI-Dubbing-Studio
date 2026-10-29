import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QPushButton, QLabel
)
from PySide6.QtGui import QTextCursor

logger = logging.getLogger("AIDubbingStudio.LogViewer")


class LogViewerWidget(QWidget):
    """Real-time log console widget with filtering and copy features."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.addWidget(QLabel("📜 Nhật ký hệ thống & tiến trình"))

        header.addStretch()

        self.btn_copy = QPushButton("Sao chép")
        self.btn_copy.clicked.connect(self._copy_logs)
        header.addWidget(self.btn_copy)

        self.btn_clear = QPushButton("Xóa log")
        self.btn_clear.clicked.connect(self._clear_logs)
        header.addWidget(self.btn_clear)

        layout.addLayout(header)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet(
            "background-color: #13141c; color: #a9b1d6; font-family: 'Consolas', 'Courier New', monospace; font-size: 11px;"
        )
        layout.addWidget(self.text_edit)

    def append_log(self, text: str):
        self.text_edit.appendPlainText(text.strip())
        self.text_edit.moveCursor(QTextCursor.End)

    def _clear_logs(self):
        self.text_edit.clear()

    def _copy_logs(self):
        self.text_edit.selectAll()
        self.text_edit.copy()
        cursor = self.text_edit.textCursor()
        cursor.clearSelection()
        self.text_edit.setTextCursor(cursor)

