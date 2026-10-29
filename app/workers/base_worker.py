import threading
import logging
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("AIDubbingStudio.Worker")


class BaseWorker(QObject):
    """Base class for all background worker objects."""

    progress = Signal(int, str)  # percent, message
    finished = Signal(object)  # result object
    error = Signal(str)  # error description
    log_message = Signal(str)  # log line

    def __init__(self):
        super().__init__()
        self.cancel_event = threading.Event()

    def cancel(self):
        """Request worker thread to stop execution."""
        logger.warning(f"Worker {self.__class__.__name__} received cancel request.")
        self.cancel_event.set()

    def run(self):
        """Entry point executed inside worker thread."""
        raise NotImplementedError

