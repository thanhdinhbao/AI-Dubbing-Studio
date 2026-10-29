import os
import sys
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.providers.base import BaseTTSProvider
from app.exceptions import TTSError
from app.utils.audio_utils import get_audio_duration

logger = logging.getLogger("AIDubbingStudio.OfflineTTS")


class OfflineTTSProvider(BaseTTSProvider):
    """Offline Text-to-Speech provider with local model verification."""

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "supports_pitch": False,
            "supports_rate": True,
            "supports_volume": True,
            "is_offline": True,
            "description": "Offline TTS Engine (Piper / SAPI / Onnx)"
        }

    def get_voices(self) -> List[Dict[str, Any]]:
        voices = []
        if self.model_path and os.path.exists(self.model_path):
            model_name = Path(self.model_path).stem
            voices.append({
                "id": self.model_path,
                "name": f"Local Model ({model_name})",
                "gender": "Custom",
                "lang": "vi"
            })
        else:
            voices.append({
                "id": "builtin_vi_unavailable",
                "name": "Chưa cài đặt mô hình Offline tiếng Việt",
                "gender": "None",
                "lang": "vi"
            })
        return voices

    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: str | Path,
        options: Optional[Dict[str, Any]] = None
    ) -> float:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.model_path or not os.path.exists(self.model_path):
            raise TTSError(
                "Không tìm thấy mô hình TTS offline tiếng Việt trên máy tính.",
                details=(
                    "Để sử dụng chế độ Offline TTS thực sự:\n"
                    "1. Hãy tải mô hình Piper tiếng Việt (ví dụ: vi_VN-vivos-x_low.onnx).\n"
                    "2. Đặt vào thư mục models/ hoặc chỉ định đường dẫn trong Cài Đặt (Settings).\n"
                    "3. Trong khi chưa có mô hình offline, hãy chuyển sang dùng Edge TTS chất lượng cao."
                )
            )

        piper_bin = shutil.which("piper") or "piper"
        try:
            import subprocess
            cmd = [
                piper_bin,
                "--model", self.model_path,
                "--output_file", str(output_path)
            ]
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = p.communicate(input=text)
            if p.returncode != 0:
                raise RuntimeError(f"Piper error: {stderr}")

            return get_audio_duration(output_path)
        except Exception as e:
            raise TTSError(f"Lỗi khi thực thi mô hình offline: {e}")
