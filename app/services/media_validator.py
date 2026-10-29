import os
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

from app.services.media_probe import MediaProbeService
from app.exceptions import InvalidMediaError

logger = logging.getLogger("AIDubbingStudio.MediaValidator")


class MediaValidatorService:
    """Verifies rendered output video integrity, streams, and duration conformity."""

    @staticmethod
    def validate_rendered_output(
        video_path: str | Path,
        expected_duration: float,
        duration_tolerance_sec: float = 0.5
    ) -> Tuple[bool, Dict[str, Any]]:
        """Validate rendered video against timeline specifications."""
        video_path = str(video_path)
        report = {
            "valid": False,
            "errors": [],
            "duration": 0.0,
            "expected_duration": expected_duration,
            "file_size_mb": 0.0,
            "video_codec": "",
            "audio_codec": "",
            "resolution": ""
        }

        if not os.path.exists(video_path):
            report["errors"].append("Tệp video không tồn tại.")
            return False, report

        size_bytes = os.path.getsize(video_path)
        report["file_size_mb"] = round(size_bytes / (1024 * 1024), 2)
        if size_bytes == 0:
            report["errors"].append("Dung lượng tệp video bằng 0 bytes.")
            return False, report

        try:
            info = MediaProbeService.probe_media(video_path)
            report["duration"] = info.duration
            report["video_codec"] = info.video_codec
            report["audio_codec"] = info.audio_codec
            report["resolution"] = f"{info.width}x{info.height}"

            if not info.has_video:
                report["errors"].append("Tệp không chứa stream hình ảnh (video).")
            if not info.has_audio:
                report["errors"].append("Tệp không chứa stream âm thanh (audio).")

            # Check duration match
            if expected_duration > 0:
                diff = abs(info.duration - expected_duration)
                if diff > duration_tolerance_sec:
                    report["errors"].append(
                        f"Thời lượng video ({info.duration:.2f}s) lệch quá nhiều so với timeline ({expected_duration:.2f}s, chênh lệch {diff:.2f}s)."
                    )

            if not report["errors"]:
                report["valid"] = True
                logger.info(f"Rendered video validated successfully: {report['resolution']}, {report['duration']:.2f}s")
                return True, report
            else:
                logger.warning(f"Video validation found issues: {report['errors']}")
                return False, report

        except Exception as e:
            report["errors"].append(f"Không thể phân tích tệp video xuất bản: {e}")
            return False, report

