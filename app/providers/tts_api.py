import logging
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.providers.base import BaseTTSProvider
from app.exceptions import TTSError
from app.utils.audio_utils import get_audio_duration

logger = logging.getLogger("AIDubbingStudio.TTSAPI")


class OpenAITTSProvider(BaseTTSProvider):
    """Text-to-Speech provider using OpenAI-compatible audio speech API."""

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: str = "",
        model: str = "tts-1",
        timeout: int = 60
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "supports_pitch": False,
            "supports_rate": True,
            "supports_volume": False,
            "is_offline": False,
            "description": "OpenAI Audio Speech API"
        }

    def get_voices(self) -> List[Dict[str, Any]]:
        return [
            {"id": "alloy", "name": "Alloy (Trung tính)", "gender": "Neutral", "lang": "vi"},
            {"id": "echo", "name": "Echo (Nam)", "gender": "Male", "lang": "vi"},
            {"id": "fable", "name": "Fable (Kể chuyện)", "gender": "Neutral", "lang": "vi"},
            {"id": "onyx", "name": "Onyx (Nam trầm)", "gender": "Male", "lang": "vi"},
            {"id": "nova", "name": "Nova (Nữ ấm áp)", "gender": "Female", "lang": "vi"},
            {"id": "shimmer", "name": "Shimmer (Nữ trong trẻo)", "gender": "Female", "lang": "vi"}
        ]

    def synthesize(
        self,
        text: str,
        voice_id: str = "alloy",
        output_path: str | Path = "",
        options: Optional[Dict[str, Any]] = None
    ) -> float:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        opts = options or {}
        speed = float(opts.get("speed", 1.0))

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }

        # Response format: wav or mp3
        is_wav = output_path.suffix.lower() == ".wav"
        fmt = "wav" if is_wav else "mp3"

        payload = {
            "model": self.model,
            "input": text.strip(),
            "voice": voice_id,
            "response_format": fmt,
            "speed": max(0.25, min(4.0, speed))
        }

        try:
            url = f"{self.base_url}/audio/speech"
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            if resp.status_code != 200:
                raise TTSError(f"TTS API phản hồi mã lỗi {resp.status_code}: {resp.text[:300]}")

            with open(output_path, "wb") as f:
                f.write(resp.content)

            duration = get_audio_duration(output_path)
            return duration
        except Exception as e:
            raise TTSError(f"Lỗi khi gọi API TTS: {e}")

