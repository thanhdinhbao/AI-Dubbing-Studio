import os
import wave
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

from app.utils.ffmpeg_utils import get_ffprobe_path, run_ffmpeg_process, get_ffmpeg_path


def calculate_tts_hash(text: str, voice_id: str, provider_id: str, options: Optional[Dict[str, Any]] = None) -> str:
    """Calculate unique hash string for a TTS sentence and synthesis parameters for caching."""
    options_str = json.dumps(options or {}, sort_keys=True)
    raw = f"{provider_id}::{voice_id}::{text.strip()}::{options_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def get_audio_duration(file_path: str | Path) -> float:
    """Accurately measure the duration of an audio file in seconds.
    Tries wave module first for uncompressed WAV, falls back to ffprobe.
    """
    file_path = str(file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file does not exist: {file_path}")

    # If it's a WAV file, try standard library wave module first
    if file_path.lower().endswith(".wav"):
        try:
            with wave.open(file_path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0 and frames > 0:
                    return round(frames / float(rate), 4)
        except Exception:
            pass

    # Use ffprobe for universal audio formats
    ffprobe_bin = get_ffprobe_path()
    args = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    res = run_ffmpeg_process(args)
    duration_str = res.stdout_text.strip()
    try:
        return round(float(duration_str), 4)
    except ValueError:
        raise ValueError(f"Could not parse audio duration from ffprobe: '{duration_str}'")


def create_silence_wav(output_path: str | Path, duration: float, sample_rate: int = 44100, channels: int = 2):
    """Generate a silence WAV file of exact duration in seconds."""
    output_path = str(output_path)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    ffmpeg_bin = get_ffmpeg_path()
    args = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi",
        "-i", f"anullsrc=r={sample_rate}:cl={'stereo' if channels == 2 else 'mono'}",
        "-t", f"{max(duration, 0.001):.4f}",
        "-c:a", "pcm_s16le",
        output_path
    ]
    run_ffmpeg_process(args)


def patch_pyav_metadata_errors() -> None:
    """Patch PyAV's av.open to safely ignore 'metadata_errors' keyword argument.

    In PyAV >= 14, 'metadata_errors' was removed, but faster-whisper 1.x still passes
    `av.open(..., metadata_errors='ignore')`. This compatibility patch intercepts
    and removes the argument so faster-whisper transcribes audio without crashing.
    """
    try:
        import av
        if hasattr(av, "open") and not getattr(av, "_patched_metadata_errors", False):
            orig_open = av.open

            def safe_av_open(*args, **kwargs):
                kwargs.pop("metadata_errors", None)
                return orig_open(*args, **kwargs)

            av.open = safe_av_open
            setattr(av, "_patched_metadata_errors", True)
    except Exception:
        pass


