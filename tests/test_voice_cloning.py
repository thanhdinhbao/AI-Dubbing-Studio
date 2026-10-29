import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.providers.vieneu_tts_provider import (
    VieNeuTTSProvider,
    load_saved_cloned_voices,
    save_cloned_voices_meta
)


def test_cloned_voices_meta_persistence():
    with tempfile.TemporaryDirectory() as tmp_dir:
        fake_meta_file = Path(tmp_dir) / "cloned_voices.json"
        dummy_audio = Path(tmp_dir) / "sample.wav"
        dummy_audio.write_bytes(b"RIFF dummy wav data")

        voices = [
            {"name": "Giọng Thử Nghiệm", "audio_path": str(dummy_audio), "created_at": "12345"}
        ]

        with patch("app.providers.vieneu_tts_provider._get_cloned_voices_meta_file", return_value=fake_meta_file):
            save_cloned_voices_meta(voices)
            loaded = load_saved_cloned_voices()
            assert len(loaded) == 1
            assert loaded[0]["name"] == "Giọng Thử Nghiệm"


def test_register_and_get_cloned_voices():
    with tempfile.TemporaryDirectory() as tmp_dir:
        fake_meta_file = Path(tmp_dir) / "cloned_voices.json"
        fake_cloned_dir = Path(tmp_dir) / "cloned_voices"
        fake_cloned_dir.mkdir(parents=True, exist_ok=True)

        source_sample = Path(tmp_dir) / "my_mic_record.wav"
        source_sample.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")

        provider = VieNeuTTSProvider()
        mock_engine = MagicMock()

        def fake_ffmpeg(cmd, **kwargs):
            target = Path(cmd[-1])
            target.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")

        with patch("app.providers.vieneu_tts_provider._get_cloned_voices_meta_file", return_value=fake_meta_file), \
             patch("app.providers.vieneu_tts_provider.get_default_cloned_voices_dir", return_value=fake_cloned_dir), \
             patch.object(provider, "_get_engine", return_value=mock_engine), \
             patch("app.providers.vieneu_tts_provider.run_ffmpeg_process", side_effect=fake_ffmpeg):

            # Register
            entry = provider.register_cloned_voice(name="MC Nam Anh", source_audio_path=source_sample, denoise=True)
            assert entry["name"] == "MC Nam Anh"
            assert mock_engine.add_voice.called

            # Check in get_voices
            all_voices = provider.get_voices()
            cloned_voices = [v for v in all_voices if v.get("is_cloned")]
            assert len(cloned_voices) == 1
            assert cloned_voices[0]["id"] == "MC Nam Anh"
            assert "MC Nam Anh" in cloned_voices[0]["name"]

            # Remove
            removed = provider.remove_cloned_voice("MC Nam Anh")
            assert removed is True
            assert mock_engine.remove_voice.called

            # Check after removal
            all_voices_after = provider.get_voices()
            cloned_after = [v for v in all_voices_after if v.get("is_cloned")]
            assert len(cloned_after) == 0
