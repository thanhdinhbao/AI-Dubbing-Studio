import os
import threading
import logging
from pathlib import Path
from typing import List, Optional, Callable

from app.models import DialogueSegment
from app.constants import DialogueStatus
from app.exceptions import TranscriptionError
from app.utils.audio_utils import patch_pyav_metadata_errors

logger = logging.getLogger("AIDubbingStudio.Transcription")


class TranscriptionService:
    """ASR Speech-to-Text service using faster-whisper with speed and precision optimizations."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        download_root: Optional[str] = None,
        cpu_threads: Optional[int] = None,
        num_workers: int = 2
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.download_root = download_root
        self.cpu_threads = cpu_threads or max(1, (os.cpu_count() or 4) - 1)
        self.num_workers = num_workers

    def transcribe(
        self,
        audio_path: str | Path,
        language: Optional[str] = None,
        beam_size: int = 1,
        condition_on_previous_text: bool = False,
        on_progress: Optional[Callable[[int, str], None]] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> List[DialogueSegment]:
        audio_path = str(audio_path)
        if not os.path.exists(audio_path):
            raise TranscriptionError(f"Tệp âm thanh không tồn tại: {audio_path}")

        # Ensure compatibility with PyAV >= 14 and CUDA DLL registration
        patch_pyav_metadata_errors()
        from app.bootstrap import setup_cuda_dll_paths
        setup_cuda_dll_paths()

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise TranscriptionError("Thư viện 'faster-whisper' chưa được cài đặt.")

        # Ensure safe fallback to CPU if CUDA is requested but not supported
        active_device = self.device
        active_compute = self.compute_type
        if active_device == "cuda":
            try:
                import torch
                if not torch.cuda.is_available():
                    logger.warning("CUDA không khả dụng trên máy này. Tự động chuyển sang CPU.")
                    active_device = "cpu"
                    active_compute = "int8"
                else:
                    major, minor = torch.cuda.get_device_capability(0)
                    dev_name = torch.cuda.get_device_name(0)
                    # CTranslate2 CUDA wheels require compute capability >= 6.0 (Pascal, Volta, Turing, Ampere...)
                    if major < 6:
                        logger.warning(
                            f"GPU '{dev_name}' có Compute Capability {major}.{minor} (< 6.0 - Maxwell sm_50), "
                            "không tương thích với CUDA kernels của faster-whisper. "
                            "Tự động chuyển sang CPU đa luồng (int8) tối ưu tốc độ và ổn định tuyệt đối."
                        )
                        active_device = "cpu"
                        active_compute = "int8"
            except Exception:
                active_device = "cpu"
                active_compute = "int8"

        # Validate compute_type with ctranslate2 capabilities
        try:
            import ctranslate2
            supported = ctranslate2.get_supported_compute_types(active_device)
            if active_compute not in supported:
                if active_device == "cuda":
                    if "float16" in supported:
                        active_compute = "float16"
                    elif "float32" in supported:
                        active_compute = "float32"
                    else:
                        active_compute = next(iter(supported)) if supported else "float32"
                else:
                    active_compute = "int8" if "int8" in supported else "float32"
                logger.info(
                    f"Thiết bị {active_device} hỗ trợ {supported}. "
                    f"Tự động điều chỉnh compute_type -> '{active_compute}'."
                )
        except Exception as e_supp:
            logger.debug(f"Không thể truy vấn supported compute types: {e_supp}")

        threads_param = self.cpu_threads if active_device == "cpu" else 0
        workers_param = self.num_workers if active_device == "cpu" else 1

        logger.info(
            f"Loading faster-whisper model '{self.model_size}' on {active_device} ({active_compute}) "
            f"with cpu_threads={threads_param}, num_workers={workers_param}..."
        )
        if on_progress:
            on_progress(10, f"Đang nạp mô hình Whisper ({self.model_size})...")

        try:
            model = WhisperModel(
                self.model_size,
                device=active_device,
                compute_type=active_compute,
                download_root=self.download_root,
                cpu_threads=threads_param,
                num_workers=workers_param
            )
        except Exception as e:
            err_str = str(e).lower()
            if active_device == "cuda":
                logger.warning(f"Khởi tạo CUDA với compute_type='{active_compute}' thất bại ({e}). Thử fallback...")
                # Try float32 on CUDA first if we didn't try it
                if active_compute != "float32":
                    try:
                        logger.info("Thử lại CUDA với compute_type='float32'...")
                        model = WhisperModel(
                            self.model_size,
                            device="cuda",
                            compute_type="float32",
                            download_root=self.download_root,
                            cpu_threads=0,
                            num_workers=1
                        )
                        active_compute = "float32"
                    except Exception as e_f32:
                        logger.warning(f"CUDA float32 vẫn thất bại ({e_f32}). Tự động fallback hoàn toàn sang CPU.")
                        model = WhisperModel(
                            self.model_size,
                            device="cpu",
                            compute_type="int8",
                            download_root=self.download_root,
                            cpu_threads=self.cpu_threads,
                            num_workers=self.num_workers
                        )
                else:
                    logger.warning("CUDA thất bại. Tự động fallback sang CPU.")
                    model = WhisperModel(
                        self.model_size,
                        device="cpu",
                        compute_type="int8",
                        download_root=self.download_root,
                        cpu_threads=self.cpu_threads,
                        num_workers=self.num_workers
                    )
            else:
                raise TranscriptionError(f"Không thể khởi tạo mô hình Whisper: {e}")

        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Nhận diện giọng nói đã bị hủy.")

        if on_progress:
            on_progress(30, f"Đang nhận diện lời thoại (beam_size={beam_size})...")

        lang_arg = None if (not language or language.lower() in ("auto", "")) else language.lower()

        try:
            segments_gen, info = model.transcribe(
                audio_path,
                language=lang_arg,
                beam_size=beam_size,
                temperature=0.0,
                condition_on_previous_text=condition_on_previous_text,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400)
            )

            logger.info(f"Detected language: '{info.language}' with probability {info.language_probability:.2f}")

            results: List[DialogueSegment] = []
            prev_text = ""

            for seg in segments_gen:
                if cancel_event and cancel_event.is_set():
                    raise RuntimeError("Nhận diện giọng nói đã bị hủy.")

                text = seg.text.strip()
                if not text:
                    continue

                # Deduplicate hallucinated identical consecutive lines
                if text == prev_text:
                    continue
                prev_text = text

                start_sec = round(float(seg.start), 3)
                end_sec = round(float(seg.end), 3)

                if end_sec <= start_sec:
                    end_sec = start_sec + 0.5

                dialogue = DialogueSegment(
                    start=start_sec,
                    end=end_sec,
                    source_text=text,
                    target_text="",
                    status=DialogueStatus.TRANSCRIBED
                )
                results.append(dialogue)

            if on_progress:
                on_progress(100, f"Nhận diện hoàn tất: {len(results)} câu thoại.")

            logger.info(f"ASR extracted {len(results)} dialogue segments.")
            return results

        except Exception as e:
            if cancel_event and cancel_event.is_set():
                raise
            err_msg = str(e).lower()
            if active_device == "cuda" and ("cuda" in err_msg or "device" in err_msg or "ordinal" in err_msg):
                logger.warning(f"CUDA runtime error ({e}). Tự động fallback sang CPU đa luồng để hoàn thành nhận diện...")
                if on_progress:
                    on_progress(35, "GPU gặp lỗi kernel CUDA. Đang chuyển sang CPU đa luồng để hoàn tất...")
                try:
                    cpu_model = WhisperModel(
                        self.model_size,
                        device="cpu",
                        compute_type="int8",
                        download_root=self.download_root,
                        cpu_threads=self.cpu_threads,
                        num_workers=self.num_workers
                    )
                    segments_gen, info = cpu_model.transcribe(
                        audio_path,
                        language=lang_arg,
                        beam_size=beam_size,
                        temperature=0.0,
                        condition_on_previous_text=condition_on_previous_text,
                        vad_filter=True,
                        vad_parameters=dict(min_silence_duration_ms=400)
                    )
                    results: List[DialogueSegment] = []
                    prev_text = ""
                    for seg in segments_gen:
                        if cancel_event and cancel_event.is_set():
                            raise RuntimeError("Nhận diện giọng nói đã bị hủy.")
                        text = seg.text.strip()
                        if not text or text == prev_text:
                            continue
                        prev_text = text
                        start_sec = round(float(seg.start), 3)
                        end_sec = max(start_sec + 0.5, round(float(seg.end), 3))
                        results.append(DialogueSegment(
                            start=start_sec,
                            end=end_sec,
                            source_text=text,
                            target_text="",
                            status=DialogueStatus.TRANSCRIBED
                        ))
                    if on_progress:
                        on_progress(100, f"Nhận diện hoàn tất (CPU Fallback): {len(results)} câu thoại.")
                    return results
                except Exception as e_cpu:
                    logger.error(f"CPU fallback failed: {e_cpu}")
            raise TranscriptionError(f"Quá trình ASR thất bại: {e}")

