import os
import threading
import logging
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from app.models import DialogueSegment
from app.constants import DialogueStatus
from app.providers.base import BaseTTSProvider
from app.exceptions import TTSError
from app.utils.audio_utils import calculate_tts_hash, get_audio_duration

logger = logging.getLogger("AIDubbingStudio.SpeechSynthesis")


import os
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from app.models import DialogueSegment
from app.constants import DialogueStatus
from app.providers.base import BaseTTSProvider
from app.exceptions import TTSError
from app.utils.audio_utils import calculate_tts_hash, get_audio_duration

logger = logging.getLogger("AIDubbingStudio.SpeechSynthesis")


class SpeechSynthesisService:
    """Manages audio generation for dialogue lines with multi-threading, caching, and exact duration measurement."""

    def __init__(self, provider: BaseTTSProvider, cache_dir: Optional[Path] = None):
        self.provider = provider
        self.cache_dir = cache_dir

    def synthesize_dialogues(
        self,
        dialogues: List[DialogueSegment],
        output_dir: str | Path,
        voice_id: str,
        options: Optional[Dict[str, Any]] = None,
        max_workers: int = 5,
        on_progress: Optional[Callable[[int, str], None]] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> List[DialogueSegment]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        total = len(dialogues)
        if total == 0:
            return []

        # Validate max_workers
        max_workers = max(1, min(max_workers, 16))
        logger.info(f"Synthesizing {total} dialogue lines with voice '{voice_id}' using {max_workers} worker threads...")

        completed_count = 0
        progress_lock = threading.Lock()
        first_error: Optional[Exception] = None

        def process_single_dialogue(idx: int, dlg: DialogueSegment) -> None:
            nonlocal completed_count, first_error

            if cancel_event and cancel_event.is_set():
                return

            text = dlg.target_text.strip() or dlg.source_text.strip()
            if not text:
                dlg.tts_duration = 0.0
                dlg.tts_audio_path = None
                with progress_lock:
                    completed_count += 1
                return

            # Hash check for cache
            tts_hash = calculate_tts_hash(text, voice_id, self.provider.__class__.__name__, options)
            dlg_out_path = output_dir / f"{dlg.id}_{tts_hash}.wav"

            # Check if valid cached audio exists
            if dlg_out_path.exists() and dlg_out_path.stat().st_size > 0:
                try:
                    duration = get_audio_duration(dlg_out_path)
                    dlg.tts_audio_path = str(dlg_out_path)
                    dlg.tts_duration = duration
                    dlg.voice_id = voice_id
                    dlg.status = DialogueStatus.SYNTHESIZED
                    logger.debug(f"Cache hit for dialogue {dlg.id}: {duration:.2f}s")
                    with progress_lock:
                        completed_count += 1
                        pct = int((completed_count / total) * 100)
                        if on_progress:
                            try:
                                on_progress(pct, f"Tạo giọng đọc: {completed_count}/{total} câu (Bộ nhớ đệm)...")
                            except Exception as prog_err:
                                logger.debug(f"Progress callback ignored error: {prog_err}")
                    return
                except Exception:
                    pass

            # Synthesize new audio via provider
            try:
                duration = self.provider.synthesize(
                    text=text,
                    voice_id=voice_id,
                    output_path=dlg_out_path,
                    options=options
                )
                dlg.tts_audio_path = str(dlg_out_path)
                dlg.tts_duration = duration
                dlg.voice_id = voice_id
                dlg.status = DialogueStatus.SYNTHESIZED
                logger.info(f"Generated TTS for dialogue {dlg.id} ({idx + 1}/{total}) -> duration: {duration:.2f}s")
            except Exception as e:
                dlg.status = DialogueStatus.ERROR
                dlg.error_message = str(e)
                logger.error(f"Failed to synthesize dialogue {dlg.id}: {e}")
                with progress_lock:
                    if first_error is None:
                        first_error = e
                return

            with progress_lock:
                completed_count += 1
                pct = int((completed_count / total) * 100)
                if on_progress:
                    try:
                        on_progress(pct, f"Đang tạo giọng đọc: {completed_count}/{total} câu ({pct}%)...")
                    except Exception as prog_err:
                        logger.debug(f"Progress callback ignored error: {prog_err}")

        # Execute tasks concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_single_dialogue, idx, dlg) for idx, dlg in enumerate(dialogues)]

            for future in as_completed(futures):
                if cancel_event and cancel_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise RuntimeError("Tổng hợp giọng đọc TTS đã bị hủy.")

                try:
                    future.result()
                except Exception as ex:
                    logger.error(f"TTS thread exception: {ex}")
                    if first_error is None:
                        first_error = ex

        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Tổng hợp giọng đọc TTS đã bị hủy.")

        if first_error:
            raise TTSError(f"Lỗi trong quá trình tạo giọng đọc TTS: {first_error}")

        if on_progress:
            try:
                on_progress(100, f"Tổng hợp thành công toàn bộ {total} câu thoại tiếng Việt.")
            except Exception:
                pass

        return dialogues


