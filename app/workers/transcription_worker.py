import logging
from app.workers.base_worker import BaseWorker
from app.services.audio_extractor import AudioExtractorService
from app.services.transcription import TranscriptionService

logger = logging.getLogger("AIDubbingStudio.TranscriptionWorker")


class TranscriptionWorker(BaseWorker):
    """Worker for audio extraction and ASR transcription with fast decoding."""

    def __init__(
        self,
        video_path: str,
        output_wav_path: str,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "auto",
        beam_size: int = 1
    ):
        super().__init__()
        self.video_path = video_path
        self.output_wav_path = output_wav_path
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.beam_size = beam_size

    def run(self):
        try:
            self.progress.emit(10, "Đang trích xuất âm thanh từ video...")
            wav_path = AudioExtractorService.extract_audio(
                video_path=self.video_path,
                output_wav_path=self.output_wav_path,
                cancel_event=self.cancel_event
            )

            self.progress.emit(30, f"Đang nhận diện lời thoại bằng Whisper ({self.model_size}, beam={self.beam_size})...")
            asr_service = TranscriptionService(
                model_size=self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )

            def on_asr_prog(p, msg):
                scaled = int(30 + (p * 0.7))
                self.progress.emit(scaled, msg)

            dialogues = asr_service.transcribe(
                audio_path=wav_path,
                language=self.language,
                beam_size=self.beam_size,
                condition_on_previous_text=False,
                on_progress=on_asr_prog,
                cancel_event=self.cancel_event
            )

            self.finished.emit(dialogues)
        except Exception as e:
            logger.error(f"Transcription worker failed: {e}")
            self.error.emit(str(e))

