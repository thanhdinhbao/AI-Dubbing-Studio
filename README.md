# AI Dubbing Studio — Trợ Lý Lồng Tiếng Phim & Video Tự Động Bằng AI

Ứng dụng Windows desktop chuyên nghiệp giúp chuyển đổi ngôn ngữ lời thoại video sang tiếng Việt tự nhiên, tự động giữ nhạc nền, hiệu ứng âm thanh và đồng bộ hóa thời lượng video linh hoạt bằng cơ chế **Dynamic Duration**.

---

## 1. Giới thiệu

**AI Dubbing Studio** là giải pháp phần mềm desktop hoàn chỉnh được xây dựng trên nền tảng **Python 3.12**, giao diện đồ họa **PySide6 (Qt 6)**, kết hợp cùng sức mạnh xử lý media của **FFmpeg** và các mô hình AI tiên tiến:
- **faster-whisper**: Nhận dạng lời thoại tự động (ASR) với độ chính xác cao và tốc độ vượt trội.
- **Dịch thuật AI**: Bản dịch tiếng Việt tự nhiên, giàu cảm xúc, giữ nguyên thuật ngữ, con số và tên riêng.
- **Tổng hợp giọng đọc (TTS)**: Hỗ trợ giọng đọc Edge TTS truyền cảm hoặc các mô hình Offline (Piper/ONNX) không cần mạng.
- **Dynamic Duration Engine**: Trọng tâm công nghệ độc quyền cho phép video tự động co giãn thời gian khớp với độ dài câu thoại tiếng Việt mà không làm méo hình hay biến dạng cao độ âm thanh.

---

## 2. Tính năng chính

- 🎬 **Hỗ trợ định dạng đa dạng**: Đọc và xử lý mượt mà MP4, MKV, MOV, AVI, WEBM, FLV...
- 🎙 **Speech-to-Text mạnh mẽ**: Tích hợp faster-whisper với đầy đủ các kích thước mô hình (`tiny`, `base`, `small`, `medium`, `large-v3`), hỗ trợ tăng tốc CPU và GPU CUDA.
- 🌐 **Dịch thuật thông minh**: Hỗ trợ OpenAI-compatible API với cơ chế batching bảo toàn ngữ cảnh toàn bộ video.
- 🔊 **AI Voice tiếng Việt**: Giọng đọc tự nhiên (Hoài My, Nam Minh), tinh chỉnh tốc độ (Speed), cao độ (Pitch), âm lượng (Volume).
- 🎵 **Giữ trọn nhạc nền & Hiệu ứng**: Cơ chế tự động Ducking thông minh làm nhỏ nhạc nền khi có lời nói và trả về âm lượng chuẩn khi kết thúc câu.
- ⏱ **Dynamic Duration Timeline**: Tự động mở rộng hoặc điều chỉnh timeline khi câu tiếng Việt dài hơn bản gốc thông qua kỹ thuật freeze-frame / pad chuẩn xác từng khung hình.
- 🖥 **Giao diện hiện đại & Worker Threads**: Đa luồng 100% bằng PySide6 QThread, không bao giờ gây đơ hay treo ứng dụng trong quá trình xử lý.
- 📦 **Đóng gói Windows Executable**: Đóng gói hoàn chỉnh thành file `.exe` bằng PyInstaller.

---

## 3. Kiến trúc dự án

```text
AI-Dubbing-Studio/
├── main.py                     # Entry point khởi chạy ứng dụng
├── requirements.txt            # Danh sách thư viện Python
├── pyinstaller.spec            # Cấu hình đóng gói PyInstaller
├── build.ps1                   # Script PowerShell tự động kiểm tra và build EXE
├── run.ps1                     # Script PowerShell khởi chạy ứng dụng
├── app/
│   ├── bootstrap.py            # Khởi tạo môi trường, logging và Qt Application
│   ├── config.py               # Quản lý cấu hình và lưu trữ tham số
│   ├── constants.py            # Hằng số hệ thống, codec, ngôn ngữ
│   ├── exceptions.py           # Phân loại ngoại lệ nghiệp vụ
│   ├── models.py               # Pydantic models (Project, Dialogue, Timeline)
│   ├── logging_config.py       # Hệ thống ghi log xoay vòng và bảo mật dữ liệu
│   ├── project_manager.py      # Quản lý không gian làm việc và lưu trữ JSON
│   ├── task_manager.py         # Quản lý luồng worker, tiến trình và nút hủy
│   ├── providers/              # Adapter cho AI Services
│   │   ├── base.py             # Interface BaseTranslationProvider, BaseTTSProvider
│   │   ├── translation_api.py  # Dịch qua OpenAI-compatible API
│   │   ├── edge_tts_provider.py# Giọng đọc tự nhiên Edge TTS
│   │   ├── tts_api.py          # API TTS OpenAI
│   │   └── offline_tts_provider.py # TTS hoàn toàn offline (Piper/ONNX)
│   ├── services/               # Nghiệp vụ xử lý Media và AI
│   │   ├── media_probe.py      # Phân tích thông số media bằng ffprobe
│   │   ├── audio_extractor.py  # Trích xuất track audio PCM 16-bit
│   │   ├── transcription.py    # ASR faster-whisper
│   │   ├── translation.py      # Dịch thuật hàng loạt giữ nguyên ID
│   │   ├── speech_synthesis.py # Tạo giọng đọc TTS và đo thời lượng thực tế
│   │   ├── source_separation.py# Tách vocal hoặc tạo track ducking
│   │   ├── timeline_engine.py  # TÍNH NĂNG TRỌNG TÂM: Dynamic Duration Timeline
│   │   ├── audio_alignment.py  # Đồng bộ thời gian và phụ đề SRT
│   │   ├── audio_mixer.py      # Hòa âm chuẩn mẫu với Auto-Ducking
│   │   ├── video_renderer.py   # Dựng video hoàn chỉnh bằng FFmpeg filter
│   │   └── media_validator.py  # Kiểm tra tính toàn vẹn của video sau render
│   ├── ui/                     # Giao diện đồ họa PySide6
│   │   ├── main_window.py      # Cửa sổ chính và điều phối Sidebar
│   │   ├── styles.py           # Bộ giao diện Dark Theme
│   │   ├── dialogs.py          # Hộp thoại Cài đặt (Settings) và Giới thiệu
│   │   ├── widgets/            # Các widget chuyên dụng
│   │   │   ├── media_player.py # Trình phát video/audio xem trước
│   │   │   ├── subtitle_editor.py # Bảng chỉnh sửa phụ đề tương tác
│   │   │   ├── timeline_editor.py # Widget vẽ timeline đồ họa 4 track
│   │   │   ├── log_viewer.py   # Bảng hiển thị log trực tiếp
│   │   │   └── progress_panel.py # Thanh tiến trình và nút Hủy tác vụ
│   │   └── pages/              # 6 Tab chức năng chính
│   │       ├── project_page.py
│   │       ├── transcription_page.py
│   │       ├── voice_page.py
│   │       ├── audio_page.py
│   │       ├── timeline_page.py
│   │       └── export_page.py
│   ├── utils/
│   │   ├── audio_utils.py
│   │   ├── ffmpeg_utils.py
│   │   ├── paths.py
│   │   ├── retry.py
│   │   ├── timecode.py
│   │   └── validation.py
└── tests/                      # Bộ kiểm thử tự động
    ├── test_subtitles.py
    ├── test_translation.py
    ├── test_timeline.py
    ├── test_audio_alignment.py
    ├── test_media_validation.py
    └── test_integration_render.py
```

---

## 4. Yêu cầu môi trường

- **Hệ điều hành**: Windows 10 hoặc Windows 11 (64-bit).
- **Python**: Phiên bản 3.12 (khuyến nghị 3.12.x).
- **FFmpeg & FFprobe**: Phiên bản 4.4 trở lên (khuyến nghị FFmpeg 6.x - 9.x).
- **Dung lượng đĩa trống**: Tối thiểu 5GB để lưu trữ video và file tạm trung gian.
- **RAM**: Tối thiểu 8GB (khuyến nghị 16GB).
- **GPU (Tùy chọn)**: Card đồ họa NVIDIA hỗ trợ CUDA nếu muốn tăng tốc ASR Whisper.

---

## 5. Hướng dẫn cài đặt

### 5.1. Cài đặt FFmpeg
1. Tải bản build đầy đủ cho Windows từ [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (chọn bản `ffmpeg-release-essentials.zip`).
2. Giải nén vào thư mục, ví dụ: `C:\ffmpeg`.
3. Thêm thư mục `C:\ffmpeg\bin` vào biến môi trường **PATH** của Windows.
4. Mở PowerShell và kiểm tra:
   ```powershell
   ffmpeg -version
   ffprobe -version
   ```

### 5.2. Cài đặt Python & Virtual Environment
1. Tải và cài đặt Python 3.12 từ trang chủ `python.org` (tích chọn **Add python.exe to PATH**).
2. Di chuyển vào thư mục dự án và tạo môi trường ảo:
   ```powershell
   cd d:\PROJECT-PYTHON\T10-2026\voice-dubbing
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

### 5.3. Cài đặt thư viện phụ thuộc
```powershell
pip install -r requirements.txt
```

---

## 6. Cấu hình dịch thuật & giọng đọc

1. Nhấp vào nút **⚙ Cài đặt** ở góc trên bên phải giao diện ứng dụng.
2. **API Dịch thuật**:
   - Nhập `Base URL` (mặc định: `https://api.openai.com/v1`).
   - Nhập `API Key`.
   - Nhập tên mô hình, ví dụ: `gpt-4o-mini`.
   - Nhấp **Kiểm tra Kết nối** để xác nhận kết nối.
3. **Mô hình Offline (Tùy chọn)**:
   - Tải file mô hình Piper tiếng Việt (ví dụ `vi_VN-vivos-x_low.onnx`).
   - Chọn đường dẫn đến file `.onnx` trong tab **Offline Models**.

---

## 7. Hướng dẫn sử dụng chi tiết từng Tab

### Tab 1: Dự án & Media
- Tạo dự án mới hoặc mở dự án đã lưu.
- Chọn tệp video nguồn (MP4, MKV, MOV, AVI...). Ứng dụng tự động đọc thông số độ phân giải, FPS, codec, thời lượng và hiển thị dung lượng đĩa trống.
- Có thể xem trước video trực tiếp trên trình phát tích hợp.

### Tab 2: Nhận diện & Phụ đề
- Chọn mô hình Whisper (`tiny`, `base`, `small`, `medium`, `large-v3`) và thiết bị (`cpu` hoặc `cuda`).
- Nhấp **🎙 Bắt đầu Nhận diện ASR** để tự động tách âm và chuyển lời thoại thành phụ đề.
- Nhấp **🌐 Dịch toàn bộ sang Tiếng Việt** để dịch câu thoại.
- Người dùng có thể nhấp trực tiếp vào từng ô trên bảng phụ đề để chỉnh sửa nội dung dịch, chỉnh sửa thời gian bắt đầu/kết thúc hoặc nghe thử từng câu.
- Hỗ trợ nhập (Import) hoặc xuất (Export) tệp phụ đề `.srt`.

### Tab 3: Giọng đọc AI
- Chọn nhà cung cấp: **Microsoft Edge TTS** (tự nhiên, khuyến nghị), **OpenAI API**, hoặc **Offline Engine**.
- Chọn giọng đọc (ví dụ: *Hoài My* - Nữ tự nhiên, *Nam Minh* - Nam trầm ấm).
- Tùy chỉnh tốc độ đọc, cao độ, âm lượng và phong cách lồng tiếng.
- Nhấp **🔊 Nghe thử giọng mẫu** để kiểm tra trước.
- Nhấp **⚡ Tạo Giọng đọc cho Toàn bộ Video** để hệ thống tổng hợp audio cho tất cả các câu thoại và đo thời lượng chính xác từng câu.

### Tab 4: Tách nhạc & Hòa âm
- Chọn phương thức giữ nhạc nền:
  - **Tự động Ducking (Khuyến nghị)**: Tự động hạ âm lượng nhạc nền xuống 20% khi có lời nói tiếng Việt và chuyển mượt về 100% khi kết thúc câu.
  - **Tách Vocal AI (Demucs)**: Sử dụng mô hình Demucs để phân tách giọng nói gốc ra khỏi nhạc phim.
  - **Giữ âm thanh gốc mức thấp**: Giữ toàn bộ âm thanh nền ở mức cố định (ví dụ 25%).
  - **Tắt hoàn toàn âm thanh gốc**: Chỉ phát giọng đọc tiếng Việt trên nền tĩnh.
- Điều chỉnh thanh trượt âm lượng nhạc nền và âm lượng giọng đọc.

### Tab 5: Dynamic Dubbing Timeline (Tính năng Trọng tâm)
- Hiển thị thống kê so sánh trực quan giữa thời lượng video gốc và thời lượng video sau khi lồng tiếng.
- Khi một câu tiếng Việt có thời lượng đọc thực tế dài hơn câu tiếng Anh ban đầu (ví dụ: gốc 2 giây, tiếng Việt đọc 3 giây):
  - Hệ thống cấp trọn vẹn 3 giây cho câu tiếng Việt, **không cắt cụt tiếng cuối hay ép tốc độ đọc bất thường**.
  - Tự động đóng băng khung hình cuối (Freeze last frame) hoặc đệm khoảng dừng cho phần dôi dư.
  - Dời toàn bộ các câu thoại và cảnh phim phía sau về mốc thời gian mới một cách chuẩn xác.
- Biểu đồ Timeline 4 track cho phép người dùng quan sát chi tiết các khối video, lời thoại gốc, TTS tiếng Việt và các vùng đóng băng khung hình (hiển thị màu cam nổi bật).

### Tab 6: Xuất Video
- Tùy chọn định dạng đầu ra, codec video (`libx264`, `h264_nvenc`, `libx265`), chất lượng CRF và codec audio.
- Nhấp **🚀 BẮT ĐẦU XUẤT VIDEO LỒNG TIẾNG**.
- Sau khi render xong, hệ thống tự động gọi FFprobe kiểm tra tính toàn vẹn của tệp (thời lượng, stream hình, stream tiếng), phát video kết quả trên màn hình và cung cấp nút mở trực tiếp thư mục chứa video.

---

## 8. Đóng gói ứng dụng thành file `.exe` (PyInstaller)

Để đóng gói ứng dụng thành gói chạy độc lập trên Windows mà không cần cài Python:

```powershell
.\build.ps1
```

Script sẽ tự động:
1. Kiểm tra Python và FFmpeg.
2. Kiểm tra các thư viện trong `requirements.txt`.
3. Chạy toàn bộ bộ kiểm thử tự động (pytest).
4. Thực thi PyInstaller và tạo thư mục chạy `dist\AIDubbingStudio\`.
5. Tệp thực thi chính: `dist\AIDubbingStudio\AIDubbingStudio.exe`.

---

## 9. Chạy kiểm thử tự động (Unit & Integration Tests)

Dự án đi kèm bộ kiểm thử toàn diện bao quát tất cả các kịch bản thực tế:

```powershell
pytest -v
```

Danh sách các bài test cốt lõi:
- `test_subtitles.py`: Kiểm tra chuyển đổi định dạng timecode SRT và tính toàn vẹn phụ đề.
- `test_translation.py`: Kiểm tra cơ chế dịch hàng loạt và ánh xạ chính xác ID từng câu.
- `test_timeline.py`:
  - **Mandatory Test 1**: TTS dài hơn bản gốc -> Video giãn thời gian chuẩn xác, chèn freeze frame, câu sau dịch chuyển đúng mốc.
  - **Mandatory Test 2**: TTS ngắn hơn bản gốc -> Không tạo timestamp âm, không gây chồng lấn.
  - **Mandatory Test 3**: Xử lý 5 câu thoại liên tiếp có thời lượng đa dạng, giữ nguyên thứ tự và tính đúng tổng thời lượng.
- `test_audio_alignment.py`: Kiểm tra ánh xạ phụ đề theo timeline đầu ra.
- `test_media_validation.py`: Kiểm tra phát hiện tệp video lỗi hoặc sai thông số.
- `test_integration_render.py`: Tạo video mẫu tổng hợp, chạy toàn bộ pipeline hòa âm ducking và render video bằng FFmpeg, sau đó dùng FFprobe xác minh file kết quả.

---

## 10. Xử lý sự cố & Lưu ý quan trọng

1. **Lỗi không tìm thấy FFmpeg**:
   - Đảm bảo FFmpeg đã được thêm vào biến môi trường PATH hoặc mở mục **Cài đặt** trên giao diện để trỏ đường dẫn trực tiếp đến file `ffmpeg.exe` và `ffprobe.exe`.
2. **Lưu ý về Voice Providers**:
   - **Microsoft Edge TTS**: Yêu cầu máy tính có kết nối mạng Internet.
   - **Offline TTS**: Yêu cầu người dùng phải tải file mô hình Piper tiếng Việt (ONNX) về máy trước khi sử dụng.
3. **Bảo mật API Key**:
   - Ứng dụng tự động ẩn và mã hóa API Key trong giao diện cấu hình và log hệ thống. Tuyệt đối không commit file `.env` chứa khóa bí mật lên repository công khai.
4. **Giới hạn Source Separation**:
   - Chế độ tự động Ducking là giải pháp nhanh, ổn định và giữ chất lượng âm thanh tốt nhất trên mọi cấu hình máy tính. Nếu sử dụng Demucs để tách vocal, máy tính nên có card đồ họa và tối thiểu 8GB RAM trống để đạt hiệu năng tối ưu.

---

## 11. Giấy phép

Phần mềm được phát hành theo giấy phép **MIT License**.

