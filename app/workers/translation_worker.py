import logging
from typing import List
from app.workers.base_worker import BaseWorker
from app.models import DialogueSegment
from app.services.translation import TranslationService
from app.providers.base import BaseTranslationProvider

logger = logging.getLogger("AIDubbingStudio.TranslationWorker")


class TranslationWorker(BaseWorker):
    """Worker for translating dialogue lines to Vietnamese."""

    def __init__(
        self,
        dialogues: List[DialogueSegment],
        provider: BaseTranslationProvider,
        source_lang: str = "auto",
        target_lang: str = "vi",
        batch_size: int = 10
    ):
        super().__init__()
        self.dialogues = dialogues
        self.provider = provider
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.batch_size = batch_size

    def run(self):
        try:
            service = TranslationService(provider=self.provider, batch_size=self.batch_size)

            def on_trans_prog(p, msg):
                self.progress.emit(p, msg)

            translated = service.translate_dialogues(
                dialogues=self.dialogues,
                source_lang=self.source_lang,
                target_lang=self.target_lang,
                on_progress=on_trans_prog,
                cancel_event=self.cancel_event
            )
            self.finished.emit(translated)
        except Exception as e:
            logger.error(f"Translation worker failed: {e}")
            self.error.emit(str(e))

