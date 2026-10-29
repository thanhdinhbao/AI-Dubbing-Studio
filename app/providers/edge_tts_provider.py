import os
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.providers.base import BaseTTSProvider
from app.constants import EDGE_TTS_VIETNAMESE_VOICES
from app.exceptions import TTSError
from app.utils.audio_utils import get_audio_duration
from app.utils.ffmpeg_utils import get_ffmpeg_path, run_ffmpeg_process

logger = logging.getLogger("AIDubbingStudio.EdgeTTS")


class EdgeTTSProvider(BaseTTSProvider):
    """High quality Text-to-Speech provider powered by Edge TTS."""

    def __init__(self):
        self.cached_voices: Optional[List[Dict[str, Any]]] = None

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "supports_pitch": True,
            "supports_rate": True,
            "supports_volume": True,
            "is_offline": False,
            "description": "Microsoft Edge TTS (Chất lượng cao, phát âm tiếng Việt tự nhiên)"
        }

    def get_voices(self) -> List[Dict[str, Any]]:
        """Return Vietnamese voices supported by Edge TTS."""
        return list(EDGE_TTS_VIETNAMESE_VOICES)

    def synthesize(
        self,
        text: str,
        voice_id: str = "vi-VN-HoaiMyNeural",
        output_path: str | Path = "",
        options: Optional[Dict[str, Any]] = None
    ) -> float:
        """Synthesize text into WAV or MP3 audio using edge_tts.
        Returns measured duration in seconds.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        opts = options or {}
        rate = opts.get("rate", "+0%")
        pitch = opts.get("pitch", "+0Hz")
        volume = opts.get("volume", "+0%")

        # Edge-tts generates mp3 natively. If target is .wav, synthesize to temp .mp3 then convert.
        is_wav = output_path.suffix.lower() == ".wav"
        temp_mp3 = output_path.with_suffix(".mp3") if is_wav else output_path

        try:
            import edge_tts
        except ImportError:
            raise TTSError("Thư viện 'edge-tts' chưa được cài đặt.")

        async def _run_edge_tts():
            communicate = edge_tts.Communicate(
                text=text.strip(),
                voice=voice_id,
                rate=rate,
                pitch=pitch,
                volume=volume
            )
            await communicate.save(str(temp_mp3))

        try:
            # Create a dedicated, isolated event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_run_edge_tts())
            finally:
                try:
                    # Clean up pending tasks and async generators to avoid IOCP crash
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception:
                    pass
                loop.close()

            # Convert to uncompressed WAV if requested
            if is_wav:
                # Fast in-process conversion using PyAV
                converted = False
                try:
                    import av
                    with av.open(str(temp_mp3)) as in_container:
                        if in_container.streams.audio:
                            in_stream = in_container.streams.audio[0]
                            with av.open(str(output_path), "w", format="wav") as out_container:
                                out_stream = out_container.add_stream("pcm_s16le", rate=44100, layout="stereo")
                                for frame in in_container.decode(in_stream):
                                    for packet in out_stream.encode(frame):
                                        out_container.mux(packet)
                                for packet in out_stream.encode(None):
                                    out_container.mux(packet)
                            converted = True
                except Exception as av_err:
                    logger.debug(f"PyAV conversion failed ({av_err}), falling back to FFmpeg...")

                if not converted:
                    ffmpeg_bin = get_ffmpeg_path()
                    conv_args = [
                        ffmpeg_bin, "-y",
                        "-i", str(temp_mp3),
                        "-ar", "44100",
                        "-ac", "2",
                        "-c:a", "pcm_s16le",
                        str(output_path)
                    ]
                    run_ffmpeg_process(conv_args)

                if temp_mp3.exists() and temp_mp3 != output_path:
                    try:
                        temp_mp3.unlink()
                    except Exception:
                        pass
                        pass

            # Measure real duration
            actual_duration = get_audio_duration(output_path)
            logger.debug(f"Synthesized Edge TTS audio for '{text[:20]}...' -> {actual_duration:.2f}s")
            return actual_duration

        except Exception as e:
            raise TTSError(f"Lỗi khi tạo giọng đọc Edge TTS: {e}")

