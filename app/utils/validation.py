import os
from pathlib import Path
from typing import List, Dict, Any, Tuple

from app.constants import SUPPORTED_VIDEO_EXTENSIONS, SUPPORTED_AUDIO_EXTENSIONS
from app.exceptions import InvalidMediaError


def validate_media_file(file_path: str | Path) -> Tuple[bool, str]:
    """Validate media file existence, non-emptiness, and valid extension."""
    path = Path(file_path)
    if not path.exists():
        return False, f"Tập tin không tồn tại: {file_path}"
    if not path.is_file():
        return False, f"Đường dẫn không phải là một tập tin: {file_path}"
    try:
        if path.stat().st_size == 0:
            return False, f"Tập tin rỗng (dung lượng 0 bytes): {file_path}"
    except Exception as e:
        return False, f"Không thể đọc thông tin tập tin: {e}"

    ext = path.suffix.lower()
    allowed = SUPPORTED_VIDEO_EXTENSIONS + SUPPORTED_AUDIO_EXTENSIONS
    if ext not in allowed:
        return False, f"Định dạng tập tin '{ext}' không nằm trong danh sách hỗ trợ ({', '.join(allowed)})."

    return True, ""


def validate_subtitles_integrity(subtitles: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Validate subtitle segments for chronological order, non-negative times, and start < end."""
    errors = []
    for idx, item in enumerate(subtitles):
        sid = item.get("id", f"idx_{idx+1}")
        start = item.get("start", 0.0)
        end = item.get("end", 0.0)

        if start < 0 or end < 0:
            errors.append(f"Mục ID '{sid}': Thời gian không được là số âm (start={start}, end={end})")
        if start >= end:
            errors.append(f"Mục ID '{sid}': Start time ({start}) phải nhỏ hơn End time ({end})")

        if idx > 0:
            prev_start = subtitles[idx - 1].get("start", 0.0)
            if start < prev_start:
                errors.append(f"Mục ID '{sid}' (start={start}) xuất hiện trước mục ID '{subtitles[idx-1].get('id')}' (start={prev_start})")

    return len(errors) == 0, errors

