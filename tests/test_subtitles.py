import pytest
from pathlib import Path
import tempfile

from app.models import DialogueSegment
from app.services.audio_alignment import AudioAlignmentService
from app.utils.timecode import seconds_to_srt_time, srt_time_to_seconds
from app.utils.validation import validate_subtitles_integrity


def test_timecode_conversions():
    sec = 83.456
    srt_str = seconds_to_srt_time(sec)
    assert srt_str == "00:01:23,456"

    parsed_sec = srt_time_to_seconds(srt_str)
    assert abs(parsed_sec - 83.456) < 0.001

    assert srt_time_to_seconds("00:00:02,500") == 2.5
    assert srt_time_to_seconds("01:30.5") == 90.5


def test_srt_export_and_import():
    dlgs = [
        DialogueSegment(id="d1", start=1.0, end=3.5, source_text="Hello world", target_text="Xin chào thế giới"),
        DialogueSegment(id="d2", start=4.0, end=7.2, source_text="This is a test", target_text="Đây là một bài kiểm tra"),
    ]

    with tempfile.NamedTemporaryFile(suffix=".srt", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp_path = tmp.name

    try:
        AudioAlignmentService.export_srt(dlgs, tmp_path, use_vietnamese=True)
        imported = AudioAlignmentService.import_srt(tmp_path)

        assert len(imported) == 2
        assert abs(imported[0].start - 1.0) < 0.01
        assert abs(imported[0].end - 3.5) < 0.01
        assert imported[0].source_text == "Xin chào thế giới"
        assert abs(imported[1].start - 4.0) < 0.01
        assert abs(imported[1].end - 7.2) < 0.01
        assert imported[1].source_text == "Đây là một bài kiểm tra"
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


def test_validate_subtitles_integrity():
    valid_subs = [
        {"id": "1", "start": 0.0, "end": 2.0},
        {"id": "2", "start": 3.0, "end": 5.0},
    ]
    ok, errors = validate_subtitles_integrity(valid_subs)
    assert ok is True
    assert len(errors) == 0

    invalid_subs = [
        {"id": "1", "start": 3.0, "end": 2.0},  # start > end
        {"id": "2", "start": -1.0, "end": 4.0},  # negative
    ]
    ok, errors = validate_subtitles_integrity(invalid_subs)
    assert ok is False
    assert len(errors) >= 2

