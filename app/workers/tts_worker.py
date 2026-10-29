import logging
from typing import List, Dict, Any, Optional
from app.workers.base_worker import BaseWorker
from app.models import DialogueSegment
from app.services.speech_synthesis import SpeechSynthesisService
from app.providers.base import BaseTTSProvider

logger = logging.getLogger("AIDubbingStudio.TTSWorker")


class TTSWorker(BaseWorker):
    """Worker for synthesizing Vietnamese dialogue speech with multi-threading."""

    def __init__(
        self,
        dialogues: List[DialogueSegment],
        provider: BaseTTSProvider,
        output_dir: str,
        voice_id: str,
        options: Optional[Dict[str, Any]] = None,
        max_workers: int = 5
    ):
        super().__init__()
        self.dialogues = dialogues
        self.provider = provider
        self.output_dir = output_dir
        self.voice_id = voice_id
        self.options = options
        self.max_workers = max_workers

    def run(self):
        try:
            service = SpeechSynthesisService(provider=self.provider)

            def on_tts_prog(p, msg):
                self.progress.emit(p, msg)

            synthesized = service.synthesize_dialogues(
                dialogues=self.dialogues,
                output_dir=self.output_dir,
                voice_id=self.voice_id,
                options=self.options,
                max_workers=self.max_workers,
                on_progress=on_tts_prog,
                cancel_event=self.cancel_event
            )
            self.finished.emit(synthesized)
        except Exception as e:
            logger.error(f"TTS worker failed: {e}")
            self.error.emit(str(e))

