import os
import shutil
import logging
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QLabel, QLineEdit, QPushButton, QComboBox,
    QGridLayout, QFileDialog, QMessageBox, QGroupBox,
    QCheckBox, QListWidget, QListWidgetItem, QProgressBar
)
from PySide6.QtMultimedia import (
    QMediaCaptureSession, QAudioInput, QMediaRecorder,
    QMediaFormat, QMediaDevices, QMediaPlayer, QAudioOutput
)

from app.config import app_config
from app.constants import APP_NAME, APP_VERSION
from app.utils.ffmpeg_utils import check_ffmpeg_available, set_custom_ffmpeg_paths
from app.utils.paths import get_default_logs_dir, get_default_cache_dir

logger = logging.getLogger("AIDubbingStudio.Dialogs")


class SettingsDialog(QDialog):
    """Global Application Settings Dialog."""

    def __init__(self, parent=None, active_tab: int = 0):
        super().__init__(parent)
        self.setWindowTitle(f"Cài Đặt — {APP_NAME}")
        self.resize(650, 480)

        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # Tab 1: FFmpeg & System
        tab_sys = QWidget()
        sys_layout = QGridLayout(tab_sys)

        sys_layout.addWidget(QLabel("Đường dẫn FFmpeg:"), 0, 0)
        self.input_ffmpeg = QLineEdit(app_config.get("ffmpeg_path", ""))
        sys_layout.addWidget(self.input_ffmpeg, 0, 1)
        btn_ff_browse = QPushButton("Duyệt...")
        btn_ff_browse.clicked.connect(lambda: self._browse_file(self.input_ffmpeg, "ffmpeg.exe"))
        sys_layout.addWidget(btn_ff_browse, 0, 2)

        sys_layout.addWidget(QLabel("Đường dẫn FFprobe:"), 1, 0)
        self.input_ffprobe = QLineEdit(app_config.get("ffprobe_path", ""))
        sys_layout.addWidget(self.input_ffprobe, 1, 1)
        btn_probe_browse = QPushButton("Duyệt...")
        btn_probe_browse.clicked.connect(lambda: self._browse_file(self.input_ffprobe, "ffprobe.exe"))
        sys_layout.addWidget(btn_probe_browse, 1, 2)

        btn_test_ff = QPushButton("🔍 Kiểm tra FFmpeg & FFprobe")
        btn_test_ff.clicked.connect(self._test_ffmpeg)
        sys_layout.addWidget(btn_test_ff, 2, 0, 1, 3)

        btn_open_logs = QPushButton("📁 Mở thư mục Logs")
        btn_open_logs.clicked.connect(lambda: os.startfile(get_default_logs_dir()))
        sys_layout.addWidget(btn_open_logs, 3, 0)

        btn_clear_cache = QPushButton("🗑 Dọn dẹp Cache tạm")
        btn_clear_cache.clicked.connect(self._clear_cache)
        sys_layout.addWidget(btn_clear_cache, 3, 1)

        self.tabs.addTab(tab_sys, "Hệ Thống & FFmpeg")

        # Tab 2: Translation API & Local Models
        tab_trans = QWidget()
        trans_layout = QGridLayout(tab_trans)
        trans_layout.setSpacing(8)

        # Section: Cloud API
        lbl_cloud = QLabel("<b>1. Cloud API (OpenAI, DeepSeek, Gemini, v.v.):</b>")
        lbl_cloud.setStyleSheet("color: #7aa2f7;")
        trans_layout.addWidget(lbl_cloud, 0, 0, 1, 2)

        trans_layout.addWidget(QLabel("Base URL:"), 1, 0)
        self.input_trans_url = QLineEdit(app_config.get("translation_base_url", "https://api.openai.com/v1"))
        trans_layout.addWidget(self.input_trans_url, 1, 1)

        trans_layout.addWidget(QLabel("API Key:"), 2, 0)
        self.input_trans_key = QLineEdit(app_config.get("translation_api_key", ""))
        self.input_trans_key.setEchoMode(QLineEdit.Password)
        trans_layout.addWidget(self.input_trans_key, 2, 1)

        trans_layout.addWidget(QLabel("Mô hình (Model):"), 3, 0)
        self.input_trans_model = QLineEdit(app_config.get("translation_model", "gpt-4o-mini"))
        trans_layout.addWidget(self.input_trans_model, 3, 1)

        btn_test_trans = QPushButton("🌐 Kiểm tra Kết nối Cloud API")
        btn_test_trans.clicked.connect(self._test_trans_api)
        trans_layout.addWidget(btn_test_trans, 4, 0, 1, 2)

        # Section: Local LLM
        lbl_local = QLabel("<b>2. Local LLM Offline (Ollama / LM Studio):</b>")
        lbl_local.setStyleSheet("color: #bb9af7;")
        trans_layout.addWidget(lbl_local, 5, 0, 1, 2)

        trans_layout.addWidget(QLabel("Ollama URL:"), 6, 0)
        self.input_ollama_url = QLineEdit(app_config.get("ollama_base_url", "http://localhost:11434/v1"))
        trans_layout.addWidget(self.input_ollama_url, 6, 1)

        trans_layout.addWidget(QLabel("Mô hình Ollama:"), 7, 0)
        self.input_ollama_model = QLineEdit(app_config.get("ollama_model", "qwen2.5:latest"))
        trans_layout.addWidget(self.input_ollama_model, 7, 1)

        btn_test_ollama = QPushButton("🖥 Kiểm tra Kết nối Local LLM (Ollama)")
        btn_test_ollama.clicked.connect(self._test_ollama_api)
        trans_layout.addWidget(btn_test_ollama, 8, 0, 1, 2)

        # Section: Free Google Translate
        btn_test_google = QPushButton("⚡ Kiểm tra Google Translate (Miễn phí)")
        btn_test_google.clicked.connect(self._test_google_trans)
        trans_layout.addWidget(btn_test_google, 9, 0, 1, 2)

        self.tabs.addTab(tab_trans, "Dịch Thuật (API & Local)")

        # Tab 3: VieNeu AI Voice
        tab_vieneu = QWidget()
        vieneu_layout = QGridLayout(tab_vieneu)
        vieneu_layout.setSpacing(8)

        vieneu_layout.addWidget(QLabel("VieNeu API Endpoint:"), 0, 0)
        self.input_vieneu_url = QLineEdit(app_config.get("vieneu_api_url", "https://www.vieneu.io/api/tts/demo"))
        vieneu_layout.addWidget(self.input_vieneu_url, 0, 1)

        vieneu_layout.addWidget(QLabel("Turnstile Token (Tùy chọn):"), 1, 0)
        self.input_vieneu_token = QLineEdit(app_config.get("vieneu_token", ""))
        self.input_vieneu_token.setPlaceholderText("Để trống nếu API không yêu cầu xác thực Cloudflare...")
        vieneu_layout.addWidget(self.input_vieneu_token, 1, 1)

        btn_test_vieneu = QPushButton("🔊 Kiểm tra Kết nối VieNeu API")
        btn_test_vieneu.clicked.connect(self._test_vieneu_api)
        vieneu_layout.addWidget(btn_test_vieneu, 2, 0, 1, 2)

        lbl_vieneu_info = QLabel(
            "📌 Giới thiệu VieNeu:\n"
            "- Hệ thống AI TTS tiếng Việt tự nhiên đa vùng miền Bắc - Trung - Nam.\n"
            "- 10 giọng đọc: Nhật Phong, Bảo Long, Bích Ngọc (Bắc); Trung Dũng, Thành Sen (Trung); "
            "Ngọc Lan, Trâm Anh, Kiều Linh, Adam vui (Nam); Adam (English)."
        )
        lbl_vieneu_info.setStyleSheet("color: #7aa2f7; padding: 10px;")
        vieneu_layout.addWidget(lbl_vieneu_info, 3, 0, 1, 2)

        self.tabs.addTab(tab_vieneu, "VieNeu AI Voice")

        # Tab 4: Offline Models
        tab_offline = QWidget()
        off_layout = QGridLayout(tab_offline)

        off_layout.addWidget(QLabel("Đường dẫn Mô hình Piper (.onnx):"), 0, 0)
        self.input_piper_model = QLineEdit(app_config.get("offline_tts_model_path", ""))
        off_layout.addWidget(self.input_piper_model, 0, 1)

        btn_browse_model = QPushButton("Duyệt...")
        btn_browse_model.clicked.connect(lambda: self._browse_file(self.input_piper_model, "Piper Model (*.onnx)"))
        off_layout.addWidget(btn_browse_model, 0, 2)

        lbl_guide = QLabel(
            "📌 Hướng dẫn Offline TTS:\n"
            "- Để sử dụng hoàn toàn offline, tải file mô hình Piper tiếng Việt (onnx) và chỉ định vào ô trên.\n"
            "- Nếu chưa có model offline, hệ thống sử dụng Microsoft Edge TTS chất lượng cao."
        )
        lbl_guide.setStyleSheet("color: #7aa2f7; padding: 10px;")
        off_layout.addWidget(lbl_guide, 1, 0, 1, 3)

        self.tabs.addTab(tab_offline, "Offline Models")

        if 0 <= active_tab < self.tabs.count():
            self.tabs.setCurrentIndex(active_tab)

        main_layout.addWidget(self.tabs)

        # Bottom Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_save = QPushButton("💾 Lưu cài đặt")
        btn_save.setObjectName("PrimaryButton")
        btn_save.clicked.connect(self._save_settings)
        btn_box.addWidget(btn_save)

        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        main_layout.addLayout(btn_box)

    def _browse_file(self, target_line_edit: QLineEdit, filter_str: str):
        path, _ = QFileDialog.getOpenFileName(self, "Chọn tệp", "", f"{filter_str};;All Files (*.*)")
        if path:
            target_line_edit.setText(path)

    def _test_ffmpeg(self):
        ff_p = self.input_ffmpeg.text().strip()
        probe_p = self.input_ffprobe.text().strip()
        set_custom_ffmpeg_paths(ff_p, probe_p)

        res = check_ffmpeg_available()
        if res["ffmpeg"] and res["ffprobe"]:
            QMessageBox.information(
                self,
                "Thành công",
                f"Đã phát hiện thành công:\nFFmpeg: {res['ffmpeg_version']}\nFFprobe: {res['ffprobe_version']}"
            )
        else:
            QMessageBox.critical(self, "Lỗi", f"Không tìm thấy công cụ FFmpeg hoặc FFprobe:\n{res.get('error')}")

    def _test_trans_api(self):
        from app.providers.translation_api import OpenAITranslationProvider
        prov = OpenAITranslationProvider(
            base_url=self.input_trans_url.text().strip(),
            api_key=self.input_trans_key.text().strip(),
            model=self.input_trans_model.text().strip()
        )
        ok, msg = prov.test_connection()
        if ok:
            QMessageBox.information(self, "Thành công", msg)
        else:
            QMessageBox.warning(self, "Thất bại", msg)

    def _test_ollama_api(self):
        from app.providers.translation_api import LocalLLMTranslationProvider
        prov = LocalLLMTranslationProvider(
            base_url=self.input_ollama_url.text().strip(),
            model=self.input_ollama_model.text().strip()
        )
        ok, msg = prov.test_connection()
        if ok:
            QMessageBox.information(self, "Thành công", msg)
        else:
            QMessageBox.warning(self, "Thất bại", msg)

    def _test_google_trans(self):
        from app.providers.translation_api import GoogleFreeTranslationProvider
        prov = GoogleFreeTranslationProvider()
        ok, msg = prov.test_connection()
        if ok:
            QMessageBox.information(self, "Thành công", msg)
        else:
            QMessageBox.warning(self, "Thất bại", msg)

    def _test_vieneu_api(self):
        from app.providers.vieneu_tts_provider import VieNeuTTSProvider
        prov = VieNeuTTSProvider(
            api_url=self.input_vieneu_url.text().strip(),
            turnstile_token=self.input_vieneu_token.text().strip()
        )
        ok, msg = prov.test_connection()
        if ok:
            QMessageBox.information(self, "Thành công", msg)
        else:
            QMessageBox.warning(self, "Thất bại", msg)

    def _clear_cache(self):
        cache_dir = get_default_cache_dir()
        try:
            for item in cache_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            QMessageBox.information(self, "Thành công", "Đã dọn dẹp sạch cache tạm.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể xóa cache: {e}")

    def _save_settings(self):
        app_config.set("ffmpeg_path", self.input_ffmpeg.text().strip(), False)
        app_config.set("ffprobe_path", self.input_ffprobe.text().strip(), False)
        app_config.set("translation_base_url", self.input_trans_url.text().strip(), False)
        app_config.set("translation_api_key", self.input_trans_key.text().strip(), False)
        app_config.set("translation_model", self.input_trans_model.text().strip(), False)
        app_config.set("ollama_base_url", self.input_ollama_url.text().strip(), False)
        app_config.set("ollama_model", self.input_ollama_model.text().strip(), False)
        app_config.set("vieneu_api_url", self.input_vieneu_url.text().strip(), False)
        app_config.set("vieneu_token", self.input_vieneu_token.text().strip(), False)
        app_config.set("offline_tts_model_path", self.input_piper_model.text().strip(), False)
        app_config.save()

        set_custom_ffmpeg_paths(
            app_config.get("ffmpeg_path"),
            app_config.get("ffprobe_path")
        )
        self.accept()


class AboutDialog(QDialog):
    """About AI Dubbing Studio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Giới thiệu — AI Dubbing Studio")
        self.setFixedSize(480, 280)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        lbl_title = QLabel(f"🎬 {APP_NAME}")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #7aa2f7;")
        layout.addWidget(lbl_title)

        lbl_ver = QLabel(f"Phiên bản: {APP_VERSION} (64-bit Windows)")
        layout.addWidget(lbl_ver)

        lbl_desc = QLabel(
            "Phần mềm lồng tiếng video tự động bằng Trí tuệ Nhân tạo.\n"
            "- Nhận diện lời thoại ASR bằng faster-whisper\n"
            "- Dịch thuật thông minh sang tiếng Việt truyền cảm\n"
            "- Tổng hợp giọng nói TTS tiếng Việt tự nhiên (Edge TTS / Offline)\n"
            "- Dynamic Timeline: Tự động co giãn thời lượng video khớp với độ dài lời thoại\n"
            "- Hòa âm thông minh, tự động Ducking giữ trọn nhạc nền & âm thanh phim."
        )
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        layout.addStretch()

        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)


class VoiceCloneDialog(QDialog):
    """Voice Cloning Dialog: Record or import 3-8s audio to clone any voice using VieNeu."""

    voice_cloned = Signal(str)  # emitted with new cloned voice name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎙 Nhân bản Giọng nói AI (Voice Cloning — VieNeu)")
        self.resize(680, 560)

        from app.providers.vieneu_tts_provider import VieNeuTTSProvider, load_saved_cloned_voices
        self.vieneu_provider = VieNeuTTSProvider()

        self.recorded_wav_path: Optional[Path] = None
        self.imported_audio_path: Optional[Path] = None
        self.recording_elapsed_sec = 0

        # Qt Multimedia Audio Recording setup
        self.capture_session = QMediaCaptureSession(self)
        self.audio_input = QAudioInput(self)
        self.recorder = QMediaRecorder(self)
        self.capture_session.setAudioInput(self.audio_input)
        self.capture_session.setRecorder(self.recorder)

        # Qt Multimedia Audio Playback setup
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)

        # Recording timer
        self.record_timer = QTimer(self)
        self.record_timer.setInterval(100)  # 100ms tick
        self.record_timer.timeout.connect(self._on_record_timer_tick)

        self._init_ui()
        self._load_cloned_voices_list()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # Header Guide
        guide_box = QGroupBox("Hướng dẫn lấy mẫu giọng nói")
        guide_layout = QVBoxLayout(guide_box)
        lbl_guide = QLabel(
            "<b>💡 Mẹo để nhân bản giọng đọc tự nhiên nhất:</b><br>"
            "• Thời lượng mẫu lý tưởng: <b>3 đến 8 giây</b> của một người nói.<br>"
            "• Nói tự nhiên, liên tục, phát âm rõ ràng, không kèm nhạc nền.<br>"
            "• Hệ thống tự động khử nhiễu (Denoise) và trích xuất hồ sơ âm thanh 48 kHz."
        )
        lbl_guide.setTextFormat(Qt.RichText)
        guide_layout.addWidget(lbl_guide)
        main_layout.addWidget(guide_box)

        # Tab Widget: Record vs Import
        self.tabs = QTabWidget()

        # --- Tab 1: Live Microphone Recording ---
        tab_rec = QWidget()
        rec_layout = QVBoxLayout(tab_rec)
        rec_layout.setSpacing(10)

        # Mic Device Selection
        mic_row = QHBoxLayout()
        mic_row.addWidget(QLabel("Thiết bị Microphone:"))
        self.combo_mic = QComboBox()
        devices = QMediaDevices.audioInputs()
        for dev in devices:
            self.combo_mic.addItem(dev.description(), dev)
        self.combo_mic.currentIndexChanged.connect(self._on_mic_device_changed)
        mic_row.addWidget(self.combo_mic, stretch=1)
        rec_layout.addLayout(mic_row)

        # Record Status & Timer
        self.lbl_record_time = QLabel("00:00.0 (Chưa ghi âm)")
        self.lbl_record_time.setAlignment(Qt.AlignCenter)
        self.lbl_record_time.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #7aa2f7; background-color: #1a1b26; "
            "border: 1px solid #3b4261; border-radius: 8px; padding: 10px;"
        )
        rec_layout.addWidget(self.lbl_record_time)

        # Action Buttons
        btn_rec_box = QHBoxLayout()
        self.btn_start_record = QPushButton("🔴 Bắt đầu Ghi âm")
        self.btn_start_record.setFixedHeight(38)
        self.btn_start_record.setStyleSheet("background-color: #f7768e; color: #1a1b26; font-weight: bold;")
        self.btn_start_record.clicked.connect(self._start_recording)
        btn_rec_box.addWidget(self.btn_start_record)

        self.btn_stop_record = QPushButton("⏹ Dừng Ghi âm")
        self.btn_stop_record.setFixedHeight(38)
        self.btn_stop_record.setEnabled(False)
        self.btn_stop_record.clicked.connect(self._stop_recording)
        btn_rec_box.addWidget(self.btn_stop_record)

        self.btn_play_record = QPushButton("🔊 Nghe lại bản ghi")
        self.btn_play_record.setFixedHeight(38)
        self.btn_play_record.setEnabled(False)
        self.btn_play_record.clicked.connect(self._play_recorded_sample)
        btn_rec_box.addWidget(self.btn_play_record)

        rec_layout.addLayout(btn_rec_box)
        rec_layout.addStretch()
        self.tabs.addTab(tab_rec, "🎙 Ghi âm trực tiếp từ Mic")

        # --- Tab 2: Import Existing Audio File ---
        tab_import = QWidget()
        imp_layout = QVBoxLayout(tab_import)
        imp_layout.setSpacing(10)

        imp_row = QHBoxLayout()
        self.input_import_path = QLineEdit()
        self.input_import_path.setPlaceholderText("Chọn file âm thanh .wav, .mp3, .m4a...")
        imp_row.addWidget(self.input_import_path, stretch=1)

        self.btn_browse_import = QPushButton("📂 Chọn tệp...")
        self.btn_browse_import.clicked.connect(self._browse_audio_file)
        imp_row.addWidget(self.btn_browse_import)
        imp_layout.addLayout(imp_row)

        self.lbl_import_info = QLabel("Chưa chọn tệp âm thanh.")
        self.lbl_import_info.setStyleSheet("color: #9ece6a; font-weight: bold;")
        imp_layout.addWidget(self.lbl_import_info)

        self.btn_play_imported = QPushButton("🔊 Nghe thử tệp đã chọn")
        self.btn_play_imported.setEnabled(False)
        self.btn_play_imported.clicked.connect(self._play_imported_sample)
        imp_layout.addWidget(self.btn_play_imported)

        imp_layout.addStretch()
        self.tabs.addTab(tab_import, "📁 Chọn tệp âm thanh có sẵn")

        main_layout.addWidget(self.tabs)

        # --- Name and Register Form ---
        reg_box = QGroupBox("Thông tin Đăng ký Giọng Clone")
        reg_layout = QGridLayout(reg_box)
        reg_layout.setSpacing(8)

        reg_layout.addWidget(QLabel("Tên giọng Clone:"), 0, 0)
        self.input_voice_name = QLineEdit()
        self.input_voice_name.setPlaceholderText("Ví dụ: Giọng của tôi, Giọng MC Nam, Giọng Review...")
        reg_layout.addWidget(self.input_voice_name, 0, 1)

        self.chk_denoise = QCheckBox("Tự động khử nhiễu nền (Denoise) và chuẩn hóa mẫu âm thanh")
        self.chk_denoise.setChecked(True)
        reg_layout.addWidget(self.chk_denoise, 1, 0, 1, 2)

        self.btn_register_clone = QPushButton("⚡ ĐĂNG KÝ & NHÂN BẢN GIỌNG NÓI")
        self.btn_register_clone.setObjectName("PrimaryButton")
        self.btn_register_clone.setFixedHeight(40)
        self.btn_register_clone.clicked.connect(self._register_cloned_voice)
        reg_layout.addWidget(self.btn_register_clone, 2, 0, 1, 2)

        main_layout.addWidget(reg_box)

        # --- Saved Cloned Voices Management ---
        saved_box = QGroupBox("Danh sách các Giọng Clone Đã Lưu")
        saved_layout = QVBoxLayout(saved_box)
        self.list_saved_voices = QListWidget()
        saved_layout.addWidget(self.list_saved_voices)

        saved_btn_box = QHBoxLayout()
        self.btn_play_saved = QPushButton("🔊 Nghe mẫu giọng đã chọn")
        self.btn_play_saved.clicked.connect(self._play_selected_saved_voice)
        saved_btn_box.addWidget(self.btn_play_saved)

        self.btn_delete_saved = QPushButton("🗑 Xóa giọng clone đã chọn")
        self.btn_delete_saved.clicked.connect(self._delete_selected_saved_voice)
        saved_btn_box.addWidget(self.btn_delete_saved)

        saved_btn_box.addStretch()
        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.accept)
        saved_btn_box.addWidget(btn_close)

        saved_layout.addLayout(saved_btn_box)
        main_layout.addWidget(saved_box)

    def _on_mic_device_changed(self):
        dev = self.combo_mic.currentData()
        if dev:
            self.audio_input.setDevice(dev)

    def _start_recording(self):
        from app.utils.paths import get_default_cache_dir
        cache_dir = get_default_cache_dir()
        self.recorded_wav_path = cache_dir / "temp_mic_recording.wav"

        # Setup format for recorder
        rec_format = QMediaFormat()
        rec_format.setFileFormat(QMediaFormat.FileFormat.Wave)
        rec_format.setAudioCodec(QMediaFormat.AudioCodec.Wave)
        self.recorder.setMediaFormat(rec_format)
        self.recorder.setOutputLocation(QUrl.fromLocalFile(str(self.recorded_wav_path)))

        self.recorder.record()
        self.recording_elapsed_sec = 0.0
        self.record_timer.start()

        self.btn_start_record.setEnabled(False)
        self.btn_stop_record.setEnabled(True)
        self.btn_play_record.setEnabled(False)
        self.lbl_record_time.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #f7768e; background-color: #2e1a24; "
            "border: 2px solid #f7768e; border-radius: 8px; padding: 10px;"
        )
        self.lbl_record_time.setText("🔴 00:00.0 (Đang ghi âm...)")

    def _on_record_timer_tick(self):
        self.recording_elapsed_sec += 0.1
        sec = int(self.recording_elapsed_sec)
        ms = int((self.recording_elapsed_sec - sec) * 10)
        status_txt = "Đang ghi âm..."
        if self.recording_elapsed_sec < 3.0:
            status_txt = "Hãy nói tiếp (tối thiểu 3s)..."
        elif self.recording_elapsed_sec <= 8.0:
            status_txt = "Độ dài lý tưởng (3-8s)!"
        else:
            status_txt = "Đã đủ độ dài mẫu, hãy bấm Dừng."

        self.lbl_record_time.setText(f"🔴 {sec:02d}.{ms}s — {status_txt}")

    def _stop_recording(self):
        self.record_timer.stop()
        self.recorder.stop()

        self.btn_start_record.setEnabled(True)
        self.btn_stop_record.setEnabled(False)
        self.btn_play_record.setEnabled(True)

        self.lbl_record_time.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #9ece6a; background-color: #1a2b24; "
            "border: 1px solid #9ece6a; border-radius: 8px; padding: 10px;"
        )
        self.lbl_record_time.setText(f"✅ Đã ghi âm xong: {self.recording_elapsed_sec:.1f}s")

    def _play_recorded_sample(self):
        if self.recorded_wav_path and os.path.exists(self.recorded_wav_path):
            self.player.setSource(QUrl.fromLocalFile(str(self.recorded_wav_path)))
            self.player.play()

    def _browse_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn tệp âm thanh giọng mẫu",
            "",
            "Audio Files (*.wav *.mp3 *.m4a *.aac *.flac *.ogg);;All Files (*.*)"
        )
        if file_path:
            self.imported_audio_path = Path(file_path)
            self.input_import_path.setText(file_path)
            try:
                from app.utils.audio_utils import get_audio_duration
                dur = get_audio_duration(self.imported_audio_path)
                self.lbl_import_info.setText(f"✅ Tệp hợp lệ: {self.imported_audio_path.name} | Thời lượng: {dur:.1f}s")
                self.btn_play_imported.setEnabled(True)
                if not self.input_voice_name.text().strip():
                    self.input_voice_name.setText(self.imported_audio_path.stem.replace("_", " ").title())
            except Exception as e:
                self.lbl_import_info.setText(f"⚠️ Không đọc được thời lượng: {e}")
                self.btn_play_imported.setEnabled(True)

    def _play_imported_sample(self):
        if self.imported_audio_path and os.path.exists(self.imported_audio_path):
            self.player.setSource(QUrl.fromLocalFile(str(self.imported_audio_path)))
            self.player.play()

    def _load_cloned_voices_list(self):
        self.list_saved_voices.clear()
        from app.providers.vieneu_tts_provider import load_saved_cloned_voices
        cloned = load_saved_cloned_voices()
        for cv in cloned:
            item = QListWidgetItem(f"✨ {cv['name']} ({Path(cv.get('audio_path', '')).name})")
            item.setData(Qt.UserRole, cv)
            self.list_saved_voices.addItem(item)

    def _play_selected_saved_voice(self):
        item = self.list_saved_voices.currentItem()
        if not item:
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn một giọng clone từ danh sách để nghe.")
            return
        cv = item.data(Qt.UserRole)
        p = cv.get("audio_path")
        if p and os.path.exists(p):
            self.player.setSource(QUrl.fromLocalFile(str(p)))
            self.player.play()
        else:
            QMessageBox.warning(self, "Thông báo", "Tệp âm thanh mẫu không tồn tại trên ổ đĩa.")

    def _delete_selected_saved_voice(self):
        item = self.list_saved_voices.currentItem()
        if not item:
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn giọng clone cần xóa.")
            return
        cv = item.data(Qt.UserRole)
        name = cv.get("name")
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa giọng clone '{name}' không?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.vieneu_provider.remove_cloned_voice(name)
            self._load_cloned_voices_list()
            self.voice_cloned.emit("")

    def _register_cloned_voice(self):
        name = self.input_voice_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên cho giọng clone.")
            return

        # Determine reference audio source
        curr_tab = self.tabs.currentIndex()
        ref_source = None
        if curr_tab == 0:  # Microphone recording
            if not self.recorded_wav_path or not os.path.exists(self.recorded_wav_path):
                QMessageBox.warning(self, "Thông báo", "Vui lòng ghi âm giọng mẫu trước khi đăng ký.")
                return
            ref_source = self.recorded_wav_path
        else:  # Imported file
            if not self.imported_audio_path or not os.path.exists(self.imported_audio_path):
                QMessageBox.warning(self, "Thông báo", "Vui lòng chọn tệp âm thanh giọng mẫu trước khi đăng ký.")
                return
            ref_source = self.imported_audio_path

        denoise = self.chk_denoise.isChecked()

        try:
            self.btn_register_clone.setEnabled(False)
            self.btn_register_clone.setText("⏳ Đang xử lý khử nhiễu & trích xuất giọng...")

            # Enroll voice
            res = self.vieneu_provider.register_cloned_voice(
                name=name,
                source_audio_path=ref_source,
                denoise=denoise
            )

            self._load_cloned_voices_list()
            self.voice_cloned.emit(name)
            QMessageBox.information(
                self,
                "Thành công",
                f"Đã nhân bản và đăng ký thành công giọng: '{name}'!\n"
                "Giọng này hiện đã sẵn sàng trong danh sách giọng đọc Tiếng Việt."
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Lỗi Nhân Bản Giọng", f"Không thể nhân bản giọng nói:\n{e}")
        finally:
            self.btn_register_clone.setEnabled(True)
            self.btn_register_clone.setText("⚡ ĐĂNG KÝ & NHÂN BẢN GIỌNG NÓI")

