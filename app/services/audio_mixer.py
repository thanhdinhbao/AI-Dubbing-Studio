import os
import wave
import logging
import threading
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
import numpy as np

from app.models import DialogueSegment, TimelineSegment
from app.exceptions import AudioMixerError
from app.utils.ffmpeg_utils import get_ffmpeg_path, run_ffmpeg_process
from app.utils.audio_utils import get_audio_duration

logger = logging.getLogger("AIDubbingStudio.AudioMixer")


class AudioMixerService:
    """Mixes dialogue TTS audio onto the dynamic timeline with background music and automatic ducking."""

    def __init__(
        self,
        sample_rate: int = 44100,
        channels: int = 2,
        bg_volume: float = 0.25,
        tts_gain: float = 1.0,
        ducking_reduction: float = 0.2,  # Multiplier when speech is active (e.g. 20% volume)
        ducking_fade: float = 0.3  # Fade ramp in seconds
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.bg_volume = bg_volume
        self.tts_gain = tts_gain
        self.ducking_reduction = ducking_reduction
        self.ducking_fade = ducking_fade

    def _convert_to_pcm_wav(self, input_path: str, output_path: str):
        """Ensure audio is standard 44.1kHz 16-bit stereo PCM WAV."""
        ffmpeg_bin = get_ffmpeg_path()
        cmd = [
            ffmpeg_bin, "-y",
            "-i", input_path,
            "-ar", str(self.sample_rate),
            "-ac", str(self.channels),
            "-c:a", "pcm_s16le",
            output_path
        ]
        run_ffmpeg_process(cmd)

    def _read_wav_samples(self, wav_path: str) -> np.ndarray:
        """Read standard 16-bit PCM WAV into normalized float32 numpy array [-1.0, 1.0]."""
        with wave.open(wav_path, "rb") as wf:
            n_frames = wf.getnframes()
            data = wf.readframes(n_frames)
            raw = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            # Reshape to (frames, channels)
            channels = wf.getnchannels()
            if channels == 1 and self.channels == 2:
                raw = np.repeat(raw[:, np.newaxis], 2, axis=1)
            elif channels == 2:
                raw = raw.reshape(-1, 2)
            return raw / 32768.0

    def mix_timeline_audio(
        self,
        timeline: List[TimelineSegment],
        output_duration: float,
        output_wav_path: str | Path,
        background_wav_path: Optional[str | Path] = None,
        on_progress: Optional[Callable[[int, str], None]] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> str:
        """Mix all dialogue TTS audio and background music into a master audio file matching output_duration."""
        output_wav_path = Path(output_wav_path)
        output_wav_path.parent.mkdir(parents=True, exist_ok=True)

        total_samples = int(round(output_duration * self.sample_rate))
        if total_samples <= 0:
            total_samples = self.sample_rate  # At least 1 second

        logger.info(
            f"Mixing audio: output duration = {output_duration:.2f}s ({total_samples} samples) "
            f"at {self.sample_rate}Hz stereo..."
        )

        # 1. Prepare empty speech master track
        speech_track = np.zeros((total_samples, self.channels), dtype=np.float32)

        # Keep track of active dialogue intervals for ducking
        speech_intervals = []

        total_segs = len(timeline)
        for idx, seg in enumerate(timeline):
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Hòa âm âm thanh đã bị hủy.")

            if seg.tts_audio_path and os.path.exists(seg.tts_audio_path):
                # Ensure PCM wav
                temp_wav = seg.tts_audio_path
                if not seg.tts_audio_path.lower().endswith(".wav"):
                    temp_wav = str(Path(seg.tts_audio_path).with_suffix(".pcm.wav"))
                    self._convert_to_pcm_wav(seg.tts_audio_path, temp_wav)

                try:
                    samples = self._read_wav_samples(temp_wav)
                    start_idx = int(round(seg.output_start * self.sample_rate))
                    end_idx = min(start_idx + len(samples), total_samples)
                    actual_len = end_idx - start_idx
                    if actual_len > 0:
                        speech_track[start_idx:end_idx] += samples[:actual_len] * self.tts_gain
                        speech_intervals.append((seg.output_start, seg.output_start + (actual_len / self.sample_rate)))
                except Exception as e:
                    logger.warning(f"Could not read dialogue audio {seg.tts_audio_path}: {e}")

        # 2. Process background music / instrumental track if provided
        bg_track = np.zeros((total_samples, self.channels), dtype=np.float32)

        if background_wav_path and os.path.exists(str(background_wav_path)):
            if on_progress:
                on_progress(50, "Đang xử lý nhạc nền và ducking...")

            temp_bg_wav = str(output_wav_path.parent / "temp_bg_pcm.wav")
            self._convert_to_pcm_wav(str(background_wav_path), temp_bg_wav)
            bg_samples = self._read_wav_samples(temp_bg_wav)

            # If output is longer than source bg, loop background with padding
            bg_len = len(bg_samples)
            if bg_len > 0:
                copied = 0
                while copied < total_samples:
                    take = min(bg_len, total_samples - copied)
                    bg_track[copied : copied + take] = bg_samples[:take]
                    copied += take

            # Apply ducking envelope
            ducking_env = np.ones(total_samples, dtype=np.float32)
            fade_samples = int(self.ducking_fade * self.sample_rate)

            for sp_start, sp_end in speech_intervals:
                s_idx = max(0, int(sp_start * self.sample_rate) - fade_samples)
                e_idx = min(total_samples, int(sp_end * self.sample_rate) + fade_samples)

                # Linear ramp down to ducking level
                sp_center_start = int(sp_start * self.sample_rate)
                sp_center_end = int(sp_end * self.sample_rate)

                # Region during speech
                ducking_env[max(0, sp_center_start) : min(total_samples, sp_center_end)] = self.ducking_reduction

                # Fade down
                if sp_center_start > s_idx:
                    ramp_down = np.linspace(1.0, self.ducking_reduction, sp_center_start - s_idx, dtype=np.float32)
                    ducking_env[s_idx:sp_center_start] = np.minimum(ducking_env[s_idx:sp_center_start], ramp_down)

                # Fade up
                if e_idx > sp_center_end:
                    ramp_up = np.linspace(self.ducking_reduction, 1.0, e_idx - sp_center_end, dtype=np.float32)
                    ducking_env[sp_center_end:e_idx] = np.minimum(ducking_env[sp_center_end:e_idx], ramp_up)

            bg_track = bg_track * ducking_env[:, np.newaxis] * self.bg_volume

            if os.path.exists(temp_bg_wav):
                try:
                    os.remove(temp_bg_wav)
                except Exception:
                    pass

        # 3. Master mix & soft limiter
        master = speech_track + bg_track
        # Soft-clip limit to avoid digital harsh clipping
        master = np.tanh(master)
        # Convert to 16-bit integer PCM
        master_int16 = (master * 32767.0).astype(np.int16)

        # Write output WAV
        with wave.open(str(output_wav_path), "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(master_int16.tobytes())

        logger.info(f"Master audio mix written to {output_wav_path}")
        if on_progress:
            on_progress(100, "Hòa âm hoàn tất.")
        return str(output_wav_path)

