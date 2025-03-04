import os
import sys
import shutil
import subprocess
import platform
import time
import threading
import ctypes
import requests
import zipfile
from io import BytesIO
from lxml import html
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import win32gui

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
        self.chromium_dir = os.path.join(self.files_dir, 'chromium')
        os.makedirs(self.chromium_dir, exist_ok=True)

    def hide_browser(self):
        time.sleep(0.1)
        def window_enum_callback(hwnd, window_list):
            window_list.append(hwnd)
        hwnd_list = []
        win32gui.EnumWindows(window_enum_callback, hwnd_list)
        for hwnd in hwnd_list:
            window_text = win32gui.GetWindowText(hwnd)
            if 'Chrome for Testing' in window_text:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
                return

    def get_download_links(self):
        url = "https://googlechromelabs.github.io/chrome-for-testing/#stable"
        response = requests.get(url)
        tree = html.fromstring(response.content)

        chrome_url = tree.xpath("//section[@id='stable']//tr[@class='status-ok' and th[1]/code/text()='chrome' and th[2]/code/text()='win64']//td[1]/code/text()")
        chromedriver_url = tree.xpath("//section[@id='stable']//tr[@class='status-ok' and th[1]/code/text()='chromedriver' and th[2]/code/text()='win64']//td[1]/code/text()")

        if not chrome_url or not chromedriver_url:
            raise Exception("Failed to find the download links for Chromium and Chromedriver.")

        return chrome_url[0].strip(), chromedriver_url[0].strip()

    def download_and_extract_zip(self, url, extract_to, component_name, log_signal=None, progress_value=None):
        if log_signal:
            try:
                if progress_value is not None:
                    log_signal.emit(progress_value, f"Downloading {component_name}...")
                else:
                    log_signal.emit(f"Downloading {component_name}...")
            except TypeError:
                log_signal.emit(f"Downloading {component_name}...")

        response = requests.get(url)
        zip_filename = os.path.join(extract_to, "download.zip")

        with open(zip_filename, 'wb') as f:
            f.write(response.content)

        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extractall(extract_to)

        os.remove(zip_filename)

        if log_signal:
            try:
                if progress_value is not None:
                    log_signal.emit(progress_value + 5, f"{component_name} downloaded and extracted.")
                else:
                    log_signal.emit(f"{component_name} downloaded and extracted.")
            except TypeError:
                log_signal.emit(f"{component_name} downloaded and extracted.")

    def check_chrome_installed(self):
        chrome_win64_dir = os.path.join(self.chromium_dir, 'chrome-win64')
        return os.path.exists(chrome_win64_dir)
    
    def check_chromedriver_installed(self):
        chromedriver_win64_dir = os.path.join(self.chromium_dir, 'chromedriver-win64')
        return os.path.exists(chromedriver_win64_dir)
    
    def install_chrome(self, log_signal=None, progress_value=None):
        if not self.check_chrome_installed():
            if log_signal:
                try:
                    if progress_value is not None:
                        log_signal.emit(progress_value, "Chromium not found, downloading...")
                    else:
                        log_signal.emit("Chromium not found, downloading...")
                except TypeError:
                    log_signal.emit("Chromium not found, downloading...")
            
            chrome_url, _ = self.get_download_links()
            
            self.download_and_extract_zip(
                chrome_url, 
                self.chromium_dir, 
                "Chromium", 
                log_signal,
                progress_value
            )

            if log_signal:
                try:
                    if progress_value is not None:
                        log_signal.emit(progress_value + 10, "Chromium installed")
                    else:
                        log_signal.emit("Chromium installed")
                except TypeError:
                    log_signal.emit("Chromium installed")
        else:
            if log_signal:
                try:
                    if progress_value is not None:
                        log_signal.emit(progress_value + 10, "Chromium already installed")
                    else:
                        log_signal.emit("Chromium already installed")
                except TypeError:
                    log_signal.emit("Chromium already installed")
    
    def install_chromedriver(self, log_signal=None, progress_value=None):
        if not self.check_chromedriver_installed():
            if log_signal:
                try:
                    if progress_value is not None:
                        log_signal.emit(progress_value, "ChromeDriver not found, downloading...")
                    else:
                        log_signal.emit("ChromeDriver not found, downloading...")
                except TypeError:
                    log_signal.emit("ChromeDriver not found, downloading...")

            _, chromedriver_url = self.get_download_links()

            self.download_and_extract_zip(
                chromedriver_url, 
                self.chromium_dir, 
                "ChromeDriver", 
                log_signal,
                progress_value
            )

            if log_signal:
                try:

                    if progress_value is not None:
                        log_signal.emit(progress_value + 10, "ChromeDriver installed")
                    else:
                        log_signal.emit("ChromeDriver installed")
                except TypeError:
                    log_signal.emit("ChromeDriver installed")
        else:
            if log_signal:
                try:
                    if progress_value is not None:
                        log_signal.emit(progress_value + 10, "ChromeDriver already installed")
                    else:
                        log_signal.emit("ChromeDriver already installed")
                except TypeError:
                    log_signal.emit("ChromeDriver already installed")

    def scrape_steamdb(self, selected_types, log_signal=None):
        if log_signal:
            log_signal.emit("Scraping SteamDB for AppIDs...")

        self.install_chrome(log_signal)
        self.install_chromedriver(log_signal)

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("window-position=-2000,0")

        chromedriver_path = os.path.abspath(os.path.join(self.chromium_dir, "chromedriver-win64", "chromedriver.exe"))
        chrome_path = os.path.abspath(os.path.join(self.chromium_dir, "chrome-win64", "chrome.exe"))
        chrome_options.binary_location = chrome_path

        driver = webdriver.Chrome(service=Service(chromedriver_path), options=chrome_options)

        hide_thread = threading.Thread(target=self.hide_browser)
        hide_thread.start()

        entries = []
        try:
            steamdb_url = "https://steamdb.info/sub/17906/apps/"
            driver.get(steamdb_url)

            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.app'))
            )

            rows = driver.find_elements(By.CSS_SELECTOR, 'tr.app')

            for row in rows:
                app_type = row.find_element(By.CSS_SELECTOR, 'td:nth-child(2)').text.strip()
                if app_type in selected_types:
                    app_name = row.find_element(By.CSS_SELECTOR, 'td:nth-child(3)').text.strip()
                    app_id = row.get_attribute('data-appid')
                    entries.append(f"{app_name},{app_id}")

            if log_signal:
                log_signal.emit("SteamDB scraping Completed.")
            return entries

        finally:
            driver.quit()

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
                self.progress_update.emit(5, "Downloading SteamCMD...")
                self.download_steamcmd()
                if self.canceled:
                    return

                self.progress_update.emit(20, "Initializing SteamCMD...")
                self.initialize_steamcmd()
                if self.canceled:
                    return
            
            self.progress_update.emit(30, "SteamCMD setup complete.")

            self.progress_update.emit(35, "Checking Chromium installation...")
            chrome_present = self.check_chrome_installed()

            if not chrome_present:
                self.progress_update.emit(40, "Chromium not found.")
                
                chrome_url, _ = self.scraper.get_download_links()
                
                self.progress_update.emit(45, "Downloading Chromium...")
                self.download_chrome(chrome_url)
                if self.canceled:
                    return
            else:
                self.progress_update.emit(45, "Chromium already installed.")
            
            self.progress_update.emit(55, "Chromium setup complete.")

            self.progress_update.emit(60, "Checking ChromeDriver installation...")
            chromedriver_present = self.check_chromedriver_installed()

            if not chromedriver_present:
                self.progress_update.emit(65, "ChromeDriver not found.")
                
                _, chromedriver_url = self.scraper.get_download_links()
                
                self.progress_update.emit(70, "Downloading ChromeDriver...")
                self.download_chromedriver(chromedriver_url)
                if self.canceled:
                    return
            else:
                self.progress_update.emit(70, "ChromeDriver already installed.")
            
            self.progress_update.emit(80, "ChromeDriver setup complete.")

            self.progress_update.emit(85, "Checking AppIDs database...")
            appids_path = os.path.join(self.files_dir, 'AppIDs.txt')
            if not os.path.isfile(appids_path):
                self.progress_update.emit(90, "Scraping SteamDB for AppIDs...")
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
    
    def check_chrome_installed(self):
        return self.scraper.check_chrome_installed()
    
    def check_chromedriver_installed(self):
        return self.scraper.check_chromedriver_installed()
    
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
    
    def download_chrome(self, url):
        try:
            self.progress_update.emit(45, "Starting Chrome download...")
            
            self.scraper.download_and_extract_zip(url, self.scraper.chromium_dir, "Chromium", self.progress_update,progress_value=50)

            self.progress_update.emit(55, "Chromium downloaded and installed.")
        except Exception as e:
            self.error_emitted = True
            self.error_occurred.emit(f"Failed to download Chromium: {str(e)}")
            raise

    def download_chromedriver(self, url):
        try:
            self.progress_update.emit(70, "Starting ChromeDriver download...")

            self.scraper.download_and_extract_zip(url, self.scraper.chromium_dir, "ChromeDriver", self.progress_update, progress_value=75)

            self.progress_update.emit(80, "ChromeDriver downloaded and installed.")
        except Exception as e:
            self.error_emitted = True
            self.error_occurred.emit(f"Failed to download ChromeDriver: {str(e)}")
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
            
        chromium_dir = os.path.join(self.files_dir, 'chromium')
        if os.path.exists(chromium_dir):
            try:
                shutil.rmtree(chromium_dir)
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