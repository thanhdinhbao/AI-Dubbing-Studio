import os
import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.constants import APP_NAME, APP_VERSION
from app.logging_config import setup_logging
from app.utils.paths import ensure_directories
from app.utils.ffmpeg_utils import check_ffmpeg_available, set_custom_ffmpeg_paths
from app.utils.audio_utils import patch_pyav_metadata_errors
from app.config import app_config
from app.ui.styles import DARK_THEME
from app.ui.main_window import MainWindow

logger = logging.getLogger("AIDubbingStudio.Bootstrap")


def setup_cuda_dll_paths() -> None:
    """Register NVIDIA CUDA runtime DLL directories from site-packages on Windows."""
    if sys.platform != "win32":
        return
    try:
        site_packages = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
        if site_packages.is_dir():
            for p in site_packages.glob("**/bin"):
                if p.is_dir():
                    try:
                        os.add_dll_directory(str(p))
                    except Exception:
                        pass
                    os.environ["PATH"] = str(p) + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass


def bootstrap_app() -> tuple[QApplication, MainWindow]:
    """Initialize application environment, logging, settings and return Qt Application and MainWindow."""
    # 1. Setup logging
    setup_logging(log_filename="app.log")
    logger.info(f"=== Starting {APP_NAME} v{APP_VERSION} ===")

    # 2. Ensure directories & apply third-party compatibility patches
    ensure_directories()
    patch_pyav_metadata_errors()
    setup_cuda_dll_paths()

    # 3. Apply custom configured FFmpeg paths if set
    set_custom_ffmpeg_paths(
        app_config.get("ffmpeg_path"),
        app_config.get("ffprobe_path")
    )
    ff_res = check_ffmpeg_available()
    if ff_res["ffmpeg"] and ff_res["ffprobe"]:
        logger.info(f"FFmpeg detected: {ff_res['ffmpeg_version']}")
    else:
        logger.warning(f"FFmpeg not found in PATH or config: {ff_res.get('error')}")

    # 4. Initialize PySide6
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setStyleSheet(DARK_THEME)

    # 5. Create Main Window
    window = MainWindow()
    return app, window

