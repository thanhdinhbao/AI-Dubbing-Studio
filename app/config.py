import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from app.constants import (
    DEFAULT_VIDEO_CODEC,
    DEFAULT_AUDIO_CODEC,
    DEFAULT_VIDEO_CRF,
    DEFAULT_AUDIO_BITRATE,
    TimelineMode,
    AudioSeparationMode,
    WHISPER_MODELS,
)
from app.utils.paths import (
    get_user_data_dir,
    get_default_output_dir,
    get_default_cache_dir,
    get_default_models_dir,
    get_default_projects_dir,
)

logger = logging.getLogger("AIDubbingStudio.Config")


class AppConfig:
    """Manages application-wide settings and persistence."""

    DEFAULT_CONFIG = {
        # Media tools
        "ffmpeg_path": "",
        "ffprobe_path": "",

        # ASR (faster-whisper)
        "asr_model": "base",
        "asr_device": "cpu",
        "asr_compute_type": "int8",
        "asr_language": "auto",

        # Translation
        "translation_backend": "google_free",
        "translation_base_url": "https://api.openai.com/v1",
        "translation_api_key": "",
        "translation_model": "gpt-4o-mini",
        "translation_temperature": 0.3,
        "translation_timeout": 60,
        "ollama_base_url": "http://localhost:11434/v1",
        "ollama_model": "qwen2.5:latest",

        # TTS
        "tts_backend": "edge_tts",
        "tts_voice": "vi-VN-HoaiMyNeural",
        "tts_rate": "+0%",
        "tts_pitch": "+0Hz",
        "tts_volume": "+0%",
        "tts_api_base_url": "https://api.openai.com/v1",
        "tts_api_key": "",
        "tts_api_model": "tts-1",
        "vieneu_api_url": "https://www.vieneu.io/api/tts/demo",
        "vieneu_token": "",
        "offline_tts_model_path": "",

        # Audio & Timeline
        "timeline_mode": TimelineMode.DYNAMIC_DURATION,
        "audio_separation_mode": AudioSeparationMode.DUCKING_ORIGINAL,
        "bg_music_volume": 0.25,
        "tts_volume_gain": 1.1,
        "ducking_fade_duration": 0.3,
        "ducking_reduction_db": -14.0,

        # Render
        "render_video_codec": DEFAULT_VIDEO_CODEC,
        "render_audio_codec": DEFAULT_AUDIO_CODEC,
        "render_crf": DEFAULT_VIDEO_CRF,
        "render_audio_bitrate": DEFAULT_AUDIO_BITRATE,
        "render_preset": "medium",

        # Directories
        "projects_dir": str(get_default_projects_dir()),
        "output_dir": str(get_default_output_dir()),
        "cache_dir": str(get_default_cache_dir()),
        "models_dir": str(get_default_models_dir()),

        # System
        "worker_concurrency": 2,
    }

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (get_user_data_dir() / "config.json")
        self.data: Dict[str, Any] = dict(self.DEFAULT_CONFIG)
        self.load()

    def load(self):
        """Load configuration from disk if available."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to read configuration: {e}. Using defaults.")
        else:
            self.save()

    def save(self):
        """Save configuration to disk."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            # Create a copy and ensure API keys are securely handled
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            logger.info("Saved configuration successfully.")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True):
        self.data[key] = value
        if auto_save:
            self.save()


# Global Singleton Configuration Instance
app_config = AppConfig()

