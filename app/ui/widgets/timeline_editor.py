import logging
from typing import List, Optional
from PySide6.QtCore import Qt, QRectF, Signal, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget

from app.models import TimelineSegment, DialogueSegment
from app.utils.timecode import seconds_to_display

logger = logging.getLogger("AIDubbingStudio.TimelineVisualizer")


class TimelineEditorWidget(QWidget):
    """Custom graphical timeline visualizer for the dynamic dubbing tracks."""

    seek_requested = Signal(float)  # seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setMouseTracking(True)

        self.timeline_segments: List[TimelineSegment] = []
        self.dialogues: List[DialogueSegment] = []
        self.source_duration: float = 0.0
        self.output_duration: float = 0.0
        self.current_playhead: float = 0.0
        self.pixels_per_second: float = 25.0

    def set_data(
        self,
        timeline_segments: List[TimelineSegment],
        dialogues: List[DialogueSegment],
        source_duration: float,
        output_duration: float
    ):
        self.timeline_segments = timeline_segments
        self.dialogues = dialogues
        self.source_duration = max(0.1, source_duration)
        self.output_duration = max(0.1, output_duration)
        self._update_zoom()
        self.update()

    def set_playhead(self, seconds: float):
        self.current_playhead = seconds
        self.update()

    def _update_zoom(self):
        w = max(400, self.width() - 40)
        if self.output_duration > 0:
            self.pixels_per_second = w / self.output_duration

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_zoom()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            x = event.position().x() - 20
            sec = max(0.0, min(self.output_duration, x / self.pixels_per_second))
            self.current_playhead = sec
            self.seek_requested.emit(sec)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#16161e"))

        left_margin = 20
        top_margin = 24
        track_h = 28
        spacing = 8

        # 1. Ruler / Time markings
        painter.setPen(QColor("#565f89"))
        painter.setFont(QFont("Segoe UI", 8))
        step_sec = 5.0 if self.output_duration < 120 else 10.0
        t = 0.0
        while t <= self.output_duration:
            x = left_margin + t * self.pixels_per_second
            painter.drawLine(int(x), top_margin - 8, int(x), top_margin)
            painter.drawText(int(x) - 15, top_margin - 10, seconds_to_display(t))
            t += step_sec

        # Track labels
        labels = ["Track Video & Freeze", "Track Lời Thoại Gốc", "Track TTS Tiếng Việt", "Nhạc Nền & Ducking"]
        track_colors = [
            QColor("#3d59a1"),  # normal video
            QColor("#bb9af7"),  # source dialogue
            QColor("#73daca"),  # vietnamese tts
            QColor("#e0af68"),  # freeze frame
        ]

        # Draw Tracks
        y_video = top_margin + 6
        y_source = y_video + track_h + spacing
        y_tts = y_source + track_h + spacing
        y_bg = y_tts + track_h + spacing

        # Track 1: Reconstructed Video (Blue normal + Amber Freeze extensions)
        painter.setPen(Qt.NoPen)
        for seg in self.timeline_segments:
            sx = left_margin + seg.output_start * self.pixels_per_second
            sw = max(2.0, seg.duration * self.pixels_per_second)

            if seg.segment_type == "video_freeze":
                painter.setBrush(QColor("#ff9e64"))  # Freeze frame extension
                painter.drawRoundedRect(QRectF(sx, y_video, sw, track_h), 4, 4)
                # Label
                if sw > 25:
                    painter.setPen(QColor("#15161e"))
                    painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
                    painter.drawText(QRectF(sx, y_video, sw, track_h), Qt.AlignCenter, f"+{seg.duration:.1f}s")
            else:
                painter.setBrush(QColor("#3d59a1"))
                painter.drawRoundedRect(QRectF(sx, y_video, sw, track_h), 4, 4)
            painter.setPen(Qt.NoPen)

        # Track 2: Original Dialogue intervals (mapped onto output start)
        for dlg in self.dialogues:
            # Find output mapping
            sx = left_margin + dlg.start * self.pixels_per_second
            sw = max(2.0, dlg.source_duration * self.pixels_per_second)
            painter.setBrush(QColor("#bb9af7"))
            painter.drawRoundedRect(QRectF(sx, y_source, sw, track_h), 4, 4)
            if sw > 30:
                painter.setPen(QColor("#15161e"))
                painter.setFont(QFont("Segoe UI", 7))
                painter.drawText(QRectF(sx + 4, y_source, sw - 8, track_h), Qt.AlignVCenter | Qt.AlignLeft, dlg.source_text[:15])
                painter.setPen(Qt.NoPen)

        # Track 3: Vietnamese TTS audio clips
        for seg in self.timeline_segments:
            if seg.dialogue_id and seg.segment_type == "video_normal":
                sx = left_margin + seg.output_start * self.pixels_per_second
                sw = max(2.0, seg.duration * self.pixels_per_second)
                painter.setBrush(QColor("#73daca"))
                painter.drawRoundedRect(QRectF(sx, y_tts, sw, track_h), 4, 4)

        # Track 4: Background music bed
        total_w = self.output_duration * self.pixels_per_second
        painter.setBrush(QColor("#24283b"))
        painter.drawRoundedRect(QRectF(left_margin, y_bg, total_w, track_h), 4, 4)

        # Draw Playhead Cursor
        px = left_margin + self.current_playhead * self.pixels_per_second
        painter.setPen(QPen(QColor("#f7768e"), 2))
        painter.drawLine(int(px), top_margin - 4, int(px), y_bg + track_h + 4)
        painter.setBrush(QColor("#f7768e"))
        painter.drawPolygon([QPointF(px - 5, top_margin - 8), QPointF(px + 5, top_margin - 8), QPointF(px, top_margin - 2)])

