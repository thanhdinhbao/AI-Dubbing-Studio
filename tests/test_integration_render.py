import os
import shutil
import tempfile
import pytest
from pathlib import Path

from app.models import DialogueSegment
from app.services.timeline_engine import TimelineEngine
from app.services.audio_mixer import AudioMixerService
from app.services.video_renderer import VideoRendererService
from app.services.media_probe import MediaProbeService
from app.services.media_validator import MediaValidatorService
from app.utils.ffmpeg_utils import get_ffmpeg_path, run_ffmpeg_process
from app.utils.audio_utils import create_silence_wav
from app.constants import TimelineMode


@pytest.fixture(scope="module")
def sample_media_workspace():
    """Create a temporary workspace with synthetic test video and audio."""
    temp_dir = tempfile.mkdtemp(prefix="dubbing_test_")
    ffmpeg_bin = get_ffmpeg_path()

    source_video = os.path.join(temp_dir, "source_video.mp4")
    # Generate 5-second test video: 640x360 30fps with 440Hz test audio tone
    gen_cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=5:size=640x360:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        source_video
    ]
    run_ffmpeg_process(gen_cmd)

    # Generate synthetic TTS audio clips
    # TTS 1: 2.5s duration (original was 1.5s -> +1.0s expansion)
    tts1_path = os.path.join(temp_dir, "tts1.wav")
    gen_tts1 = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "sine=frequency=880:duration=2.5",
        "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le",
        tts1_path
    ]
    run_ffmpeg_process(gen_tts1)

    # TTS 2: 1.0s duration
    tts2_path = os.path.join(temp_dir, "tts2.wav")
    gen_tts2 = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "sine=frequency=660:duration=1.0",
        "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le",
        tts2_path
    ]
    run_ffmpeg_process(gen_tts2)

    yield {
        "dir": temp_dir,
        "source_video": source_video,
        "tts1": tts1_path,
        "tts2": tts2_path,
    }

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_mandatory_4_and_5_real_render_pipeline(sample_media_workspace):
    """Mandatory Tests 4 & 5:
    Full real render execution using FFmpeg and FFprobe:
    - Source video duration: 5.0s
    - Dialogue 1: [1.0s, 2.5s] (source dur 1.5s), TTS dur 2.5s (longer by 1.0s)
    - Dialogue 2: [3.5s, 4.5s] (source dur 1.0s), TTS dur 1.0s
    - Expected output duration: 5.0 + 1.0 = 6.0s
    - Mix audio, render video with freeze-frame padding, and probe resulting file.
    """
    ws = sample_media_workspace
    source_video = ws["source_video"]
    tts1 = ws["tts1"]
    tts2 = ws["tts2"]

    # 1. Probe source video
    info = MediaProbeService.probe_media(source_video)
    assert abs(info.duration - 5.0) < 0.2
    assert info.has_video is True
    assert info.has_audio is True

    # 2. Build dynamic timeline
    dlgs = [
        DialogueSegment(id="d1", start=1.0, end=2.5, source_text="Sentence 1", target_text="Câu một", tts_duration=2.5, tts_audio_path=tts1),
        DialogueSegment(id="d2", start=3.5, end=4.5, source_text="Sentence 2", target_text="Câu hai", tts_duration=1.0, tts_audio_path=tts2),
    ]

    engine = TimelineEngine(mode=TimelineMode.DYNAMIC_DURATION)
    timeline = engine.build_timeline(source_duration=info.duration, dialogues=dlgs)
    output_dur = engine.calculate_output_duration(timeline)

    # Expected: 5.0s + 1.0s delta = 6.0s
    assert abs(output_dur - 6.0) < 0.2

    # 3. Audio Mixing with Ducking
    mixed_wav = os.path.join(ws["dir"], "final_mix.wav")
    mixer = AudioMixerService(bg_volume=0.3, tts_gain=1.0, ducking_reduction=0.2)
    mixer.mix_timeline_audio(
        timeline=timeline,
        output_duration=output_dur,
        output_wav_path=mixed_wav,
        background_wav_path=source_video  # Using original audio as background track
    )

    assert os.path.exists(mixed_wav)
    assert os.path.getsize(mixed_wav) > 0

    # 4. Video Rendering
    output_video = os.path.join(ws["dir"], "rendered_output.mp4")
    renderer = VideoRendererService(video_codec="libx264", audio_codec="aac", crf=22, preset="ultrafast")
    renderer.render(
        source_video_path=source_video,
        mixed_audio_path=mixed_wav,
        timeline=timeline,
        output_video_path=output_video
    )

    # 5. Output Verification with FFprobe
    assert os.path.exists(output_video)
    valid, report = MediaValidatorService.validate_rendered_output(output_video, expected_duration=output_dur, duration_tolerance_sec=0.5)
    assert valid is True
    assert report["valid"] is True
    assert abs(report["duration"] - 6.0) < 0.5
    assert report["file_size_mb"] > 0.0

