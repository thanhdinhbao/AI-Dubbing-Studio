import os
import json
import shutil
import threading
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.providers.base import BaseTTSProvider
from app.constants import VIENEU_VIETNAMESE_VOICES
from app.exceptions import TTSError
from app.utils.paths import get_default_cloned_voices_dir, sanitize_filename
from app.utils.audio_utils import get_audio_duration
from app.utils.ffmpeg_utils import get_ffmpeg_path, run_ffmpeg_process

logger = logging.getLogger("AIDubbingStudio.VieNeuTTS")

_engine_lock = threading.Lock()
_engine_cache: Dict[str, Any] = {}


def _get_cloned_voices_meta_file() -> Path:
    return get_default_cloned_voices_dir() / "cloned_voices.json"


def load_saved_cloned_voices() -> List[Dict[str, Any]]:
    """Read saved custom cloned voices metadata."""
    meta_file = _get_cloned_voices_meta_file()
    if not meta_file.exists():
        return []
    try:
        data = json.loads(meta_file.read_text(encoding="utf-8"))
        if isinstance(data, list):
            # Verify audio files exist
            return [v for v in data if os.path.exists(v.get("audio_path", ""))]
    except Exception as e:
        logger.warning(f"Failed to read cloned voices meta: {e}")
    return []


def save_cloned_voices_meta(voices: List[Dict[str, Any]]):
    """Persist custom cloned voices metadata to disk."""
    meta_file = _get_cloned_voices_meta_file()
    try:
        meta_file.write_text(json.dumps(voices, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to save cloned voices meta: {e}")


class VieNeuTTSProvider(BaseTTSProvider):
    """Text-to-Speech provider powered directly by the official VieNeu SDK (v3 Turbo / v3 Nano).

    Supports:
    - 25+ built-in Vietnamese regional voices
    - Instant voice cloning from 3-8s audio references (recorded or imported)
    - Runs on-device (ONNX on CPU, PyTorch on GPU) completely offline
    """

    def __init__(
        self,
        mode: str = "v3turbo",
        backend: str = "auto",
        precision: str = "fp32"
    ):
        self.mode = mode
        self.backend = backend
        self.precision = precision
        self._engine = None

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "supports_pitch": False,
            "supports_rate": True,
            "supports_volume": False,
            "supports_cloning": True,
            "is_offline": True,
            "description": "VieNeu-TTS SDK v3 Turbo (48 kHz - On-device AI Voice & Voice Cloning)"
        }

    def get_voices(self) -> List[Dict[str, Any]]:
        """Return list of preset Vietnamese voices plus user cloned voices."""
        cloned = load_saved_cloned_voices()
        result: List[Dict[str, Any]] = []

        # Put user cloned voices first with badge
        for cv in cloned:
            result.append({
                "id": cv["name"],
                "name": f"✨ [Giọng Clone] {cv['name']}",
                "gender": "Custom",
                "region": "Nhân bản giọng",
                "is_cloned": True,
                "audio_path": cv["audio_path"]
            })

        # Append default preset voices
        result.extend(VIENEU_VIETNAMESE_VOICES)
        return result

    def register_cloned_voice(
        self,
        name: str,
        source_audio_path: str | Path,
        denoise: bool = True
    ) -> Dict[str, Any]:
        """Enroll a new cloned voice using a 3-8s audio sample.

        Converts source audio to clean WAV in cloned_voices dir and registers it with VieNeu.
        """
        name = str(name).strip()
        if not name:
            raise TTSError("Tên giọng clone không được để trống.")

        source_path = Path(source_audio_path)
        if not source_path.exists() or source_path.stat().st_size == 0:
            raise TTSError(f"Tệp âm thanh mẫu không tồn tại: {source_path}")

        # Store standardized sample in cloned_voices directory
        cloned_dir = get_default_cloned_voices_dir()
        safe_name = sanitize_filename(name)
        target_wav = cloned_dir / f"{safe_name}.wav"

        # Standardize audio to 44100Hz mono WAV via FFmpeg
        ffmpeg_bin = get_ffmpeg_path()
        conv_cmd = [
            ffmpeg_bin, "-y",
            "-i", str(source_path),
            "-ar", "44100",
            "-ac", "1",
            "-t", "10",  # Cap reference at 10s max (VieNeu recommends 3-8s)
            str(target_wav)
        ]
        try:
            run_ffmpeg_process(conv_cmd)
        except Exception as e:
            raise TTSError(f"Không thể chuẩn hóa tệp âm thanh mẫu cho giọng clone: {e}")

        # Enroll into VieNeu engine
        engine = self._get_engine()
        try:
            logger.info(f"Đang trích xuất đặc trưng và đăng ký giọng clone '{name}' với VieNeu...")
            engine.add_voice(name, str(target_wav), denoise=denoise, save=False)
        except Exception as e_add:
            raise TTSError(f"VieNeu không thể nhân bản giọng nói từ mẫu âm thanh: {e_add}")

        # Persist metadata
        saved = load_saved_cloned_voices()
        # Remove existing if same name
        saved = [v for v in saved if v["name"] != name]
        created_time = str(target_wav.stat().st_mtime) if target_wav.exists() else str(time.time())
        voice_entry = {
            "name": name,
            "audio_path": str(target_wav),
            "denoise": denoise,
            "created_at": created_time
        }
        saved.insert(0, voice_entry)
        save_cloned_voices_meta(saved)
        logger.info(f"Đã đăng ký và lưu giọng clone '{name}' thành công.")
        return voice_entry

    def remove_cloned_voice(self, name: str) -> bool:
        """Remove a registered cloned voice and its associated files."""
        saved = load_saved_cloned_voices()
        removed_entry = None
        new_list = []
        for v in saved:
            if v["name"] == name:
                removed_entry = v
            else:
                new_list.append(v)

        if not removed_entry:
            return False

        save_cloned_voices_meta(new_list)

        # Remove audio file
        try:
            p = Path(removed_entry.get("audio_path", ""))
            if p.exists():
                p.unlink()
        except Exception:
            pass

        # Remove from running engine if loaded
        try:
            engine = self._get_engine()
            engine.remove_voice(name, save=False)
        except Exception:
            pass

        logger.info(f"Đã xóa giọng clone '{name}'.")
        return True

    def _get_engine(self):
        """Retrieve or initialize the cached VieNeu engine instance thread-safely."""
        cache_key = f"{self.mode}_{self.backend}_{self.precision}"
        with _engine_lock:
            if cache_key in _engine_cache:
                return _engine_cache[cache_key]

            try:
                from vieneu import Vieneu
            except ImportError as imp_err:
                raise TTSError(
                    f"Thư viện SDK 'vieneu' chưa được cài đặt trong môi trường: {imp_err}. "
                    f"Vui lòng chạy: pip install vieneu"
                )

            logger.info(f"Khởi tạo VieNeu SDK Engine (mode={self.mode}, backend={self.backend})...")
            try:
                # First attempt with requested backend
                engine = Vieneu(
                    mode=self.mode,
                    backend=self.backend,
                    precision=self.precision
                )
            except Exception as e_init:
                logger.warning(f"Khởi tạo VieNeu với backend '{self.backend}' gặp cảnh báo ({e_init}). Thử fallback sang ONNX/CPU...")
                try:
                    engine = Vieneu(
                        mode=self.mode,
                        backend="onnx",
                        precision="fp32"
                    )
                except Exception as e_fallback:
                    raise TTSError(f"Không thể khởi tạo mô hình VieNeu-TTS: {e_fallback}")

            # Register any previously saved cloned voices into the engine
            saved_clones = load_saved_cloned_voices()
            for cv in saved_clones:
                c_name = cv.get("name")
                c_path = cv.get("audio_path")
                if c_name and c_path and os.path.exists(c_path):
                    try:
                        engine.add_voice(c_name, c_path, denoise=False, save=False)
                        logger.info(f"Đã nạp sẵn giọng clone: '{c_name}'")
                    except Exception as e_reg:
                        logger.warning(f"Không thể nạp giọng clone '{c_name}': {e_reg}")

            _engine_cache[cache_key] = engine
            logger.info("VieNeu SDK Engine đã sẵn sàng.")
            return engine

    def synthesize(
        self,
        text: str,
        voice_id: str = "Hải Đăng",
        output_path: str | Path = "",
        options: Optional[Dict[str, Any]] = None
    ) -> float:
        """Synthesize text into WAV audio using VieNeu SDK directly on-device.

        Supports both preset voices and custom cloned voice names.
        """
        text_clean = text.strip()
        if not text_clean:
            raise TTSError("Văn bản cần đọc không được để trống.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        engine = self._get_engine()

        # Map legacy voice names or aliases to official 25 VieNeu presets
        resolved_voice = voice_id
        alias_map = {
            "Minh Quân Pro": "Hải Đăng",
            "Minh Quân": "Hải Đăng",
            "Anh Khôi": "Thiện Minh",
            "Mạnh Dũng": "Quốc Tuấn",
            "Bảo Long": "Hải Đăng",
            "Nhật Phong": "Phạm Tuyên",
            "Bích Ngọc": "Trúc Ly",
            "Trung Dũng": "Quang Sơn",
            "Thành Sen": "Ngọc Trân",
            "Ngọc Lan": "Thùy Dung",
            "Trâm Anh": "Mỹ Duyên",
            "Kiều Linh": "Thục Đoan",
            "Adam vui": "Adam"
        }
        if resolved_voice in alias_map:
            resolved_voice = alias_map[resolved_voice]

        try:
            # Perform inference on device
            logger.debug(f"VieNeu SDK inferring text: '{text_clean[:40]}...' with voice '{resolved_voice}'")
            audio = engine.infer(text_clean, voice=resolved_voice)

            if audio is None or len(audio) == 0:
                raise TTSError(f"VieNeu không sinh được âm thanh cho câu: '{text_clean[:30]}'")

            # Save generated waveform directly using engine or soundfile
            engine.save(audio, str(output_path))

            # Verify file exists and measure duration
            if not output_path.exists() or output_path.stat().st_size == 0:
                raise TTSError(f"Tệp âm thanh VieNeu đầu ra rỗng: {output_path}")

            sample_rate = getattr(engine, "sample_rate", 48000)
            duration = round(len(audio) / sample_rate, 3)
            if duration <= 0:
                duration = get_audio_duration(output_path)

            logger.info(f"VieNeu synthesized '{resolved_voice}' ({duration:.2f}s) -> {output_path.name}")
            return duration

        except Exception as e:
            if isinstance(e, TTSError):
                raise
            raise TTSError(f"Lỗi trong quá trình tạo giọng đọc VieNeu SDK: {e}")
