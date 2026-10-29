import logging
from app.workers.base_worker import BaseWorker
from app.services.source_separation import SourceSeparationService

logger = logging.getLogger("AIDubbingStudio.SeparationWorker")


class SeparationWorker(BaseWorker):
    """Worker for vocal/background instrumental separation."""

    def __init__(self, audio_path: str, output_dir: str, separation_mode: str):
        super().__init__()
        self.audio_path = audio_path
        self.output_dir = output_dir
        self.separation_mode = separation_mode

    def run(self):
        try:
            service = SourceSeparationService(mode=self.separation_mode)

            def on_sep_prog(p, msg):
                self.progress.emit(p, msg)

            vocal_stem, inst_stem = service.separate_audio(
                audio_path=self.audio_path,
                output_dir=self.output_dir,
                on_progress=on_sep_prog,
                cancel_event=self.cancel_event
            )
            self.finished.emit({"vocal_stem": vocal_stem, "instrumental_stem": inst_stem})
        except Exception as e:
            logger.error(f"Separation worker failed: {e}")
            self.error.emit(str(e))

