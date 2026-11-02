import logging
import threading
from typing import Optional
from PySide6.QtCore import QObject, QThread, Signal, Qt

logger = logging.getLogger("AIDubbingStudio.TaskManager")


class TaskManager(QObject):
    """Coordinates asynchronous worker threads and cancellation."""

    task_started = Signal(str)  # task name
    task_finished = Signal(str, bool, str)  # task name, success, message
    task_progress = Signal(int, str)  # percent (0-100), message

    def __init__(self):
        super().__init__()
        self.current_worker: Optional[QThread] = None
        self.cancel_event = threading.Event()
        self._is_busy = False

    @property
    def is_busy(self) -> bool:
        """Indicates whether a background task is actively running.
        Includes self-healing logic to automatically recover if a previous worker
        thread terminated without explicitly resetting the state.
        """
        if not self._is_busy:
            return False
        # Self-healing: if marked busy but current_worker is None or no longer running
        if self.current_worker is None or not self.current_worker.isRunning():
            logger.warning("TaskManager was marked busy but worker is not running. Auto-recovering...")
            self.current_worker = None
            self._is_busy = False
            self.cancel_event.clear()
            return False
        return True

    @is_busy.setter
    def is_busy(self, val: bool):
        self._is_busy = bool(val)

    def start_worker(self, worker: QThread, task_name: str = "Tác vụ") -> bool:
        """Start worker thread, wire standard signals, and manage execution lifecycle.
        Returns True if started, False if another task is already in progress.
        """
        if self.is_busy:
            logger.warning(f"Không thể bắt đầu '{task_name}': Một tác vụ khác đang được xử lý.")
            return False

        self.cancel_event.clear()
        self.is_busy = True
        self.current_worker = worker

        if hasattr(worker, "cancel_event"):
            worker.cancel_event = self.cancel_event

        # Progress forwarding safely onto main GUI thread via Qt QueuedConnection
        if hasattr(worker, "progress"):
            worker.progress.connect(self._on_progress, Qt.QueuedConnection)

        # One-shot cleanup closure guaranteeing execution on either finish or error
        cleaned_up = False

        def _do_cleanup():
            nonlocal cleaned_up
            if not cleaned_up:
                cleaned_up = True
                self._cleanup(worker)

        def _on_done(*args):
            self._on_worker_finished(task_name, True, "Hoàn tất")
            _do_cleanup()

        def _on_err(err=None):
            self._on_worker_finished(task_name, False, str(err))
            _do_cleanup()

        if hasattr(worker, "finished"):
            worker.finished.connect(_on_done, Qt.QueuedConnection)
        if hasattr(worker, "error"):
            worker.error.connect(_on_err, Qt.QueuedConnection)

        self.task_started.emit(task_name)
        worker.start()
        logger.info(f"Started worker thread for: {task_name}")
        return True

    def cancel_current_task(self):
        """Signal the running worker to cancel immediately and force unblock the UI."""
        logger.warning("Requesting task cancellation...")
        self.cancel_event.set()

        worker = self.current_worker
        if worker is not None:
            if hasattr(worker, "cancel"):
                try:
                    worker.cancel()
                except Exception as e:
                    logger.warning(f"Error calling worker.cancel(): {e}")

            if worker.isRunning():
                worker.requestInterruption()
                worker.wait(500)

        # Always force cleanup to ensure UI is completely unblocked
        self._cleanup()
        self.task_finished.emit("Tác vụ", False, "Đã dừng tác vụ.")

    def _on_progress(self, percent: int, msg: str):
        self.task_progress.emit(percent, msg)

    def _on_worker_finished(self, task_name: str, success: bool, msg: str):
        self.task_finished.emit(task_name, success, msg)

    def _cleanup(self, finished_worker: Optional[QThread] = None):
        if finished_worker is None or self.current_worker is None or self.current_worker is finished_worker:
            self.current_worker = None
            self.is_busy = False
            self.cancel_event.clear()
        logger.debug(f"Worker thread {getattr(finished_worker, '__class__', type(None)).__name__} cleaned up safely.")

