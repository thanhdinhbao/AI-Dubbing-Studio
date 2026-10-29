import logging
import threading
from typing import Optional
from PySide6.QtCore import QObject, QThread, Signal, QTimer

logger = logging.getLogger("AIDubbingStudio.TaskManager")


class TaskManager(QObject):
    """Coordinates asynchronous worker threads and cancellation."""

    task_started = Signal(str)  # task name
    task_finished = Signal(str, bool, str)  # task name, success, message
    task_progress = Signal(int, str)  # percent (0-100), message

    def __init__(self):
        super().__init__()
        self.current_thread: Optional[QThread] = None
        self.current_worker: Optional[QObject] = None
        self.cancel_event = threading.Event()
        self.is_busy = False

    def start_worker(self, worker: QObject, task_name: str = "Tác vụ") -> bool:
        """Attach worker to a new QThread, wire standard signals, and start execution.
        Returns True if started, False if another task is already in progress.
        """
        if self.is_busy:
            logger.warning(f"Không thể bắt đầu '{task_name}': Một tác vụ khác đang được xử lý.")
            return False

        self.cancel_event.clear()
        self.is_busy = True

        thread = QThread()
        self.current_thread = thread
        self.current_worker = worker

        # Pass cancel event if worker supports it
        if hasattr(worker, "cancel_event"):
            worker.cancel_event = self.cancel_event

        worker.moveToThread(thread)

        # Connect thread start to worker run
        if hasattr(worker, "run"):
            thread.started.connect(worker.run)

        # Progress forwarding safely onto main GUI thread via Qt QueuedConnection
        if hasattr(worker, "progress"):
            worker.progress.connect(self._on_progress)

        # Completion handling safely onto main GUI thread via Qt QueuedConnection
        if hasattr(worker, "finished"):
            worker.finished.connect(
                lambda res: self._on_worker_finished(task_name, True, "Hoàn tất")
            )
        if hasattr(worker, "error"):
            worker.error.connect(
                lambda err: self._on_worker_finished(task_name, False, str(err))
            )

        # Clean-up when thread finishes
        thread.finished.connect(self._cleanup)

        self.task_started.emit(task_name)
        thread.start()
        logger.info(f"Started worker thread for: {task_name}")
        return True

    def cancel_current_task(self):
        """Signal the running worker to cancel immediately."""
        if self.is_busy and self.current_thread and self.current_thread.isRunning():
            logger.warning("Requesting task cancellation...")
            self.cancel_event.set()
            if self.current_worker and hasattr(self.current_worker, "cancel"):
                self.current_worker.cancel()

    def _on_progress(self, percent: int, msg: str):
        self.task_progress.emit(percent, msg)

    def _on_worker_finished(self, task_name: str, success: bool, msg: str):
        self.task_finished.emit(task_name, success, msg)
        if self.current_thread:
            self.current_thread.quit()

    def _cleanup(self):
        if self.current_thread:
            self.current_thread.wait(2000)
            self.current_thread.deleteLater()
            self.current_thread = None

        if self.current_worker:
            self.current_worker.deleteLater()
            self.current_worker = None

        self.is_busy = False
        self.cancel_event.clear()
        logger.debug("Worker thread cleaned up.")

