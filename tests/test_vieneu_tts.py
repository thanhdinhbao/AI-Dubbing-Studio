import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from app.providers.vieneu_tts_provider import VieNeuTTSProvider
from app.constants import VIENEU_VIETNAMESE_VOICES


def test_vieneu_voices_list():
    provider = VieNeuTTSProvider()
    voices = provider.get_voices()
    assert len(voices) >= 25
    voice_ids = [v["id"] for v in voices]
    assert "Hải Đăng" in voice_ids
    assert "Mai Anh" in voice_ids
    assert "Trúc Ly" in voice_ids
    assert "Thiện Minh" in voice_ids
    assert "Quang Sơn" in voice_ids
    assert "Ngọc Trân" in voice_ids
    assert "Thùy Dung" in voice_ids
    assert "Quốc Tuấn" in voice_ids


def test_vieneu_capabilities():
    provider = VieNeuTTSProvider()
    caps = provider.get_capabilities()
    assert caps["is_offline"] is True
    assert "VieNeu" in caps["description"]


def test_vieneu_synthesize_mock():
    import tempfile
    from pathlib import Path

    provider = VieNeuTTSProvider()
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_file = Path(tmp_dir) / "mock_test.wav"

        # Mock engine instance
        mock_engine = MagicMock()
        mock_engine.sample_rate = 48000
        # 1 second of audio at 48000 Hz
        dummy_audio = np.zeros(48000, dtype=np.float32)
        mock_engine.infer.return_value = dummy_audio

        def mock_save(audio, p):
            with open(p, "wb") as f:
                f.write(b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")

        mock_engine.save.side_effect = mock_save

        with patch.object(provider, "_get_engine", return_value=mock_engine):
            dur = provider.synthesize("Xin chào các bạn", voice_id="Minh Quân Pro", output_path=out_file)
            assert dur == 1.0
            assert out_file.exists()


