import os
import json
import shutil
import queue
import threading
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.providers.base import BaseTTSProvider
from app.constants import VIENEU_TURBO_VOICES, VIENEU_NANO_VOICES, VIENEU_VIETNAMESE_VOICES
from app.exceptions import TTSError
from app.utils.paths import get_default_cloned_voices_dir, sanitize_filename
from app.utils.audio_utils import get_audio_duration
from app.utils.ffmpeg_utils import get_ffmpeg_path, run_ffmpeg_process

logger = logging.getLogger("AIDubbingStudio.VieNeuTTS")

_gpu_infer_lock = threading.Lock()
_CUDA_SUPPORTED_CACHE: Optional[bool] = None


def is_cuda_supported_for_vieneu() -> bool:
    """Check if current CUDA hardware is compatible with modern PyTorch builds (CC >= 6.0). Cached."""
    global _CUDA_SUPPORTED_CACHE
    if _CUDA_SUPPORTED_CACHE is not None:
        return _CUDA_SUPPORTED_CACHE

    try:
        import torch
        if not torch.cuda.is_available():
            _CUDA_SUPPORTED_CACHE = False
            return False
        cap = torch.cuda.get_device_capability(0)
        # Maxwell CC 5.0 (e.g. GTX 750 Ti) and CC 5.2 are not supported by modern PyTorch CUDA
        if cap[0] < 6:
            logger.info(
                f"Phát hiện GPU NVIDIA ({torch.cuda.get_device_name(0)}, CC {cap[0]}.{cap[1]} < 6.0). "
                "PyTorch CUDA không hỗ trợ kiến trúc này, tự động chuyển VieNeu sang ONNX/CPU."
            )
            _CUDA_SUPPORTED_CACHE = False
            return False
        _CUDA_SUPPORTED_CACHE = True
        return True
    except Exception:
        _CUDA_SUPPORTED_CACHE = False
        return False


def resolve_vieneu_backend(backend: str) -> str:
    """Normalize VieNeu backend to 'onnx' if CUDA is unavailable or GPU architecture is incompatible."""
    if backend == "onnx":
        return "onnx"
    if not is_cuda_supported_for_vieneu():
        return "onnx"
    return backend


def get_vieneu_voices_list(mode: str = "v3turbo") -> List[Dict[str, Any]]:
    """Return list of preset Vietnamese voices plus user cloned voices instantly without initializing engine/CUDA."""
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

    # Append default preset voices based on model mode (Turbo vs Nano)
    if mode == "v3nano":
        result.extend(VIENEU_NANO_VOICES)
    else:
        result.extend(VIENEU_TURBO_VOICES)
    return result


class VieNeuEnginePool:
    """Thread-safe pool of VieNeu engine instances allowing parallel inference
    across multiple worker threads without sharing ONNX sessions.
    """

    def __init__(self, mode: str, backend: str, precision: str, max_size: int = 3):
        self.mode = mode
        self.backend = resolve_vieneu_backend(backend)
        self.precision = precision
        self.max_size = max(1, min(max_size, 3))
        self._pool: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._created_count = 0
        self._instances: List[Any] = []

    def _create_engine(self):
        try:
            from vieneu import Vieneu
        except ImportError as imp_err:
            raise TTSError(
                f"Thư viện SDK 'vieneu' chưa được cài đặt trong môi trường: {imp_err}. "
                f"Vui lòng chạy: pip install vieneu"
            )

        logger.info(
            f"Khởi tạo VieNeu SDK Engine ({self._created_count + 1}/{self.max_size}) "
            f"(mode={self.mode}, backend={self.backend})..."
        )
        try:
            engine = Vieneu(
                mode=self.mode,
                backend=self.backend,
                precision=self.precision
            )
        except Exception as e_init:
            logger.warning(
                f"Khởi tạo VieNeu backend '{self.backend}' gặp cảnh báo ({e_init}). Thử fallback sang ONNX/CPU..."
            )
            try:
                engine = Vieneu(
                    mode=self.mode,
                    backend="onnx",
                    precision="fp32"
                )
            except Exception as e_fallback:
                raise TTSError(f"Không thể khởi tạo mô hình VieNeu-TTS: {e_fallback}")

        # Register any previously saved cloned voices into this engine
        saved_clones = load_saved_cloned_voices()
        for cv in saved_clones:
            c_name = cv.get("name")
            c_path = cv.get("audio_path")
            if c_name and c_path and os.path.exists(c_path):
                try:
                    engine.add_voice(c_name, c_path, denoise=False, save=False)
                    logger.debug(f"Đã nạp sẵn giọng clone '{c_name}' vào engine worker #{self._created_count + 1}")
                except Exception as e_reg:
                    logger.warning(f"Không thể nạp giọng clone '{c_name}': {e_reg}")

        return engine

    def acquire(self, timeout: float = 120.0):
        try:
            return self._pool.get_nowait()
        except queue.Empty:
            with self._lock:
                if self._created_count < self.max_size:
                    engine = self._create_engine()
                    self._created_count += 1
                    self._instances.append(engine)
                    return engine
            try:
                return self._pool.get(block=True, timeout=timeout)
            except queue.Empty:
                raise TTSError(f"Hết thời gian chờ động cơ VieNeu khả dụng ({timeout:.0f}s).")

    def release(self, engine):
        self._pool.put(engine)

    def add_cloned_voice(self, name: str, audio_path: str, denoise: bool = True):
        with self._lock:
            for eng in self._instances:
                try:
                    eng.add_voice(name, audio_path, denoise=denoise, save=False)
                except Exception as e:
                    logger.warning(f"Failed to add voice '{name}' to engine instance: {e}")

    def remove_cloned_voice(self, name: str):
        with self._lock:
            for eng in self._instances:
                try:
                    eng.remove_voice(name, save=False)
                except Exception:
                    pass


_engine_pools: Dict[str, VieNeuEnginePool] = {}
_pools_lock = threading.Lock()


def _get_engine_pool(mode: str, backend: str, precision: str) -> VieNeuEnginePool:
    cache_key = f"{mode}_{backend}_{precision}"
    with _pools_lock:
        if cache_key not in _engine_pools:
            _engine_pools[cache_key] = VieNeuEnginePool(mode, backend, precision, max_size=3)
        return _engine_pools[cache_key]


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
        self.backend = resolve_vieneu_backend(backend)
        self.precision = precision
        self._engine = None

    def get_capabilities(self) -> Dict[str, Any]:
        desc = (
            "VieNeu-TTS SDK v3 Nano (24 kHz - Siêu nhẹ, mượt mà trên CPU)"
            if self.mode == "v3nano"
            else "VieNeu-TTS SDK v3 Turbo (48 kHz - Chất lượng cao, hỗ trợ Voice Cloning)"
        )
        return {
            "supports_pitch": False,
            "supports_rate": True,
            "supports_volume": False,
            "supports_cloning": True,
            "is_offline": True,
            "description": desc
        }

    def get_voices(self) -> List[Dict[str, Any]]:
        """Return list of preset Vietnamese voices plus user cloned voices for current mode."""
        return get_vieneu_voices_list(self.mode)

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

        # Enroll into VieNeu engines
        engine = self._get_engine()
        try:
            logger.info(f"Đang trích xuất đặc trưng và đăng ký giọng clone '{name}' với VieNeu...")
            engine.add_voice(name, str(target_wav), denoise=denoise, save=False)
            self._get_pool().add_cloned_voice(name, str(target_wav), denoise=denoise)
        except Exception as e_add:
            raise TTSError(f"VieNeu không thể nhân bản giọng nói từ mẫu âm thanh: {e_add}")
        finally:
            self._release_engine(engine)

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

        # Remove from running engine pool if loaded
        try:
            engine = self._get_engine()
            try:
                engine.remove_voice(name, save=False)
            finally:
                self._release_engine(engine)
            self._get_pool().remove_cloned_voice(name)
        except Exception:
            pass

        logger.info(f"Đã xóa giọng clone '{name}'.")
        return True

    def _get_pool(self) -> VieNeuEnginePool:
        """Retrieve or initialize the thread-safe engine pool."""
        return _get_engine_pool(self.mode, self.backend, self.precision)

    def _get_engine(self):
        """Retrieve an available VieNeu engine instance from the pool."""
        return self._get_pool().acquire()

    def _release_engine(self, engine):
        """Release an engine instance back into the pool."""
        pool = self._get_pool()
        if any(engine is inst for inst in pool._instances):
            pool.release(engine)

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

        # Check if requested voice is an enrolled custom cloned voice
        saved_clones = {cv.get("name") for cv in load_saved_cloned_voices()}
        is_cloned = voice_id in saved_clones

        resolved_voice = voice_id

        if not is_cloned:
            if self.mode == "v3nano":
                nano_valid = {
                    "Adam", "Ái Hân", "Mỹ Duyên", "Đức Trí", "Hữu Quân",
                    "Xuân Tiên", "Mai Anh", "Trúc Ly", "Anh Khôi", "Minh Quân",
                    "Mạnh Dũng", "xoai_ngan"
                }
                alias_map_nano = {
                    "Adam bựa": "Adam",
                    "Adam vui": "Adam",
                    "Hải Đăng": "Minh Quân",
                    "Minh Quân Pro": "Minh Quân",
                    "Thiện Minh": "Anh Khôi",
                    "Quốc Tuấn": "Mạnh Dũng",
                    "Thùy Dung": "Xuân Tiên",
                    "Quang Sơn": "Minh Quân",
                    "Ngọc Trân": "Ái Hân",
                    "Thiền Tâm Đức": "Hữu Quân",
                    "Ngọc Huyền": "Trúc Ly",
                    "Phạm Tuyên": "Minh Quân",
                    "Minh Đức": "Minh Quân",
                    "Xuân Vĩnh": "Minh Quân",
                    "Thanh Bình": "Hữu Quân",
                    "Ngọc Linh": "Mai Anh",
                    "Đoan Trang": "Ái Hân",
                    "Quỳnh Anh": "Trúc Ly",
                    "Thái Sơn": "Đức Trí",
                    "Thục Đoan": "Mỹ Duyên",
                    "Minh Triết": "Đức Trí",
                    "Kim Thanh": "Mỹ Duyên",
                    "Bảo Long": "Minh Quân",
                    "Nhật Phong": "Minh Quân",
                    "Bích Ngọc": "Trúc Ly",
                    "Trung Dũng": "Minh Quân",
                    "Thành Sen": "Ái Hân",
                    "Ngọc Lan": "Xuân Tiên",
                    "Trâm Anh": "Mỹ Duyên",
                    "Kiều Linh": "Mỹ Duyên",
                }
                if resolved_voice in alias_map_nano:
                    resolved_voice = alias_map_nano[resolved_voice]
                elif resolved_voice not in nano_valid:
                    logger.warning(
                        f"Giọng '{resolved_voice}' không thuộc danh sách preset của VieNeu Nano. Tự động chuyển sang 'Minh Quân'."
                    )
                    resolved_voice = "Minh Quân"
            else:
                turbo_valid = {
                    "Adam bựa", "Trúc Ly", "Thiện Minh", "Mai Anh", "Hải Đăng",
                    "Thùy Dung", "Thiền Tâm Đức", "Ngọc Huyền", "Quang Sơn",
                    "Ngọc Trân", "Minh Đức", "Phạm Tuyên", "Thái Sơn", "Xuân Vĩnh",
                    "Thanh Bình", "Ngọc Linh", "Đoan Trang", "Thục Đoan",
                    "Minh Triết", "Mỹ Duyên", "Quỳnh Anh", "Đức Trí", "Kim Thanh",
                    "Adam", "Quốc Tuấn"
                }
                alias_map_turbo = {
                    "Minh Quân Pro": "Hải Đăng",
                    "Minh Quân": "Hải Đăng",
                    "Anh Khôi": "Thiện Minh",
                    "Mạnh Dũng": "Quốc Tuấn",
                    "Ái Hân": "Đoan Trang",
                    "Hữu Quân": "Thiền Tâm Đức",
                    "Xuân Tiên": "Thùy Dung",
                    "xoai_ngan": "Ngọc Huyền",
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
                if resolved_voice in alias_map_turbo:
                    resolved_voice = alias_map_turbo[resolved_voice]
                elif resolved_voice not in turbo_valid:
                    logger.warning(
                        f"Giọng '{resolved_voice}' không thuộc danh sách preset của VieNeu Turbo. Tự động chuyển sang 'Hải Đăng'."
                    )
                    resolved_voice = "Hải Đăng"

        engine = self._get_engine()
        try:
            # Perform inference on device safely (synchronize if running on GPU PyTorch)
            logger.debug(f"VieNeu SDK inferring text: '{text_clean[:40]}...' with voice '{resolved_voice}'")
            eng_backend = getattr(engine, "backend", "onnx")
            if eng_backend != "onnx":
                with _gpu_infer_lock:
                    audio = engine.infer(text_clean, voice=resolved_voice)
            else:
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
        finally:
            self._release_engine(engine)
