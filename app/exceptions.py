"""Custom Exceptions for AI Dubbing Studio"""

class DubbingStudioError(Exception):
    """Base exception for all AI Dubbing Studio errors."""
    def __init__(self, message: str, details: str = "", error_code: str = "ERR_GENERAL"):
        super().__init__(message)
        self.message = message
        self.details = details
        self.error_code = error_code

    def __str__(self):
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class FFmpegNotFoundError(DubbingStudioError):
    """Raised when FFmpeg or FFprobe executable is not found."""
    def __init__(self, binary_name: str = "ffmpeg"):
        super().__init__(
            message=f"Không tìm thấy công cụ media bắt buộc: '{binary_name}' trong hệ thống.",
            details="Hãy cài đặt FFmpeg và thêm vào PATH hệ thống hoặc cấu hình đường dẫn trong Cài đặt.",
            error_code="ERR_FFMPEG_NOT_FOUND"
        )


class MediaProbeError(DubbingStudioError):
    """Raised when media analysis fails."""
    pass


class InvalidMediaError(DubbingStudioError):
    """Raised when file is corrupt or invalid format."""
    pass


class AudioExtractionError(DubbingStudioError):
    """Raised when audio extraction from video fails."""
    pass


class TranscriptionError(DubbingStudioError):
    """Raised when speech recognition fails."""
    pass


class TranslationError(DubbingStudioError):
    """Raised when translation fails."""
    pass


class TTSError(DubbingStudioError):
    """Raised when TTS generation fails."""
    pass


class SourceSeparationError(DubbingStudioError):
    """Raised during vocal separation."""
    pass


class TimelineError(DubbingStudioError):
    """Raised during timeline calculations or conflict detection."""
    pass


class AudioMixerError(DubbingStudioError):
    """Raised during audio mixing."""
    pass


class RenderError(DubbingStudioError):
    """Raised during final video rendering."""
    pass


class ProjectError(DubbingStudioError):
    """Raised when project file saving/loading fails."""
    pass

