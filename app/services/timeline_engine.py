import logging
from typing import List, Dict, Any, Optional, Tuple

from app.models import DialogueSegment, TimelineSegment
from app.constants import TimelineMode, VisualExtendMode
from app.exceptions import TimelineError

logger = logging.getLogger("AIDubbingStudio.TimelineEngine")


class TimelineEngine:
    """Core Dynamic Duration Engine that reconstructs video and audio timelines
    to adapt naturally to Vietnamese TTS length without distorting video pitch or speed.
    """

    def __init__(self, mode: str = TimelineMode.DYNAMIC_DURATION):
        self.mode = mode

    def build_timeline(
        self,
        source_duration: float,
        dialogues: List[DialogueSegment],
        options: Optional[Dict[str, Any]] = None
    ) -> List[TimelineSegment]:
        """Construct the dynamic timeline segments from source video duration and dialogue TTS durations."""
        opts = options or {}
        extend_mode = opts.get("visual_extend_mode", VisualExtendMode.FREEZE_LAST_FRAME)
        allow_contraction = opts.get("allow_contraction", False)

        # Sort dialogues by start time
        sorted_dialogues = sorted(dialogues, key=lambda d: d.start)

        timeline_segments: List[TimelineSegment] = []
        current_source_time = 0.0
        current_output_time = 0.0

        for idx, dlg in enumerate(sorted_dialogues):
            dlg_start = max(0.0, dlg.start)
            dlg_end = max(dlg_start, dlg.end)

            # 1. Handle preceding gap (silent video interval before dialogue)
            if dlg_start > current_source_time:
                gap_duration = dlg_start - current_source_time
                if gap_duration > 0.001:
                    seg = TimelineSegment(
                        dialogue_id=None,
                        segment_type="gap",
                        source_start=current_source_time,
                        source_end=dlg_start,
                        output_start=current_output_time,
                        output_end=current_output_time + gap_duration,
                        duration=gap_duration,
                        action="normal"
                    )
                    timeline_segments.append(seg)
                    current_output_time += gap_duration
                current_source_time = dlg_start

            # 2. Handle dialogue segment
            source_dur = dlg_end - dlg_start
            tts_dur = dlg.tts_duration if (dlg.tts_duration and dlg.tts_duration > 0) else source_dur

            if self.mode == TimelineMode.DYNAMIC_DURATION:
                if tts_dur > source_dur:
                    # TTS is longer than original audio: DYNAMIC EXPANSION
                    # Segment 2a: Normal video playback of original dialogue
                    seg_normal = TimelineSegment(
                        dialogue_id=dlg.id,
                        segment_type="video_normal",
                        source_start=dlg_start,
                        source_end=dlg_end,
                        output_start=current_output_time,
                        output_end=current_output_time + source_dur,
                        duration=source_dur,
                        tts_audio_path=dlg.tts_audio_path,
                        action="normal"
                    )
                    timeline_segments.append(seg_normal)
                    current_output_time += source_dur

                    # Segment 2b: Visual freeze/hold block for the extra time delta
                    delta = tts_dur - source_dur
                    seg_freeze = TimelineSegment(
                        dialogue_id=dlg.id,
                        segment_type="video_freeze",
                        source_start=dlg_end,
                        source_end=dlg_end,
                        output_start=current_output_time,
                        output_end=current_output_time + delta,
                        duration=delta,
                        tts_audio_path=None,
                        action="freeze_frame"
                    )
                    timeline_segments.append(seg_freeze)
                    current_output_time += delta

                elif tts_dur < source_dur and allow_contraction:
                    # Contracted playback if explicitly enabled
                    seg_contract = TimelineSegment(
                        dialogue_id=dlg.id,
                        segment_type="video_normal",
                        source_start=dlg_start,
                        source_end=dlg_start + tts_dur,
                        output_start=current_output_time,
                        output_end=current_output_time + tts_dur,
                        duration=tts_dur,
                        tts_audio_path=dlg.tts_audio_path,
                        action="normal"
                    )
                    timeline_segments.append(seg_contract)
                    current_output_time += tts_dur
                else:
                    # TTS is equal or shorter without video contraction (preserves original video pacing)
                    seg_normal = TimelineSegment(
                        dialogue_id=dlg.id,
                        segment_type="video_normal",
                        source_start=dlg_start,
                        source_end=dlg_end,
                        output_start=current_output_time,
                        output_end=current_output_time + source_dur,
                        duration=source_dur,
                        tts_audio_path=dlg.tts_audio_path,
                        action="normal"
                    )
                    timeline_segments.append(seg_normal)
                    current_output_time += source_dur
            else:
                # PRESERVE DURATION MODE
                seg_fixed = TimelineSegment(
                    dialogue_id=dlg.id,
                    segment_type="video_normal",
                    source_start=dlg_start,
                    source_end=dlg_end,
                    output_start=current_output_time,
                    output_end=current_output_time + source_dur,
                    duration=source_dur,
                    tts_audio_path=dlg.tts_audio_path,
                    action="normal"
                )
                timeline_segments.append(seg_fixed)
                current_output_time += source_dur

            current_source_time = dlg_end

        # 3. Handle trailing video segment after last dialogue
        if current_source_time < source_duration:
            tail_duration = source_duration - current_source_time
            if tail_duration > 0.001:
                tail_seg = TimelineSegment(
                    dialogue_id=None,
                    segment_type="gap",
                    source_start=current_source_time,
                    source_end=source_duration,
                    output_start=current_output_time,
                    output_end=current_output_time + tail_duration,
                    duration=tail_duration,
                    action="normal"
                )
                timeline_segments.append(tail_seg)
                current_output_time += tail_duration

        self.validate_timeline(timeline_segments)
        logger.info(
            f"Built dynamic timeline: {len(timeline_segments)} segments | "
            f"Source: {source_duration:.2f}s -> Output: {current_output_time:.2f}s "
            f"(Delta: {current_output_time - source_duration:+.2f}s)"
        )
        return timeline_segments

    def map_source_time(self, source_time: float, timeline: List[TimelineSegment]) -> float:
        """Map a time in the original source video to its new time in the output video."""
        if not timeline:
            return source_time

        for seg in timeline:
            if seg.segment_type in ("video_normal", "gap"):
                if seg.source_start <= source_time <= seg.source_end:
                    offset = source_time - seg.source_start
                    return seg.output_start + offset

        # If beyond last segment, extrapolate from last segment's end
        last = timeline[-1]
        return last.output_end + max(0.0, source_time - last.source_end)

    def calculate_output_duration(self, timeline: List[TimelineSegment]) -> float:
        """Calculate total output video duration from timeline."""
        if not timeline:
            return 0.0
        return round(timeline[-1].output_end, 4)

    def validate_timeline(self, timeline: List[TimelineSegment]):
        """Validate timeline integrity: non-negative times, monotonicity, valid durations."""
        if not timeline:
            return

        for idx, seg in enumerate(timeline):
            if seg.output_start < 0 or seg.output_end < 0:
                raise TimelineError(f"Segment #{idx} có mốc thời gian âm: [{seg.output_start}, {seg.output_end}]")

            if seg.output_end < seg.output_start:
                raise TimelineError(
                    f"Segment #{idx} có output_end ({seg.output_end}) nhỏ hơn output_start ({seg.output_start})"
                )

            if idx > 0:
                prev = timeline[idx - 1]
                # Small epsilon check for floating point rounding
                if seg.output_start < prev.output_end - 0.005:
                    raise TimelineError(
                        f"Phát hiện chồng lấn timeline giữa segment #{idx-1} (kết thúc {prev.output_end}) "
                        f"và segment #{idx} (bắt đầu {seg.output_start})"
                    )

    def detect_conflicts(self, dialogues: List[DialogueSegment]) -> List[str]:
        """Detect overlapping dialogues in the source video."""
        conflicts = []
        sorted_dlgs = sorted(dialogues, key=lambda d: d.start)
        for i in range(len(sorted_dlgs) - 1):
            curr = sorted_dlgs[i]
            nxt = sorted_dlgs[i + 1]
            if curr.end > nxt.start + 0.05:
                conflicts.append(
                    f"Câu ID '{curr.id}' (kết thúc lúc {curr.end:.2f}s) chồng lấn với câu ID '{nxt.id}' (bắt đầu lúc {nxt.start:.2f}s)"
                )
        return conflicts

