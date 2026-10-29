import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.constants import (
    DialogueStatus,
    TimelineMode,
    AudioSeparationMode,
    VisualExtendMode,
)


class MediaInfo(BaseModel):
    """Media information extracted via ffprobe."""
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 30.0
    video_codec: str = ""
    audio_codec: str = ""
    audio_sample_rate: int = 44100
    audio_channels: int = 2
    has_video: bool = True
    has_audio: bool = True
    file_size_bytes: int = 0
    bitrate_kbps: int = 0


class DialogueSegment(BaseModel):
    """Represents a single dialogue line with stable ID and TTS metadata."""
    id: str = Field(default_factory=lambda: f"dlg_{uuid.uuid4().hex[:8]}")
    start: float = 0.0
    end: float = 0.0
    source_text: str = ""
    target_text: str = ""
    tts_audio_path: Optional[str] = None
    tts_duration: float = 0.0
    voice_id: str = ""
    status: str = DialogueStatus.PENDING
    error_message: Optional[str] = None
    visual_extend_mode: str = VisualExtendMode.FREEZE_LAST_FRAME

    @property
    def source_duration(self) -> float:
        return max(0.0, self.end - self.start)

    @property
    def duration_diff(self) -> float:
        """Difference between TTS duration and original source duration."""
        if self.tts_duration > 0:
            return round(self.tts_duration - self.source_duration, 4)
        return 0.0


class TimelineSegment(BaseModel):
    """Represents an atomic time block in the reconstructed dynamic timeline."""
    id: str = Field(default_factory=lambda: f"tl_{uuid.uuid4().hex[:8]}")
    dialogue_id: Optional[str] = None
    segment_type: str = "normal"  # 'normal', 'freeze_frame', 'gap'
    source_start: float = 0.0
    source_end: float = 0.0
    output_start: float = 0.0
    output_end: float = 0.0
    duration: float = 0.0
    tts_audio_path: Optional[str] = None
    action: str = "normal"  # 'normal', 'freeze_frame', 'pad'


class ProjectData(BaseModel):
    """Complete project data structure stored in project.json."""
    project_id: str = Field(default_factory=lambda: f"proj_{uuid.uuid4().hex[:8]}")
    name: str = "Untitled Project"
    project_dir: str = ""
    video_path: str = ""
    extracted_audio_path: Optional[str] = None
    vocal_stem_path: Optional[str] = None
    instrumental_path: Optional[str] = None
    media_info: Optional[MediaInfo] = None
    dialogues: List[DialogueSegment] = Field(default_factory=list)
    timeline_segments: List[TimelineSegment] = Field(default_factory=list)
    output_duration: float = 0.0
    timeline_mode: str = TimelineMode.DYNAMIC_DURATION
    separation_mode: str = AudioSeparationMode.DUCKING_ORIGINAL
    source_language: str = "auto"
    target_language: str = "vi"
    output_video_path: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    custom_settings: Dict[str, Any] = Field(default_factory=dict)

