import os
import re
import sys
import subprocess
import webbrowser
import configparser
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

# ==========================
# Autoinstall Packages
# ==========================
def install_and_import_packages():
    """Tự động cài đặt các gói nếu thiếu và nhập chúng."""
    required_packages = ['numpy', 'librosa', 'yt-dlp', 'PyQt5']
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("Cảnh báo: Đang thiếu các gói sau. Đang tiến hành cài đặt...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--upgrade', *missing_packages])
            print("Cài đặt thành công. Đang khởi động lại ứng dụng...")
            
        except subprocess.CalledProcessError as e:
            print(f"Lỗi khi cài đặt các gói: {e}")
            print("Vui lòng cài đặt thủ công bằng lệnh: pip install numpy librosa yt-dlp PyQt5")
            sys.exit(1)
        except Exception as e:
            print(f"Lỗi không xác định: {e}")
            sys.exit(1)

    # Nhập các gói chỉ khi tất cả đã được cài đặt thành công
    global np, librosa, YoutubeDL
    global QObject, pyqtSignal, QThread, Qt, QProcess, QSize, QFileSystemWatcher
    global QPalette, QColor, QPixmap, QIcon
    global QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QSpinBox, QGroupBox, QTextEdit, QComboBox, QProgressBar, QCheckBox, QTabWidget, QListWidget, QListWidgetItem, QMenu, QAction, QGridLayout, QFrame, QScrollArea, QSizePolicy, QSpacerItem

    import numpy as np
    import librosa
    from yt_dlp import YoutubeDL

    from PyQt5.QtCore import QObject, pyqtSignal, QThread, Qt, QProcess, QSize, QFileSystemWatcher
    from PyQt5.QtGui import QPalette, QColor, QPixmap, QIcon
    from PyQt5.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
        QPushButton, QFileDialog, QMessageBox, QSpinBox, QGroupBox, QTextEdit,
        QComboBox, QProgressBar, QCheckBox, QTabWidget, QListWidget, QListWidgetItem,
        QMenu, QAction, QGridLayout, QFrame, QScrollArea, QSizePolicy, QSpacerItem
    )

install_and_import_packages()

# ==========================
# Các import khác (không cần kiểm tra)
# ==========================
# Fix UnicodeEncodeError on Windows
if sys.version_info.major >= 3 and sys.version_info.minor >= 7:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass

# ==========================
# Helpers
# ==========================
def safe_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip() or "highlight"

def sec_to_time(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def hms_to_sec(hms: str) -> int:
    parts = list(map(int, hms.split(":")))
    s = parts.pop()
    m = parts.pop() if parts else 0
    h = parts.pop() if parts else 0
    return h * 3600 + m * 60 + s

def find_highlight(audio_file: str, clip_duration: int = 30, num_clips: int = 1) -> list[tuple[str, str]]:
    y, sr = librosa.load(audio_file, sr=22050, mono=True)
    rms = librosa.feature.rms(y=y, frame_length=sr, hop_length=sr, center=False)[0]

    highlight_points = []
    for _ in range(num_clips):
        best_sec = int(np.argmax(rms))
        if rms[best_sec] == 0:
            break
        start = max(0, best_sec - clip_duration // 2)
        end = start + clip_duration
        highlight_points.append((sec_to_time(start), sec_to_time(end)))
        start_idx = max(0, best_sec - clip_duration)
        end_idx = min(len(rms), best_sec + clip_duration)
        rms[start_idx:end_idx] = 0
    return highlight_points

def save_config(ffmpeg_path: str, cookies_path: str, output_path: str, quality: str, num_clips: int, aspect_ratio: str):
    config = configparser.ConfigParser()
    config['PATHS'] = {
        'ffmpeg_path': ffmpeg_path,
        'cookies_path': cookies_path,
        'output_path': output_path,
    }
    config['SETTINGS'] = {
        'quality': quality,
        'num_clips': str(num_clips),
        'aspect_ratio': aspect_ratio,
    }
    with open('config.ini', 'w', encoding='utf-8') as f:
        config.write(f)

def load_config() -> tuple[str, str, str, str, int, str]:
    config = configparser.ConfigParser()
    if os.path.exists('config.ini'):
        config.read('config.ini', encoding='utf-8')
        ffmpeg_path = config.get('PATHS', 'ffmpeg_path', fallback='')
        cookies_path = config.get('PATHS', 'cookies_path', fallback='')
        output_path = config.get('SETTINGS', 'output_path', fallback=os.path.join(os.getcwd(), 'highlights'))
        quality = config.get('SETTINGS', 'quality', fallback='1080p')
        num_clips = config.getint('SETTINGS', 'num_clips', fallback=1)
        aspect_ratio = config.get('SETTINGS', 'aspect_ratio', fallback='Gốc')
        return ffmpeg_path, cookies_path, output_path, quality, num_clips, aspect_ratio
    return '', '', os.path.join(os.getcwd(), 'highlights'), '1080p', 1, 'Gốc'

def find_ffmpeg_in_path() -> str | None:
    path_env = os.environ.get('PATH', '')
    for p in path_env.split(os.pathsep):
        full_path = os.path.join(p, 'ffmpeg.exe')
        if os.path.exists(full_path):
            return full_path
    return None

def get_human_readable_size(file_path: str) -> str:
    try:
        size_bytes = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:3.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:3.1f} PB"
    except FileNotFoundError:
        return "N/A"

def get_video_duration(file_path: str, ffprobe_bin: str) -> float:
    if not os.path.exists(ffprobe_bin):
        return 0
    try:
        cmd = [ffprobe_bin, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return 0

# ==========================
# Worker (QThread)
# ==========================
@dataclass
class JobConfig:
    url: str
    clip_duration: int
    ffmpeg_path: str
    cookies_path: str | None
    output_path: str
    quality: str
    num_clips: int
    aspect_ratio: str

class HighlightWorker(QObject):
    log = pyqtSignal(str)
    done = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, cfg: JobConfig, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.process = None

    def _resolve_ffmpeg_bin(self):
        path = self.cfg.ffmpeg_path
        if not os.path.exists(path):
            raise FileNotFoundError("Đường dẫn ffmpeg.exe/ffprobe.exe không hợp lệ.")
        if path.lower().endswith("ffmpeg.exe"):
            return os.path.dirname(path)
        return path

    def _ydl_common(self):
        headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/115.0.0.0 Safari/537.36'),
        }
        opts = {
            'http_headers': headers,
            'nocheckcertificate': True,
            'ffmpeg_location': self._resolve_ffmpeg_bin(),
        }
        if self.cfg.cookies_path and os.path.isfile(self.cfg.cookies_path):
            opts['cookiefile'] = self.cfg.cookies_path
        return opts

    def _get_title(self) -> str:
        self.log.emit("Đang lấy metadata...")
        opts = self._ydl_common()
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(self.cfg.url, download=False)
        title = info.get("title", "highlight")
        return safe_filename(title)

    def _download_audio_wav(self) -> str:
        self.log.emit("Đang tải audio (WAV) để phân tích...")
        self.progress.emit(10)
        opts = self._ydl_common()
        opts.update({
            'format': 'bestaudio/best',
            'outtmpl': "temp_audio.%(ext)s",
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
        })
        with YoutubeDL(opts) as ydl:
            ydl.download([self.cfg.url])
        return "temp_audio.wav"

    def _download_full_video(self, out_path: str):
        self.log.emit("⬇Đang tải video gốc...")
        self.progress.emit(40)
        opts = self._ydl_common()

        if self.cfg.quality == '1080p':
            format_str = 'bestvideo[height<=1080]+bestaudio/best'
        elif self.cfg.quality == '720p':
            format_str = 'bestvideo[height<=720]+bestaudio/best'
        else:
            format_str = 'bestvideo[height<=720]+bestaudio/best'

        opts.update({
            'format': format_str,
            'outtmpl': out_path.replace(".mp4", "") + ".%(ext)s",
            'merge_output_format': 'mp4',
        })
        with YoutubeDL(opts) as ydl:
            ydl.download([self.cfg.url])

    def _cut_with_ffmpeg(self, src: str, dst: str, start_hms: str, duration: int):
        self.log.emit(f"FFmpeg: cắt {start_hms} (dài {duration}s) -> {os.path.basename(dst)}")
        self.progress.emit(75)

        ffmpeg_bin = os.path.join(self._resolve_ffmpeg_bin(), "ffmpeg.exe")

        cmd = [
            ffmpeg_bin,
            "-hide_banner", "-loglevel", "error",
            "-ss", start_hms,
            "-i", src,
            "-t", str(duration)
        ]

        video_codec = "copy"
        filters = []

        if self.cfg.aspect_ratio != "Gốc":
            ffprobe_bin = os.path.join(self._resolve_ffmpeg_bin(), "ffprobe.exe")
            get_res_cmd = [
                ffprobe_bin, "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", src
            ]

            try:
                result = subprocess.run(get_res_cmd, capture_output=True, text=True, check=True)
                w_orig, h_orig = map(int, result.stdout.strip().split('x'))
                video_codec = "libx264"
            except (subprocess.CalledProcessError, ValueError):
                self.log.emit("Cảnh báo: Không thể lấy kích thước video. Bỏ qua thay đổi tỷ lệ.")
                video_codec = "copy"
                self.cfg.aspect_ratio = "Gốc"

        if self.cfg.aspect_ratio == "Dọc 9:16 (Cắt)":
            new_w = int(h_orig * 9 / 16)
            filters.append(f"crop={new_w}:{h_orig}")
        elif self.cfg.aspect_ratio == "Dọc 9:16 (Viền đen)":
            new_h = int(w_orig * 16 / 9)
            pad_y = (new_h - h_orig) // 2
            filters.append(f"pad=width={w_orig}:height={new_h}:x=0:y={pad_y}:color=black")

        if filters:
            cmd.extend(["-vf", ",".join(filters), "-c:v", video_codec])
        else:
            cmd.extend(["-c:v", video_codec])

        cmd.extend([
            "-c:a", "aac",
            "-movflags", "+faststart",
            "-y",
            dst
        ])

        try:
            subprocess.run(cmd, check=True, text=True, stderr=subprocess.PIPE, encoding='utf-8')
        except subprocess.CalledProcessError as e:
            raise Exception(f"FFmpeg process failed with exit code {e.returncode}\n{e.stderr}")

    def run(self):
        try:
            title = self._get_title()
            self.log.emit(f"Video: {title}")

            temp_audio_path = "temp_audio.wav"
            temp_full_video_path = f"{title}_full.mp4"

            self._download_audio_wav()

            self.log.emit("Đang phân tích audio để tìm highlight...")
            highlight_points = find_highlight(temp_audio_path, self.cfg.clip_duration, self.cfg.num_clips)

            if not highlight_points:
                raise Exception("Không tìm thấy đoạn highlight nào.")

            self._download_full_video(temp_full_video_path)

            if not os.path.exists(self.cfg.output_path):
                os.makedirs(self.cfg.output_path)

            for i, (start_hms, end_hms) in enumerate(highlight_points):
                out_mp4 = os.path.join(self.cfg.output_path, f"{title}_highlight_{i+1}.mp4")
                duration = hms_to_sec(end_hms) - hms_to_sec(start_hms)
                self._cut_with_ffmpeg(temp_full_video_path, out_mp4, start_hms, duration)

            # Clean up
            for p in (temp_audio_path, temp_full_video_path):
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass

            self.progress.emit(100)
            self.done.emit(self.cfg.output_path)

        except Exception as e:
            self.error.emit(str(e))

# ==========================
# Dark Theme (Fusion)
# ==========================
def apply_dark_theme(app: QApplication, accent="#34c759"):
    app.setStyle("Fusion")
    palette = QPalette()

    bg = QColor(24, 24, 24)
    base = QColor(32, 32, 32)
    alt = QColor(40, 40, 40)
    text = QColor(232, 232, 232)
    disabled = QColor(127, 127, 127)

    palette.setColor(QPalette.Window, bg)
    palette.setColor(QPalette.WindowText, text)
    palette.setColor(QPalette.Base, base)
    palette.setColor(QPalette.AlternateBase, alt)
    palette.setColor(QPalette.ToolTipBase, base)
    palette.setColor(QPalette.ToolTipText, text)
    palette.setColor(QPalette.Text, text)
    palette.setColor(QPalette.Button, alt)
    palette.setColor(QPalette.ButtonText, text)
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Highlight, QColor(accent))
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    palette.setColor(QPalette.Disabled, QPalette.Text, disabled)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled)

    app.setPalette(palette)

    app.setStyleSheet(f"""
        QWidget {{
            font-size: 14px;
            color: {text.name()};
            background-color: {bg.name()};
        }}
        QGroupBox {{
            border: 1px solid #3a3a3a;
            border-radius: 8px;
            margin-top: 10px;
            padding: 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: {QColor(accent).name()};
            font-weight: 600;
        }}
        QLineEdit, QSpinBox, QComboBox, QTextEdit {{
            background-color: {base.name()};
            border: 1px solid #3a3a3a;
            border-radius: 6px;
            padding: 6px;
        }}
        QPushButton {{
            background-color: {QColor(accent).name()};
            color: #000;
            border: none;
            border-radius: 8px;
            padding: 8px 14px;
            font-weight: 600;
        }}
        QPushButton:disabled {{
            background-color: #2c2c2c;
            color: #888;
        }}
        QProgressBar {{
            border: 1px solid #3a3a3a;
            border-radius: 6px;
            text-align: center;
            background-color: #2c2c2c;
            color: white;
        }}
        QProgressBar::chunk {{
            background-color: {QColor(accent).name()};
            border-radius: 6px;
        }}
        QTabWidget::pane {{
            border: 1px solid #3a3a3a;
            border-top-left-radius: 0;
            border-top-right-radius: 0;
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
            background-color: {bg.name()};
        }}
        QTabWidget::tab-bar {{
            left: 5px;
        }}
        QTabBar::tab {{
            background: #2c2c2c;
            color: #ddd;
            border: 1px solid #3a3a3a;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 6px 12px;
            min-width: 100px;
        }}
        QTabBar::tab:selected {{
            background: {bg.name()};
            border-bottom-color: {bg.name()};
        }}
        .VideoItemWidget {{
            border: 1px solid #4a4a4a;
            border-radius: 8px;
            background-color: #2a2a2a;
        }}
        .VideoItemWidget:hover {{
            border-color: {QColor(accent).name()};
        }}
        .VideoItemWidget QLabel {{
            font-size: 12px;
        }}
        .VideoListItemWidget {{
            border: 1px solid #4a4a4a;
            border-radius: 8px;
            background-color: #2a2a2a;
            padding: 5px;
        }}
        .VideoListItemWidget:hover {{
            border-color: {QColor(accent).name()};
        }}
    """)

# ==========================
# Video Library UI
# ==========================
class VideoItemWidget(QFrame):
    def __init__(self, file_path, ffmpeg_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_bin = self._get_ffprobe_path(ffmpeg_path)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("VideoItemWidget")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(90, 160)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setStyleSheet("border: 1px solid #555; background-color: black; border-radius: 5px;")
        self.layout.addWidget(self.thumbnail_label, alignment=Qt.AlignCenter)

        self.name_label = QLabel(os.path.basename(self.file_path))
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.layout.addWidget(self.name_label)
        self.generate_thumbnail()

    def _get_ffprobe_path(self, ffmpeg_path):
        if os.path.isfile(ffmpeg_path) and ffmpeg_path.lower().endswith("ffmpeg.exe"):
            return os.path.join(os.path.dirname(ffmpeg_path), "ffprobe.exe")
        elif os.path.isdir(ffmpeg_path):
            return os.path.join(ffmpeg_path, "ffprobe.exe")
        return None

    def generate_thumbnail(self):
        try:
            thumb_dir = os.path.join(os.path.dirname(self.file_path), "thumbs")
            thumb_path = os.path.join(thumb_dir, os.path.basename(self.file_path) + ".png")
            os.makedirs(thumb_dir, exist_ok=True)

            if not os.path.exists(thumb_path):
                if not self.ffprobe_bin:
                    return
                duration = get_video_duration(self.file_path, self.ffprobe_bin)
                ss_time = min(duration / 3, 5)
                ffmpeg_bin = self.ffprobe_bin.replace("ffprobe.exe", "ffmpeg.exe")
                cmd = [ffmpeg_bin, "-ss", str(ss_time), "-i", self.file_path, "-vframes", "1", "-q:v", "2", thumb_path]
                subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')

            if os.path.exists(thumb_path):
                pixmap = QPixmap(thumb_path)
                if not pixmap.isNull():
                    self.thumbnail_label.setPixmap(pixmap.scaled(self.thumbnail_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            self.thumbnail_label.setText("Lỗi")
            return

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.open_video()
        super().mousePressEvent(event)

    def show_context_menu(self, position):
        menu = QMenu()
        open_action = QAction("Mở video", self)
        open_action.triggered.connect(self.open_video)
        delete_action = QAction("Xóa", self)
        delete_action.triggered.connect(self.delete_video)
        menu.addAction(open_action)
        menu.addAction(delete_action)
        menu.exec_(self.mapToGlobal(position))

    def open_video(self):
        if os.path.exists(self.file_path):
            if os.name == "nt":
                os.startfile(self.file_path)
            else:
                webbrowser.open(f"file://{self.file_path}")

    def delete_video(self):
        confirm = QMessageBox.question(self, "Xác nhận xóa", f"Bạn có chắc muốn xóa video này không?\n\n{os.path.basename(self.file_path)}", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                os.remove(self.file_path)
                thumb_path = os.path.join(os.path.dirname(self.file_path), "thumbs", os.path.basename(self.file_path) + ".png")
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)
                self.setParent(None)
                self.deleteLater()
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa file: {str(e)}")

class VideoListItemWidget(QWidget):
    def __init__(self, file_path, ffmpeg_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.ffmpeg_path = ffmpeg_path
        self.setObjectName("VideoListItemWidget")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(60, 60)
        self.thumbnail_label.setStyleSheet("border: 1px solid #555; background-color: black; border-radius: 5px;")
        self.layout.addWidget(self.thumbnail_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(f"<b>{os.path.basename(file_path)}</b>")
        info_layout.addWidget(name_label)

        try:
            file_size = get_human_readable_size(file_path)
            ffprobe_bin = os.path.join(os.path.dirname(ffmpeg_path), "ffprobe.exe")
            duration = get_video_duration(file_path, ffprobe_bin)
            details_text = f"Kích thước: {file_size} | Độ dài: {sec_to_time(int(duration))}"
            details_label = QLabel(details_text)
            info_layout.addWidget(details_label)
        except Exception:
            info_layout.addWidget(QLabel("Kích thước: N/A | Độ dài: N/A"))

        self.layout.addLayout(info_layout)
        self.layout.addStretch()

        self.generate_thumbnail()

    def generate_thumbnail(self):
        thumb_dir = os.path.join(os.path.dirname(self.file_path), "thumbs")
        thumb_path = os.path.join(thumb_dir, os.path.basename(self.file_path) + ".png")
        if os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path)
            if not pixmap.isNull():
                self.thumbnail_label.setPixmap(pixmap.scaled(self.thumbnail_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

class VideoLibraryWidget(QWidget):
    def __init__(self, output_dir: str, ffmpeg_path: str, parent=None):
        super().__init__(parent)
        self.output_dir = output_dir
        self.ffmpeg_path = ffmpeg_path
        self.current_view_mode = "grid"

        self.main_layout = QVBoxLayout(self)

        top_toolbar_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Tìm kiếm theo tên...")
        self.search_bar.textChanged.connect(self.refresh_list)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Ngày tạo (mới nhất)", "Ngày tạo (cũ nhất)", "Tên (A-Z)", "Tên (Z-A)", "Kích thước (lớn nhất)", "Kích thước (nhỏ nhất)"])
        self.sort_combo.currentIndexChanged.connect(self.refresh_list)

        self.view_mode_btn = QPushButton("Chế độ Lưới")
        self.view_mode_btn.setCheckable(True)
        self.view_mode_btn.setChecked(True)
        self.view_mode_btn.toggled.connect(self.toggle_view_mode)
        self.view_mode_btn.setToolTip("Chuyển đổi giữa chế độ lưới và danh sách")

        self.refresh_btn = QPushButton("Làm mới")
        self.refresh_btn.clicked.connect(self.refresh_list)
        self.open_folder_btn = QPushButton("Mở thư mục")
        self.open_folder_btn.clicked.connect(self.open_output_folder)

        top_toolbar_layout.addWidget(self.search_bar, 1)
        top_toolbar_layout.addWidget(self.sort_combo)
        top_toolbar_layout.addWidget(self.view_mode_btn)
        top_toolbar_layout.addWidget(self.refresh_btn)
        top_toolbar_layout.addWidget(self.open_folder_btn)
        self.main_layout.addLayout(top_toolbar_layout)

        self.grid_scroll_area = QScrollArea()
        self.grid_scroll_area.setWidgetResizable(True)
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.grid_layout.setSpacing(15)
        self.grid_scroll_area.setWidget(self.grid_widget)

        self.list_widget = QListWidget()
        self.list_widget.hide()
        self.list_widget.itemDoubleClicked.connect(self.open_video_from_list)

        self.main_layout.addWidget(self.grid_scroll_area)
        self.main_layout.addWidget(self.list_widget)

        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(self.refresh_list)
        if os.path.isdir(self.output_dir):
            self.watcher.addPath(self.output_dir)

    def set_output_dir(self, path: str):
        if self.output_dir and os.path.isdir(self.output_dir):
            self.watcher.removePath(self.output_dir)
        self.output_dir = path
        if os.path.isdir(self.output_dir):
            self.watcher.addPath(self.output_dir)

    def set_ffmpeg_path(self, path: str):
        self.ffmpeg_path = path

    def refresh_list(self):
        self.clear_layout(self.grid_layout)
        self.list_widget.clear()

        if not os.path.isdir(self.output_dir):
            return

        all_files = [f for f in os.listdir(self.output_dir) if f.lower().endswith(".mp4") and not re.search(r'\.f\d+\.mp4$', f)]

        search_text = self.search_bar.text().lower()
        filtered_files = [f for f in all_files if search_text in f.lower()]

        sort_option = self.sort_combo.currentText()
        if "Ngày tạo" in sort_option:
            filtered_files_with_mtime = []
            for f in filtered_files:
                try:
                    mtime = os.path.getmtime(os.path.join(self.output_dir, f))
                    filtered_files_with_mtime.append((f, mtime))
                except FileNotFoundError:
                    continue
            filtered_files_with_mtime.sort(key=lambda x: x[1], reverse="mới nhất" in sort_option)
            filtered_files = [f[0] for f in filtered_files_with_mtime]
        elif "Tên" in sort_option:
            filtered_files.sort(reverse="Z-A" in sort_option)
        elif "Kích thước" in sort_option:
            filtered_files_with_size = []
            for f in filtered_files:
                try:
                    size = os.path.getsize(os.path.join(self.output_dir, f))
                    filtered_files_with_size.append((f, size))
                except FileNotFoundError:
                    continue
            filtered_files_with_size.sort(key=lambda x: x[1], reverse="lớn nhất" in sort_option)
            filtered_files = [f[0] for f in filtered_files_with_size]

        if self.current_view_mode == "grid":
            item_width = 110
            scroll_area_width = self.grid_scroll_area.viewport().width() - 20
            num_cols = max(1, int(scroll_area_width / item_width))

            for i, file_name in enumerate(filtered_files):
                full_path = os.path.join(self.output_dir, file_name)
                item_widget = VideoItemWidget(full_path, self.ffmpeg_path)
                row = i // num_cols
                col = i % num_cols
                self.grid_layout.addWidget(item_widget, row, col)

            self.grid_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, num_cols)
            self.grid_layout.update()
        else:
            for file_name in filtered_files:
                full_path = os.path.join(self.output_dir, file_name)
                item = QListWidgetItem()
                list_item_widget = VideoListItemWidget(full_path, self.ffmpeg_path)
                item.setSizeHint(list_item_widget.sizeHint())
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, list_item_widget)
            self.list_widget.update()

    def toggle_view_mode(self, checked):
        if checked:
            self.current_view_mode = "grid"
            self.view_mode_btn.setText("Chế độ Lưới")
            self.grid_scroll_area.show()
            self.list_widget.hide()
        else:
            self.current_view_mode = "list"
            self.view_mode_btn.setText("Chế độ Danh sách")
            self.list_widget.show()
            self.grid_scroll_area.hide()
        self.refresh_list()

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def open_output_folder(self):
        if not os.path.isdir(self.output_dir):
            QMessageBox.warning(self, "Cảnh báo", "Thư mục đầu ra không tồn tại.")
            return
        if os.name == "nt":
            os.startfile(self.output_dir)
        else:
            webbrowser.open(f"file://{self.output_dir}")

    def open_video_from_list(self, item):
        list_item_widget = self.list_widget.itemWidget(item)
        if list_item_widget and os.path.exists(list_item_widget.file_path):
            if os.name == "nt":
                os.startfile(list_item_widget.file_path)
            else:
                webbrowser.open(f"file://{list_item_widget.file_path}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.tabs.currentIndex() == 1:
            self.library_widget.refresh_list()

# ==========================
# UI
# ==========================
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Highlight Maker (Dark)")
        self.setMinimumWidth(800)
        self.ffmpeg_path, self.cookies_path, self.output_path, self.quality, self.num_clips, self.aspect_ratio = load_config()
        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tabs.addTab(self.tab1, "Tạo Highlight")
        self.tabs.addTab(self.tab2, "Thư viện")
        self.setup_creation_tab()
        self.setup_library_tab()
        self.layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.library_widget.set_ffmpeg_path(self.ffmpeg_path)

    def on_tab_changed(self, index):
        if index == 1:
            self.library_widget.refresh_list()

    def setup_creation_tab(self):
        layout = QVBoxLayout(self.tab1)
        url_box = QGroupBox("YouTube URL")
        url_l = QVBoxLayout(url_box)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Dán link YouTube vào đây…")
        url_l.addWidget(self.url_edit)
        layout.addWidget(url_box)
        opt_box = QGroupBox("Tùy chọn")
        opt_l = QVBoxLayout(opt_box)
        grid_layout = QGridLayout()
        grid_layout.addWidget(QLabel("Chất lượng video:"), 0, 0)
        self.qual_combo = QComboBox()
        self.qual_combo.addItems(["1080p", "720p"])
        self.qual_combo.setCurrentText(self.quality)
        grid_layout.addWidget(self.qual_combo, 0, 1)
        grid_layout.addWidget(QLabel("Số lượng clip:"), 0, 2)
        self.num_clips_spin = QSpinBox()
        self.num_clips_spin.setRange(1, 10)
        self.num_clips_spin.setValue(self.num_clips)
        grid_layout.addWidget(self.num_clips_spin, 0, 3)
        grid_layout.addWidget(QLabel("Thời lượng (giây):"), 1, 0)
        self.dur_spin = QSpinBox()
        self.dur_spin.setRange(5, 600)
        self.dur_spin.setValue(30)
        grid_layout.addWidget(self.dur_spin, 1, 1)
        grid_layout.addWidget(QLabel("Tỷ lệ khung hình:"), 1, 2)
        self.aspect_combo = QComboBox()
        self.aspect_combo.addItems(["Gốc", "Dọc 9:16 (Cắt)", "Dọc 9:16 (Viền đen)"])
        self.aspect_combo.setCurrentText(self.aspect_ratio)
        grid_layout.addWidget(self.aspect_combo, 1, 3)
        opt_l.addLayout(grid_layout)
        ff_row = QHBoxLayout()
        self.ff_edit = QLineEdit()
        self.ff_edit.setPlaceholderText(r"Ví dụ: C:\\ffmpeg\\bin\\ffmpeg.exe hoặc C:\\ffmpeg\\bin")
        auto_path = find_ffmpeg_in_path()
        if auto_path:
            self.ff_edit.setText(auto_path)
        else:
            self.ff_edit.setText(self.ffmpeg_path)
        browse_ff = QPushButton("Chọn FFmpeg…")
        browse_ff.clicked.connect(self.choose_ffmpeg)
        ff_row.addWidget(QLabel("FFmpeg:"))
        ff_row.addWidget(self.ff_edit, 1)
        ff_row.addWidget(browse_ff)
        opt_l.addLayout(ff_row)
        ck_row = QHBoxLayout()
        self.ck_edit = QLineEdit()
        self.ck_edit.setPlaceholderText(r"Tùy chọn: cookies.txt (nếu cần)")
        self.ck_edit.setText(self.cookies_path)
        browse_ck = QPushButton("Chọn cookies.txt")
        browse_ck.clicked.connect(self.choose_cookies)
        ck_row.addWidget(QLabel("Cookies:"))
        ck_row.addWidget(self.ck_edit, 1)
        ck_row.addWidget(browse_ck)
        opt_l.addLayout(ck_row)
        out_row = QHBoxLayout()
        self.out_edit = QLineEdit()
        self.out_edit.setText(self.output_path)
        browse_out = QPushButton("Chọn thư mục đầu ra…")
        browse_out.clicked.connect(self.choose_output_dir)
        out_row.addWidget(QLabel("Thư mục đầu ra:"))
        out_row.addWidget(self.out_edit, 1)
        out_row.addWidget(browse_out)
        opt_l.addLayout(out_row)
        self.auto_open_cb = QCheckBox("Tự động mở thư mục sau khi hoàn thành")
        self.auto_open_cb.setChecked(True)
        opt_l.addWidget(self.auto_open_cb)
        layout.addWidget(opt_box)
        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("Tạo Highlight")
        self.run_btn.clicked.connect(self.start_job)
        btn_row.addStretch()
        btn_row.addWidget(self.run_btn)
        layout.addLayout(btn_row)
        self.log_box = QGroupBox("Tiến trình")
        log_l = QVBoxLayout(self.log_box)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        log_l.addWidget(self.progress_bar)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        log_l.addWidget(self.log_edit)
        layout.addWidget(self.log_box)

    def setup_library_tab(self):
        self.library_widget = VideoLibraryWidget(self.output_path, self.ffmpeg_path)
        library_layout = QVBoxLayout(self.tab2)
        library_layout.addWidget(self.library_widget)

    def choose_ffmpeg(self):
        f, _ = QFileDialog.getOpenFileName(self, "Chọn ffmpeg.exe", "", "Executable (*.exe);;All files (*.*)")
        if f:
            self.ff_edit.setText(f)
            self.library_widget.set_ffmpeg_path(f)
        else:
            d = QFileDialog.getExistingDirectory(self, "Chọn thư mục ffmpeg/bin")
            if d:
                self.ff_edit.setText(d)
                self.library_widget.set_ffmpeg_path(d)

    def choose_cookies(self):
        f, _ = QFileDialog.getOpenFileName(self, "Chọn cookies.txt", "", "Text files (*.txt);;All files (*.*)")
        if f:
            self.ck_edit.setText(f)

    def choose_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Chọn thư mục đầu ra", self.out_edit.text())
        if d:
            self.out_edit.setText(d)
            self.library_widget.set_output_dir(d)

    def start_job(self):
        url = self.url_edit.text().strip()
        ff_path = self.ff_edit.text().strip()
        out_path = self.out_edit.text().strip()
        cookies_path = self.ck_edit.text().strip()
        quality = self.qual_combo.currentText()
        num_clips = self.num_clips_spin.value()
        aspect_ratio = self.aspect_combo.currentText()

        if not url:
            QMessageBox.critical(self, "Lỗi", "Vui lòng nhập YouTube URL.")
            return
        if not ff_path or not (os.path.exists(ff_path) and (os.path.isdir(ff_path) or ff_path.lower().endswith("ffmpeg.exe"))):
            QMessageBox.critical(self, "Lỗi", "Đường dẫn FFmpeg không hợp lệ.")
            return
        if not out_path:
            QMessageBox.critical(self, "Lỗi", "Vui lòng chọn thư mục đầu ra.")
            return

        save_config(ff_path, cookies_path, out_path, quality, num_clips, aspect_ratio)

        cfg = JobConfig(
            url=url,
            clip_duration=int(self.dur_spin.value()),
            ffmpeg_path=ff_path,
            cookies_path=(cookies_path or None),
            output_path=out_path,
            quality=quality,
            num_clips=num_clips,
            aspect_ratio=aspect_ratio
        )

        self.run_btn.setEnabled(False)
        self.tabs.setCurrentIndex(0)
        self.progress_bar.setValue(0)
        self.log_edit.clear()
        self.append_log(" Bắt đầu…")

        self.thread = QThread(self)
        self.worker = HighlightWorker(cfg)
        self.worker.moveToThread(self.thread)
        self.worker.log.connect(self.append_log)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.done.connect(self.on_done)
        self.worker.error.connect(self.on_error)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def append_log(self, msg: str):
        self.log_edit.append(msg)
        self.log_edit.verticalScrollBar().setValue(self.log_edit.verticalScrollBar().maximum())

    def on_done(self, out_path: str):
        self.run_btn.setEnabled(True)
        self.append_log(f"Hoàn tất! Đã tạo các clip trong thư mục: {out_path}")
        self.library_widget.set_output_dir(out_path)
        self.library_widget.set_ffmpeg_path(self.ff_edit.text())
        self.library_widget.refresh_list()
        QMessageBox.information(self, "Xong", f"Đã tạo các clip trong thư mục:\n{out_path}")
        if self.auto_open_cb.isChecked():
            if os.path.isdir(out_path):
                if os.name == "nt":
                    os.startfile(out_path)
                else:
                    webbrowser.open(f"file://{out_path}")

    def on_error(self, msg: str):
        self.run_btn.setEnabled(True)
        self.append_log(f"Lỗi: {msg}")
        QMessageBox.critical(self, "Lỗi", msg)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.tabs.currentIndex() == 1:
            self.library_widget.refresh_list()

# ==========================
# Entry
# ==========================
def main():
    app = QApplication(sys.argv)
    apply_dark_theme(app, accent="#34c759")
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()