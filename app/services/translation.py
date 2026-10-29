import threading
import logging
from typing import List, Optional, Callable

from app.models import DialogueSegment
from app.constants import DialogueStatus
from app.providers.base import BaseTranslationProvider
from app.exceptions import TranslationError

logger = logging.getLogger("AIDubbingStudio.TranslationService")


class TranslationService:
    """Translates dialogue segments to Vietnamese using configured provider."""

    def __init__(self, provider: BaseTranslationProvider, batch_size: int = 10):
        self.provider = provider
        self.batch_size = batch_size

    def translate_dialogues(
        self,
        dialogues: List[DialogueSegment],
        source_lang: str = "auto",
        target_lang: str = "vi",
        on_progress: Optional[Callable[[int, str], None]] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> List[DialogueSegment]:
        if not dialogues:
            return []

        total = len(dialogues)
        logger.info(f"Translating {total} dialogues to Vietnamese in batches of {self.batch_size}...")

        # Process in chunks
        for i in range(0, total, self.batch_size):
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Dịch thuật đã bị hủy.")

            chunk = dialogues[i : i + self.batch_size]
            texts = [d.source_text for d in chunk]

            percent = int((i / total) * 100)
            if on_progress:
                on_progress(percent, f"Đang dịch câu {i+1} đến {min(i+self.batch_size, total)}/{total}...")

            try:
                translated_texts = self.provider.translate_batch(texts, source_lang, target_lang)
                for dlg, trans in zip(chunk, translated_texts):
                    dlg.target_text = trans
                    dlg.status = DialogueStatus.TRANSLATED
            except Exception as e:
                logger.error(f"Translation batch failed at {i}: {e}")
                raise TranslationError(f"Dịch thuật thất bại tại câu {i+1}: {e}")

        if on_progress:
            on_progress(100, "Dịch thuật hoàn tất thành công.")

        logger.info("Translation completed.")
        return dialogues

