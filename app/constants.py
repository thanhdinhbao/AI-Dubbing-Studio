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

# Supported Target Languages for Translation & Dubbing
SUPPORTED_TARGET_LANGUAGES = [
    {"code": "vi", "name": "🇻🇳 Tiếng Việt (Vietnamese)", "prompt_name": "tiếng Việt"},
    {"code": "en", "name": "🇺🇸 Tiếng Anh (English)", "prompt_name": "tiếng Anh (English)"},
    {"code": "ja", "name": "🇯🇵 Tiếng Nhật (Japanese)", "prompt_name": "tiếng Nhật (Japanese)"},
    {"code": "ko", "name": "🇰🇷 Tiếng Hàn (Korean)", "prompt_name": "tiếng Hàn (Korean)"},
    {"code": "zh-CN", "name": "🇨🇳 Tiếng Trung (Simplified Chinese)", "prompt_name": "tiếng Trung Giản thể (Simplified Chinese)"},
    {"code": "fr", "name": "🇫🇷 Tiếng Pháp (French)", "prompt_name": "tiếng Pháp (French)"},
    {"code": "de", "name": "🇩🇪 Tiếng Đức (German)", "prompt_name": "tiếng Đức (German)"},
    {"code": "es", "name": "🇪🇸 Tiếng Tây Ban Nha (Spanish)", "prompt_name": "tiếng Tây Ban Nha (Spanish)"},
    {"code": "ru", "name": "🇷🇺 Tiếng Nga (Russian)", "prompt_name": "tiếng Nga (Russian)"},
    {"code": "th", "name": "🇹🇭 Tiếng Thái (Thai)", "prompt_name": "tiếng Thái (Thai)"},
    {"code": "id", "name": "🇮🇩 Tiếng Indonesia (Indonesian)", "prompt_name": "tiếng Indonesia"}
]

# Edge TTS Multilingual Voices
EDGE_TTS_VOICES_BY_LANG = {
    "vi": [
        {"id": "vi-VN-HoaiMyNeural", "name": "Hoài My (Nữ - Tự nhiên)", "gender": "Female"},
        {"id": "vi-VN-NamMinhNeural", "name": "Nam Minh (Nam - Trầm ấm)", "gender": "Male"}
    ],
    "en": [
        {"id": "en-US-JennyNeural", "name": "Jenny (Nữ - Mỹ / Tự nhiên)", "gender": "Female"},
        {"id": "en-US-GuyNeural", "name": "Guy (Nam - Mỹ / Truyền cảm)", "gender": "Male"},
        {"id": "en-US-AriaNeural", "name": "Aria (Nữ - Mỹ / Tin tức)", "gender": "Female"},
        {"id": "en-GB-SoniaNeural", "name": "Sonia (Nữ - Anh)", "gender": "Female"},
        {"id": "en-GB-RyanNeural", "name": "Ryan (Nam - Anh)", "gender": "Male"}
    ],
    "ja": [
        {"id": "ja-JP-NanamiNeural", "name": "Nanami (Nữ - Nhật / Tự nhiên)", "gender": "Female"},
        {"id": "ja-JP-KeitaNeural", "name": "Keita (Nam - Nhật / Chuẩn)", "gender": "Male"}
    ],
    "ko": [
        {"id": "ko-KR-SunHiNeural", "name": "Sun-Hi (Nữ - Hàn / Truyền cảm)", "gender": "Female"},
        {"id": "ko-KR-InJoonNeural", "name": "InJoon (Nam - Hàn / Trầm ấm)", "gender": "Male"}
    ],
    "zh-CN": [
        {"id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao (Nữ - Phổ thông)", "gender": "Female"},
        {"id": "zh-CN-YunjianNeural", "name": "Yunjian (Nam - Phim tài liệu)", "gender": "Male"}
    ],
    "fr": [
        {"id": "fr-FR-DeniseNeural", "name": "Denise (Nữ - Pháp)", "gender": "Female"},
        {"id": "fr-FR-HenriNeural", "name": "Henri (Nam - Pháp)", "gender": "Male"}
    ],
    "de": [
        {"id": "de-DE-KatjaNeural", "name": "Katja (Nữ - Đức)", "gender": "Female"},
        {"id": "de-DE-ConradNeural", "name": "Conrad (Nam - Đức)", "gender": "Male"}
    ],
    "es": [
        {"id": "es-ES-ElviraNeural", "name": "Elvira (Nữ - Tây Ban Nha)", "gender": "Female"},
        {"id": "es-ES-AlvaroNeural", "name": "Alvaro (Nam - Tây Ban Nha)", "gender": "Male"}
    ],
    "ru": [
        {"id": "ru-RU-SvetlanaNeural", "name": "Svetlana (Nữ - Nga)", "gender": "Female"},
        {"id": "ru-RU-DmitryNeural", "name": "Dmitry (Nam - Nga)", "gender": "Male"}
    ],
    "th": [
        {"id": "th-TH-PremwadeeNeural", "name": "Premwadee (Nữ - Thái)", "gender": "Female"},
        {"id": "th-TH-NiwatNeural", "name": "Niwat (Nam - Thái)", "gender": "Male"}
    ],
    "id": [
        {"id": "id-ID-GadisNeural", "name": "Gadis (Nữ - Indonesia)", "gender": "Female"},
        {"id": "id-ID-ArdiNeural", "name": "Ardi (Nam - Indonesia)", "gender": "Male"}
    ]
}

# Legacy alias for backward compatibility
EDGE_TTS_VIETNAMESE_VOICES = EDGE_TTS_VOICES_BY_LANG["vi"]

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

