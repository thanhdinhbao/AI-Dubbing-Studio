import os
import re
import tempfile
import threading
import logging
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from app.models import TimelineSegment
from app.exceptions import RenderError
from app.utils.ffmpeg_utils import get_ffmpeg_path, run_ffmpeg_process
from app.services.media_probe import MediaProbeService

logger = logging.getLogger("AIDubbingStudio.VideoRenderer")


class VideoRendererService:
    """Renders final dubbed video with dynamic timeline reconstruction using FFmpeg with GPU/CPU acceleration."""

    def __init__(
        self,
        video_codec: str = "libx264",
        audio_codec: str = "aac",
        crf: int = 20,
        preset: str = "faster",
        audio_bitrate: str = "192k",
        threads: int = 0
    ):
        self.video_codec = video_codec
        self.audio_codec = audio_codec
        self.crf = crf
        self.preset = preset
        self.audio_bitrate = audio_bitrate
        self.threads = threads

    def render(
        self,
        source_video_path: str | Path,
        mixed_audio_path: str | Path,
        timeline: List[TimelineSegment],
        output_video_path: str | Path,
        on_progress: Optional[Callable[[int, str], None]] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> str:
        """Render the final dubbed video according to dynamic timeline segments."""
        source_video_path = str(source_video_path)
        mixed_audio_path = str(mixed_audio_path)
        output_video_path = str(output_video_path)

        if not os.path.exists(source_video_path):
            raise RenderError(f"Tệp video nguồn không tồn tại: {source_video_path}")
        if not os.path.exists(mixed_audio_path):
            raise RenderError(f"Tệp âm thanh hòa âm không tồn tại: {mixed_audio_path}")
        if not timeline:
            raise RenderError("Timeline rỗng, không có dữ liệu để render.")

        os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)

        logger.info(f"Preparing video render with codec '{self.video_codec}' preset '{self.preset}' to: {output_video_path}")
        ffmpeg_bin = get_ffmpeg_path()

        # Build combined video intervals from timeline
        video_actions = []
        i = 0
        while i < len(timeline):
            seg = timeline[i]
            if seg.segment_type == "video_normal":
                # Check if next segment is its corresponding freeze frame
                delta = 0.0
                if i + 1 < len(timeline) and timeline[i + 1].segment_type == "video_freeze":
                    delta = timeline[i + 1].duration
                    i += 1  # consume freeze segment

                video_actions.append({
                    "start": seg.source_start,
                    "end": seg.source_end,
                    "pad_duration": delta
                })
            elif seg.segment_type == "gap":
                video_actions.append({
                    "start": seg.source_start,
                    "end": seg.source_end,
                    "pad_duration": 0.0
                })
            elif seg.segment_type == "video_freeze":
                video_actions.append({
                    "start": seg.source_start,
                    "end": seg.source_end,
                    "pad_duration": seg.duration
                })
            i += 1

        filter_lines = []
        stream_labels = []

        for idx, act in enumerate(video_actions):
            s = act["start"]
            e = max(s + 0.001, act["end"])
            pad = act["pad_duration"]

            label = f"v{idx}"
            stream_labels.append(f"[{label}]")

            if pad > 0.005:
                # Trim clip and clone last frame for pad duration
                fl = f"[0:v]trim=start={s:.4f}:end={e:.4f},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={pad:.4f}[{label}];"
            else:
                fl = f"[0:v]trim=start={s:.4f}:end={e:.4f},setpts=PTS-STARTPTS[{label}];"

            filter_lines.append(fl)

        # Concatenate all video streams
        concat_filter = f"{''.join(stream_labels)}concat=n={len(stream_labels)}:v=1:a=0[v_out]"
        filter_lines.append(concat_filter)

        filter_script_content = "\n".join(filter_lines)

        # Write filter script to temporary file to avoid command length limits on Windows
        temp_filter_file = Path(output_video_path).parent / f"filter_complex_{os.getpid()}.txt"
        with open(temp_filter_file, "w", encoding="utf-8") as f:
            f.write(filter_script_content)

        total_output_duration = timeline[-1].output_end

        # Codec specific encoding options
        vcodec = self.video_codec.lower()
        codec_args = []

        if "nvenc" in vcodec:
            # NVIDIA NVENC Hardware Encoding
            nvenc_preset = "p4"
            if self.preset in ("ultrafast", "veryfast"):
                nvenc_preset = "p1"
            elif self.preset in ("faster", "fast"):
                nvenc_preset = "p3"
            elif self.preset in ("medium", "slow"):
                nvenc_preset = "p4"

            codec_args = [
                "-c:v", self.video_codec,
                "-preset", nvenc_preset,
                "-cq", str(self.crf),
                "-spatial_aq", "1"
            ]
        else:
            # CPU Software Encoding (libx264, libx265)
            codec_args = [
                "-c:v", self.video_codec,
                "-crf", str(self.crf),
                "-preset", self.preset,
                "-threads", str(self.threads)
            ]

        # Build FFmpeg command with thread buffers and multi-threaded filtergraph
        cmd = [
            ffmpeg_bin,
            "-y",
            "-thread_queue_size", "1024",
            "-i", source_video_path,
            "-thread_queue_size", "1024",
            "-i", mixed_audio_path,
            "-filter_complex_threads", "0",
            "-filter_complex", filter_script_content,
            "-map", "[v_out]",
            "-map", "1:a"
        ] + codec_args + [
            "-c:a", self.audio_codec,
            "-b:a", self.audio_bitrate,
            "-shortest",
            output_video_path
        ]

        logger.info(f"Executing render for {total_output_duration:.2f}s output video...")
        if on_progress:
            on_progress(10, "Bắt đầu render video với FFmpeg...")

        # Parse time progress from FFmpeg stderr
        def parse_progress(line: str):
            time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
            if time_match and total_output_duration > 0:
                h, m, s = time_match.groups()
                curr_sec = float(h) * 3600 + float(m) * 60 + float(s)
                pct = min(99, int((curr_sec / total_output_duration) * 90) + 10)
                if on_progress:
                    on_progress(pct, f"Đang render: {curr_sec:.1f}s / {total_output_duration:.1f}s ({pct}%)")

        try:
            run_ffmpeg_process(cmd, on_progress=parse_progress, cancel_event=cancel_event)

            # Clean temp filter script
            if temp_filter_file.exists():
                try:
                    temp_filter_file.unlink()
                except Exception:
                    pass

            if not os.path.exists(output_video_path) or os.path.getsize(output_video_path) == 0:
                raise RenderError("Tệp video đầu ra không được tạo hoặc có dung lượng 0 bytes.")

            if on_progress:
                on_progress(100, "Render video hoàn tất thành công!")

            logger.info(f"Render completed successfully: {output_video_path}")
            return output_video_path

        except Exception as e:
            if temp_filter_file.exists():
                try:
                    temp_filter_file.unlink()
                except Exception:
                    pass
            if cancel_event and cancel_event.is_set():
                raise
            raise RenderError(f"Render video thất bại: {e}")
