"""Application Constants"""

APP_NAME = "AI Dubbing Studio"
APP_VERSION = "1.0.0"
AUTHOR = "AI Dubbing Studio Team"

# Supported Media Formats
SUPPORTED_VIDEO_EXTENSIONS = [".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".ts"]
SUPPORTED_AUDIO_EXTENSIONS = [".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"]

# ASR Constants
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
WHISPER_DEVICES = ["cpu", "cuda"]
WHISPER_COMPUTE_TYPES = ["int8", "float16", "float32", "default"]

# Supported Translation Backends
TRANSLATION_BACKENDS = ["openai_compatible", "offline_model"]

# Supported TTS Backends
TTS_BACKENDS = ["edge_tts", "vieneu", "openai_compatible", "offline_engine"]

# Edge TTS Vietnamese Voices
EDGE_TTS_VIETNAMESE_VOICES = [
    {"id": "vi-VN-HoaiMyNeural", "name": "Hoài My (Nữ - Tự nhiên)", "gender": "Female"},
    {"id": "vi-VN-NamMinhNeural", "name": "Nam Minh (Nam - Trầm ấm)", "gender": "Male"}
]

# VieNeu Vietnamese Voices (25 Preset Voices chính thức từ VieNeu SDK v3 Turbo)
VIENEU_VIETNAMESE_VOICES = [
    # --- ⭐ Editors' Picks (Khuyến nghị hàng đầu) ---
    {"id": "Hải Đăng", "name": "⭐ Hải Đăng (Minh Quân Pro) — Nam · Bắc · Tự nhiên (Mặc định)", "gender": "Male", "region": "Miền Bắc"},
    {"id": "Mai Anh", "name": "⭐ Mai Anh — Nữ · Bắc · Tin tức / Thuyết minh", "gender": "Female", "region": "Miền Bắc"},
    {"id": "Trúc Ly", "name": "⭐ Trúc Ly — Nữ · Bắc · Truyền cảm tự nhiên", "gender": "Female", "region": "Miền Bắc"},
    {"id": "Thiện Minh", "name": "⭐ Thiện Minh (Anh Khôi) — Nam · Bắc · Kể chuyện / Phim", "gender": "Male", "region": "Miền Bắc"},
    {"id": "Thùy Dung", "name": "⭐ Thùy Dung — Nữ · Nam · Tin tức / Phim tài liệu", "gender": "Female", "region": "Miền Nam"},
    {"id": "Quang Sơn", "name": "⭐ Quang Sơn — Nam · Trung · Tự nhiên", "gender": "Male", "region": "Miền Trung"},
    {"id": "Ngọc Trân", "name": "⭐ Ngọc Trân — Nữ · Trung · Dịu dàng tự nhiên", "gender": "Female", "region": "Miền Trung"},
    {"id": "Adam bựa", "name": "⭐ Adam bựa — Nam · Bắc · Hài hước / Review", "gender": "Male", "region": "Miền Bắc"},
    {"id": "Thiền Tâm Đức", "name": "⭐ Thiền Tâm Đức — Nam · Bắc · Trầm ấm kể chuyện", "gender": "Male", "region": "Miền Bắc"},
    {"id": "Ngọc Huyền", "name": "⭐ Ngọc Huyền — Nữ · Bắc · Trong trẻo tự nhiên", "gender": "Female", "region": "Miền Bắc"},

    # --- 🎙 Miền Bắc ---
    {"id": "Phạm Tuyên", "name": "Phạm Tuyên — Nam · Bắc · Tự nhiên", "gender": "Male", "region": "Miền Bắc"},
    {"id": "Minh Đức", "name": "Minh Đức — Nam · Bắc · Tin tức", "gender": "Male", "region": "Miền Bắc"},
    {"id": "Xuân Vĩnh", "name": "Xuân Vĩnh — Nam · Bắc · Tự nhiên", "gender": "Male", "region": "Miền Bắc"},
    {"id": "Thanh Bình", "name": "Thanh Bình — Nam · Bắc · Kể chuyện", "gender": "Male", "region": "Miền Bắc"},
    {"id": "Ngọc Linh", "name": "Ngọc Linh — Nữ · Bắc · Kể chuyện", "gender": "Female", "region": "Miền Bắc"},
    {"id": "Đoan Trang", "name": "Đoan Trang — Nữ · Bắc · Tự nhiên", "gender": "Female", "region": "Miền Bắc"},
    {"id": "Quỳnh Anh", "name": "Quỳnh Anh — Nữ · Bắc · Đọc truyện", "gender": "Female", "region": "Miền Bắc"},
    {"id": "Quốc Tuấn", "name": "Quốc Tuấn (Mạnh Dũng) — Nam · Bắc · Chững chạc", "gender": "Male", "region": "Miền Bắc"},

    # --- 🎙 Miền Nam ---
    {"id": "Adam", "name": "Adam — Nam · Nam · Tự nhiên", "gender": "Male", "region": "Miền Nam"},
    {"id": "Thái Sơn", "name": "Thái Sơn — Nam · Nam · Kể chuyện", "gender": "Male", "region": "Miền Nam"},
    {"id": "Thục Đoan", "name": "Thục Đoan — Nữ · Nam · Dịu dàng", "gender": "Female", "region": "Miền Nam"},
    {"id": "Minh Triết", "name": "Minh Triết — Nam · Nam · Tin tức", "gender": "Male", "region": "Miền Nam"},
    {"id": "Mỹ Duyên", "name": "Mỹ Duyên — Nữ · Nam · Đọc truyện", "gender": "Female", "region": "Miền Nam"},
    {"id": "Đức Trí", "name": "Đức Trí — Nam · Nam · Đọc truyện", "gender": "Male", "region": "Miền Nam"},
    {"id": "Kim Thanh", "name": "Kim Thanh — Nữ · Nam · Đọc truyện", "gender": "Female", "region": "Miền Nam"}
]

# Timeline Modes
class TimelineMode:
    DYNAMIC_DURATION = "dynamic_duration"
    PRESERVE_DURATION = "preserve_duration"

# Video Processing Actions for Dynamic Extension
class VisualExtendMode:
    FREEZE_LAST_FRAME = "freeze_last_frame"
    HOLD_AND_PAD = "hold_and_pad"
    SPEED_ADJUST = "speed_adjust"

# Audio Mixing Modes
class AudioSeparationMode:
    DEMUCS_SEPARATION = "demucs_separation"
    DUCKING_ORIGINAL = "ducking_original"
    KEEP_ORIGINAL_LOW = "keep_original_low"
    MUTE_ORIGINAL = "mute_original"

# Dialogue Status
class DialogueStatus:
    PENDING = "pending"
    TRANSCRIBED = "transcribed"
    TRANSLATED = "translated"
    SYNTHESIZED = "synthesized"
    MODIFIED = "modified"
    ERROR = "error"

# Default Media Specs
DEFAULT_AUDIO_SAMPLE_RATE = 44100
DEFAULT_AUDIO_CHANNELS = 2
DEFAULT_VIDEO_FPS = 30.0
DEFAULT_VIDEO_CODEC = "libx264"
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_AUDIO_BITRATE = "192k"
DEFAULT_VIDEO_PRESET = "medium"
DEFAULT_VIDEO_CRF = 20

