"""
Flux
Copyright (c) 2025 Alexander Nemchinov
https://linktr.ee/Nemchinov

MIT License

Copyright (c) 2025 Alexander Nemchinov

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import sys
import os
import subprocess
import time
import configparser
import json
import webbrowser
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QStatusBar,
    QLineEdit,
    QTextEdit,
    QFileDialog,
    QLabel,
)
from PyQt5.QtCore import Qt, QTimer, QProcess
from PyQt5.QtGui import QPainter, QColor, QFont, QIcon
from PyQt5.QtWidgets import QGraphicsDropShadowEffect

try:
    from PyQt5.QtWinExtras import QWinTaskbarButton
    windows_taskbar_available = True
except ImportError:
    windows_taskbar_available = False

translations = {
    "ru": {
        "window_title": "Flux",
        "url_placeholder": "Введите URL видео или плейлиста",
        "single_video": "Одно видео",
        "playlist": "Плейлист",
        "select_cookie": "Выбрать файл cookie",
        "clear_cookie": "Очистить",
        "cookie_display": "{path}",
        "no_cookie": "Файл cookie не выбран",
        "select_path": "Выбрать",
        "download_path": "Папка загрузки:",
        "no_path": "Выберите папку для скачивания",
        "download": "Скачать",
        "waiting": "Ожидание",
        "cancel": "Отмена",
        "error": "Ошибка: {message}",
        "no_url": "Введите URL для скачивания!",
        "select_type": "Выберите тип скачивания: одно видео или плейлист",
        "invalid_path": "Папка для скачивания не существует!",
        "yt_dlp_error": "Не удалось запустить yt-dlp!",
        "download_error": "Ошибка скачивания: {error}",
        "download_completed": "Скачивание завершено",
        "download_canceled": "Скачивание отменено",
        "warning": "Предупреждение: {message}",
        "unavailable_videos": "YouTube: Информация - {count} видео недоступны и скрыты",
        "get_cookies": "Где взять куки?",
        "download_label": "Что скачать?",
        "params_label": "Параметры",
        "youtube_cookie_error": "Ошибка скачивания: неизвестная ошибка или файл cookies устарел либо не выбран."
    },
    "en": {
        "window_title": "Flux",
        "url_placeholder": "Enter video or playlist URL",
        "single_video": "Single Video",
        "playlist": "Playlist",
        "select_cookie": "Select cookie file",
        "clear_cookie": "Clear",
        "cookie_display": "{path}",
        "no_cookie": "No cookie file selected",
        "select_path": "Select",
        "download_path": "Download path:",
        "no_path": "Select a download folder",
        "download": "Download",
        "waiting": "Waiting",
        "cancel": "Cancel",
        "error": "Error: {message}",
        "no_url": "Enter a URL to download!",
        "select_type": "Select download type: single video or playlist",
        "invalid_path": "Download folder does not exist!",
        "yt_dlp_error": "Failed to start yt-dlp!",
        "download_error": "Download error: {error}",
        "download_completed": "Download completed",
        "download_canceled": "Download canceled",
        "warning": "Warning: {message}",
        "unavailable_videos": "YouTube: Info - {count} videos are unavailable and hidden",
        "get_cookies": "Where to get cookies?",
        "download_label": "What to download?",
        "params_label": "Parameters",
        "youtube_cookie_error": "Download error: Unknown error, or your cookies file is either outdated or not selected."
    }
}

def get_yt_dlp_path():
    try:
        if getattr(sys, "frozen", False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_path, "bin", "yt-dlp.exe")
        if not os.path.exists(path):
            raise FileNotFoundError(f"yt-dlp.exe not found at {path}")
        return path
    except Exception as e:
        raise

yt_dlp_path = get_yt_dlp_path()

class DownloadButton(QPushButton):
    def __init__(self, text, parent=None, language="en"):
        super().__init__(text, parent)
        self.language = language
        self.progress = 0
        self.completed = False
        self.waiting = False
        self.current_state = "default"
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_seconds = 0
        self.setStyleSheet(""" 
            QPushButton {
                background-color: #4a4a4a;
                color: #ffffff;
                border: none;
                padding: 15px;
                border-radius: 5px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:disabled {
                background-color: #3a3a3a;
                color: #aaaaaa;
            }
        """)
        self.setMinimumSize(200, 100)
        self.setFont(QFont("Arial", 18))

    def set_waiting(self):
        self.waiting = True
        self.completed = False
        self.progress = 0
        self.current_state = "waiting"
        self.countdown_timer.stop()
        self.setText(translations[self.language]["waiting"])
        self.update()

    def set_progress(self, value):
        self.progress = min(max(value, 0), 99)
        self.completed = False
        self.waiting = False
        self.current_state = "progress"
        self.countdown_timer.stop()
        self.setText(f"{int(self.progress)}%")
        self.update()

    def set_completed(self):
        self.completed = True
        self.progress = 100
        self.waiting = False
        self.current_state = "completed"
        self.countdown_seconds = 3
        self.setText(f"✔ ({self.countdown_seconds} {'с.' if self.language == 'ru' else 'sec'})")
        self.countdown_timer.start(1000)
        self.setEnabled(False)
        self.update()

    def reset(self):
        self.completed = False
        self.progress = 0
        self.waiting = False
        self.current_state = "default"
        self.countdown_timer.stop()
        self.setText(translations[self.language]["download"])
        self.setEnabled(True)
        self.update()

    def update_countdown(self):
        self.countdown_seconds -= 1
        if self.countdown_seconds > 0:
            self.setText(f"✔ ({self.countdown_seconds} {'с.' if self.language == 'ru' else 'sec'})")
            self.update()
        else:
            self.countdown_timer.stop()
            self.reset()

    def update_language(self, new_language):
        self.language = new_language
        if self.current_state == "waiting":
            self.setText(translations[self.language]["waiting"])
        elif self.current_state == "completed":
            self.setText(f"✔ ({self.countdown_seconds} {'с.' if self.language == 'ru' else 'sec'})")
        elif self.current_state == "default":
            self.setText(translations[self.language]["download"])

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.completed:
            painter.setBrush(QColor("#4CAF50"))
            painter.drawRoundedRect(self.rect(), 5, 5)
        elif self.progress > 0:
            painter.setBrush(QColor("#4a4a4a"))
            painter.drawRoundedRect(self.rect(), 5, 5)
            painter.setBrush(QColor("#4CAF50"))
            painter.drawRoundedRect(0, 0, int(self.width() * self.progress / 100), self.height(), 5, 5)
        else:
            painter.setBrush(QColor("#4a4a4a"))
            painter.drawRoundedRect(self.rect(), 5, 5)
        painter.setPen(QColor("#ffffff"))
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())

class FluxWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = configparser.ConfigParser()
        self.config_file = "settings.ini"
        self.language = "en"
        self.cookie_file = ""
        self.download_path = os.path.expanduser("~/Downloads")
        self.window_width = 900
        self.window_height = 800
        self.window_x = 100
        self.window_y = 100
        self.completed_videos = 0
        self.current_video_index = 0
        self.total_progress = 0.0
        self.was_canceled = False
        self.current_status = ""
        self.current_status_key = ""
        try:
            if os.path.exists(self.config_file):
                self.config.read(self.config_file, encoding="utf-8")
                self.language = self.config.get("Settings", "language", fallback="en")
                self.cookie_file = self.config.get("Settings", "cookie_file", fallback="")
                self.download_path = self.config.get("Settings", "download_path", fallback=os.path.expanduser("~/Downloads"))
                self.window_width = self.config.getint("Settings", "window_width", fallback=900)
                self.window_height = self.config.getint("Settings", "window_height", fallback=800)
                self.window_x = self.config.getint("Settings", "window_x", fallback=100)
                self.window_y = self.config.getint("Settings", "window_y", fallback=100)
        except Exception:
            pass

        self.taskbar_button = None
        if windows_taskbar_available and sys.platform == "win32":
            self.taskbar_button = QWinTaskbarButton(self)
            self.windowHandleCreated = False
            self.showEvent = self._showEvent

        self.setWindowTitle(translations[self.language]["window_title"])
        icon_path = None
        for ext in ["icon.png", "icon.ico"]:
            if os.path.exists(ext):
                icon_path = ext
                break
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
            QApplication.setWindowIcon(QIcon(icon_path))
        self.setGeometry(self.window_x, self.window_y, self.window_width, self.window_height)
        self.setMinimumWidth(900)
        self.setStyleSheet(""" 
            QMainWindow { background-color: #2b2b2b; color: #ffffff; }
            QLineEdit { background-color: #3c3c3c; color: #ffffff; border: none; font-size: 18px; padding: 10px; border-radius: 5px; }
            QPushButton {
                background-color: #4a4a4a;
                color: #ffffff;
                border: none;
                padding: 15px;
                border-radius: 5px;
                font-size: 18px;
            }
            QPushButton:hover { background-color: #5a5a5a; }
            QStatusBar { background-color: #3c3c3c; color: #ffffff; }
            QTextEdit { background-color: #3c3c3c; color: #ffffff; border: none; font-size: 18px; border-radius: 5px; }
            QLabel { color: #ffffff; font-size: 18px; font-weight: bold; }
            QWidget#block {
                background-color: #353535;
                border: 1px solid #4a4a4a;
                border-radius: 10px;
                padding: 10px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        central_widget.setLayout(main_layout)

        block1 = QWidget()
        block1.setObjectName("block")
        block1_layout = QVBoxLayout()
        block1_layout.setSpacing(10)
        self.download_label = QLabel(translations[self.language]["download_label"])
        self.download_label.setAlignment(Qt.AlignCenter)
        block1_layout.addWidget(self.download_label)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(translations[self.language]["url_placeholder"])
        self.url_input.setFont(QFont("Arial", 18))
        self.url_input.textChanged.connect(self.update_status_text)
        block1_layout.addWidget(self.url_input)
        type_layout = QHBoxLayout()
        self.single_video_button = QPushButton(translations[self.language]["single_video"])
        self.playlist_button = QPushButton(translations[self.language]["playlist"])
        for btn in (self.single_video_button, self.playlist_button):
            btn.clicked.connect(lambda _, b=btn: self.select_download_type(b))
            btn.setFont(QFont("Arial", 18))
            type_layout.addWidget(btn)
        block1_layout.addLayout(type_layout)
        block1.setLayout(block1_layout)
        main_layout.addWidget(block1)

        block2 = QWidget()
        block2.setObjectName("block")
        block2_layout = QVBoxLayout()
        block2_layout.setSpacing(10)
        self.params_label = QLabel(translations[self.language]["params_label"])
        self.params_label.setAlignment(Qt.AlignCenter)
        block2_layout.addWidget(self.params_label)

        path_layout = QHBoxLayout()
        self.path_label = QLabel("📁 " + translations[self.language]["download_path"])
        self.path_label.setFont(QFont("Arial", 18))
        path_layout.addWidget(self.path_label, stretch=1)
        self.select_path_button = QPushButton(translations[self.language]["select_path"])
        self.select_path_button.clicked.connect(self.select_download_path)
        self.select_path_button.setFont(QFont("Arial", 18))
        path_layout.addWidget(self.select_path_button, stretch=1)
        block2_layout.addLayout(path_layout)
        self.path_display = QTextEdit()
        self.path_display.setReadOnly(True)
        self.path_display.setFixedHeight(30)
        self.path_display.setText(self.download_path if self.download_path else translations[self.language]["no_path"])
        self.path_display.setFont(QFont("Arial", 18))
        block2_layout.addWidget(self.path_display)

        cookie_layout = QHBoxLayout()
        self.cookie_label = QLabel("🍪 Cookies:")
        self.cookie_label.setFont(QFont("Arial", 18))
        cookie_layout.addWidget(self.cookie_label, stretch=1)
        self.select_cookie_button = QPushButton(translations[self.language]["select_cookie"])
        self.select_cookie_button.clicked.connect(self.select_cookie_file)
        self.select_cookie_button.setFont(QFont("Arial", 18))
        cookie_layout.addWidget(self.select_cookie_button, stretch=2)
        self.clear_cookie_button = QPushButton(translations[self.language]["clear_cookie"])
        self.clear_cookie_button.clicked.connect(self.clear_cookie_file)
        self.clear_cookie_button.setFont(QFont("Arial", 18))
        cookie_layout.addWidget(self.clear_cookie_button, stretch=1)
        block2_layout.addLayout(cookie_layout)
        self.cookie_display = QTextEdit()
        self.cookie_display.setReadOnly(True)
        self.cookie_display.setFixedHeight(30)
        self.cookie_display.setText(
            translations[self.language]["cookie_display"].format(path=self.cookie_file)
            if self.cookie_file else translations[self.language]["no_cookie"]
        )
        self.cookie_display.setFont(QFont("Arial", 18))
        block2_layout.addWidget(self.cookie_display)

        self.get_cookies_button = QPushButton(translations[self.language]["get_cookies"])
        self.get_cookies_button.clicked.connect(lambda: webbrowser.open("https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies"))
        self.get_cookies_button.setFont(QFont("Arial", 18))
        block2_layout.addWidget(self.get_cookies_button)

        block2.setLayout(block2_layout)
        main_layout.addWidget(block2)

        download_layout = QHBoxLayout()
        self.download_button = DownloadButton(translations[self.language]["download"], language=self.language)
        self.download_button.clicked.connect(self.start_download)
        download_layout.addWidget(self.download_button, stretch=3)
        self.cancel_button = QPushButton(translations[self.language]["cancel"])
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setFont(QFont("Arial", 18))
        self.cancel_button.setVisible(False)
        download_layout.addWidget(self.cancel_button, stretch=1)
        main_layout.addLayout(download_layout)

        links_layout = QHBoxLayout()
        links_layout.setSpacing(10)
        github_button = QPushButton("GitHub")
        github_icon_path = "github.png" if os.path.exists("github.png") else None
        if github_icon_path:
            github_button.setIcon(QIcon(github_icon_path))
        github_button.clicked.connect(lambda: webbrowser.open("https://github.com/AlexanderNemchinov"))
        github_button.setFont(QFont("Arial", 18))
        links_layout.addWidget(github_button)
        paypal_button = QPushButton("PayPal")
        paypal_icon_path = "paypal.png" if os.path.exists("paypal.png") else None
        if paypal_icon_path:
            paypal_button.setIcon(QIcon(paypal_icon_path))
        paypal_button.clicked.connect(lambda: webbrowser.open("https://www.paypal.com/paypalme/AlexanderNemchinov"))
        paypal_button.setFont(QFont("Arial", 18))
        links_layout.addWidget(paypal_button)
        donationalerts_button = QPushButton("DonationAlerts")
        donationalerts_icon_path = "donationalerts.png" if os.path.exists("donationalerts.png") else None
        if donationalerts_icon_path:
            donationalerts_button.setIcon(QIcon(donationalerts_icon_path))
        donationalerts_button.clicked.connect(lambda: webbrowser.open("https://www.donationalerts.com/c/Nemchinov"))
        donationalerts_button.setFont(QFont("Arial", 18))
        links_layout.addWidget(donationalerts_button)
        main_layout.addLayout(links_layout)

        self.status_bar = QStatusBar()
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setFixedHeight(60)
        self.status_text.setStyleSheet("background-color: #3c3c3c; color: #ffffff; border: none; border-radius: 5px;")
        self.status_text.setFont(QFont("Arial", 18))
        self.status_bar.addWidget(self.status_text, 1)
        self.language_button = QPushButton("RU" if self.language == "en" else "EN")
        self.language_button.clicked.connect(self.toggle_language)
        self.language_button.setFont(QFont("Arial", 18))
        self.language_button.setStyleSheet(""" 
            QPushButton {
                background-color: #4a4a4a;
                color: #ffffff;
                border: none;
                padding: 5px;
                border-radius: 5px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
        """)
        self.status_bar.addPermanentWidget(self.language_button)
        self.setStatusBar(self.status_bar)

        main_layout.addStretch(1)
        main_layout.insertStretch(2, 1)
        main_layout.insertStretch(4, 1)

        self.error_timer = QTimer(self)
        self.error_timer.setSingleShot(True)
        self.error_timer.timeout.connect(self.clear_status_text)

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_output)
        self.process.readyReadStandardError.connect(self.handle_error)
        self.process.finished.connect(self.download_finished)

        self.download_type = None
        self.active_type_button = None
        self.total_videos = 1
        self.video_progress = {}
        self.current_video_id = None
        self.first_video_completed = False

    def _showEvent(self, event):
        super().showEvent(event)
        if windows_taskbar_available and sys.platform == "win32" and not self.windowHandleCreated:
            if self.windowHandle():
                self.taskbar_button.setWindow(self.windowHandle())
                self.windowHandleCreated = True

    def save_settings(self):
        try:
            if not self.config.has_section("Settings"):
                self.config.add_section("Settings")
            self.config.set("Settings", "language", self.language)
            self.config.set("Settings", "cookie_file", self.cookie_file)
            self.config.set("Settings", "download_path", self.download_path)
            self.config.set("Settings", "window_width", str(self.width()))
            self.config.set("Settings", "window_height", str(self.height()))
            self.config.set("Settings", "window_x", str(self.x()))
            self.config.set("Settings", "window_y", str(self.y()))
            with open(self.config_file, "w", encoding="utf-8") as configfile:
                self.config.write(configfile)
        except Exception:
            pass

    def clear_status_text(self):
        if not self.current_status:
            self.status_text.setText("")
            self.current_status_key = ""

    def update_status_text(self):
        if self.current_status:
            self.status_text.setText(self.current_status)
        else:
            self.status_text.setText("")
            self.current_status_key = ""

    def toggle_language(self):
        previous_language = self.language
        self.language = "en" if self.language == "ru" else "ru"
        self.language_button.setText("EN" if self.language == "ru" else "RU")
        self.setWindowTitle(translations[self.language]["window_title"])
        self.url_input.setPlaceholderText(translations[self.language]["url_placeholder"])
        self.single_video_button.setText(translations[self.language]["single_video"])
        self.playlist_button.setText(translations[self.language]["playlist"])
        self.select_cookie_button.setText(translations[self.language]["select_cookie"])
        self.clear_cookie_button.setText(translations[self.language]["clear_cookie"])
        self.cookie_display.setText(
            translations[self.language]["cookie_display"].format(path=self.cookie_file)
            if self.cookie_file else translations[self.language]["no_cookie"]
        )
        self.select_path_button.setText(translations[self.language]["select_path"])
        self.path_display.setText(self.download_path if self.download_path else translations[self.language]["no_path"])
        self.cancel_button.setText(translations[self.language]["cancel"])
        self.get_cookies_button.setText(translations[self.language]["get_cookies"])
        self.download_label.setText(translations[self.language]["download_label"])
        self.params_label.setText(translations[self.language]["params_label"])
        self.path_label.setText("📁 " + translations[self.language]["download_path"])
        self.cookie_label.setText("🍪 Cookies:")

        self.download_button.update_language(self.language)

        if self.current_status_key:
            if self.current_status_key in ["error", "download_error", "warning"]:
                current_text = self.status_text.toPlainText()
                if current_text.startswith(translations[previous_language][self.current_status_key].split(":")[0]):
                    message = current_text[len(translations[previous_language][self.current_status_key].split(":")[0]) + 2:].strip()
                    if self.current_status_key == "download_error":
                        self.current_status = translations[self.language][self.current_status_key].format(error=message)
                    else:
                        self.current_status = translations[self.language][self.current_status_key].format(message=message)
                else:
                    self.current_status = current_text
            elif self.current_status_key == "unavailable_videos":
                current_text = self.status_text.toPlainText()
                count = current_text.split(" ")[-5] if previous_language == "ru" else current_text.split(" ")[-4]
                self.current_status = translations[self.language][self.current_status_key].format(count=count)
            else:
                self.current_status = translations[self.language].get(self.current_status_key, self.current_status)
            self.status_text.setText(self.current_status)
        elif self.current_status:
            self.status_text.setText(self.current_status)

        self.save_settings()

    def select_download_type(self, button):
        if self.active_type_button:
            self.active_type_button.setStyleSheet(""" 
                QPushButton {
                    background-color: #4a4a4a;
                    color: #ffffff;
                    border: none;
                    padding: 15px;
                    border-radius: 5px;
                    font-size: 18px;
                }
                QPushButton:hover {
                    background-color: #5a5a5a;
                }
            """)
            self.active_type_button.setGraphicsEffect(None)

        self.active_type_button = button
        effect = QGraphicsDropShadowEffect()
        effect.setColor(QColor("#000000"))
        effect.setOffset(2, 2)
        effect.setBlurRadius(10)
        button.setGraphicsEffect(effect)
        button.setStyleSheet(""" 
            QPushButton {
                background-color: #4CAF50;
                color: #ffffff;
                border: none;
                padding: 15px;
                border-radius: 5px;
                font-size: 18px;
            }
        """)
        self.download_type = "single" if button.text() in (translations[self.language]["single_video"], "Single Video") else "playlist"
        self.update_status_text()

    def select_cookie_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select cookie file" if self.language == "en" else "Выберите файл cookie", "", "Text files (*.txt)")
        if file_path:
            self.cookie_file = file_path
            self.cookie_display.setText(
                translations[self.language]["cookie_display"].format(path=self.cookie_file)
                if self.cookie_file else translations[self.language]["no_cookie"]
            )
            self.save_settings()

    def clear_cookie_file(self):
        self.cookie_file = ""
        self.cookie_display.setText(translations[self.language]["no_cookie"])
        self.save_settings()

    def select_download_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select download folder" if self.language == "en" else "Выберите папку для скачивания", self.download_path)
        if path:
            self.download_path = path
            self.path_display.setText(self.download_path if self.download_path else translations[self.language]["no_path"])
            self.save_settings()

    def get_playlist_video_count(self, url):
        try:
            result = subprocess.run(
                [yt_dlp_path, "--flat-playlist", "--dump-json", url],
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8',
                creationflags=0x08000000
            )
            entries = [json.loads(line) for line in result.stdout.splitlines()]
            return len(entries)
        except Exception:
            return 1

    def get_video_title(self, url):
        try:
            args = [yt_dlp_path, "--get-title", "--no-playlist"]
            if self.cookie_file and os.path.exists(self.cookie_file):
                args.extend(["--cookies", self.cookie_file])
            args.append(url)
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8',
                creationflags=0x08000000
            )
            return result.stdout.strip()
        except Exception:
            return "Unknown Title"

    def start_download(self):
        self.status_text.setText("")
        self.current_status_key = ""
        url = self.url_input.text().strip()
        if not url:
            self.status_text.setText(translations[self.language]["no_url"])
            self.current_status = translations[self.language]["no_url"]
            self.current_status_key = "no_url"
            self.error_timer.start(5000)
            return
        if not self.download_type:
            self.status_text.setText(translations[self.language]["select_type"])
            self.current_status = translations[self.language]["select_type"]
            self.current_status_key = "select_type"
            self.error_timer.start(5000)
            return
        if not os.path.exists(self.download_path):
            self.status_text.setText(translations[self.language]["invalid_path"])
            self.current_status = translations[self.language]["invalid_path"]
            self.current_status_key = "invalid_path"
            self.error_timer.start(5000)
            return

        self.download_button.setEnabled(False)
        self.cancel_button.setVisible(True)
        self.download_button.set_waiting()
        self.completed_videos = 0
        self.total_progress = 0.0
        self.current_video_id = None
        self.video_progress = {}
        self.was_canceled = False
        self.first_video_completed = False
        self.current_status = ""
        self.current_status_key = ""
        self.total_videos = 1 if self.download_type == "single" else self.get_playlist_video_count(url)

        args = [
            "-f", "bv+ba[acodec=opus][language=ru]+ba[acodec=opus][language=en]/ba[acodec=aac][language=ru]+ba[acodec=aac][language=en]/bv+ba/b",
            "--audio-multistreams",
            "--merge-output-format", "mkv",
            "--embed-metadata",
            "--embed-thumbnail",
            "--convert-thumbnails", "png",
            "--embed-chapters",
            "--sleep-requests", "10",
            "--sleep-interval", "10",
            "--sponsorblock-mark", "all",
            "--no-keep-fragments",
        ]

        if self.cookie_file and os.path.exists(self.cookie_file):
            args.extend(["--cookies", self.cookie_file])

        args.extend(["--no-playlist" if self.download_type == "single" else "--yes-playlist"])
        output_template = os.path.join(self.download_path, "%(title)s.%(ext)s" if self.download_type == "single" else "%(playlist_title)s/%(title)s.%(ext)s")
        args.extend(["-o", output_template, "--parse-metadata", "%(title)s:%(meta_title)s", "--parse-metadata", "%(playlist_title)s:%(meta_playlist_title)s"])
        args.append(url)

        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.start(yt_dlp_path, args, QProcess.ReadWrite)
        if not self.process.waitForStarted():
            self.status_text.setText(translations[self.language]["yt_dlp_error"])
            self.current_status = translations[self.language]["yt_dlp_error"]
            self.current_status_key = "yt_dlp_error"
            self.error_timer.start(5000)
            self.download_button.setEnabled(True)
            self.cancel_button.setVisible(False)
            self.download_button.reset()
        else:
            if self.taskbar_button and self.windowHandleCreated:
                self.taskbar_button.progress().setVisible(True)
                self.taskbar_button.progress().setValue(0)

    def update_progress(self, total_percentage):
        self.total_progress = total_percentage
        self.download_button.set_progress(total_percentage)
        if self.taskbar_button and self.windowHandleCreated:
            self.taskbar_button.progress().setValue(int(total_percentage))

    def handle_output(self):
        output = str(self.process.readAllStandardOutput(), encoding='utf-8', errors='ignore')
        for line in output.splitlines():
            if "[download] Destination" in line:
                filename_part = line.split("Destination:")[-1].strip()
                self.current_status = os.path.splitext(os.path.basename(filename_part))[0]
                self.current_status_key = ""
                self.status_text.setText(self.current_status)
                self.current_video_id = filename_part
                if self.current_video_id not in self.video_progress:
                    self.video_progress[self.current_video_id] = {
                        "thumbnail": 0.0,
                        "download": 0.0,
                        "audio": 0.0,
                        "merging": 0.0,
                        "audio_streams": 0,
                        "postprocessing": False
                    }
                self.completed_videos += 1
                if self.download_type == "single":
                    self.total_videos = 1
            elif "[ThumbnailsConvertor]" in line:
                if self.current_video_id:
                    self.video_progress[self.current_video_id]["thumbnail"] = 1.0
            elif "[download]" in line and "%" in line and "of" in line:
                if self.current_video_id:
                    try:
                        percent_str = line.split("%")[0].split()[-1]
                        self.video_progress[self.current_video_id]["download"] = float(percent_str) / 100
                    except (ValueError, IndexError):
                        pass
            elif "[ExtractAudio]" in line:
                if self.current_video_id:
                    self.video_progress[self.current_video_id]["audio_streams"] += 1
                    audio_progress_per_stream = 1.0 / max(self.video_progress[self.current_video_id]["audio_streams"], 1)
                    self.video_progress[self.current_video_id]["audio"] = min(
                        self.video_progress[self.current_video_id]["audio"] + audio_progress_per_stream, 1.0
                    )
            elif "[Merger]" in line:
                if self.current_video_id:
                    self.video_progress[self.current_video_id]["merging"] = 1.0
            elif "[Metadata]" in line or "[EmbedThumbnail]" in line:
                if self.current_video_id:
                    self.video_progress[self.current_video_id]["postprocessing"] = True
            elif "[download] Finished downloading playlist" in line or (
                self.download_type == "single" and
                self.current_video_id and
                self.video_progress[self.current_video_id]["merging"] == 1.0 and
                self.video_progress[self.current_video_id]["postprocessing"]
            ):
                if self.download_type == "single" and not self.first_video_completed:
                    self.first_video_completed = True
                    self.process.terminate()
                    self.process.waitForFinished(1000)
                    if self.process.state() != QProcess.NotRunning:
                        self.process.kill()
                    self.download_button.set_completed()
                    self.current_status = translations[self.language]["download_completed"]
                    self.current_status_key = "download_completed"
                    self.status_text.setText(self.current_status)
                    self.error_timer.start(5000)
                    self.cancel_button.setVisible(False)
                    if self.taskbar_button and self.windowHandleCreated:
                        self.taskbar_button.progress().setVisible(False)

            total_progress = 0.0
            for video_id, progress in self.video_progress.items():
                thumbnail_weight = 0.10 if progress["thumbnail"] > 0 else 0.0
                video_weight = 0.50 if progress["thumbnail"] > 0 else 0.60
                audio_weight = 0.30
                merging_weight = 0.10
                total_weight = thumbnail_weight + video_weight + audio_weight + merging_weight
                video_progress = (
                    progress["thumbnail"] * thumbnail_weight +
                    progress["download"] * video_weight +
                    progress["audio"] * audio_weight +
                    progress["merging"] * merging_weight
                ) / total_weight if total_weight > 0 else 0.0
                total_progress += video_progress / self.total_videos

            total_percentage = min(total_progress * 99, 99)
            self.update_progress(total_percentage)

    def handle_error(self):
        error = str(self.process.readAllStandardError(), encoding='utf-8', errors='ignore')
        if error.strip() and not self.was_canceled:
            url = self.url_input.text().strip().lower()
            if ("youtube.com" in url or "youtu.be" in url) and "ERROR" in error.upper():
                self.status_text.setText(translations[self.language]["youtube_cookie_error"])
                self.current_status = translations[self.language]["youtube_cookie_error"]
                self.current_status_key = "youtube_cookie_error"
            elif "WARNING" in error:
                if "unavailable videos are hidden" in error:
                    count = error.split("INFO - ")[1].split(" ")[0]
                    message = translations[self.language]["unavailable_videos"].format(count=count)
                    self.status_text.setText(translations[self.language]["warning"].format(message=message))
                    self.current_status = translations[self.language]["warning"].format(message=message)
                    self.current_status_key = "unavailable_videos"
                else:
                    self.status_text.setText(translations[self.language]["warning"].format(message=error.strip()))
                    self.current_status = translations[self.language]["warning"].format(message=error.strip())
                    self.current_status_key = "warning"
            else:
                self.status_text.setText(translations[self.language]["download_error"].format(error=error.strip()))
                self.current_status = translations[self.language]["download_error"].format(error=error.strip())
                self.current_status_key = "download_error"
            self.error_timer.start(5000)

    def download_finished(self, exit_code, exit_status):
        self.download_button.setEnabled(True)
        self.cancel_button.setVisible(False)
        if self.taskbar_button and self.windowHandleCreated:
            try:
                self.taskbar_button.progress().setVisible(False)
            except Exception:
                pass
        if exit_code == 0 or (self.download_type == "single" and self.first_video_completed):
            self.download_button.set_completed()
            self.status_text.setText(translations[self.language]["download_completed"])
            self.current_status = translations[self.language]["download_completed"]
            self.current_status_key = "download_completed"
            self.error_timer.start(5000)
        else:
            self.download_button.reset()
            if self.was_canceled:
                self.status_text.setText(translations[self.language]["download_canceled"])
                self.current_status = translations[self.language]["download_canceled"]
                self.current_status_key = "download_canceled"
            else:
                url = self.url_input.text().strip().lower()
                if "youtube.com" in url or "youtu.be" in url:
                    self.status_text.setText(translations[self.language]["youtube_cookie_error"])
                    self.current_status = translations[self.language]["youtube_cookie_error"]
                    self.current_status_key = "youtube_cookie_error"
                else:
                    self.status_text.setText(translations[self.language]["download_error"].format(error="Unknown error"))
                    self.current_status = translations[self.language]["download_error"].format(error="Unknown error")
                    self.current_status_key = "download_error"
            self.error_timer.start(5000)
        self.was_canceled = False
        self.first_video_completed = False

    def cancel_download(self):
        if self.process.state() != QProcess.NotRunning:
            self.was_canceled = True
            self.process.terminate()
            self.process.waitForFinished(1000)
            if self.process.state() != QProcess.NotRunning:
                self.process.kill()
        self.download_button.setEnabled(True)
        self.cancel_button.setVisible(False)
        self.download_button.reset()
        self.status_text.setText(translations[self.language]["download_canceled"])
        self.current_status = translations[self.language]["download_canceled"]
        self.current_status_key = "download_canceled"
        self.error_timer.start(5000)
        if self.taskbar_button and self.windowHandleCreated:
            try:
                self.taskbar_button.progress().setVisible(False)
            except Exception:
                pass

    def closeEvent(self, event):
        if self.process.state() != QProcess.NotRunning:
            self.process.terminate()
            self.process.waitForFinished(1000)
            if self.process.state() != QProcess.NotRunning:
                self.process.kill()
        if self.taskbar_button and self.windowHandleCreated:
            try:
                self.taskbar_button.progress().setVisible(False)
            except Exception:
                pass
        self.save_settings()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    icon_path = None
    for ext in ["icon.png", "icon.ico"]:
        if os.path.exists(ext):
            icon_path = ext
            break
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
    window = FluxWindow()
    window.show()
    sys.exit(app.exec_())
