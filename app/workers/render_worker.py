import os
import logging
from typing import List, Optional, Dict, Any
from app.workers.base_worker import BaseWorker
from app.models import TimelineSegment
from app.services.audio_mixer import AudioMixerService
from app.services.video_renderer import VideoRendererService
from app.services.media_validator import MediaValidatorService

logger = logging.getLogger("AIDubbingStudio.RenderWorker")


class RenderWorker(BaseWorker):
    """Worker for audio mixing, dynamic timeline video rendering, and output validation."""

    def __init__(
        self,
        source_video_path: str,
        timeline: List[TimelineSegment],
        output_duration: float,
        output_video_path: str,
        workspace_dir: str,
        background_audio_path: Optional[str] = None,
        render_settings: Optional[Dict[str, Any]] = None
    ):
        super().__init__()
        self.source_video_path = source_video_path
        self.timeline = timeline
        self.output_duration = output_duration
        self.output_video_path = output_video_path
        self.workspace_dir = workspace_dir
        self.background_audio_path = background_audio_path
        self.render_settings = render_settings or {}

    def run(self):
        try:
            # Step 1: Audio mixing
            self.progress.emit(10, "Đang hòa âm lời thoại tiếng Việt và nhạc nền...")
            mixed_wav_path = os.path.join(self.workspace_dir, "audio", "final_mixed_audio.wav")

            bg_vol = float(self.render_settings.get("bg_music_volume", 0.25))
            tts_gain = float(self.render_settings.get("tts_volume_gain", 1.0))
            ducking_reduction = float(self.render_settings.get("ducking_reduction", 0.2))

            mixer = AudioMixerService(
                bg_volume=bg_vol,
                tts_gain=tts_gain,
                ducking_reduction=ducking_reduction
            )

            def on_mix_prog(p, msg):
                scaled = int(10 + (p * 0.25))
                self.progress.emit(scaled, msg)

            mixer.mix_timeline_audio(
                timeline=self.timeline,
                output_duration=self.output_duration,
                output_wav_path=mixed_wav_path,
                background_wav_path=self.background_audio_path,
                on_progress=on_mix_prog,
                cancel_event=self.cancel_event
            )

            if self.cancel_event.is_set():
                raise RuntimeError("Quá trình xuất video đã bị hủy.")

            # Step 2: Video Rendering
            self.progress.emit(35, "Đang dựng và mã hóa video hoàn chỉnh với FFmpeg...")
            video_codec = self.render_settings.get("render_video_codec", "libx264")
            audio_codec = self.render_settings.get("render_audio_codec", "aac")
            crf = int(self.render_settings.get("render_crf", 20))
            preset = self.render_settings.get("render_preset", "medium")
            audio_bitrate = self.render_settings.get("render_audio_bitrate", "192k")

            renderer = VideoRendererService(
                video_codec=video_codec,
                audio_codec=audio_codec,
                crf=crf,
                preset=preset,
                audio_bitrate=audio_bitrate
            )

            def on_render_prog(p, msg):
                scaled = int(35 + (p * 0.55))
                self.progress.emit(scaled, msg)

            rendered_path = renderer.render(
                source_video_path=self.source_video_path,
                mixed_audio_path=mixed_wav_path,
                timeline=self.timeline,
                output_video_path=self.output_video_path,
                on_progress=on_render_prog,
                cancel_event=self.cancel_event
            )

            # Step 3: Validation
            self.progress.emit(92, "Đang kiểm tra tính toàn vẹn của video hoàn chỉnh...")
            valid, report = MediaValidatorService.validate_rendered_output(
                video_path=rendered_path,
                expected_duration=self.output_duration
            )

            self.progress.emit(100, "Xuất bản video thành công!")
            self.finished.emit({
                "output_video_path": rendered_path,
                "validation": report,
                "valid": valid
            })

        except Exception as e:
            logger.error(f"Render worker failed: {e}")
            self.error.emit(str(e))

