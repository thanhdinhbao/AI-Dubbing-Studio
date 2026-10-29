import os
import re
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from app.utils.paths import get_default_logs_dir

API_KEY_PATTERN = re.compile(r"(sk-[a-zA-Z0-9_-]{10,}|key-[a-zA-Z0-9_-]{10,}|[a-zA-Z0-9_-]{32,})")


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data like API keys in logs."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = API_KEY_PATTERN.sub(lambda m: m.group(0)[:4] + "..." + m.group(0)[-4:], record.msg)
        return True


def setup_logging(log_filename: str = "app.log", log_level: int = logging.INFO) -> logging.Logger:
    """Setup application-wide logging with console and rotating file handler."""
    logs_dir = get_default_logs_dir()
    log_file_path = logs_dir / log_filename

    root_logger = logging.getLogger("AIDubbingStudio")
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers if called multiple times
    if root_logger.handlers:
        return root_logger

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    sensitive_filter = SensitiveDataFilter()

    # Rotating file handler (max 10MB, keep 5 backups)
    file_handler = RotatingFileHandler(
        str(log_file_path),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(sensitive_filter)
    file_handler.setLevel(log_level)
    root_logger.addHandler(file_handler)

    # Console handler (safe for UTF-8 and Vietnamese characters on Windows)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(sensitive_filter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    root_logger.info("Application logging initialized. Log file: %s", log_file_path)
    return root_logger

