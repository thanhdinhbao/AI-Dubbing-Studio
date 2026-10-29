import os
import sys
import shutil
import subprocess
import threading
import logging
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from app.exceptions import FFmpegNotFoundError

logger = logging.getLogger("AIDubbingStudio.FFmpegUtils")

# Cache resolved paths
_FFMPEG_PATH: Optional[str] = None
_FFPROBE_PATH: Optional[str] = None


def set_custom_ffmpeg_paths(ffmpeg_path: Optional[str], ffprobe_path: Optional[str] = None):
    """Set custom user-configured paths for ffmpeg and ffprobe."""
    global _FFMPEG_PATH, _FFPROBE_PATH
    if ffmpeg_path and os.path.exists(ffmpeg_path):
        _FFMPEG_PATH = os.path.abspath(ffmpeg_path)
    if ffprobe_path and os.path.exists(ffprobe_path):
        _FFPROBE_PATH = os.path.abspath(ffprobe_path)


def find_executable(name: str) -> str:
    """Find the path to an executable (ffmpeg or ffprobe).
    Checks:
    1. Globally overridden paths
    2. Bundled directory if packaged with PyInstaller
    3. System PATH
    """
    global _FFMPEG_PATH, _FFPROBE_PATH
    exe_name = f"{name}.exe" if sys.platform == "win32" and not name.endswith(".exe") else name

    if name.startswith("ffmpeg") and _FFMPEG_PATH and os.path.exists(_FFMPEG_PATH):
        return _FFMPEG_PATH
    if name.startswith("ffprobe") and _FFPROBE_PATH and os.path.exists(_FFPROBE_PATH):
        return _FFPROBE_PATH

    # Check next to executable if frozen
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidate = exe_dir / exe_name
        if candidate.exists():
            return str(candidate)
        # Check bundled ffmpeg subfolder
        candidate = exe_dir / "ffmpeg" / exe_name
        if candidate.exists():
            return str(candidate)

    # Check system PATH
    found = shutil.which(name)
    if found:
        return os.path.abspath(found)

    raise FFmpegNotFoundError(name)


def get_ffmpeg_path() -> str:
    return find_executable("ffmpeg")


def get_ffprobe_path() -> str:
    return find_executable("ffprobe")


def check_ffmpeg_available() -> Dict[str, Any]:
    """Test availability of ffmpeg and ffprobe and return versions."""
    res = {
        "ffmpeg": False,
        "ffprobe": False,
        "ffmpeg_path": "",
        "ffprobe_path": "",
        "ffmpeg_version": "",
        "ffprobe_version": "",
        "error": None
    }
    try:
        ffmpeg_p = get_ffmpeg_path()
        res["ffmpeg_path"] = ffmpeg_p
        out = subprocess.check_output([ffmpeg_p, "-version"], stderr=subprocess.STDOUT, text=True, errors="replace")
        res["ffmpeg_version"] = out.split("\n")[0]
        res["ffmpeg"] = True
    except Exception as e:
        res["error"] = str(e)

    try:
        ffprobe_p = get_ffprobe_path()
        res["ffprobe_path"] = ffprobe_p
        out = subprocess.check_output([ffprobe_p, "-version"], stderr=subprocess.STDOUT, text=True, errors="replace")
        res["ffprobe_version"] = out.split("\n")[0]
        res["ffprobe"] = True
    except Exception as e:
        if not res["error"]:
            res["error"] = str(e)

    return res


def run_ffmpeg_process(
    args: List[str],
    on_progress: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None
) -> subprocess.CompletedProcess:
    """Run an FFmpeg or FFprobe command using argument list.
    Supports real-time output reading and safe cancellation.
    """
    logger.debug("Executing FFmpeg command: %s", " ".join(f'"{a}"' if " " in a else a for a in args))

    # Windows flags to prevent opening console window
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW

    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags
    )

    stdout_lines = []
    stderr_lines = []

    def read_stream(stream, accumulator, is_stderr=True):
        try:
            for line in iter(stream.readline, ''):
                if line:
                    clean_line = line.strip()
                    accumulator.append(clean_line)
                    if on_progress:
                        on_progress(clean_line)
            stream.close()
        except Exception:
            pass

    t_err = threading.Thread(target=read_stream, args=(process.stderr, stderr_lines, True), daemon=True)
    t_out = threading.Thread(target=read_stream, args=(process.stdout, stdout_lines, False), daemon=True)
    t_err.start()
    t_out.start()

    # Poll process while checking cancellation
    while process.poll() is None:
        if cancel_event and cancel_event.is_set():
            logger.warning("Cancellation requested! Terminating FFmpeg process...")
            try:
                process.terminate()
                process.wait(timeout=3)
            except Exception:
                process.kill()
            raise RuntimeError("Thao tác xử lý FFmpeg đã bị hủy bởi người dùng.")
        try:
            process.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            pass

    t_err.join(timeout=2.0)
    t_out.join(timeout=2.0)

    exit_code = process.returncode
    stdout_text = "\n".join(stdout_lines)
    stderr_text = "\n".join(stderr_lines)

    if exit_code != 0:
        logger.error(f"FFmpeg command exited with code {exit_code}. Stderr: {stderr_text[-1000:]}")
        raise RuntimeError(f"FFmpeg thất bại (Mã lỗi {exit_code}):\n{stderr_text[-500:]}")

    cp = subprocess.CompletedProcess(args, exit_code, stdout_text, stderr_text)
    # Also add convenience attributes for compatibility
    setattr(cp, "stdout_text", stdout_text)
    setattr(cp, "stderr_text", stderr_text)
    return cp
