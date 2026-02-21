import ctypes
import os
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from io import BytesIO
from pathlib import Path

import requests

from web_backend import AppIDScraper, StreamlineWebBackend

current_version = "1.3.1"

DEFAULT_SETTINGS = {
    "current_theme": "Dark",
    "modal_text_color": "",
    "logo_style": "Light",
    "batch_size": 20,
    "show_logs": True,
    "show_provider": True,
    "show_queue_entire_workshop": True,
    "keep_downloaded_in_queue": False,
    "folder_naming_format": "id",
    "auto_detect_urls": False,
    "auto_add_to_queue": False,
    "delete_downloads_on_cancel": False,
    "steamcmd_existing_mod_behavior": "Only Redownload if Updated",
    "download_button": True,
    "show_searchbar": True,
    "show_commands_button": True,
    "show_export_import_buttons": True,
    "show_sort_indicator": True,
    "show_row_numbers": False,
    "header_locked": True,
    "steam_accounts": [],
    "active_account": "Anonymous",
    "queue_tree_default_widths": [115, 90, 230, 100, 95],
    "queue_tree_column_widths": None,
    "queue_tree_column_hidden": None,
    "reset_provider_on_startup": False,
    "download_provider": "Default",
    "log_category_filter": "all",
    "reset_window_size_on_startup": True,
    "show_tutorial_on_startup": True,
    "tutorial_shown": False,
}

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def _get_runtime_executable_path():
    argv0 = str(sys.argv[0] if sys.argv else "").strip()
    argv0_lower = argv0.lower()
    if argv0:
        candidate = os.path.abspath(argv0)
        if candidate.lower().endswith(".exe") and os.path.isfile(candidate):
            return candidate

    running_script = argv0_lower.endswith(".py") or argv0_lower.endswith(".pyw")
    if not running_script:
        exe_path = str(getattr(sys, "executable", "")).strip()
        if exe_path and exe_path.lower().endswith(".exe") and os.path.isfile(exe_path):
            return os.path.abspath(exe_path)

    is_frozen = bool(getattr(sys, "frozen", False)) or hasattr(sys, "_MEIPASS") or ("__compiled__" in globals())
    if is_frozen:
        exe_path = str(getattr(sys, "executable", "")).strip()
        if exe_path and exe_path.lower().endswith(".exe") and os.path.isfile(exe_path):
            return os.path.abspath(exe_path)
    return ""


def runtime_base_path():
    exe_path = _get_runtime_executable_path()
    if exe_path:
        return os.path.dirname(os.path.realpath(exe_path))
    return os.path.dirname(os.path.abspath(__file__))


def runtime_path(relative_path=""):
    base_path = runtime_base_path()
    return os.path.join(base_path, relative_path) if relative_path else base_path


class WebMainGuiApi:
    def __init__(self, script_path, files_dir):
        self.script_path = script_path
        self.files_dir = files_dir
        self.main_url = ""
        self.backend = StreamlineWebBackend(
            script_path=script_path,
            files_dir=files_dir,
            default_settings=DEFAULT_SETTINGS,
            app_version=current_version,
        )
        self.setup_manager = StartupSetupManager(script_path=script_path, files_dir=files_dir)
        self.setup_manager.start()

    @staticmethod
    def _get_window():
        try:
            import webview
            if webview.windows:
                return webview.windows[0]
        except Exception:
            return None
        return None

    @staticmethod
    def _normalize_file_dialog_path(selection):
        if not selection:
            return None
        if isinstance(selection, (list, tuple)):
            if not selection:
                return None
            return str(selection[0])
        return str(selection)

    @staticmethod
    def _destroy_window_deferred(window, delay_sec=0.6):
        def _do_destroy():
            try:
                window.destroy()
            except Exception:
                pass

        timer = threading.Timer(max(0.0, float(delay_sec)), _do_destroy)
        timer.daemon = True
        timer.start()

    def _persist_window_size(self, window, use_js_viewport=True):
        if window is None:
            return {"success": False, "error": "Window is not ready."}

        reset_on_startup = bool(self.backend.config.get("reset_window_size_on_startup", True))
        if reset_on_startup:
            if "window_size" in self.backend.config:
                self.backend.config.pop("window_size", None)
                self.backend.save_config()
            return {"success": True, "saved": False, "reason": "reset_window_size_on_startup"}

        width = 0
        height = 0
        if use_js_viewport:
            try:
                # Save CSS viewport size first. This stays stable across DPI scaling.
                size = window.evaluate_js(
                    "({w: Math.round(window.innerWidth||0), h: Math.round(window.innerHeight||0)})"
                )
                width = int((size or {}).get("w") or 0)
                height = int((size or {}).get("h") or 0)
            except Exception:
                width = 0
                height = 0

        if width <= 0 or height <= 0:
            try:
                width = int(getattr(window, "width"))
                height = int(getattr(window, "height"))
            except Exception:
                width = 0
                height = 0

        if width <= 0 or height <= 0:
            return {"success": False, "error": "Could not determine window size."}

        width = max(656, width)
        height = max(740, height)
        next_size = {"width": int(width), "height": int(height)}
        current_size = self.backend.config.get("window_size")
        if current_size == next_size:
            return {"success": True, "saved": False, "unchanged": True, "window_size": next_size}

        self.backend.config["window_size"] = next_size
        self.backend.save_config(immediate=True)
        return {"success": True, "saved": True, "window_size": next_size}

    def get_bootstrap_data(self):
        return self.backend.get_bootstrap_data()

    def poll_events(self, last_event_id=0):
        return {"events": self.backend.poll_events(last_event_id)}

    def open_downloads_folder(self, mod_id=None):
        return self.backend.open_downloads_folder(mod_id)

    def get_preview_queue(self):
        return self.backend.get_preview_queue()

    def get_queue(self):
        return self.backend.get_queue()

    def get_queue_page(
        self,
        filter_name="All",
        search_query="",
        regex_enabled=False,
        case_sensitive=False,
        sort_key="",
        sort_direction="asc",
        offset=0,
        limit=200,
    ):
        return self.backend.get_queue_page(
            filter_name=filter_name,
            search_query=search_query,
            regex_enabled=regex_enabled,
            case_sensitive=case_sensitive,
            sort_key=sort_key,
            sort_direction=sort_direction,
            offset=offset,
            limit=limit,
        )

    def add_workshop_item(self, item_url, app_id="", provider="Default"):
        return self.backend.add_workshop_item(item_url, app_id, provider)

    def download_workshop_item_now(self, item_url, app_id="", provider="Default"):
        result = self.backend.add_preview_queue_item(item_url, app_id, provider)
        if not result.get("success"):
            return result
        return self.backend.start_download()

    def start_download(self):
        return self.backend.start_download()

    def cancel_download(self):
        return self.backend.cancel_download()

    def remove_mods(self, mod_ids):
        return self.backend.remove_mods(mod_ids)

    def move_mods(self, mod_ids, direction):
        return self.backend.move_mods(mod_ids, direction)

    def change_provider_for_mods(self, mod_ids, provider):
        return self.backend.change_provider_for_mods(mod_ids, provider)

    def set_global_provider(self, provider, override_existing=False):
        return self.backend.set_global_provider(provider, override_existing)

    def override_appid(self, mod_ids, app_id_input):
        return self.backend.override_appid(mod_ids, app_id_input)

    def reset_status(self, mod_ids):
        return self.backend.reset_status(mod_ids)

    def import_queue(self, file_path):
        return self.backend.import_queue(file_path)

    def export_queue(self, file_path):
        return self.backend.export_queue(file_path)

    def browse_import_queue_file(self):
        window = self._get_window()
        if window is None:
            return {"success": False, "error": "Window is not ready."}
        try:
            import webview
            selected = window.create_file_dialog(
                dialog_type=webview.FileDialog.OPEN,
                allow_multiple=False,
                file_types=("Text files (*.txt)", "All files (*.*)"),
            )
            file_path = self._normalize_file_dialog_path(selected)
            if not file_path:
                return {"success": False, "cancelled": True}
            return {"success": True, "path": file_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def browse_export_queue_file(self):
        window = self._get_window()
        if window is None:
            return {"success": False, "error": "Window is not ready."}
        try:
            import webview
            selected = window.create_file_dialog(
                dialog_type=webview.FileDialog.SAVE,
                save_filename="queue_export.txt",
                file_types=("Text files (*.txt)", "All files (*.*)"),
            )
            file_path = self._normalize_file_dialog_path(selected)
            if not file_path:
                return {"success": False, "cancelled": True}
            return {"success": True, "path": file_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_settings(self):
        return self.backend.get_settings()

    def update_settings(self, settings):
        return self.backend.update_settings(settings)

    def get_accounts(self):
        return self.backend.get_accounts()

    def add_account(self, username, steamid64=""):
        return self.backend.add_account(username, steamid64)

    def remove_account(self, username):
        return self.backend.remove_account(username)

    def purge_accounts(self):
        return self.backend.purge_accounts()

    def reorder_accounts(self, usernames):
        return self.backend.reorder_accounts(usernames)

    def set_active_account(self, username):
        return self.backend.set_active_account(username)

    def launch_steamcmd_login(self, username, password=""):
        return self.backend.launch_steamcmd_login(username, password)

    def poll_steamcmd_login_session(self):
        return self.backend.poll_steamcmd_login_session()

    def send_steamcmd_login_input(self, text):
        return self.backend.send_steamcmd_login_input(text)

    def close_steamcmd_login_session(self, force=True):
        return self.backend.close_steamcmd_login_session(force)

    def get_appids_info(self):
        return self.backend.get_appids_info()

    def update_appids(self, selected_types, headless=True):
        return self.backend.update_appids(selected_types, headless)

    def clear_logs(self):
        return self.backend.clear_logs()

    def launch_documentation(self):
        return self.backend.launch_documentation()

    def launch_report_issue(self):
        return self.backend.launch_report_issue()

    def launch_repository(self):
        return self.backend.launch_repository()

    def minimize_window(self):
        window = self._get_window()
        if window is None:
            return {"success": False, "error": "Window is not ready."}
        try:
            window.minimize()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def begin_window_resize(self, mode="southeast"):
        window = self._get_window()
        if window is None:
            return {"success": False, "error": "Window is not ready."}
        if os.name != "nt":
            return {"success": False, "error": "Custom resize is only supported on Windows."}

        normalized_mode = str(mode or "southeast").strip().lower()
        if normalized_mode not in {"east", "west", "south", "southeast", "southwest"}:
            normalized_mode = "southeast"

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        def get_cursor_pos():
            user32 = ctypes.windll.user32
            pt = POINT()
            if not user32.GetCursorPos(ctypes.byref(pt)):
                return None
            return int(pt.x), int(pt.y)

        try:
            user32 = ctypes.windll.user32
            start_cursor = get_cursor_pos()
            if not start_cursor:
                return {"success": False, "error": "Could not read cursor position."}

            start_width = max(656, int(getattr(window, "width", 0) or 0))
            start_height = max(740, int(getattr(window, "height", 0) or 0))
            start_window_y = int(getattr(window, "y", 0) or 0)
            if start_width <= 0 or start_height <= 0:
                return {"success": False, "error": "Could not determine window size."}

            start_x, start_y = start_cursor
            last_width = start_width
            last_height = start_height
            start_window_x = int(getattr(window, "x", 0) or 0)
            last_window_x = start_window_x
            screen_width = max(656, int(user32.GetSystemMetrics(0)))
            screen_height = max(740, int(user32.GetSystemMetrics(1)))
            max_east_width = max(656, screen_width - start_window_x)
            max_south_height = max(740, screen_height - start_window_y)
            right_edge = start_window_x + start_width
            max_west_width = max(656, right_edge)
            first_sample = True

            while user32.GetAsyncKeyState(0x01) & 0x8000:
                cursor = get_cursor_pos()
                if not cursor:
                    break

                dx = int(cursor[0] - start_x)
                dy = int(cursor[1] - start_y)

                # Ignore an initial coordinate spike from async call startup.
                if first_sample:
                    first_sample = False
                    if abs(dx) > 80 or abs(dy) > 80:
                        start_x = int(cursor[0])
                        start_y = int(cursor[1])
                        continue

                target_width = start_width
                target_height = start_height
                target_window_x = start_window_x

                if normalized_mode in {"east", "southeast"}:
                    target_width = max(656, min(max_east_width, start_width + dx))
                elif normalized_mode in {"west", "southwest"}:
                    target_width = max(656, min(max_west_width, start_width - dx))
                    target_window_x = max(0, right_edge - target_width)

                if normalized_mode in {"south", "southeast", "southwest"}:
                    target_height = max(740, min(max_south_height, start_height + dy))

                size_changed = (target_width != last_width) or (target_height != last_height)
                pos_changed = target_window_x != last_window_x

                if normalized_mode in {"west", "southwest"}:
                    if pos_changed:
                        window.move(int(target_window_x), int(start_window_y))
                        last_window_x = int(target_window_x)
                    if size_changed:
                        window.resize(int(target_width), int(target_height))
                        last_width = int(target_width)
                        last_height = int(target_height)
                elif size_changed:
                    window.resize(int(target_width), int(target_height))
                    last_width = int(target_width)
                    last_height = int(target_height)

                time.sleep(0.01)

            self._persist_window_size(window)
            return {"success": True, "width": last_width, "height": last_height}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close_window(self):
        window = self._get_window()
        if window is None:
            return {"success": False, "error": "Window is not ready."}
        try:
            # Do not evaluate JS during shutdown; WebView may already be disposing.
            self._persist_window_size(window, use_js_viewport=False)
            # Defer destruction until after this JS->Python bridge call returns.
            # Otherwise pywebview may try to evaluate the callback on a disposed WebView2.
            self._destroy_window_deferred(window)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def setup_get_state(self):
        return self.setup_manager.get_state()

    def setup_cancel(self):
        return self.setup_manager.cancel_setup()

    def setup_retry(self):
        started = self.setup_manager.start(force=True)
        return {"success": bool(started)}

    def setup_open_anyway(self):
        return self.setup_manager.open_anyway()

    def setup_continue_to_main(self):
        state = self.setup_manager.get_state()
        if not state.get("done") or not state.get("success"):
            return {"success": False, "error": "Setup is not complete."}

        if self.main_url:
            try:
                self.backend._load_app_ids()
            except Exception:
                pass
            return {"success": True, "redirect_url": self.main_url}
        return {"success": False, "error": "Main UI URL is not set."}

    def setup_exit(self):
        return self.close_window()


class StartupSetupManager:
    def __init__(self, script_path: str, files_dir: str):
        self.script_path = script_path
        self.script_dir = os.path.dirname(script_path)
        self.files_dir = files_dir
        self.steamcmd_dir = os.path.join(self.files_dir, "steamcmd")
        self.appids_path = os.path.join(self.files_dir, "AppIDs.txt")
        self.scraper = AppIDScraper(self.files_dir)

        self._lock = threading.Lock()
        self._cancel_event = threading.Event()
        self._thread = None
        self._state = {
            "running": False,
            "done": False,
            "success": False,
            "canceled": False,
            "progress": 0,
            "status": "Preparing setup...",
            "error": "",
            "can_open_anyway": False,
        }

    def _set_state(self, **kwargs):
        with self._lock:
            self._state.update(kwargs)

    def get_state(self):
        with self._lock:
            return dict(self._state)

    def start(self, force=False):
        with self._lock:
            if self._state.get("running"):
                return False
            if self._thread and self._thread.is_alive() and not force:
                return False

            self._cancel_event.clear()
            self._state.update({
                "running": True,
                "done": False,
                "success": False,
                "canceled": False,
                "progress": 0,
                "status": "Preparing setup...",
                "error": "",
                "can_open_anyway": False,
            })
            self._thread = threading.Thread(target=self._run_setup, name="streamline-startup-setup", daemon=True)
            self._thread.start()
            return True

    def cancel_setup(self):
        self._cancel_event.set()
        self._set_state(status="Canceling setup...", canceled=True)
        return {"success": True}

    def open_anyway(self):
        with self._lock:
            if not self._state.get("done"):
                return {"success": False, "error": "Setup is still running."}
            self._state["success"] = True
            self._state["error"] = ""
            self._state["status"] = "Continuing without full setup."
            self._state["can_open_anyway"] = False
        return {"success": True}

    def _check_steamcmd_installed(self):
        steamcmd_executable = os.path.join(self.steamcmd_dir, "steamcmd.exe")
        essential_files = [
            os.path.join(self.steamcmd_dir, "steam.dll"),
            os.path.join(self.steamcmd_dir, "steamclient.dll"),
        ]
        return os.path.isfile(steamcmd_executable) and all(os.path.isfile(path) for path in essential_files)

    def _download_steamcmd(self):
        os.makedirs(self.steamcmd_dir, exist_ok=True)
        steamcmd_zip_url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
        response = requests.get(steamcmd_zip_url, stream=True, timeout=60)
        response.raise_for_status()
        with zipfile.ZipFile(BytesIO(response.content)) as zip_ref:
            zip_ref.extractall(self.steamcmd_dir)

    def _initialize_steamcmd(self):
        steamcmd_executable = os.path.join(self.steamcmd_dir, "steamcmd.exe")
        if not os.path.isfile(steamcmd_executable):
            raise FileNotFoundError("steamcmd.exe was not found after extraction.")

        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        steamcmd_process = subprocess.Popen(
            [steamcmd_executable, "+quit"],
            cwd=self.steamcmd_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1,
            shell=(os.name == "nt"),
            creationflags=creationflags,
        )

        if steamcmd_process.stdout is not None:
            for _line in steamcmd_process.stdout:
                if self._cancel_event.is_set():
                    steamcmd_process.terminate()
                    break
            steamcmd_process.stdout.close()
        steamcmd_process.wait()

        # SteamCMD can return non-zero on first-run/update while still completing setup.
        # Match original app behavior: verify required files after run instead of hard-failing on exit code.
        essential_files = [
            os.path.join(self.steamcmd_dir, "steam.dll"),
            os.path.join(self.steamcmd_dir, "steamclient.dll"),
        ]
        if not all(os.path.isfile(path) for path in essential_files):
            raise RuntimeError(
                f"SteamCMD initialization failed (exit code {steamcmd_process.returncode}). "
                "Required SteamCMD files were not created."
            )

    def _download_appids(self):
        entries = self.scraper.scrape_steamdb(["Game"])
        if not entries:
            raise RuntimeError("SteamDB scraping returned zero AppIDs.")
        with open(self.appids_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(entries))

    def _cleanup_files(self):
        if os.path.isdir(self.steamcmd_dir):
            try:
                shutil.rmtree(self.steamcmd_dir)
            except Exception:
                pass
        if os.path.isfile(self.appids_path):
            try:
                os.remove(self.appids_path)
            except Exception:
                pass

    def _finish_canceled(self):
        self._cleanup_files()
        self._set_state(
            running=False,
            done=True,
            success=False,
            canceled=True,
            progress=0,
            status="Setup canceled.",
            error="",
            can_open_anyway=False,
        )

    def _run_setup(self):
        try:
            self._set_state(progress=0, status="Checking SteamCMD installation...")
            if self._cancel_event.is_set():
                self._finish_canceled()
                return

            steamcmd_present = self._check_steamcmd_installed()
            if not steamcmd_present:
                self._set_state(progress=10, status="Downloading SteamCMD...")
                self._download_steamcmd()
                if self._cancel_event.is_set():
                    self._finish_canceled()
                    return

                self._set_state(progress=30, status="Initializing SteamCMD...")
                self._initialize_steamcmd()
                if self._cancel_event.is_set():
                    self._finish_canceled()
                    return

            self._set_state(progress=50, status="SteamCMD setup complete.")
            if self._cancel_event.is_set():
                self._finish_canceled()
                return

            self._set_state(progress=60, status="Checking AppIDs database...")
            if not os.path.isfile(self.appids_path):
                self._set_state(progress=70, status="Scraping SteamDB for AppIDs...")
                self._download_appids()
                if self._cancel_event.is_set():
                    self._finish_canceled()
                    return
            else:
                self._set_state(progress=90, status="AppIDs database already exists.")

            self._set_state(
                running=False,
                done=True,
                success=True,
                canceled=False,
                progress=100,
                status="Setup complete!",
                error="",
                can_open_anyway=False,
            )
        except Exception as e:
            self._set_state(
                running=False,
                done=True,
                success=False,
                canceled=False,
                progress=0,
                status="Setup failed.",
                error=f"{e}",
                can_open_anyway=True,
            )


def run_pywebview_main_gui():
    try:
        import webview
    except ImportError:
        print("pywebview is not installed. Install dependencies from Files/requirements.txt.")
        return 1

    script_path = _get_runtime_executable_path() or os.path.abspath(__file__)
    files_dir = runtime_path("Files")
    api = WebMainGuiApi(script_path=script_path, files_dir=files_dir)

    runtime_webui_index = runtime_path(os.path.join("Files", "webui", "index.html"))
    runtime_setup_index = runtime_path(os.path.join("Files", "webui", "setup.html"))
    bundled_webui_index = resource_path(os.path.join("Files", "webui", "index.html"))
    bundled_setup_index = resource_path(os.path.join("Files", "webui", "setup.html"))

    webui_index = runtime_webui_index if os.path.isfile(runtime_webui_index) else bundled_webui_index
    setup_index = runtime_setup_index if os.path.isfile(runtime_setup_index) else bundled_setup_index
    api.main_url = Path(webui_index).resolve().as_uri() if os.path.isfile(webui_index) else ""

    default_window_width = 695
    default_window_height = 775
    min_window_width = 656
    min_window_height = 740

    screen_width = None
    screen_height = None
    max_window_width = None
    max_window_height = None
    if os.name == "nt":
        try:
            user32 = ctypes.windll.user32
            screen_width = int(user32.GetSystemMetrics(0))
            screen_height = int(user32.GetSystemMetrics(1))
            max_window_width = max(min_window_width, screen_width)
            max_window_height = max(min_window_height, screen_height)
        except Exception:
            screen_width = None
            screen_height = None
            max_window_width = None
            max_window_height = None

    window_width = default_window_width
    window_height = default_window_height

    try:
        settings = api.backend.get_settings()
    except Exception:
        settings = {}

    if not settings.get("reset_window_size_on_startup", True):
        saved_size = settings.get("window_size") or {}
        try:
            saved_width = int(saved_size.get("width", 0))
            saved_height = int(saved_size.get("height", 0))
            if saved_width > 0 and saved_height > 0:
                window_width = max(min_window_width, saved_width)
                window_height = max(min_window_height, saved_height)
                if max_window_width is not None:
                    window_width = min(max_window_width, window_width)
                if max_window_height is not None:
                    window_height = min(max_window_height, window_height)
        except Exception:
            window_width = default_window_width
            window_height = default_window_height

    window_x = None
    window_y = None
    if os.name == "nt":
        try:
            if screen_width is None or screen_height is None:
                user32 = ctypes.windll.user32
                screen_width = int(user32.GetSystemMetrics(0))
                screen_height = int(user32.GetSystemMetrics(1))
            window_x = max(0, (int(screen_width) - window_width) // 2)
            window_y = max(0, (int(screen_height) - window_height) // 2)
        except Exception:
            window_x = None
            window_y = None

    create_window_kwargs = {
        "title": f"Streamline v{current_version}",
        "js_api": api,
        "width": window_width,
        "height": window_height,
        "min_size": (min_window_width, min_window_height),
        "resizable": True,
        "background_color": "#121212",
        "frameless": True,
        "easy_drag": False,
    }
    if window_x is not None and window_y is not None:
        create_window_kwargs["x"] = window_x
        create_window_kwargs["y"] = window_y

    if os.path.isfile(setup_index):
        create_window_kwargs["url"] = Path(setup_index).resolve().as_uri()
    elif os.path.isfile(webui_index):
        create_window_kwargs["url"] = Path(webui_index).resolve().as_uri()
    else:
        create_window_kwargs["html"] = "<h2>Streamline</h2><p>Web UI files were not found.</p>"

    webview.create_window(**create_window_kwargs)
    webview.start(debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(run_pywebview_main_gui())
