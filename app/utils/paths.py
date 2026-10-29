import os
import sys
import re
import shutil
from pathlib import Path


def get_app_root() -> Path:
    """Return the absolute path to the application tool root directory.
    Compatible with normal Python execution and PyInstaller bundled executable.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # Path to voice-dubbing tool root folder
    return Path(__file__).resolve().parent.parent.parent


def get_user_data_dir() -> Path:
    """Return the tool root directory for storing configurations, logs, projects, and cache."""
    data_dir = get_app_root()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_default_projects_dir() -> Path:
    """Return the projects directory located inside the tool folder."""
    p = get_app_root() / "projects"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_default_output_dir() -> Path:
    """Return the output directory located inside the tool folder."""
    p = get_app_root() / "output"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_default_cache_dir() -> Path:
    """Return the cache directory located inside the tool folder."""
    p = get_app_root() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_default_logs_dir() -> Path:
    """Return the logs directory located inside the tool folder."""
    p = get_app_root() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_default_models_dir() -> Path:
    """Return the models directory located inside the tool folder."""
    p = get_app_root() / "models"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_default_cloned_voices_dir() -> Path:
    """Return the cloned voices storage directory inside models."""
    p = get_default_models_dir() / "cloned_voices"
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_directories():
    """Ensure standard runtime directories exist."""
    get_user_data_dir()
    get_default_projects_dir()
    get_default_output_dir()
    get_default_cache_dir()
    get_default_logs_dir()
    get_default_models_dir()
    get_default_cloned_voices_dir()


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """Sanitize string to be safe for Windows file and folder names."""
    # Replace illegal Windows characters: < > : " / \ | ? *
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    clean = clean.strip(". ")
    if not clean:
        clean = "untitled"
    return clean[:max_length]


def get_disk_free_space_gb(path: str | Path) -> float:
    """Get free disk space in Gigabytes for the volume containing the given path."""
    try:
        total, used, free = shutil.disk_usage(str(path))
        return round(free / (1024 ** 3), 2)
    except Exception:
        return 0.0

