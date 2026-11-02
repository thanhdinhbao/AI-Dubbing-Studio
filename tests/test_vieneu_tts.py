import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from app.providers.vieneu_tts_provider import VieNeuTTSProvider
from app.constants import VIENEU_VIETNAMESE_VOICES


def test_vieneu_voices_list():
    provider = VieNeuTTSProvider(mode="v3turbo")
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
    assert "Adam bựa" in voice_ids


def test_vieneu_nano_voices_list():
    provider = VieNeuTTSProvider(mode="v3nano")
    voices = provider.get_voices()
    assert len(voices) >= 12
    voice_ids = [v["id"] for v in voices]
    assert "Adam" in voice_ids
    assert "Minh Quân" in voice_ids
    assert "Trúc Ly" in voice_ids
    assert "Mai Anh" in voice_ids
    # "Adam bựa" should not be in nano preset list
    assert "Adam bựa" not in voice_ids


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
            assert mock_engine.infer.call_args[1]["voice"] == "Hải Đăng"


def test_vieneu_nano_synthesize_voice_resolution():
    import tempfile
    from pathlib import Path

    provider = VieNeuTTSProvider(mode="v3nano")
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_file = Path(tmp_dir) / "mock_nano.wav"
        mock_engine = MagicMock()
        mock_engine.sample_rate = 24000
        mock_engine.infer.return_value = np.zeros(24000, dtype=np.float32)

        def mock_save(audio, p):
            with open(p, "wb") as f:
                f.write(b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")

        mock_engine.save.side_effect = mock_save

        with patch.object(provider, "_get_engine", return_value=mock_engine):
            # Test that "Adam bựa" is mapped to "Adam" for nano
            dur = provider.synthesize("Xin chào", voice_id="Adam bựa", output_path=out_file)
            assert dur == 1.0
            assert mock_engine.infer.call_args[1]["voice"] == "Adam"

            # Test that unknown Turbo voice falls back to safe Nano default
            dur2 = provider.synthesize("Xin chào", voice_id="Ngọc Huyền", output_path=out_file)
            assert mock_engine.infer.call_args[1]["voice"] == "Trúc Ly"

            # Test that completely unknown voice falls back to "Minh Quân"
            dur3 = provider.synthesize("Xin chào", voice_id="UnknownVoice123", output_path=out_file)
            assert mock_engine.infer.call_args[1]["voice"] == "Minh Quân"


def test_vieneu_engine_pool_parallel():
    from app.providers.vieneu_tts_provider import VieNeuEnginePool
    pool = VieNeuEnginePool(mode="mock", backend="onnx", precision="fp32", max_size=2)
    # Mock creating engine
    m1, m2 = MagicMock(), MagicMock()
    pool._create_engine = MagicMock(side_effect=[m1, m2])

    eng1 = pool.acquire()
    eng2 = pool.acquire()
    assert eng1 is m1
    assert eng2 is m2
    assert pool._created_count == 2

    # Release eng1
    pool.release(eng1)
    eng3 = pool.acquire()
    assert eng3 is m1
    pool.release(eng2)
    pool.release(eng3)


