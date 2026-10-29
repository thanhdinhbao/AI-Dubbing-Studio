import pytest
from app.models import DialogueSegment, TimelineSegment
from app.services.audio_alignment import AudioAlignmentService


def test_align_dialogues_to_output():
    dlgs = [
        DialogueSegment(id="d1", start=1.0, end=3.0, tts_duration=4.0),
        DialogueSegment(id="d2", start=5.0, end=7.0, tts_duration=2.0),
    ]

    # Suppose dynamic timeline mapped d1 to output 1.0 -> 5.0, and d2 to output 7.0 -> 9.0
    timeline = [
        TimelineSegment(dialogue_id="d1", segment_type="video_normal", source_start=1.0, source_end=3.0, output_start=1.0, output_end=3.0, duration=2.0),
        TimelineSegment(dialogue_id="d1", segment_type="video_freeze", source_start=3.0, source_end=3.0, output_start=3.0, output_end=5.0, duration=2.0),
        TimelineSegment(dialogue_id=None, segment_type="gap", source_start=3.0, source_end=5.0, output_start=5.0, output_end=7.0, duration=2.0),
        TimelineSegment(dialogue_id="d2", segment_type="video_normal", source_start=5.0, source_end=7.0, output_start=7.0, output_end=9.0, duration=2.0),
    ]

    aligned = AudioAlignmentService.align_dialogues_to_output(dlgs, timeline)

    assert len(aligned) == 2
    assert aligned[0].id == "d1"
    assert aligned[0].start == 1.0
    assert aligned[0].end == 5.0  # 1.0 + 4.0s tts_duration

    assert aligned[1].id == "d2"
    assert aligned[1].start == 7.0
    assert aligned[1].end == 9.0  # 7.0 + 2.0s tts_duration

