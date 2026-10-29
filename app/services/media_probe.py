import os
import json
import logging
from pathlib import Path

from app.models import MediaInfo
from app.exceptions import MediaProbeError, InvalidMediaError
from app.utils.ffmpeg_utils import get_ffprobe_path, run_ffmpeg_process
from app.utils.validation import validate_media_file

logger = logging.getLogger("AIDubbingStudio.MediaProbe")


class MediaProbeService:
    """Inspects video and audio files using ffprobe."""

    @staticmethod
    def probe_media(file_path: str | Path) -> MediaInfo:
        """Analyze media container, video, and audio streams."""
        valid, err_msg = validate_media_file(file_path)
        if not valid:
            raise InvalidMediaError(err_msg)

        file_path = str(file_path)
        ffprobe_bin = get_ffprobe_path()

        args = [
            ffprobe_bin,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]

        try:
            res = run_ffmpeg_process(args)
            data = json.loads(res.stdout_text)
        except Exception as e:
            raise MediaProbeError(f"Không thể phân tích tệp media: {e}")

        format_info = data.get("format", {})
        streams = data.get("streams", [])

        if not streams and not format_info:
            raise InvalidMediaError("Tệp không chứa stream dữ liệu hợp lệ.")

        duration = float(format_info.get("duration", 0.0))
        file_size = int(format_info.get("size", os.path.getsize(file_path)))
        bitrate = int(format_info.get("bit_rate", 0)) // 1000

        video_stream = None
        audio_stream = None

        for stream in streams:
            codec_type = stream.get("codec_type")
            if codec_type == "video" and not video_stream:
                video_stream = stream
            elif codec_type == "audio" and not audio_stream:
                audio_stream = stream

        info = MediaInfo(
            duration=duration,
            file_size_bytes=file_size,
            bitrate_kbps=bitrate,
            has_video=video_stream is not None,
            has_audio=audio_stream is not None
        )

        if video_stream:
            info.width = int(video_stream.get("width", 0))
            info.height = int(video_stream.get("height", 0))
            info.video_codec = video_stream.get("codec_name", "")

            # Parse FPS from r_frame_rate e.g. "30/1" or "30000/1001"
            fps_str = video_stream.get("r_frame_rate", "30/1")
            try:
                if "/" in fps_str:
                    num, den = fps_str.split("/")
                    info.fps = round(float(num) / float(den), 3) if float(den) > 0 else 30.0
                else:
                    info.fps = round(float(fps_str), 3)
            except Exception:
                info.fps = 30.0

            if info.duration == 0.0 and "duration" in video_stream:
                try:
                    info.duration = float(video_stream["duration"])
                except Exception:
                    pass

        if audio_stream:
            info.audio_codec = audio_stream.get("codec_name", "")
            info.audio_sample_rate = int(audio_stream.get("sample_rate", 44100))
            info.audio_channels = int(audio_stream.get("channels", 2))

            if info.duration == 0.0 and "duration" in audio_stream:
                try:
                    info.duration = float(audio_stream["duration"])
                except Exception:
                    pass

        logger.info(
            f"Probed media: {Path(file_path).name} | Duration: {info.duration:.2f}s | "
            f"Resolution: {info.width}x{info.height} | FPS: {info.fps} | Audio: {info.has_audio}"
        )
        return info

