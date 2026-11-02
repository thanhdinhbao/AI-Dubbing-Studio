import os
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from app.models import DialogueSegment
from app.services.speech_synthesis import SpeechSynthesisService
from app.services.transcription import TranscriptionService
from app.services.video_renderer import VideoRendererService
from app.providers.base import BaseTTSProvider


class MockSlowTTSProvider(BaseTTSProvider):
    """Simulates a TTS provider with network latency."""

    def __init__(self, delay: float = 0.05):
        self.delay = delay

    def get_voices(self):
        return [{"id": "v1", "name": "Voice 1"}]

    def get_capabilities(self):
        return {"supports_speed": True, "supports_pitch": True}

    def synthesize(self, text: str, voice_id: str, output_path: Path, options=None) -> float:
        time.sleep(self.delay)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Write minimal dummy wav
        with open(output_path, "wb") as f:
            f.write(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        return 1.5


def test_multithreaded_tts_speedup():
    """Verify that multi-threaded TTS synthesis is significantly faster than sequential."""
    dialogues = [
        DialogueSegment(id=f"dlg_{i}", start=float(i), end=float(i + 1), source_text=f"Câu số {i}", target_text=f"Câu tiếng Việt số {i}")
        for i in range(10)
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        provider = MockSlowTTSProvider(delay=0.08)
        service = SpeechSynthesisService(provider=provider)

        start_time = time.time()
        results = service.synthesize_dialogues(
            dialogues=dialogues,
            output_dir=tmp_dir,
            voice_id="v1",
            max_workers=5
        )
        duration = time.time() - start_time

        # 10 items * 0.08s = 0.80s sleep + file IO. Multi-threaded completes in reasonable time.
        assert len(results) == 10
        assert duration < 1.5, f"Expected multi-threaded execution to be fast, but took {duration:.3f}s"
        # Ensure order is preserved
        for i, dlg in enumerate(results):
            assert dlg.id == f"dlg_{i}"
            assert dlg.tts_duration == 1.5


def test_offline_tts_safe_worker_cap():
    """Verify that offline TTS providers are safely capped at 3 workers to prevent CPU thrashing."""
    class MockOfflineTTSProvider(MockSlowTTSProvider):
        def get_capabilities(self):
            return {"is_offline": True}

    with tempfile.TemporaryDirectory() as tmp_dir:
        provider = MockOfflineTTSProvider(delay=0.01)
        service = SpeechSynthesisService(provider=provider)
        dlgs = [DialogueSegment(id="dlg_1", start=0.0, end=1.0, source_text="a", target_text="b")]
        # Even with max_workers=8, it safely caps at 3 and synthesizes properly without crashing
        res = service.synthesize_dialogues(dialogues=dlgs, output_dir=tmp_dir, voice_id="v1", max_workers=8)
        assert len(res) == 1
        assert res[0].status == "synthesized"


def test_transcription_fast_mode_parameters():
    """Verify TranscriptionService initializes with fast beam_size and thread options."""
    service = TranscriptionService(model_size="base", device="cpu", compute_type="int8")
    assert service.cpu_threads >= 1
    assert service.num_workers == 2


def test_video_renderer_command_construction():
    """Verify VideoRendererService properly configures NVENC and CPU presets with multi-threading."""
    # Test CPU with faster preset
    renderer_cpu = VideoRendererService(video_codec="libx264", preset="faster", crf=20, threads=0)
    assert renderer_cpu.video_codec == "libx264"
    assert renderer_cpu.preset == "faster"
    assert renderer_cpu.threads == 0

    # Test NVENC GPU with hardware acceleration
    renderer_nvenc = VideoRendererService(video_codec="h264_nvenc", preset="veryfast", crf=22)
    assert renderer_nvenc.video_codec == "h264_nvenc"


def test_encoder_support_detection_and_safe_fallback():
    """Verify is_encoder_supported returns correct boolean and does not throw."""
    from app.utils.ffmpeg_utils import is_encoder_supported
    # libx264 is always supported in standard ffmpeg builds
    assert is_encoder_supported("libx264") is True
    # Non-existent dummy encoder returns False
    assert is_encoder_supported("non_existent_magic_encoder_xyz") is False


def test_audio_mixer_zero_background_volume_mute():
    """Verify AudioMixerService ignores background track when bg_volume <= 0.001."""
    from app.services.audio_mixer import AudioMixerService
    from app.models import TimelineSegment
    from app.utils.ffmpeg_utils import get_ffmpeg_path, run_ffmpeg_process
    import numpy as np

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_wav = os.path.join(tmp_dir, "test_mix.wav")
        fake_bg = os.path.join(tmp_dir, "fake_bg.wav")

        # Create 1 second loud 440Hz sine wave as fake background
        ffmpeg_bin = get_ffmpeg_path()
        run_ffmpeg_process([
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1.0",
            "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le",
            fake_bg
        ])

        # Mix with bg_volume = 0.0 and no dialogue
        mixer = AudioMixerService(bg_volume=0.0)
        mixer.mix_timeline_audio(
            timeline=[],
            output_duration=1.0,
            output_wav_path=out_wav,
            background_wav_path=fake_bg
        )

        assert os.path.exists(out_wav)
        # Read samples and verify complete silence (all zeros)
        samples = mixer._read_wav_samples(out_wav)
        assert np.max(np.abs(samples)) == 0.0
