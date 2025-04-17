import os
import sys
import time
import json
import traceback
import logging
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QPushButton,
    QGroupBox, QCheckBox, QFileDialog, QSplitter, QLineEdit, QComboBox,
    QFormLayout, QToolButton, QSizePolicy, QApplication,
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QEvent, QSize, QCoreApplication
from PySide6.QtGui import QTextCursor, QColor, QTextCharFormat, QTextDocument, QIcon


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class LogViewerDialog(QDialog):
    status_update = Signal(str)
    append_content_signal = Signal(object)

    def __init__(self, parent=None, debug_manager=None):
        super().__init__()
        self.setWindowTitle("Debug Log Viewer")
        self.resize(900, 600)

        self.debug_manager = debug_manager
        self.current_file = None
        self.search_index = 0
        self.search_results = []
        self._last_search_text = ""
        self._current_content_lines = []

        self.initUI()

        self.status_update.connect(self.status_label.setText)
        self.append_content_signal.connect(self._append_line_to_display)

        if self.debug_manager:
            self.debug_manager.register_log_viewer(self)
            if self.debug_manager.current_log_file:
                self.load_log_file(self.debug_manager.current_log_file)
        else:
            self.status_update.emit("Ready. Load a file or connect to the application.")

    def initUI(self):
        main_layout = QVBoxLayout(self)

        top_layout = QVBoxLayout()
        filter_group = QGroupBox("Filter Levels")
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setSpacing(10)

        self.level_checkboxes = {}
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            checkbox = QCheckBox(level)
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self.apply_filters)
            self.level_checkboxes[level] = checkbox
            filter_layout.addWidget(checkbox)

        top_layout.addWidget(filter_group)

        options_group = QGroupBox("Options")
        options_layout = QHBoxLayout(options_group)
        options_layout.setSpacing(15)

        self.auto_scroll_checkbox = QCheckBox("Auto-scroll with new logs")
        self.auto_scroll_checkbox.setChecked(True)
        options_layout.addWidget(self.auto_scroll_checkbox)

        self.newest_logs_checkbox = QCheckBox("Newest logs first")
        self.newest_logs_checkbox.setChecked(False)
        self.newest_logs_checkbox.stateChanged.connect(self.toggle_newest_logs_mode)
        options_layout.addWidget(self.newest_logs_checkbox)

        top_layout.addWidget(options_group)
        main_layout.addLayout(top_layout)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search text...")
        self.search_input.returnPressed.connect(self.search_text)
        search_layout.addWidget(self.search_input, stretch=1)

        self.caseButton = QToolButton()
        self.caseButton.setCheckable(True)
        self.caseButton.setToolTip("Case Sensitive Search")
        try:
            self.caseButton.setIcon(QIcon(resource_path("Files/case_disabled.png")))
        except:
            self.caseButton.setText("Aa")
        self.caseButton.setIconSize(QSize(16, 16))
        self.caseButton.setStyleSheet("QToolButton { border: none; padding: 2px; }")
        self.caseButton.toggled.connect(self.updateCaseIcon)
        search_layout.addWidget(self.caseButton)

        self.regexButton = QToolButton()
        self.regexButton.setCheckable(True)
        self.regexButton.setToolTip("Use Regular Expression")
        try:
            self.regexButton.setIcon(QIcon(resource_path("Files/regex_disabled.png")))
        except:
            self.regexButton.setText(".*")
        self.regexButton.setIconSize(QSize(16, 16))
        self.regexButton.setStyleSheet("QToolButton { border: none; padding: 2px; }")
        self.regexButton.toggled.connect(self.updateRegexIcon)
        search_layout.addWidget(self.regexButton)

        self.search_next_button = QPushButton("Find Next")
        self.search_next_button.clicked.connect(self.find_next)
        search_layout.addWidget(self.search_next_button)

        self.search_prev_button = QPushButton("Find Prev")
        self.search_prev_button.clicked.connect(self.find_prev)
        search_layout.addWidget(self.search_prev_button)

        main_layout.addLayout(search_layout)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setLineWrapMode(QTextEdit.NoWrap)
        main_layout.addWidget(self.log_display, stretch=1)

        bottom_layout = QHBoxLayout()
        action_buttons_layout = QHBoxLayout()
        action_buttons_layout.setSpacing(5)

        self.load_button = QPushButton("Load File")
        self.load_button.clicked.connect(self.browse_log_file)
        action_buttons_layout.addWidget(self.load_button)

        self.reload_button = QPushButton("Reload")
        self.reload_button.clicked.connect(self.reload_logs)
        action_buttons_layout.addWidget(self.reload_button)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_display)
        action_buttons_layout.addWidget(self.clear_button)

        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self.export_logs)
        action_buttons_layout.addWidget(self.export_button)

        bottom_layout.addLayout(action_buttons_layout)
        bottom_layout.addStretch(1)
        self.status_label = QLabel("Initializing...")
        bottom_layout.addWidget(self.status_label)
        main_layout.addLayout(bottom_layout)

    def updateCaseIcon(self, checked):
        try:
            icon_path = resource_path(f"Files/case_{'enabled' if checked else 'disabled'}.png")
            self.caseButton.setIcon(QIcon(icon_path))
        except:
            self.caseButton.setChecked(checked)

    def updateRegexIcon(self, checked):
        try:
            icon_path = resource_path(f"Files/regex_{'enabled' if checked else 'disabled'}.png")
            self.regexButton.setIcon(QIcon(icon_path))
        except:
            self.regexButton.setChecked(checked)

    def browse_log_file(self):
        start_dir = self.debug_manager.logs_dir if self.debug_manager else ""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Log File", start_dir,
            "Log Files (*.log);;Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.load_log_file(file_path)

    def load_log_file(self, file_path):
        if not file_path or not os.path.isfile(file_path):
            self.status_update.emit("File not found")
            return

        self.current_file = file_path
        self.log_display.clear()
        self.status_update.emit(f"Loading {os.path.basename(file_path)}...")
        QCoreApplication.processEvents()
        self.process_and_display_file(file_path)

    def reload_logs(self):
        if self.current_file and os.path.isfile(self.current_file):
            self.log_display.clear()
            self.status_update.emit(f"Reloading {os.path.basename(self.current_file)}...")
            QCoreApplication.processEvents()
            self.process_and_display_file(self.current_file)
        else:
            self.status_update.emit("No log file loaded to reload")

    def clear_display(self):
        self.log_display.clear()
        self.status_update.emit("Display cleared")

    def export_logs(self):
        content = self.log_display.toPlainText()
        if not content:
            self.status_update.emit("No content to export")
            return

        default_filename = f"exported_{os.path.basename(self.current_file)}" if self.current_file else "exported_logs.log"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Logs", default_filename,
            "Log Files (*.log);;Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.status_update.emit(f"Exported to {os.path.basename(file_path)}")
            except Exception as e:
                self.status_update.emit(f"Error exporting: {str(e)}")

    def apply_filters(self):
        if not self.current_file or not os.path.isfile(self.current_file):
            return
        self.status_update.emit("Applying filters...")
        QCoreApplication.processEvents()
        self.process_and_display_file(self.current_file)

    def process_and_display_file(self, file_path):
        active_levels = {level for level, checkbox in self.level_checkboxes.items()
                         if checkbox.isChecked()}

        self.log_display.clear()
        self.log_display.blockSignals(True)

        lines_to_process = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                if self.newest_logs_checkbox.isChecked():
                    try:
                        all_lines = f.readlines()
                        all_lines.reverse()
                        lines_to_process = all_lines
                    except MemoryError:
                        self.log_display.blockSignals(False)
                        return
                else:
                    lines_to_process = f

                filtered_lines_data = []
                for line in lines_to_process:
                    line = line.rstrip('\n')
                    level = None
                    log_format_found = False

                    for l_name in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                        if f" - {l_name} - " in line:
                            log_format_found = True
                            level = l_name
                            break

                    should_display = False
                    if log_format_found:
                        if level in active_levels:
                            should_display = True
                    elif active_levels:
                        should_display = True
                        level = "INFO"

                    if should_display:
                        color = self.get_level_color(level)
                        filtered_lines_data.append((line, color))

                cursor = self.log_display.textCursor()
                cursor.beginEditBlock()
                for line_text, color in filtered_lines_data:
                    line_format = QTextCharFormat()
                    line_format.setForeground(color)
                    cursor.movePosition(QTextCursor.End)
                    cursor.insertText(line_text + "\n", line_format)
                cursor.endEditBlock()

        except FileNotFoundError:
            self.status_update.emit("Error: File not found during processing.")
        except Exception as e:
            self.status_update.emit(f"Error processing file: {str(e)}")
            if self.debug_manager:
                self.debug_manager.exception(f"Error processing log file {file_path}")
        finally:
            self.log_display.blockSignals(False)

        if self.newest_logs_checkbox.isChecked():
            self.log_display.moveCursor(QTextCursor.Start)
        elif self.auto_scroll_checkbox.isChecked():
            self.log_display.moveCursor(QTextCursor.End)
        else:
            self.log_display.moveCursor(QTextCursor.Start)

        self.log_display.ensureCursorVisible()
        self.status_update.emit(f"Displayed content from: {os.path.basename(file_path)}")

    def _append_line_to_display(self, line_data):
        line_text, color = line_data
        log_format = QTextCharFormat()
        log_format.setForeground(color)

        scrollbar = self.log_display.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 4

        cursor = self.log_display.textCursor()

        if self.newest_logs_checkbox.isChecked():
            cursor.movePosition(QTextCursor.Start)
            cursor.insertText(line_text + "\n", log_format)
            self.log_display.moveCursor(QTextCursor.Start)
            self.log_display.ensureCursorVisible()
        else:
            cursor.movePosition(QTextCursor.End)
            cursor.insertText(line_text + "\n", log_format)
            if self.auto_scroll_checkbox.isChecked() and was_at_bottom:
                scrollbar.setValue(scrollbar.maximum())

    def get_level_color(self, level):
        colors = {
            "DEBUG": QColor(100, 100, 100),
            "INFO": QColor(0, 0, 0),
            "WARNING": QColor(180, 90, 0),
            "ERROR": QColor(200, 0, 0),
            "CRITICAL": QColor(130, 0, 0),
        }
        return colors.get(level, QColor(0, 0, 0))

    def toggle_newest_logs_mode(self, state):
        self.apply_filters()

    def search_text(self):
        search_text = self.search_input.text()
        if not search_text:
            self.status_update.emit("Cleared search.")
            self._highlight_matches([])
            return

        self.search_results = []
        self.search_index = 0
        self._last_search_text = search_text

        doc_text = self.log_display.toPlainText()
        if not doc_text:
            self.status_update.emit("No content to search.")
            return

        self.status_update.emit("Searching...")
        QCoreApplication.processEvents()

        use_regex = self.regexButton.isChecked()
        case_sensitive = self.caseButton.isChecked()

        try:
            if use_regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(search_text, flags)
                for match in pattern.finditer(doc_text):
                    self.search_results.append((match.start(), match.end() - match.start()))
            else:
                start_pos = 0
                find_method = doc_text.find if case_sensitive else doc_text.lower().find
                term_to_find = search_text if case_sensitive else search_text.lower()
                term_len = len(search_text)

                while True:
                    pos = find_method(term_to_find, start_pos)
                    if pos == -1:
                        break
                    self.search_results.append((pos, term_len))
                    start_pos = pos + 1

            if self.search_results:
                self.find_next(new_search=True)
            else:
                self.status_update.emit("No matches found")
                self._highlight_matches([])

        except re.error as e:
            self.status_update.emit(f"Invalid regex: {str(e)}")
            self._highlight_matches([])
        except Exception as e:
            self.status_update.emit(f"Search error: {str(e)}")
            self._highlight_matches([])

    def find_next(self, new_search=False):
        if not new_search and self._last_search_text != self.search_input.text():
            self.search_text()
            return

        if not self.search_results:
            if self.search_input.text():
                self.search_text()
            else:
                self.status_update.emit("Enter text to search.")
            return

        if self.search_index >= len(self.search_results):
            self.search_index = 0

        pos, length = self.search_results[self.search_index]
        cursor = self.log_display.textCursor()
        cursor.setPosition(pos)
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, length)

        self.log_display.setTextCursor(cursor)
        self.log_display.ensureCursorVisible()

        self.search_index += 1
        self.status_update.emit(f"Match {self.search_index} of {len(self.search_results)}")

    def find_prev(self):
        if self._last_search_text != self.search_input.text():
            self.search_text()
            return

        if not self.search_results:
            if self.search_input.text():
                self.search_text()
            else:
                self.status_update.emit("Enter text to search.")
            return

        self.search_index -= 2
        if self.search_index < 0:
            self.search_index = len(self.search_results) - 1

        self.find_next(new_search=True)

    def _highlight_matches(self, results):
        selections = []
        if results:
            highlight_format = QTextCharFormat()
            highlight_format.setBackground(QColor("yellow"))

            for pos, length in results:
                cursor = self.log_display.textCursor()
                cursor.setPosition(pos)
                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, length)

                selection = QTextEdit.ExtraSelection()
                selection.format = highlight_format
                selection.cursor = cursor
                selections.append(selection)

        self.log_display.setExtraSelections(selections)

    def append_log(self, message, level="INFO"):
        if level in self.level_checkboxes and not self.level_checkboxes[level].isChecked():
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"{timestamp} - {level} - {message}"
        color = self.get_level_color(level)

        self.append_content_signal.emit((formatted_message, color))

    def closeEvent(self, event):
        if self.debug_manager:
            self.debug_manager.unregister_log_viewer()
        super().closeEvent(event)


class DebugManager(QObject):
    # Manages debug-related functionalities
    log_signal = Signal(str)
    _instance = None

    @classmethod
    def instance(cls, files_dir=None, log_signal=None):
        if cls._instance is None:
            if files_dir is None:
                raise ValueError("files_dir must be provided for initial instantiation")
            cls._instance = cls(files_dir, log_signal)
        if log_signal and cls._instance.app_log_signal != log_signal:
            cls._instance.app_log_signal = log_signal
        return cls._instance

    def __init__(self, files_dir, log_signal=None):
        if hasattr(self, '_initialized'):
            return
        super().__init__()
        self.files_dir = files_dir
        self.debug_dir = os.path.join(files_dir, 'Debug')
        self.logs_dir = os.path.join(self.debug_dir, 'Logs')
        self.crash_dir = os.path.join(self.debug_dir, 'Crashes')
        self.app_log_signal = log_signal

        os.makedirs(self.debug_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.crash_dir, exist_ok=True)

        self.debug_enabled = False
        self.write_to_file = False
        self.verbose_output = False
        self.save_crashes = False
        self.raw_steamcmd_logs = False

        self.current_log_file = None
        self.file_handler = None
        self.log_viewer = None

        self.setup_logger()
        self._initialized = True
        self.debug("DebugManager initialized.")

    def setup_logger(self):
        self.logger = logging.getLogger('streamline_debug')
        self.logger.setLevel(logging.DEBUG)
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        self.console_handler = console_handler

    def enable_file_logging(self):
        if self.file_handler:
            return
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_log_file = os.path.join(self.logs_dir, f'debug_{timestamp}.log')
            self.file_handler = RotatingFileHandler(
                self.current_log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8'
            )
            self.file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s'
            )
            self.file_handler.setFormatter(file_formatter)
            self.logger.addHandler(self.file_handler)
            self.info(f"Debug file logging enabled: {self.current_log_file}")
        except Exception as e:
            self.logger.error(f"Failed to enable file logging: {e}", exc_info=True)
            self.current_log_file = None
            self.file_handler = None

    def disable_file_logging(self):
        if self.file_handler:
            self.info("Disabling debug file logging.")
            try:
                self.logger.removeHandler(self.file_handler)
                self.file_handler.close()
            except Exception as e:
                self.logger.error(f"Error removing file logger handler: {e}", exc_info=True)
            finally:
                self.file_handler = None

    def update_settings(self, settings: dict):
        old_debug_enabled = self.debug_enabled
        old_write_to_file = self.write_to_file

        self.debug_enabled = settings.get('debug_enabled', False)
        self.write_to_file = settings.get('write_debug_to_file', False)
        self.verbose_output = settings.get('verbose_console_output', False)
        self.save_crashes = settings.get('save_crash_reports', False)
        self.raw_steamcmd_logs = settings.get('output_raw_steamcmd_logs', False)

        if self.console_handler:
            self.console_handler.setLevel(logging.DEBUG if self.verbose_output else logging.INFO)

        if self.debug_enabled and not old_debug_enabled:
            self.info("Debug mode enabled.")
        elif not self.debug_enabled and old_debug_enabled:
            self.info("Debug mode disabled.")

        if self.debug_enabled and self.write_to_file:
            if not old_write_to_file or not self.file_handler:
                self.enable_file_logging()
        elif old_write_to_file:
            self.disable_file_logging()

        if self.debug_enabled:
            self.debug(f"Debug settings updated: {settings}")

    def _log_to_targets(self, level, message, exc_info=None):
        if not self.debug_enabled:
            return

        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message, exc_info=exc_info)

        if self.app_log_signal and (self.verbose_output or level.upper() in ["INFO", "WARNING", "ERROR", "CRITICAL"]):
            prefix = f"[{level.upper()}] "
            if exc_info:
                if isinstance(exc_info, tuple):
                    tb_text = ''.join(traceback.format_exception(*exc_info))
                    full_message = f"{prefix}{message}\nStack trace:\n{tb_text}"
                else:
                    tb_text = traceback.format_exc()
                    full_message = f"{prefix}{message}\nStack trace:\n{tb_text}"
                self.app_log_signal.emit(full_message)
            else:
                self.app_log_signal.emit(f"{prefix}{message}")

        if self.log_viewer:
            if exc_info:
                if isinstance(exc_info, tuple):
                    tb_text = ''.join(traceback.format_exception(*exc_info))
                else:
                    tb_text = traceback.format_exc()
                full_message = f"{message}\nStack trace:\n{tb_text}"
                self.log_viewer.append_log(full_message, "ERROR")
            else:
                self.log_viewer.append_log(message, level.upper())

    def debug(self, message):
        self._log_to_targets("DEBUG", message)

    def info(self, message):
        self._log_to_targets("INFO", message)

    def warning(self, message):
        self._log_to_targets("WARNING", message)

    def error(self, message, exc_info=None):
        self._log_to_targets("ERROR", message, exc_info=exc_info)

    def critical(self, message, exc_info=None):
        self._log_to_targets("CRITICAL", message, exc_info=exc_info)

    def exception(self, message):
        self._log_to_targets("ERROR", message, exc_info=True)

    def log_network_request(self, method, url, params=None, headers=None, data=None, response=None, error=None):
        if not self.debug_enabled:
            return
        request_info = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'method': method,
            'url': url,
        }
        if params: request_info['params'] = str(params)
        if headers:
            safe_headers = headers.copy() if isinstance(headers, dict) else {}
            if isinstance(safe_headers, dict) and 'Authorization' in safe_headers:
                safe_headers['Authorization'] = '**** REDACTED ****'
            request_info['headers'] = str(safe_headers)
        if data:
            request_info['data'] = str(data)[:500] + ('...' if len(str(data)) > 500 else '')
        if response:
            try:
                status_code = getattr(response, 'status_code', getattr(response, 'status', 'N/A'))
                request_info['status_code'] = status_code
                content_preview = ""
                try:
                    if hasattr(response, 'text'):
                        content_preview = str(response.text)[:500]
                    elif hasattr(response, 'content'):
                        content_preview = str(response.content)[:500]
                    elif hasattr(response, 'read'):
                        request_info['response_type'] = response.__class__.__name__ + " (content not previewed)"
                except Exception:
                    content_preview = "(Could not get response body)"

                if content_preview:
                    if len(content_preview) >= 500: content_preview += '...'
                    request_info['response_preview'] = content_preview

                resp_headers = getattr(response, 'headers', None)
                if resp_headers:
                    request_info['response_headers'] = str(dict(resp_headers))

            except Exception as e:
                request_info['response_processing_error'] = str(e)
        if error:
            request_info['error'] = str(error)

        try:
            log_message = f"Network Request: {json.dumps(request_info)}"
        except Exception:
            log_message = f"Network Request: {str(request_info)} (JSON failed)"
        self.debug(log_message)

    def log_steamcmd(self, command, output):
        if not (self.debug_enabled and self.raw_steamcmd_logs):
            return
        cmd_str = " ".join(command) if isinstance(command, list) else str(command)
        self.debug(f"SteamCMD Command: {cmd_str}")
        if output and isinstance(output, str):
            max_chunk = 1000
            if len(output) > max_chunk:
                for i in range(0, len(output), max_chunk):
                    self.debug(f"SteamCMD Output (Chunk {i // max_chunk + 1}): {output[i:i + max_chunk]}")
            else:
                self.debug(f"SteamCMD Output: {output}")

        if self.app_log_signal and self.verbose_output:
            self.app_log_signal.emit(f"[SteamCMD] Cmd: {cmd_str}")
            if output and isinstance(output, str):
                preview = output[:200] + ('...' if len(output) > 200 else '')
                self.app_log_signal.emit(f"[SteamCMD] Out: {preview}")

    def log_steamcmd_line(self, line):
        if self.debug_enabled and self.raw_steamcmd_logs:
            self.debug(f"SteamCMD Line: {line.strip()}")

    def save_crash_report(self, exc_type, exc_value, exc_traceback):
        if not (self.debug_enabled and self.save_crashes):
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        crash_file = os.path.join(self.crash_dir, f'crash_{timestamp}.txt')
        try:
            with open(crash_file, 'w', encoding='utf-8') as f:
                f.write(f"--- Crash Report --- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                f.write(f"Exception Type: {exc_type.__name__}\n")
                f.write(f"Exception Value: {exc_value}\n\n")
                f.write("--- Traceback ---\n")
                traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
                f.write("\n--- System Information ---\n")
                f.write(f"Platform: {sys.platform}\n")
                f.write(f"Python Version: {sys.version.split()[0]}\n")
            self.critical(f"Unhandled exception occurred. Crash report saved to: {crash_file}")
        except Exception as e:
            self.error(f"Failed to save crash report: {e}", exc_info=True)

    def register_log_viewer(self, log_viewer_instance):
        self.log_viewer = log_viewer_instance
        self.debug("Log viewer window connected.")
        if self.current_log_file and hasattr(log_viewer_instance, 'load_log_file'):
            pass

    def unregister_log_viewer(self):
        if self.log_viewer:
            self.debug("Log viewer window disconnected.")
            self.log_viewer = None

def debug_network_request(method="GET"):
    import functools
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                debug_manager = DebugManager.instance()
                do_debug = debug_manager.debug_enabled
            except ValueError:
                debug_manager = None
                do_debug = False

            if not do_debug:
                return func(*args, **kwargs)

            url = kwargs.get('url', 'N/A')
            if url == 'N/A' and args:
                url = args[0] if isinstance(args[0], str) else 'N/A'
            params = kwargs.get('params')
            headers = kwargs.get('headers')
            data = kwargs.get('data')

            debug_manager.debug(f"Making {method} request to {url}...")
            start_time = time.perf_counter()
            try:
                response = func(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                debug_manager.log_network_request(
                    method=method, url=url, params=params,
                    headers=headers, data=data, response=response
                )
                debug_manager.debug(f"Request to {url} completed in {elapsed:.3f}s")
                return response
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                debug_manager.log_network_request(
                    method=method, url=url, params=params,
                    headers=headers, data=data, error=e
                )
                debug_manager.error(f"Request to {url} failed after {elapsed:.3f}s: {e}", exc_info=True)
                raise
        return wrapper
    return decorator


def _global_exception_handler(exc_type, exc_value, exc_traceback):
    try:
        debug_manager = DebugManager.instance()
        if debug_manager:
            debug_manager.save_crash_report(exc_type, exc_value, exc_traceback)
    except Exception as e:
        print(f"Error in global exception handler: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    finally:
        _original_excepthook(exc_type, exc_value, exc_traceback)


_original_excepthook = sys.excepthook

def install_global_exception_hook():
    sys.excepthook = _global_exception_handler
    print("Installed global exception handler.")
