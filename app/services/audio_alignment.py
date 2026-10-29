import re
import logging
from pathlib import Path
from typing import List, Optional

from app.models import DialogueSegment, TimelineSegment
from app.utils.timecode import seconds_to_srt_time, srt_time_to_seconds

logger = logging.getLogger("AIDubbingStudio.AudioAlignment")


class AudioAlignmentService:
    """Aligns audio dialogues and updates subtitle timestamps for the final dynamic output."""

    @staticmethod
    def align_dialogues_to_output(
        dialogues: List[DialogueSegment],
        timeline: List[TimelineSegment]
    ) -> List[DialogueSegment]:
        """Map each dialogue to its new output start and end times according to the dynamic timeline."""
        dlg_map = {}
        for seg in timeline:
            if seg.dialogue_id and seg.dialogue_id not in dlg_map:
                if seg.segment_type in ("video_normal", "normal"):
                    dlg_map[seg.dialogue_id] = seg

        aligned_list: List[DialogueSegment] = []
        for dlg in dialogues:
            aligned = dlg.model_copy()
            if dlg.id in dlg_map:
                seg = dlg_map[dlg.id]
                aligned.start = round(seg.output_start, 3)
                # Output end covers the full TTS duration
                tts_dur = dlg.tts_duration if dlg.tts_duration > 0 else (dlg.end - dlg.start)
                aligned.end = round(aligned.start + tts_dur, 3)
            aligned_list.append(aligned)

        return aligned_list

    @staticmethod
    def export_srt(dialogues: List[DialogueSegment], output_path: str | Path, use_vietnamese: bool = True) -> str:
        """Export dialogues to standard SRT subtitle file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        for idx, dlg in enumerate(dialogues, 1):
            start_str = seconds_to_srt_time(dlg.start)
            end_str = seconds_to_srt_time(dlg.end)
            text = (dlg.target_text if use_vietnamese and dlg.target_text else dlg.source_text).strip()

            lines.append(str(idx))
            lines.append(f"{start_str} --> {end_str}")
            lines.append(text)
            lines.append("")

        content = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Exported SRT with {len(dialogues)} subtitles to {output_path}")
        return str(output_path)

    @staticmethod
    def import_srt(srt_path: str | Path) -> List[DialogueSegment]:
        """Parse SRT file into DialogueSegment list."""
        srt_path = Path(srt_path)
        if not srt_path.exists():
            raise FileNotFoundError(f"SRT file not found: {srt_path}")

        with open(srt_path, "r", encoding="utf-8-sig") as f:
            content = f.read()

        blocks = re.split(r"\n\s*\n", content.strip())
        dialogues: List[DialogueSegment] = []

        for block in blocks:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if len(lines) < 2:
                continue

            time_line = lines[1] if "-->" in lines[1] else (lines[0] if "-->" in lines[0] else None)
            if not time_line:
                continue

            parts = time_line.split("-->")
            if len(parts) != 2:
                continue

            start_sec = srt_time_to_seconds(parts[0].strip())
            end_sec = srt_time_to_seconds(parts[1].strip())
            text_lines = lines[2:] if time_line == lines[1] else lines[1:]
            text = " ".join(text_lines).strip()

            dialogues.append(DialogueSegment(
                start=start_sec,
                end=end_sec,
                source_text=text,
                target_text="",
            ))

        logger.info(f"Imported {len(dialogues)} dialogue segments from SRT.")
        return dialogues
