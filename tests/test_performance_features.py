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
        provider = MockSlowTTSProvider(delay=0.04)
        service = SpeechSynthesisService(provider=provider)

        start_time = time.time()
        results = service.synthesize_dialogues(
            dialogues=dialogues,
            output_dir=tmp_dir,
            voice_id="v1",
            max_workers=5
        )
        duration = time.time() - start_time

        # 10 items * 0.04s = 0.40s sequentially. With 5 threads, it should take ~0.08s - 0.20s
        assert len(results) == 10
        assert duration < 0.35, f"Expected multi-threaded execution to be fast, but took {duration:.3f}s"
        # Ensure order is preserved
        for i, dlg in enumerate(results):
            assert dlg.id == f"dlg_{i}"
            assert dlg.tts_duration == 1.5


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
