import math
from typing import Tuple


def seconds_to_srt_time(seconds: float) -> str:
    """Convert float seconds to SRT timestamp format: HH:MM:SS,mmm"""
    if seconds < 0:
        seconds = 0.0
    total_millis = int(round(seconds * 1000))
    millis = total_millis % 1000
    total_secs = total_millis // 1000
    secs = total_secs % 60
    total_mins = total_secs // 60
    mins = total_mins % 60
    hours = total_mins // 60
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def srt_time_to_seconds(srt_time: str) -> float:
    """Parse SRT timestamp (HH:MM:SS,mmm or HH:MM:SS.mmm) into float seconds."""
    clean = srt_time.strip().replace(",", ".")
    parts = clean.split(":")
    if len(parts) == 3:
        hours = float(parts[0])
        mins = float(parts[1])
        secs = float(parts[2])
        return round(hours * 3600.0 + mins * 60.0 + secs, 4)
    elif len(parts) == 2:
        mins = float(parts[0])
        secs = float(parts[1])
        return round(mins * 60.0 + secs, 4)
    else:
        return round(float(clean), 4)


def seconds_to_display(seconds: float) -> str:
    """Convert seconds to human-readable string: MM:SS.ss (e.g. 01:23.45) or HH:MM:SS.ss"""
    if seconds < 0:
        seconds = 0.0
    total_secs = int(seconds)
    fraction = int(round((seconds - total_secs) * 100))
    mins = total_secs // 60
    secs = total_secs % 60
    hours = mins // 60
    mins = mins % 60

    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}.{fraction:02d}"
    return f"{mins:02d}:{secs:02d}.{fraction:02d}"


def seconds_to_timecode(seconds: float, fps: float = 30.0) -> str:
    """Convert seconds to SMPTE timecode HH:MM:SS:FF"""
    if seconds < 0:
        seconds = 0.0
    if fps <= 0:
        fps = 30.0
    total_frames = int(round(seconds * fps))
    frames = int(total_frames % round(fps))
    total_seconds = int(total_frames // round(fps))
    secs = total_seconds % 60
    total_mins = total_seconds // 60
    mins = total_mins % 60
    hours = total_mins // 60
    return f"{hours:02d}:{mins:02d}:{secs:02d}:{frames:02d}"


def timecode_to_seconds(timecode: str, fps: float = 30.0) -> float:
    """Convert SMPTE timecode HH:MM:SS:FF to float seconds."""
    parts = timecode.strip().split(":")
    if len(parts) == 4:
        h, m, s, f = map(int, parts)
        return h * 3600 + m * 60 + s + (f / fps)
    elif len(parts) == 3:
        h, m, s = map(float, parts)
        return h * 3600 + m * 60 + s
    return 0.0

