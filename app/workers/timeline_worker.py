import logging
from typing import List, Dict, Any, Optional
from app.workers.base_worker import BaseWorker
from app.models import DialogueSegment
from app.services.timeline_engine import TimelineEngine
from app.constants import TimelineMode

logger = logging.getLogger("AIDubbingStudio.TimelineWorker")


class TimelineWorker(BaseWorker):
    """Worker for dynamic timeline calculation."""

    def __init__(
        self,
        source_duration: float,
        dialogues: List[DialogueSegment],
        mode: str = TimelineMode.DYNAMIC_DURATION,
        options: Optional[Dict[str, Any]] = None
    ):
        super().__init__()
        self.source_duration = source_duration
        self.dialogues = dialogues
        self.mode = mode
        self.options = options

    def run(self):
        try:
            self.progress.emit(20, "Đang tính toán timeline động...")
            engine = TimelineEngine(mode=self.mode)
            timeline_segments = engine.build_timeline(
                source_duration=self.source_duration,
                dialogues=self.dialogues,
                options=self.options
            )
            out_dur = engine.calculate_output_duration(timeline_segments)
            self.progress.emit(100, f"Timeline hoàn tất: thời lượng dự kiến {out_dur:.2f}s")
            self.finished.emit({
                "timeline_segments": timeline_segments,
                "output_duration": out_dur
            })
        except Exception as e:
            logger.error(f"Timeline worker failed: {e}")
            self.error.emit(str(e))

