import logging
from app.workers.base_worker import BaseWorker
from app.services.media_probe import MediaProbeService

logger = logging.getLogger("AIDubbingStudio.ProbeWorker")


class ProbeWorker(BaseWorker):
    """Worker for probing media file metadata."""

    def __init__(self, video_path: str):
        super().__init__()
        self.video_path = video_path

    def run(self):
        try:
            self.progress.emit(10, "Đang phân tích định dạng tệp media...")
            info = MediaProbeService.probe_media(self.video_path)
            self.progress.emit(100, "Phân tích thành công.")
            self.finished.emit(info)
        except Exception as e:
            logger.error(f"Probe worker failed: {e}")
            self.error.emit(str(e))

