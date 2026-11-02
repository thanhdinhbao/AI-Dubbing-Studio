import time
import pytest
from PySide6.QtCore import QCoreApplication, QThread, Signal
from app.task_manager import TaskManager


@pytest.fixture(scope="session")
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


class MockSuccessWorker(QThread):
    finished = Signal(object)

    def run(self):
        # Simulates a worker that returns dialogues (a list object)
        self.finished.emit(["dialogue_1", "dialogue_2"])


class MockErrorWorker(QThread):
    error = Signal(str)

    def run(self):
        self.error.emit("Mock error message")


class MockSilentWorker(QThread):
    def run(self):
        # Exits without emitting finished or error
        pass


def test_task_manager_success_with_payload(qapp):
    tm = TaskManager()
    worker = MockSuccessWorker()

    assert not tm.is_busy
    started = tm.start_worker(worker, "Test Success Task")
    assert started
    assert tm.is_busy
    assert tm.current_worker is worker

    worker.wait()
    qapp.processEvents()

    assert not tm.is_busy
    assert tm.current_worker is None


def test_task_manager_error_cleanup(qapp):
    tm = TaskManager()
    worker = MockErrorWorker()

    started = tm.start_worker(worker, "Test Error Task")
    assert started
    assert tm.is_busy

    worker.wait()
    qapp.processEvents()

    assert not tm.is_busy
    assert tm.current_worker is None


def test_task_manager_self_healing_when_worker_dead(qapp):
    tm = TaskManager()
    worker = MockSilentWorker()

    tm.start_worker(worker, "Test Silent Task")
    worker.wait()
    # At this point, worker is dead. Even before event loop processes anything,
    # the self-healing is_busy property must return False!
    assert not tm.is_busy
    assert tm.current_worker is None


def test_task_manager_cancel_forces_cleanup(qapp):
    tm = TaskManager()
    worker = MockSilentWorker()

    tm.start_worker(worker, "Test Cancel Task")
    worker.wait()

    # User clicks cancel
    tm.cancel_current_task()
    qapp.processEvents()

    assert not tm.is_busy
    assert tm.current_worker is None

