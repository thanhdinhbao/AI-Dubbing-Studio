import os
import shutil
import threading
import logging
from pathlib import Path
from typing import Optional, Tuple, Callable

from app.constants import AudioSeparationMode
from app.exceptions import SourceSeparationError
from app.utils.ffmpeg_utils import get_ffmpeg_path, run_ffmpeg_process

logger = logging.getLogger("AIDubbingStudio.SourceSeparation")


class SourceSeparationService:
    """Handles audio separation into vocal and background instrumental stems."""

    def __init__(self, mode: str = AudioSeparationMode.DUCKING_ORIGINAL):
        self.mode = mode

    def separate_audio(
        self,
        audio_path: str | Path,
        output_dir: str | Path,
        on_progress: Optional[Callable[[int, str], None]] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Separate audio into (vocal_stem_path, instrumental_stem_path).
        If separation backend is ducking or keep_original, uses audio_path as instrumental.
        """
        audio_path = Path(audio_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if not audio_path.exists():
            raise SourceSeparationError(f"Tệp âm thanh không tồn tại: {audio_path}")

        vocal_path = output_dir / "vocal_stem.wav"
        instrumental_path = output_dir / "instrumental_stem.wav"

        if self.mode == AudioSeparationMode.DEMUCS_SEPARATION:
            # Check if demucs is installed in environment
            demucs_bin = shutil.which("demucs")
            if not demucs_bin:
                logger.warning("Demucs không được cài đặt. Tự động chuyển sang chế độ Ducking Background.")
                self.mode = AudioSeparationMode.DUCKING_ORIGINAL
            else:
                if on_progress:
                    on_progress(20, "Đang chạy mô hình AI tách giọng nói Demucs...")
                try:
                    import subprocess
                    cmd = [
                        demucs_bin,
                        "-n", "htdemucs",
                        "--two-stems", "vocals",
                        "-o", str(output_dir),
                        str(audio_path)
                    ]
                    run_ffmpeg_process(cmd, cancel_event=cancel_event)
                    # Check demucs output folder
                    stem_dir = output_dir / "htdemucs" / audio_path.stem
                    if (stem_dir / "vocals.wav").exists() and (stem_dir / "no_vocals.wav").exists():
                        shutil.copy2(stem_dir / "vocals.wav", vocal_path)
                        shutil.copy2(stem_dir / "no_vocals.wav", instrumental_path)
                        return str(vocal_path), str(instrumental_path)
                except Exception as e:
                    logger.error(f"Demucs failed: {e}. Falling back to ducking.")
                    self.mode = AudioSeparationMode.DUCKING_ORIGINAL

        if self.mode in (AudioSeparationMode.DUCKING_ORIGINAL, AudioSeparationMode.KEEP_ORIGINAL_LOW):
            # Copy original audio to instrumental stem so it can be ducked / mixed
            shutil.copy2(audio_path, instrumental_path)
            if on_progress:
                on_progress(100, "Đã chuẩn bị track nhạc nền (Chế độ Ducking).")
            return None, str(instrumental_path)

        elif self.mode == AudioSeparationMode.MUTE_ORIGINAL:
            # No background track used
            if on_progress:
                on_progress(100, "Chế độ tắt hoàn toàn âm thanh gốc.")
            return None, None

        return None, str(instrumental_path)

