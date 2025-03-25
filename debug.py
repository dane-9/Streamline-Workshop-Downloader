import os
import sys
import time
import json
import traceback
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox, QGroupBox, QFormLayout,
    QLabel, QHBoxLayout, QPushButton, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QObject


class DebugManager(QObject):
    # Manages all debug-related functionality.
    log_signal = Signal(str)
    _instance = None

    @classmethod
    def instance(cls, files_dir=None, log_signal=None):
        if cls._instance is None:
            if files_dir is None:
                raise ValueError("files_dir must be provided for initial instantiation")
            cls._instance = cls(files_dir, log_signal)
        return cls._instance

    def __init__(self, files_dir, log_signal=None):
        super().__init__()
        self.files_dir = files_dir
        self.debug_dir = os.path.join(files_dir, 'Debug')
        self.logs_dir = os.path.join(self.debug_dir, 'Logs')
        self.crash_dir = os.path.join(self.debug_dir, 'Crashes')
        self.app_log_signal = log_signal
        os.makedirs(self.debug_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.crash_dir, exist_ok=True)
        self.setup_logger()
        self.debug_enabled = False
        self.write_to_file = False
        self.verbose_output = False
        self.save_crashes = False
        self.raw_steamcmd_logs = False
        self.current_log_file = None

    def setup_logger(self):
        self.logger = logging.getLogger('streamline_debug')
        self.logger.setLevel(logging.DEBUG)
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def enable_file_logging(self):
        if hasattr(self, 'file_handler') and self.file_handler:
            return
        self.current_log_file = os.path.join(
            self.logs_dir, f'debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
        self.file_handler = RotatingFileHandler(
            self.current_log_file,
            maxBytes=10*1024*1024,
            backupCount=5
        )
        self.file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        self.file_handler.setFormatter(file_formatter)
        self.logger.addHandler(self.file_handler)
        self.log("Debug file logging enabled to " + self.current_log_file)

    def disable_file_logging(self):
        if hasattr(self, 'file_handler') and self.file_handler:
            self.logger.removeHandler(self.file_handler)
            self.file_handler = None
            self.current_log_file = None

    def update_settings(self, settings):
        old_write_to_file = self.write_to_file
        old_debug_enabled = self.debug_enabled
        self.debug_enabled = settings.get('debug_enabled', False)
        self.write_to_file = settings.get('write_debug_to_file', False)
        self.verbose_output = settings.get('verbose_console_output', False)
        self.save_crashes = settings.get('save_crash_reports', False)
        self.raw_steamcmd_logs = settings.get('output_raw_steamcmd_logs', False)
        if not old_debug_enabled and self.debug_enabled:
            self.log("Debug mode enabled")
        if old_debug_enabled and not self.debug_enabled:
            self.log("Debug mode disabled")
        if self.debug_enabled and self.write_to_file and (not old_write_to_file or not old_debug_enabled):
            self.enable_file_logging()
        elif (not self.debug_enabled or not self.write_to_file) and old_write_to_file:
            self.disable_file_logging()
        if self.debug_enabled:
            self.debug(f"Debug settings updated: {settings}")

    def log(self, message):
        if self.app_log_signal:
            self.app_log_signal.emit(message)
        if self.debug_enabled:
            self.logger.info(message)

    def debug(self, message):
        if self.debug_enabled:
            self.logger.debug(message)
            if self.verbose_output and self.app_log_signal:
                self.app_log_signal.emit(f"[DEBUG] {message}")

    def info(self, message):
        if self.debug_enabled:
            self.logger.info(message)
            if self.verbose_output and self.app_log_signal:
                self.app_log_signal.emit(f"[INFO] {message}")

    def warning(self, message):
        if self.debug_enabled:
            self.logger.warning(message)
            if self.app_log_signal:
                self.app_log_signal.emit(f"[WARNING] {message}")

    def error(self, message):
        if self.debug_enabled:
            self.logger.error(message)
            if self.app_log_signal:
                self.app_log_signal.emit(f"[ERROR] {message}")

    def critical(self, message):
        if self.debug_enabled:
            self.logger.critical(message)
            if self.app_log_signal:
                self.app_log_signal.emit(f"[CRITICAL] {message}")

    def exception(self, message):
        if self.debug_enabled:
            self.logger.exception(message)
            if self.app_log_signal:
                exc_info = sys.exc_info()
                self.app_log_signal.emit(f"[EXCEPTION] {message}")
                if exc_info[0]:
                    tb_text = ''.join(traceback.format_exception(*exc_info))
                    self.app_log_signal.emit(f"Stack trace: {tb_text}")

    def log_network_request(self, method, url, params=None, headers=None, data=None, response=None, error=None):
        if not self.debug_enabled:
            return
        request_info = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'method': method,
            'url': url,
        }
        if params:
            request_info['params'] = str(params)
        if headers:
            safe_headers = headers.copy() if isinstance(headers, dict) else headers
            if isinstance(safe_headers, dict) and 'Authorization' in safe_headers:
                safe_headers['Authorization'] = '****'
            request_info['headers'] = str(safe_headers)
        if data:
            request_info['data'] = str(data)
        if response:
            try:
                if hasattr(response, 'status_code'):
                    request_info['status_code'] = response.status_code
                elif hasattr(response, 'status'):
                    request_info['status_code'] = response.status
                content_preview = None
                if hasattr(response, 'text'):
                    try:
                        if callable(response.text):
                            content_preview = str(response.text())[:500]
                        else:
                            content_preview = str(response.text)[:500]
                    except:
                        pass
                elif hasattr(response, 'read'):
                    try:
                        request_info['response_type'] = 'aiohttp.ClientResponse (content not extracted)'
                    except:
                        pass
                elif hasattr(response, 'content'):
                    try:
                        content_preview = str(response.content)[:500]
                    except:
                        pass
                if content_preview:
                    if len(content_preview) >= 500:
                        content_preview += '...'
                    request_info['response_preview'] = content_preview
                if hasattr(response, 'headers'):
                    headers_dict = {}
                    for key, value in response.headers.items():
                        headers_dict[key] = value
                    request_info['response_headers'] = str(headers_dict)
                request_info['response_class'] = response.__class__.__name__
            except Exception as e:
                request_info['response'] = f'Could not extract response details: {str(e)}'
        if error:
            request_info['error'] = str(error)
        try:
            log_message = f"Network Request: {json.dumps(request_info, indent=2)}"
        except Exception as json_err:
            log_message = f"Network Request: {str(request_info)} (JSON serialization failed: {str(json_err)})"
        self.debug(log_message)

    def log_steamcmd(self, command, output):
        if not self.debug_enabled:
            return
        if self.raw_steamcmd_logs:
            if isinstance(command, list):
                command = " ".join(command)
            self.debug(f"SteamCMD Command: {command}")
            if output and isinstance(output, str):
                if len(output) > 1000:
                    chunks = [output[i:i+1000] for i in range(0, len(output), 1000)]
                    for i, chunk in enumerate(chunks):
                        self.debug(f"SteamCMD Output [{i+1}/{len(chunks)}]: {chunk}")
                else:
                    self.debug(f"SteamCMD Output: {output}")
            if self.app_log_signal and self.verbose_output:
                self.app_log_signal.emit(f"[SteamCMD] Command: {command}")
                if output and isinstance(output, str):
                    self.app_log_signal.emit(f"[SteamCMD] Output: {output[:200]}...")

    def log_steamcmd_line(self, line):
        if self.debug_enabled and self.raw_steamcmd_logs:
            self.debug(f"SteamCMD: {line.strip()}")

    def save_crash_report(self, exception_type, exception_value, exception_traceback):
        if not (self.debug_enabled and self.save_crashes):
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        crash_file = os.path.join(self.crash_dir, f'crash_{timestamp}.txt')
        with open(crash_file, 'w', encoding='utf-8') as f:
            f.write(f"Crash Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Exception Type: {exception_type.__name__}\n")
            f.write(f"Exception Value: {exception_value}\n")
            f.write("Traceback:\n")
            traceback.print_tb(exception_traceback, file=f)
            f.write("\nSystem Information:\n")
            f.write(f"Platform: {sys.platform}\n")
            f.write(f"Python Version: {sys.version}\n")
        self.critical(f"Crash report saved to {crash_file}")


def debug_network_request(method="GET"):
    # Performs network I/O with debug logs of request and response details.
    def decorator(func):
        def wrapper(*args, **kwargs):
            debug_manager = DebugManager.instance()
            if not debug_manager.debug_enabled:
                return func(*args, **kwargs)
            url = kwargs.get('url', None)
            if not url and len(args) > 0:
                url = args[0]
            params = kwargs.get('params', None)
            headers = kwargs.get('headers', None)
            data = kwargs.get('data', None)
            debug_manager.debug(f"Making {method} request to {url}")
            try:
                start_time = time.time()
                response = func(*args, **kwargs)
                elapsed = time.time() - start_time
                debug_manager.log_network_request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    data=data,
                    response=response
                )
                debug_manager.debug(f"Network request completed in {elapsed:.2f}s")
                return response
            except Exception as e:
                debug_manager.log_network_request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    data=data,
                    error=e
                )
                debug_manager.error(f"Network request failed: {str(e)}")
                raise
        return wrapper
    return decorator


def global_exception_hook():
    # Global exception hook to capture any unhandled exceptions, allows DebugManager to save crash reports.
    def global_exception_hook(exception_type, exception_value, exception_traceback):
        debug_manager = DebugManager.instance()
        debug_manager.save_crash_report(exception_type, exception_value, exception_traceback)
        sys.__excepthook__(exception_type, exception_value, exception_traceback)
    sys.excepthook = global_exception_hook
