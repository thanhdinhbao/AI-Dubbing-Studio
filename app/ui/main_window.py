import os
import logging
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QUrl, QThread, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame,
    QSplitter, QMessageBox, QFileDialog
)

from app.constants import APP_NAME, APP_VERSION, TimelineMode
from app.config import app_config
from app.models import ProjectData, MediaInfo
from app.project_manager import ProjectManager
from app.task_manager import TaskManager
from app.utils.ffmpeg_utils import check_ffmpeg_available

from app.ui.widgets.progress_panel import ProgressPanelWidget
from app.ui.widgets.log_viewer import LogViewerWidget
from app.ui.dialogs import SettingsDialog, AboutDialog

from app.ui.pages.project_page import ProjectPage
from app.ui.pages.transcription_page import TranscriptionPage
from app.ui.pages.voice_page import VoicePage
from app.ui.pages.audio_page import AudioPage
from app.ui.pages.timeline_page import TimelinePage
from app.ui.pages.export_page import ExportPage

from app.workers.probe_worker import ProbeWorker
from app.workers.transcription_worker import TranscriptionWorker
from app.workers.translation_worker import TranslationWorker
from app.workers.separation_worker import SeparationWorker
from app.workers.tts_worker import TTSWorker
from app.workers.timeline_worker import TimelineWorker
from app.workers.render_worker import RenderWorker

from app.providers.translation_api import OpenAITranslationProvider
from app.providers.edge_tts_provider import EdgeTTSProvider
from app.providers.vieneu_tts_provider import VieNeuTTSProvider
from app.providers.tts_api import OpenAITTSProvider
from app.providers.offline_tts_provider import OfflineTTSProvider

logger = logging.getLogger("AIDubbingStudio.MainWindow")


class MainWindow(QMainWindow):
    """Main Application Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} — Trợ Lý Lồng Tiếng Phim Thông Minh")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)

        self.project_manager = ProjectManager()
        self.task_manager = TaskManager()

        # Dedicated runner for non-blocking voice testing
        self._test_voice_thread: Optional[QThread] = None
        self._test_voice_worker = None

        # Connect TaskManager signals to bottom progress panel
        self.task_manager.task_started.connect(self._on_task_started)
        self.task_manager.task_finished.connect(self._on_task_finished)
        self.task_manager.task_progress.connect(self._on_task_progress)

        self._init_ui()
        self._check_ffmpeg_status()

    def _run_on_ui_thread(self, func, *args, **kwargs):
        """Safely marshal a callback onto the Qt Main GUI thread's event loop."""
        QTimer.singleShot(0, self, lambda: func(*args, **kwargs))

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header Bar
        header = QFrame()
        header.setFixedHeight(48)
        header.setStyleSheet("background-color: #16161e; border-bottom: 1px solid #292e42;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)

        self.lbl_logo = QLabel(f"🎙 <b>{APP_NAME}</b>")
        self.lbl_logo.setStyleSheet("font-size: 15px; color: #7aa2f7;")
        header_layout.addWidget(self.lbl_logo)

        self.lbl_proj_title = QLabel("— [Chưa chọn dự án]")
        self.lbl_proj_title.setStyleSheet("color: #a9b1d6;")
        header_layout.addWidget(self.lbl_proj_title)

        header_layout.addStretch()

        self.lbl_ffmpeg_status = QLabel("● FFmpeg: Đang kiểm tra...")
        self.lbl_ffmpeg_status.setStyleSheet("color: #e0af68; font-weight: bold; margin-right: 12px;")
        header_layout.addWidget(self.lbl_ffmpeg_status)

        btn_save = QPushButton("💾 Lưu dự án")
        btn_save.clicked.connect(self._save_current_project)
        header_layout.addWidget(btn_save)

        btn_open = QPushButton("📂 Mở dự án")
        btn_open.clicked.connect(self._open_project_dialog)
        header_layout.addWidget(btn_open)

        btn_settings = QPushButton("⚙ Cài đặt")
        btn_settings.clicked.connect(self._open_settings)
        header_layout.addWidget(btn_settings)

        btn_about = QPushButton("ℹ Giới thiệu")
        btn_about.clicked.connect(lambda: AboutDialog(self).exec())
        header_layout.addWidget(btn_about)

        main_layout.addWidget(header)

        # 2. Main Content (Sidebar + Stacked Pages)
        body_splitter = QSplitter(Qt.Horizontal)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(8, 12, 8, 12)
        sidebar_layout.setSpacing(4)

        self.nav_buttons = []
        nav_items = [
            ("1. Dự án & Media", 0),
            ("2. Nhận diện & Phụ đề", 1),
            ("3. Giọng đọc AI", 2),
            ("4. Tách nhạc & Hòa âm", 3),
            ("5. Timeline Động", 4),
            ("6. Xuất Video", 5),
        ]

        for text, idx in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self._switch_page(i))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Log toggle button
        self.btn_toggle_log = QPushButton("📜 Nhật ký hệ thống")
        self.btn_toggle_log.setCheckable(True)
        self.btn_toggle_log.clicked.connect(self._toggle_log_drawer)
        sidebar_layout.addWidget(self.btn_toggle_log)

        body_splitter.addWidget(self.sidebar)

        # Stacked Pages
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.page_stack = QStackedWidget()

        # Instantiate pages
        self.page_project = ProjectPage()
        self.page_transcription = TranscriptionPage()
        self.page_voice = VoicePage()
        self.page_audio = AudioPage()
        self.page_timeline = TimelinePage()
        self.page_export = ExportPage()

        self.page_stack.addWidget(self.page_project)
        self.page_stack.addWidget(self.page_transcription)
        self.page_stack.addWidget(self.page_voice)
        self.page_stack.addWidget(self.page_audio)
        self.page_stack.addWidget(self.page_timeline)
        self.page_stack.addWidget(self.page_export)

        content_layout.addWidget(self.page_stack, stretch=1)

        # Log Viewer Drawer (hidden by default)
        self.log_viewer = LogViewerWidget()
        self.log_viewer.setFixedHeight(160)
        self.log_viewer.setVisible(False)
        content_layout.addWidget(self.log_viewer)

        # Forward logger output to LogViewerWidget
        class QtLogHandler(logging.Handler):
            def __init__(self, callback):
                super().__init__()
                self.callback = callback
            def emit(self, record):
                msg = self.format(record)
                self.callback(msg)

        handler = QtLogHandler(self.log_viewer.append_log)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S"))
        logging.getLogger("AIDubbingStudio").addHandler(handler)

        body_splitter.addWidget(content_frame)
        body_splitter.setSizes([220, 1060])
        main_layout.addWidget(body_splitter, stretch=1)

        # 3. Bottom Progress Panel
        self.progress_panel = ProgressPanelWidget()
        self.progress_panel.cancel_requested.connect(self.task_manager.cancel_current_task)
        main_layout.addWidget(self.progress_panel)

        # Wire Page Signals
        self._wire_page_signals()

        # Select first page
        self._switch_page(0)

    def _wire_page_signals(self):
        # Page 1
        self.page_project.project_created.connect(self._on_project_created)
        self.page_project.video_selected.connect(self._on_video_selected)

        # Page 2
        self.page_transcription.transcription_requested.connect(self._on_transcription_requested)
        self.page_transcription.translation_requested.connect(self._on_translation_requested)
        self.page_transcription.translate_single_requested.connect(self._on_translate_single_requested)
        self.page_transcription.config_requested.connect(lambda: self._open_settings(active_tab=1))

        # Page 3
        self.page_voice.tts_generation_requested.connect(self._on_tts_requested)
        self.page_voice.test_voice_requested.connect(self._on_test_voice_requested)

        # Page 4
        self.page_audio.separation_requested.connect(self._on_separation_requested)

        # Page 5
        self.page_timeline.rebuild_timeline_requested.connect(self._on_rebuild_timeline_requested)

        # Page 6
        self.page_export.render_requested.connect(self._on_render_requested)

    def _switch_page(self, index: int):
        self.page_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def _toggle_log_drawer(self):
        vis = self.btn_toggle_log.isChecked()
        self.log_viewer.setVisible(vis)

    def _check_ffmpeg_status(self):
        res = check_ffmpeg_available()
        if res["ffmpeg"] and res["ffprobe"]:
            self.lbl_ffmpeg_status.setText("● FFmpeg: Sẵn sàng")
            self.lbl_ffmpeg_status.setStyleSheet("color: #9ece6a; font-weight: bold; margin-right: 12px;")
        else:
            self.lbl_ffmpeg_status.setText("● FFmpeg: Chưa tìm thấy!")
            self.lbl_ffmpeg_status.setStyleSheet("color: #f7768e; font-weight: bold; margin-right: 12px;")

    def _create_or_load_default_project(self):
        try:
            proj = self.project_manager.create_project("Dự án mặc định")
            self._update_all_pages(proj)
        except Exception as e:
            logger.error(f"Failed to create default project: {e}")

    def _update_all_pages(self, project: ProjectData):
        self.lbl_proj_title.setText(f"— [{project.name}]")
        self.page_project.set_project(project)
        self.page_transcription.set_project(project)
        self.page_voice.set_project(project)
        self.page_audio.set_project(project)
        self.page_timeline.set_project(project)
        self.page_export.set_project(project)

    def _save_current_project(self):
        proj = self.project_manager.current_project
        if not proj:
            QMessageBox.information(self, "Thông báo", "Chưa có dự án nào đang mở để lưu.")
            return

        # Sync dialogues from editor
        proj.dialogues = self.page_transcription.get_dialogues()
        try:
            self.project_manager.save_project(proj)
            QMessageBox.information(self, "Thành công", f"Đã lưu dự án '{proj.name}' thành công.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu dự án: {e}")

    def _open_project_dialog(self):
        from app.utils.paths import get_default_projects_dir
        projects_dir = str(get_default_projects_dir())
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Mở file dự án",
            projects_dir,
            "AI Dubbing Project (*project.json);;All Files (*.*)"
        )
        if path:
            try:
                proj = self.project_manager.load_project(path)
                self._update_all_pages(proj)
                QMessageBox.information(self, "Thành công", f"Đã mở dự án '{proj.name}' thành công.")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể mở dự án: {e}")

    def _open_settings(self, active_tab: int = 0):
        dlg = SettingsDialog(self, active_tab=active_tab)
        if dlg.exec():
            self._check_ffmpeg_status()

    # --- Task Handlers ---

    def _on_task_started(self, task_name: str):
        self.progress_panel.set_busy(True, f"Đang thực hiện: {task_name}...")

    def _on_task_finished(self, task_name: str, success: bool, msg: str):
        self.progress_panel.set_busy(False, f"{task_name}: {msg}" if success else f"Lỗi {task_name}: {msg}")
        if not success:
            QMessageBox.critical(self, "Lỗi xử lý", f"Tác vụ '{task_name}' gặp sự cố:\n{msg}")

    def _on_task_progress(self, percent: int, msg: str):
        self.progress_panel.set_progress(percent, msg)

    # --- Step 1: Video Selected & Probed ---
    def _on_project_created(self, name: str, video_path: str):
        try:
            proj = self.project_manager.create_project(name, video_path)
            self._update_all_pages(proj)
            if video_path:
                self._on_video_selected(video_path)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))

    def _on_video_selected(self, video_path: str):
        proj = self.project_manager.current_project
        if not proj:
            # If no project is currently open, create one based on the chosen video
            video_name = Path(video_path).stem
            proj = self.project_manager.create_project(f"Dự án {video_name}", video_path=video_path)
            self._update_all_pages(proj)
        else:
            proj.video_path = video_path

        if self.task_manager.is_busy:
            QMessageBox.warning(self, "Đang xử lý", "Một tác vụ khác đang được thực hiện. Vui lòng chờ hoàn tất.")
            return

        worker = ProbeWorker(video_path)

        def on_probe_done(info: MediaInfo):
            proj.media_info = info
            self.page_project.update_media_info(info)
            self.project_manager.save_project(proj)
            logger.info("Probe completed and project updated.")

        worker.finished.connect(lambda info: self._run_on_ui_thread(on_probe_done, info))
        self.task_manager.start_worker(worker, "Phân tích Media")

    # --- Step 2: Transcription (ASR) ---
    def _on_transcription_requested(self, model_size: str, device: str, beam_size: int = 1):
        proj = self.project_manager.current_project
        if not proj or not proj.video_path:
            return
        if self.task_manager.is_busy:
            QMessageBox.warning(self, "Đang xử lý", "Một tác vụ khác đang được thực hiện. Vui lòng chờ hoàn tất.")
            return

        out_wav = os.path.join(proj.project_dir, "audio", "extracted_source.wav")
        worker = TranscriptionWorker(
            video_path=proj.video_path,
            output_wav_path=out_wav,
            model_size=model_size,
            device=device,
            beam_size=beam_size
        )

        def on_asr_done(dialogues):
            proj.extracted_audio_path = out_wav
            proj.dialogues = dialogues
            self.page_transcription.set_project(proj)
            self.project_manager.save_project(proj)
            QMessageBox.information(self, "Thành công", f"Nhận diện hoàn tất: tìm thấy {len(dialogues)} câu thoại.")

        worker.finished.connect(lambda dlgs: self._run_on_ui_thread(on_asr_done, dlgs))
        self.task_manager.start_worker(worker, "Nhận diện Giọng nói ASR")

    # --- Step 3: Translation ---
    def _create_translation_provider(self, backend: str = "google_free", options: Optional[dict] = None):
        """Factory for translation providers (Google Free, OpenAI Cloud API, or Local LLM)."""
        options = options or {}
        if backend == "google_free":
            from app.providers.translation_api import GoogleFreeTranslationProvider
            return GoogleFreeTranslationProvider()
        elif backend == "local_llm":
            from app.providers.translation_api import LocalLLMTranslationProvider
            base_url = options.get("base_url") or app_config.get("ollama_base_url", "http://localhost:11434/v1")
            model = options.get("model") or app_config.get("ollama_model", "qwen2.5:latest")
            return LocalLLMTranslationProvider(base_url=base_url, model=model)
        else:
            from app.providers.translation_api import OpenAITranslationProvider
            base_url = options.get("base_url") or app_config.get("translation_base_url", "https://api.openai.com/v1")
            api_key = options.get("api_key") or app_config.get("translation_api_key", "")
            model = options.get("model") or app_config.get("translation_model", "gpt-4o-mini")
            return OpenAITranslationProvider(base_url=base_url, api_key=api_key, model=model)

    def _on_translation_requested(self, backend: str = "google_free", options: Optional[dict] = None):
        proj = self.project_manager.current_project
        if not proj or not proj.dialogues:
            return
        if self.task_manager.is_busy:
            QMessageBox.warning(self, "Đang xử lý", "Một tác vụ khác đang được thực hiện. Vui lòng chờ hoàn tất.")
            return

        try:
            provider = self._create_translation_provider(backend, options)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể khởi tạo bộ máy dịch thuật: {e}")
            return

        worker = TranslationWorker(
            dialogues=proj.dialogues,
            provider=provider
        )

        def on_trans_done(dialogues):
            proj.dialogues = dialogues
            self.page_transcription.set_project(proj)
            self.project_manager.save_project(proj)
            QMessageBox.information(
                self,
                "Thành công",
                f"Đã dịch toàn bộ {len(dialogues)} câu thoại sang Tiếng Việt ({backend}) thành công!"
            )

        worker.finished.connect(lambda dlgs: self._run_on_ui_thread(on_trans_done, dlgs))
        self.task_manager.start_worker(worker, f"Dịch thuật Tiếng Việt ({backend})")

    def _on_translate_single_requested(self, row_index: int, backend: str = "google_free", options: Optional[dict] = None):
        proj = self.project_manager.current_project
        if not proj or not proj.dialogues or row_index < 0 or row_index >= len(proj.dialogues):
            return

        dlg = proj.dialogues[row_index]
        try:
            provider = self._create_translation_provider(backend, options)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể khởi tạo bộ máy dịch thuật: {e}")
            return

        # Perform translation in dedicated background thread
        thread = QThread()
        worker = TranslationWorker(
            dialogues=[dlg],
            provider=provider
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        def on_single_done(dlgs):
            if dlgs:
                self.page_transcription.update_dialogue_target_at(row_index, dlgs[0].target_text)
                self.project_manager.save_project(proj)
            thread.quit()

        def on_single_err(err):
            QMessageBox.warning(self, "Lỗi Dịch Thuật", f"Không thể dịch câu đã chọn:\n{err}")
            thread.quit()

        worker.finished.connect(lambda d: self._run_on_ui_thread(on_single_done, d))
        worker.error.connect(lambda e: self._run_on_ui_thread(on_single_err, e))
        thread.finished.connect(thread.deleteLater)
        thread.start()

    # --- Step 4: TTS Generation ---
    def _on_tts_requested(self, backend: str, voice_id: str, options: dict):
        proj = self.project_manager.current_project
        if not proj or not proj.dialogues:
            return
        if self.task_manager.is_busy:
            QMessageBox.warning(self, "Đang xử lý", "Một tác vụ khác đang được thực hiện. Vui lòng chờ hoàn tất.")
            return

        out_tts_dir = os.path.join(proj.project_dir, "tts")

        if backend == "edge_tts":
            provider = EdgeTTSProvider()
        elif backend == "vieneu":
            provider = VieNeuTTSProvider(mode="v3turbo", backend="auto")
        elif backend == "vieneu_nano":
            provider = VieNeuTTSProvider(mode="v3nano", backend="onnx")
        elif backend == "openai_compatible":
            provider = OpenAITTSProvider(
                base_url=app_config.get("tts_api_base_url"),
                api_key=app_config.get("tts_api_key")
            )
        else:
            provider = OfflineTTSProvider(model_path=app_config.get("offline_tts_model_path"))

        max_workers = int(options.get("max_workers", 5))
        worker = TTSWorker(
            dialogues=proj.dialogues,
            provider=provider,
            output_dir=out_tts_dir,
            voice_id=voice_id,
            options=options,
            max_workers=max_workers
        )

        def on_tts_done(dialogues):
            proj.dialogues = dialogues
            self.page_transcription.set_project(proj)
            # Automatically rebuild timeline after TTS generation
            self._rebuild_dynamic_timeline(TimelineMode.DYNAMIC_DURATION)
            self.project_manager.save_project(proj)
            QMessageBox.information(self, "Thành công", "Đã tổng hợp toàn bộ giọng đọc tiếng Việt thành công!")

        worker.finished.connect(lambda dlgs: self._run_on_ui_thread(on_tts_done, dlgs))
        self.task_manager.start_worker(worker, "Tổng hợp Giọng đọc TTS")

    def _on_test_voice_requested(self, backend: str, voice_id: str, options: dict):
        proj = self.project_manager.current_project
        temp_dir = os.path.join(proj.project_dir if proj else ".", "cache")
        os.makedirs(temp_dir, exist_ok=True)

        if backend == "edge_tts":
            provider = EdgeTTSProvider()
        elif backend == "vieneu":
            provider = VieNeuTTSProvider(mode="v3turbo", backend="auto")
        elif backend == "vieneu_nano":
            provider = VieNeuTTSProvider(mode="v3nano", backend="onnx")
        elif backend == "openai_compatible":
            provider = OpenAITTSProvider(
                base_url=app_config.get("tts_api_base_url"),
                api_key=app_config.get("tts_api_key")
            )
        else:
            provider = OfflineTTSProvider(model_path=app_config.get("offline_tts_model_path"))

        from app.models import DialogueSegment
        dummy_dlg = DialogueSegment(
            source_text="Xin chào, đây là giọng đọc thử nghiệm của hệ thống lồng tiếng AI.",
            target_text="Xin chào, đây là giọng đọc thử nghiệm của hệ thống lồng tiếng AI."
        )

        # Safely cancel and clean up any previous test voice preview thread
        if self._test_voice_thread is not None:
            try:
                if self._test_voice_thread.isRunning():
                    if self._test_voice_worker:
                        self._test_voice_worker.cancel()
                    self._test_voice_thread.quit()
                    self._test_voice_thread.wait(500)
            except (RuntimeError, Exception):
                pass
            self._test_voice_thread = None
            self._test_voice_worker = None

        thread = QThread()
        worker = TTSWorker(
            dialogues=[dummy_dlg],
            provider=provider,
            output_dir=temp_dir,
            voice_id=voice_id,
            options=options,
            max_workers=1
        )
        self._test_voice_thread = thread
        self._test_voice_worker = worker

        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        def on_test_done(dlgs):
            if dlgs and dlgs[0].tts_audio_path:
                self.page_voice.sample_player.load_media(dlgs[0].tts_audio_path)
                self.page_voice.sample_player.play()
            thread.quit()

        def on_test_error(err):
            logger.warning(f"Test voice error: {err}")
            QMessageBox.warning(self, "Lỗi Thử Giọng", f"Không thể tạo mẫu giọng đọc:\n{err}")
            thread.quit()

        def on_thread_finished():
            if self._test_voice_thread is thread:
                self._test_voice_thread = None
                self._test_voice_worker = None

        worker.finished.connect(lambda dlgs: self._run_on_ui_thread(on_test_done, dlgs))
        worker.error.connect(lambda err: self._run_on_ui_thread(on_test_error, err))
        thread.finished.connect(on_thread_finished)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    # --- Step 5: Separation ---
    def _on_separation_requested(self, separation_mode: str):
        proj = self.project_manager.current_project
        if not proj or not proj.extracted_audio_path:
            return
        if self.task_manager.is_busy:
            QMessageBox.warning(self, "Đang xử lý", "Một tác vụ khác đang được thực hiện. Vui lòng chờ hoàn tất.")
            return

        out_audio_dir = os.path.join(proj.project_dir, "audio")
        worker = SeparationWorker(
            audio_path=proj.extracted_audio_path,
            output_dir=out_audio_dir,
            separation_mode=separation_mode
        )

        def on_sep_done(stems):
            proj.vocal_stem_path = stems.get("vocal_stem")
            proj.instrumental_path = stems.get("instrumental_stem")
            self.page_audio.set_project(proj)
            self.project_manager.save_project(proj)
            QMessageBox.information(self, "Thành công", "Đã chuẩn bị track âm thanh nền thành công.")

        worker.finished.connect(lambda stems: self._run_on_ui_thread(on_sep_done, stems))
        self.task_manager.start_worker(worker, "Tách Âm thanh Nền")

    # --- Step 6: Dynamic Timeline Calculation ---
    def _on_rebuild_timeline_requested(self, mode: str, options: dict):
        self._rebuild_dynamic_timeline(mode, options)

    def _rebuild_dynamic_timeline(self, mode: str = TimelineMode.DYNAMIC_DURATION, options: Optional[dict] = None):
        proj = self.project_manager.current_project
        if not proj or not proj.media_info:
            return

        worker = TimelineWorker(
            source_duration=proj.media_info.duration,
            dialogues=proj.dialogues,
            mode=mode,
            options=options
        )

        def on_timeline_done(result):
            proj.timeline_segments = result["timeline_segments"]
            proj.output_duration = result["output_duration"]
            proj.timeline_mode = mode
            self.page_timeline.set_project(proj)
            self.project_manager.save_project(proj)

        worker.finished.connect(lambda res: self._run_on_ui_thread(on_timeline_done, res))
        self.task_manager.start_worker(worker, "Tính toán Timeline Động")

    # --- Step 7: Export & Video Rendering ---
    def _on_render_requested(self, output_video_path: str, render_settings: dict):
        proj = self.project_manager.current_project
        if not proj or not proj.timeline_segments:
            return
        if self.task_manager.is_busy:
            QMessageBox.warning(self, "Đang xử lý", "Một tác vụ khác đang được thực hiện. Vui lòng chờ hoàn tất.")
            return

        # Background track: instrumental if available, otherwise extracted original audio
        bg_track = proj.instrumental_path or proj.extracted_audio_path

        worker = RenderWorker(
            source_video_path=proj.video_path,
            timeline=proj.timeline_segments,
            output_duration=proj.output_duration,
            output_video_path=output_video_path,
            workspace_dir=proj.project_dir,
            background_audio_path=bg_track,
            render_settings=render_settings
        )

        def on_render_done(res):
            proj.output_video_path = res["output_video_path"]
            self.page_export.show_render_result(res["output_video_path"])
            self.project_manager.save_project(proj)
            QMessageBox.information(
                self,
                "Hoàn tất Xuất bản!",
                f"Video lồng tiếng đã được xuất thành công!\n"
                f"Đường dẫn: {res['output_video_path']}\n"
                f"Thời lượng: {res['validation'].get('duration', 0.0):.2f}s"
            )

        worker.finished.connect(lambda res: self._run_on_ui_thread(on_render_done, res))
        self.task_manager.start_worker(worker, "Render Video Hoàn chỉnh")

