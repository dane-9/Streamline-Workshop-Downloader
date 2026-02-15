import os
import sys
import shutil
import subprocess
import platform
import json
import time
import ctypes
import requests
import zipfile
from io import BytesIO
from botasaurus.browser import browser, Driver

from PySide6.QtWidgets import (
    QDialog, QLabel, QProgressBar, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QWidget, QMessageBox, QApplication, QGraphicsDropShadowEffect
)
from PySide6.QtCore import (
    Qt, Signal, QThread, QTimer, QPoint
)
from PySide6.QtGui import (
    QIcon, QPixmap, QColor,
)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)
    
def set_windows_dark_titlebar(window_handle, enable_dark, color=None):
    if platform.system().lower() != 'windows':
        return
    try:
        # Enable or disable dark mode
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
        dark_mode = ctypes.c_int(1 if enable_dark else 0)
        set_window_attribute(
            ctypes.wintypes.HWND(window_handle),
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(dark_mode),
            ctypes.sizeof(dark_mode)
        )
        if color:
            DWMWA_COLORIZATION_COLOR = 35
            # Convert RGB tuple to DWORD (0x00BBGGRR)
            r, g, b = color
            color_value = (b << 16) | (g << 8) | r
            colorization_color = ctypes.c_uint32(color_value)
            set_window_attribute(
                ctypes.wintypes.HWND(window_handle),
                DWMWA_COLORIZATION_COLOR,
                ctypes.byref(colorization_color),
                ctypes.sizeof(colorization_color)
            )

            DWMWA_COLORIZATION_COLOR_BALANCE = 38
            color_balance = ctypes.c_int(0)
            set_window_attribute(
                ctypes.wintypes.HWND(window_handle),
                DWMWA_COLORIZATION_COLOR_BALANCE,
                ctypes.byref(color_balance),
                ctypes.sizeof(color_balance)
            )

    except Exception as e:
        print(f"Failed to customize title bar: {e}")
        
def apply_theme_titlebar(window, config):
    if platform.system().lower() != 'windows':
        return
    theme = config.get('current_theme', 'Dark')
    is_dark = "dark" in theme.lower()

    theme_color_mapping = {
        "Dark": (45, 45, 45),          # Dark gray
        "Light": (255, 255, 255),      # White
    }

    color = theme_color_mapping.get(theme, None)
    set_windows_dark_titlebar(int(window.winId()), is_dark, color)
    
class AppIDScraper:
    def __init__(self, files_dir):
        self.files_dir = files_dir

    def scrape_steamdb(self, selected_types, log_signal=None):
        if log_signal:
            log_signal.emit("Scraping SteamDB for AppIDs...")

        try:
            result = _scrape_steamdb_botasaurus({"selected_types": selected_types})
            # The @browser decorator may wrap results in a list
            if isinstance(result, list) and len(result) == 1 and isinstance(result[0], list):
                entries = result[0]
            elif isinstance(result, list) and all(isinstance(e, str) for e in result):
                entries = result
            else:
                entries = result if result else []
        except Exception as e:
            if log_signal:
                log_signal.emit(f"SteamDB scraping failed: {e}")
            raise

        if log_signal:
            log_signal.emit("SteamDB scraping Completed.")
        return entries


@browser(
    headless=True,
    block_images=True,
    output=None,
    cache=False,
    close_on_crash=True,
    raise_exception=True,
)
def _scrape_steamdb_botasaurus(driver: Driver, data):
    selected_types = data["selected_types"]

    driver.google_get("https://steamdb.info/sub/17906/apps/", bypass_cloudflare=True)
    
    # Wait for the table rows to appear after Cloudflare bypass
    driver.wait_for_element("tr.app", wait=60)

    # Small delay to ensure the full table has rendered
    time.sleep(2)

    # Debug: check what page we're actually on and how many rows exist
    current_url = driver.run_js("return window.location.href")
    row_count = driver.run_js("return document.querySelectorAll('tr.app').length")
    print(f"[SteamDB Scraper] Current URL: {current_url}")
    print(f"[SteamDB Scraper] Found {row_count} tr.app rows")

    if not row_count or row_count == 0:
        print("[SteamDB Scraper] No rows found — page may not have loaded correctly")
        return []

    # Extract all data in one JS call — note the "return" keyword is required
    types_json = json.dumps(selected_types)
    entries = driver.run_js(f"""
        return (function() {{
            var selectedTypes = {types_json};
            var rows = document.querySelectorAll('tr.app');
            var results = [];
            for (var i = 0; i < rows.length; i++) {{
                var cells = rows[i].querySelectorAll('td');
                if (cells.length >= 3) {{
                    var appType = cells[1].textContent.trim();
                    if (selectedTypes.indexOf(appType) !== -1) {{
                        var appName = cells[2].textContent.trim();
                        var appId = rows[i].getAttribute('data-appid');
                        if (appId) {{
                            results.push(appName + ',' + appId);
                        }}
                    }}
                }}
            }}
            return results;
        }})();
    """)

    print(f"[SteamDB Scraper] Extracted {len(entries) if entries else 0} entries")
    return entries if entries else []

class SetupWorker(QThread):
    progress_update = Signal(int, str)
    error_occurred = Signal(str)
    finished_success = Signal()

    def __init__(self, steamcmd_dir, files_dir):
        super().__init__()
        self.steamcmd_dir = steamcmd_dir
        self.files_dir = files_dir
        self.canceled = False
        self.error_emitted = False
        self.scraper = AppIDScraper(self.files_dir)

    def run(self):
        try:
            self.progress_update.emit(0, "Checking SteamCMD installation...")
            steamcmd_present = self.check_steamcmd_installed()

            if not steamcmd_present:
                self.progress_update.emit(10, "Downloading SteamCMD...")
                self.download_steamcmd()
                if self.canceled:
                    return

                self.progress_update.emit(30, "Initializing SteamCMD...")
                self.initialize_steamcmd()
                if self.canceled:
                    return
            
            self.progress_update.emit(50, "SteamCMD setup complete.")

            self.progress_update.emit(60, "Checking AppIDs database...")
            appids_path = os.path.join(self.files_dir, 'AppIDs.txt')
            if not os.path.isfile(appids_path):
                self.progress_update.emit(70, "Scraping SteamDB for AppIDs...")
                self.download_appids()
                if self.canceled:
                    return
            else:
                self.progress_update.emit(90, "AppIDs database already exists.")

            self.progress_update.emit(100, "Setup complete!")
            self.finished_success.emit()
            
        except Exception as e:
            if not self.error_emitted:
                self.error_occurred.emit(f"Setup failed: {str(e)}")
    
    def cancel(self):
        self.canceled = True
        
    def check_steamcmd_installed(self):
        steamcmd_executable = os.path.join(self.steamcmd_dir, 'steamcmd.exe')
        essential_files = [
            os.path.join(self.steamcmd_dir, 'steam.dll'),
            os.path.join(self.steamcmd_dir, 'steamclient.dll')
        ]
        return os.path.isfile(steamcmd_executable) and all(os.path.isfile(file) for file in essential_files)
    
    def download_steamcmd(self):
        try:
            os.makedirs(self.steamcmd_dir, exist_ok=True)
            steamcmd_zip_url = 'https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip'
            response = requests.get(steamcmd_zip_url, stream=True)
            response.raise_for_status()
            with zipfile.ZipFile(BytesIO(response.content)) as zip_ref:
                zip_ref.extractall(self.steamcmd_dir)
        except Exception as e:
            self.error_emitted = True
            self.error_occurred.emit(f"Failed to download SteamCMD: {str(e)}")
            raise
    
    def initialize_steamcmd(self):
        try:
            steamcmd_executable = os.path.join(self.steamcmd_dir, 'steamcmd.exe')
            steamcmd_process = subprocess.Popen(
                [steamcmd_executable, '+quit'],
                cwd=self.steamcmd_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            for line in steamcmd_process.stdout:
                if self.canceled:
                    steamcmd_process.terminate()
                    break
            
            steamcmd_process.stdout.close()
            steamcmd_process.wait()
        except Exception as e:
            self.error_emitted = True
            self.error_occurred.emit(f"Failed to initialize SteamCMD: {str(e)}")
            raise

    def download_appids(self):
        try:
            entries = self.scraper.scrape_steamdb(["Game"])

            appids_path = os.path.join(self.files_dir, 'AppIDs.txt')
            with open(appids_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(entries))
        except Exception as e:
            self.error_emitted = True
            self.error_occurred.emit(f"Failed to update AppIDs: {str(e)}")
            raise

    def cleanup_files(self):
        if os.path.exists(self.steamcmd_dir):
            try:
                shutil.rmtree(self.steamcmd_dir)
            except Exception:
                pass
            
        appids_path = os.path.join(self.files_dir, 'AppIDs.txt')
        if os.path.exists(appids_path):
            try:
                os.remove(appids_path)
            except Exception:
                pass

class ThemedSplashScreen(QDialog):
    setup_completed = Signal(bool)

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint)
        self.setWindowTitle("Initializing Streamline")
        self.setFixedSize(530, 330)
        self.setWindowModality(Qt.ApplicationModal)
        self.setObjectName("splashScreen")

        self.setAttribute(Qt.WA_TranslucentBackground)

        screen_geometry = QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - self.width()) / 2
        y = (screen_geometry.height() - self.height()) / 2
        self.move(x, y)

        self.files_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'Files')
        os.makedirs(self.files_dir, exist_ok=True)
        self.steamcmd_dir = os.path.join(self.files_dir, 'steamcmd')

        self.apply_splash_theme()

        self.init_ui()

        self.worker = SetupWorker(self.steamcmd_dir, self.files_dir)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.finished_success.connect(self.on_setup_success)

        QTimer.singleShot(100, self.worker.start)

    def apply_splash_theme(self):
        self.setStyleSheet("""
            #splashScreen {
                background-color: transparent;
            }
            #backgroundPanel {
                background-color: #1E1E1E;
                border: 1px solid #3F3F46;
                border-radius: 10px;
            }
            QLabel {
                color: #E0E0E0;
            }
            QProgressBar {
                border: 1px solid #3F3F46;
                color: #FFFFFF;
                border-radius: 3px;
                text-align: center;
                background-color: #252526;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4D8AC9;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #4D8AC9;
                color: #FFFFFF;
                border: none;
                border-radius: 3px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5A97D6;
            }
            QPushButton:pressed {
                background-color: #3D7AB9;
            }
            #titleLabel {
                font-size: 18px;
                font-weight: bold;
                color: #FFFFFF;
            }
            #statusLabel {
                color: #FFFFFF;
            }
        """)
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.background_panel = QFrame(self)
        self.background_panel.setObjectName("backgroundPanel")

        shadow = QGraphicsDropShadowEffect(self.background_panel)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 0)
        self.background_panel.setGraphicsEffect(shadow)

        panel_layout = QVBoxLayout(self.background_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        content_frame = QFrame()
        content_frame.setObjectName("contentFrame")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(25, 25, 25, 25)
        content_layout.setSpacing(15)

        logo_container = QWidget()
        logo_container.setFixedHeight(80)
        logo_container_layout = QVBoxLayout(logo_container)
        logo_container_layout.setContentsMargins(0, 0, 0, 0)

        logo_label = QLabel()
        logo_path = resource_path('Files/logo.png')
        pixmap = QPixmap(logo_path)
        logo_label.setPixmap(pixmap.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        logo_container_layout.addWidget(logo_label)
        content_layout.addWidget(logo_container)

        title_label = QLabel("Initializing Streamline")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(title_label)

        self.status_label = QLabel("Preparing setup...")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(20)
        content_layout.addWidget(self.progress_bar)

        content_layout.addStretch(1)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setCursor(Qt.PointingHandCursor)
        self.cancel_button.clicked.connect(self.cancel_setup)
        self.cancel_button.setFixedWidth(100)
        button_layout.addWidget(self.cancel_button)

        content_layout.addLayout(button_layout)

        panel_layout.addWidget(content_frame)

        main_layout.addWidget(self.background_panel)

        main_layout.setContentsMargins(15, 15, 15, 15)
    
    def update_progress(self, progress, status):
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)
    
    def show_error(self, error_message):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Setup Error")
        msg_box.setText(error_message)
        
        close_button = msg_box.addButton("Close", QMessageBox.RejectRole)
        open_anyway_button = msg_box.addButton("Open Anyway", QMessageBox.AcceptRole)
        open_anyway_button.setObjectName("setup_open_anyway")

        msg_box.setDefaultButton(close_button)
        
        self.apply_message_box_theme(msg_box)

        set_windows_dark_titlebar(int(msg_box.winId()), True, (45, 45, 45))

        msg_box.exec_()
        clicked_button = msg_box.clickedButton()
        if clicked_button == open_anyway_button:
            self.setup_completed.emit(True)
        else:
            self.setup_completed.emit(False)
        
        self.close()

    def apply_message_box_theme(self, msg_box):
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #1E1E1E;
                color: #E0E0E0;
            }
            QLabel {
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #4D8AC9;
                color: #FFFFFF;
                border: none;
                border-radius: 3px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5A97D6;
            }
            QPushButton:pressed {
                background-color: #3D7AB9;
            }
            #setup_open_anyway {
                background-color: #333333;
                color: #A0A0A0;
                border: none;
                border-radius: 3px;
                padding: 8px 16px;
                font-weight: bold;
            }
            #setup_open_anyway:hover {
                background-color: #555555;
                color: #FFFFFF;
            }
            #setup_open_anyway:pressed {
                background-color: #444444;
                color: #FFFFFF;
            }
        """)
    
    def on_setup_success(self):
        self.setup_completed.emit(True)
        self.close()
    
    def cancel_setup(self):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Cancel Setup")
        msg_box.setText("Are you sure you want to cancel the setup?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)

        self.apply_message_box_theme(msg_box)
        
        set_windows_dark_titlebar(int(msg_box.winId()), True, (45, 45, 45))

        reply = msg_box.exec_()

        if reply == QMessageBox.Yes:
            self.worker.cancel()
            self.worker.cleanup_files()
            self.setup_completed.emit(False)
            self.close()

    def closeEvent(self, event):
        if self.worker.isRunning():
            self.worker.cancel()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.dragPos)
            event.accept()
