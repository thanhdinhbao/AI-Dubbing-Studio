import logging
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QProgressBar,
    QLabel, QPushButton
)

logger = logging.getLogger("AIDubbingStudio.ProgressPanel")


class ProgressPanelWidget(QWidget):
    """Bottom status & progress bar panel with Cancel Task action."""

    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)

        self.status_label = QLabel("Sẵn sàng")
        self.status_label.setMinimumWidth(250)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar, stretch=1)

        self.btn_cancel = QPushButton("⛔ Dừng tác vụ")
        self.btn_cancel.setObjectName("DangerButton")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel)
        layout.addWidget(self.btn_cancel)

    def set_progress(self, percent: int, message: str = ""):
        self.progress_bar.setValue(max(0, min(100, percent)))
        if message:
            self.status_label.setText(message)

    def set_busy(self, is_busy: bool, message: str = ""):
        self.btn_cancel.setEnabled(is_busy)
        if message:
            self.status_label.setText(message)
        if not is_busy:
            self.progress_bar.setValue(100 if "hoàn tất" in message.lower() else 0)

    def _on_cancel(self):
        self.status_label.setText("Đang yêu cầu dừng...")
        self.cancel_requested.emit()

