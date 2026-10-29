import os
import threading
import logging
from pathlib import Path
from typing import Optional, Callable

from app.exceptions import AudioExtractionError
from app.utils.ffmpeg_utils import get_ffmpeg_path, run_ffmpeg_process
from app.services.media_probe import MediaProbeService

logger = logging.getLogger("AIDubbingStudio.AudioExtractor")


class AudioExtractorService:
    """Extracts audio track from video into uncompressed WAV."""

    @staticmethod
    def extract_audio(
        video_path: str | Path,
        output_wav_path: str | Path,
        sample_rate: int = 44100,
        channels: int = 2,
        audio_stream_index: int = 0,
        on_progress: Optional[Callable[[str], None]] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> str:
        video_path = str(video_path)
        output_wav_path = str(output_wav_path)
        os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)

        info = MediaProbeService.probe_media(video_path)
        if not info.has_audio:
            raise AudioExtractionError(
                "Tệp video nguồn không chứa track âm thanh (No Audio Stream).",
                details="Không thể thực hiện nhận dạng giọng nói hoặc tách lời thoại trên video không có tiếng."
            )

        ffmpeg_bin = get_ffmpeg_path()
        args = [
            ffmpeg_bin,
            "-y",
            "-i", video_path,
            "-map", f"0:a:{audio_stream_index}",
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(sample_rate),
            "-ac", str(channels),
            output_wav_path
        ]

        logger.info(f"Extracting audio from {video_path} to {output_wav_path}...")
        try:
            run_ffmpeg_process(args, on_progress=on_progress, cancel_event=cancel_event)
            if not os.path.exists(output_wav_path) or os.path.getsize(output_wav_path) == 0:
                raise AudioExtractionError("Tệp âm thanh trích xuất không tồn tại hoặc rỗng.")
            logger.info("Audio extraction completed successfully.")
            return output_wav_path
        except Exception as e:
            if cancel_event and cancel_event.is_set():
                raise
            raise AudioExtractionError(f"Trích xuất âm thanh thất bại: {e}")

