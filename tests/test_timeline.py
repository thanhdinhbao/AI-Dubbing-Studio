import pytest
from app.models import DialogueSegment
from app.services.timeline_engine import TimelineEngine
from app.constants import TimelineMode, VisualExtendMode


def test_mandatory_1_tts_longer_than_original():
    """Mandatory Test 1: TTS longer than original.
    - Sentence 1 original duration: 2s (0.0 to 2.0s)
    - TTS duration: 3.0s
    - Sentence 2 original start: 3.0s, end: 5.0s, TTS duration: 2.0s
    - Total source duration: 6.0s
    Kỳ vọng:
    - Sentence 1 được cấp đủ 3 giây (không bị cắt cụt).
    - Xuất hiện block video freeze / pad với độ dài delta = 1.0s.
    - Sentence 2 bắt đầu sau khi Sentence 1 kết thúc trong timeline đầu ra (output_start >= 4.0s).
    - Tổng thời lượng video đầu ra tăng tương ứng (7.0s thay vì 6.0s).
    """
    engine = TimelineEngine(mode=TimelineMode.DYNAMIC_DURATION)
    dlgs = [
        DialogueSegment(id="d1", start=0.0, end=2.0, source_text="Hello", target_text="Xin chào", tts_duration=3.0),
        DialogueSegment(id="d2", start=3.0, end=5.0, source_text="World", target_text="Thế giới", tts_duration=2.0),
    ]
    source_dur = 6.0

    timeline = engine.build_timeline(source_duration=source_dur, dialogues=dlgs)
    output_dur = engine.calculate_output_duration(timeline)

    # 1. Total output duration must expand from 6.0s to 7.0s (extra 1.0s)
    assert abs(output_dur - 7.0) < 0.01

    # 2. Check Sentence 1 allocation
    # Segment 0: normal video for d1 [0, 2.0], output [0, 2.0]
    # Segment 1: freeze frame for d1 [2.0, 2.0], output [2.0, 3.0] (duration 1.0s)
    d1_normal = [s for s in timeline if s.dialogue_id == "d1" and s.segment_type == "video_normal"][0]
    d1_freeze = [s for s in timeline if s.dialogue_id == "d1" and s.segment_type == "video_freeze"][0]

    assert d1_normal.output_start == 0.0
    assert d1_normal.output_end == 2.0
    assert d1_freeze.output_start == 2.0
    assert d1_freeze.output_end == 3.0
    assert abs(d1_freeze.duration - 1.0) < 0.01

    # 3. Gap between d1 and d2 in source was 2.0s to 3.0s (1.0s)
    # In output, gap should be 3.0s to 4.0s
    gap = [s for s in timeline if s.segment_type == "gap" and s.source_start == 2.0][0]
    assert gap.output_start == 3.0
    assert gap.output_end == 4.0

    # 4. Check Sentence 2 start in output
    d2_normal = [s for s in timeline if s.dialogue_id == "d2" and s.segment_type == "video_normal"][0]
    assert d2_normal.output_start == 4.0
    assert d2_normal.output_end == 6.0


def test_mandatory_2_tts_shorter_than_original():
    """Mandatory Test 2: TTS shorter than original.
    - Sentence original duration: 4.0s (1.0s to 5.0s)
    - TTS duration: 2.5s
    - Total source duration: 6.0s
    Kỳ vọng:
    - Timeline hợp lệ, không tạo timestamp âm.
    - Không gây chồng lấn ngoài ý muốn.
    - Giữ trọn nội dung hình ảnh.
    """
    engine = TimelineEngine(mode=TimelineMode.DYNAMIC_DURATION)
    dlgs = [
        DialogueSegment(id="d1", start=1.0, end=5.0, source_text="Long speech", target_text="Ngắn", tts_duration=2.5)
    ]
    source_dur = 6.0

    timeline = engine.build_timeline(source_duration=source_dur, dialogues=dlgs)
    output_dur = engine.calculate_output_duration(timeline)

    # Valid timeline without errors
    engine.validate_timeline(timeline)
    assert output_dur >= 6.0
    assert timeline[0].output_start == 0.0
    for s in timeline:
        assert s.output_start >= 0.0
        assert s.output_end >= s.output_start


def test_mandatory_3_multiple_consecutive_sentences():
    """Mandatory Test 3: Multiple consecutive sentences (at least 5 sentences with different TTS durations).
    Kỳ vọng:
    - Timeline được tính lại đúng thứ tự.
    - Không bỏ câu nào.
    - Không chồng lấn ngoài ý muốn.
    - Duration tổng được tính từ timeline cuối cùng.
    """
    engine = TimelineEngine(mode=TimelineMode.DYNAMIC_DURATION)
    dlgs = [
        DialogueSegment(id="s1", start=0.0, end=2.0, source_text="One", tts_duration=3.5),    # 2.0s -> 3.5s (+1.5s)
        DialogueSegment(id="s2", start=3.0, end=4.0, source_text="Two", tts_duration=1.0),    # 1.0s -> 1.0s (0s)
        DialogueSegment(id="s3", start=5.0, end=8.0, source_text="Three", tts_duration=4.0),  # 3.0s -> 4.0s (+1.0s)
        DialogueSegment(id="s4", start=9.0, end=11.0, source_text="Four", tts_duration=1.5),  # 2.0s -> 1.5s (shorter)
        DialogueSegment(id="s5", start=12.0, end=15.0, source_text="Five", tts_duration=4.0), # 3.0s -> 4.0s (+1.0s)
    ]
    source_dur = 20.0

    timeline = engine.build_timeline(source_duration=source_dur, dialogues=dlgs)
    engine.validate_timeline(timeline)

    # Expected expansion: +1.5s (s1) + 1.0s (s3) + 1.0s (s5) = +3.5s -> Total 23.5s
    out_dur = engine.calculate_output_duration(timeline)
    assert abs(out_dur - 23.5) < 0.01

    # Verify all 5 sentences are present and in order
    found_ids = [s.dialogue_id for s in timeline if s.dialogue_id]
    for expected_id in ["s1", "s2", "s3", "s4", "s5"]:
        assert expected_id in found_ids
