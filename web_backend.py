import json
import os
import platform
import re
import shutil
import subprocess
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
import ctypes

import requests
from lxml import html

try:
    from botasaurus.browser import browser, Driver
except Exception:
    browser = None
    Driver = None


if browser is not None:
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
        driver.wait_for_element("tr.app", wait=60)
        time.sleep(2)

        types_json = json.dumps(selected_types)
        entries = driver.run_js(
            f"""
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
            """
        )
        return entries if entries else []
else:
    def _scrape_steamdb_botasaurus(_data):
        raise RuntimeError("Botasaurus is not available in this environment.")

class SteamCmdConPTYSession:
    def __init__(self, steamcmd_exe: str, steamcmd_dir: str, username: str, cols: int = 120, rows: int = 40):
        self.steamcmd_exe = steamcmd_exe
        self.steamcmd_dir = steamcmd_dir
        self.username = username
        self.cols = cols
        self.rows = rows

        self._lock = threading.RLock()
        self._started = False
        self._closed = False
        self._output_chunks = []
        self._pending_output = []
        self._popen = None
        self._reader_thread = None

    def _append_output(self, text: str):
        with self._lock:
            if not text:
                return
            self._output_chunks.append(text)
            self._pending_output.append(text)
            if len(self._output_chunks) > 500:
                self._output_chunks = self._output_chunks[-250:]

    def _reader_loop(self):
        if not self._popen or not self._popen.stdout:
            return
        while True:
            try:
                chunk = self._popen.stdout.read(4096)
            except Exception:
                break
            if not chunk:
                break
            if isinstance(chunk, bytes):
                text = chunk.decode("utf-8", errors="ignore")
            else:
                text = str(chunk)
            if text:
                self._append_output(text)

    def start(self):
        if not os.path.isfile(self.steamcmd_exe):
            return False, "steamcmd.exe not found."

        try:
            creationflags = 0
            if platform.system().lower() == "windows":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            self._popen = subprocess.Popen(
                [self.steamcmd_exe, "+login", self.username],
                cwd=self.steamcmd_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                creationflags=creationflags,
            )
            self._started = True
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()
            return True, ""
        except Exception as e:
            self.close(force=True)
            return False, str(e)

    def is_running(self):
        return bool(self._popen and self._popen.poll() is None)

    def get_exit_code(self):
        if not self._popen:
            return None
        return self._popen.poll()

    def poll(self):
        with self._lock:
            output = "".join(self._pending_output)
            self._pending_output = []
            running = self.is_running()
            exit_code = None if running else self.get_exit_code()
            return {"running": running, "done": not running, "exit_code": exit_code, "output": output}

    def send(self, text: str):
        with self._lock:
            if not self._started or not self._popen or not self._popen.stdin:
                return {"success": False, "error": "SteamCMD session is not running."}
            payload = ((text or "") + "\r\n").encode("utf-8", errors="ignore")
            if not payload:
                return {"success": False, "error": "Input is empty."}
            try:
                self._popen.stdin.write(payload)
                self._popen.stdin.flush()
                return {"success": True, "written": len(payload)}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def close(self, force=False):
        with self._lock:
            if self._closed:
                return
            self._closed = True

            try:
                if self._started and self._popen and self.is_running():
                    if force:
                        self._popen.terminate()
                        try:
                            self._popen.wait(timeout=2.5)
                        except Exception:
                            self._popen.kill()
                    else:
                        self.send("quit")
                        try:
                            self._popen.wait(timeout=2.5)
                        except Exception:
                            self._popen.terminate()
            except Exception:
                pass

            try:
                if self._popen and self._popen.stdin:
                    self._popen.stdin.close()
            except Exception:
                pass
            try:
                if self._popen and self._popen.stdout:
                    self._popen.stdout.close()
            except Exception:
                pass
            self._popen = None
            self._reader_thread = None


class AppIDScraper:
    def __init__(self, files_dir):
        self.files_dir = files_dir

    def scrape_steamdb(self, selected_types):
        result = _scrape_steamdb_botasaurus({"selected_types": selected_types})

        # Botasaurus may wrap the return value in a list depending on execution mode.
        if isinstance(result, list) and len(result) == 1 and isinstance(result[0], list):
            entries = result[0]
        elif isinstance(result, list) and all(isinstance(e, str) for e in result):
            entries = result
        else:
            entries = result if result else []
        return entries


class StreamlineWebBackend:
    def __init__(self, script_path: str, files_dir: str, default_settings: dict, app_version: str):
        self.script_path = script_path
        self.script_dir = os.path.dirname(script_path)
        self.files_dir = files_dir
        self.default_settings = dict(default_settings)
        self.app_version = app_version

        self.config_path = os.path.join(self.files_dir, "config.json")
        self.downloads_root = os.path.join(self.script_dir, "Downloads")
        self.steamcmd_dir = os.path.join(self.files_dir, "steamcmd")
        self.steamcmd_exe = os.path.join(self.steamcmd_dir, "steamcmd.exe")
        self.steamcmd_download_path = os.path.join(self.downloads_root, "SteamCMD")
        self.steamwebapi_download_path = os.path.join(self.downloads_root, "SteamWebAPI")
        self.mod_log_path = os.path.join(self.files_dir, "Logs", "mod_downloads.json")

        os.makedirs(self.files_dir, exist_ok=True)
        os.makedirs(self.downloads_root, exist_ok=True)
        os.makedirs(self.steamcmd_download_path, exist_ok=True)
        os.makedirs(self.steamwebapi_download_path, exist_ok=True)
        os.makedirs(os.path.dirname(self.mod_log_path), exist_ok=True)

        self.state_lock = threading.RLock()
        self.events_lock = threading.Lock()
        self.events = []
        self.event_id = 0
        self.runtime_logs = []
        self._config_save_lock = threading.Lock()
        self._config_save_timer = None
        self._config_dirty = False
        self._config_save_delay_sec = 0.25
        self._mod_logs_lock = threading.Lock()
        self._mod_logs_cache = None
        self._mod_logs_save_timer = None
        self._mod_logs_dirty = False
        self._mod_logs_save_delay_sec = 0.5
        self._queue_revision = 0
        self._queue_query_cache = None
        self._queue_emit_lock = threading.Lock()
        self._queue_emit_timer = None
        self._queue_emit_interval_sec = 0.6
        self._queue_emit_last_at = 0.0
        self._queue_build_lock = threading.Lock()
        self._queue_build_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="queue-build")
        self._operation_lock = threading.Lock()
        self._operation_seq = 0
        self._active_download_operation_id = ""
        self._active_download_targets = set()
        self._active_download_provider_counts = {"SteamCMD": 0, "SteamWebAPI": 0}
        self._active_download_started_at = 0.0
        self._active_download_retry_by_mod = {}
        self._active_download_last_progress_at = 0.0
        self._active_download_last_progress_key = ""
        self._download_progress_log_interval_sec = 1.2
        self._download_max_retries = 3

        self._metadata_cache_path = os.path.join(self.files_dir, "cache_mod_metadata.json")
        self._metadata_cache_lock = threading.Lock()
        self._metadata_cache = {}
        self._metadata_cache_dirty = False
        self._metadata_cache_save_timer = None
        self._metadata_cache_save_delay_sec = 0.8
        self._metadata_cache_ttl_sec = 60 * 60 * 24 * 14
        self._hydration_lock = threading.Lock()
        self._hydration_inflight = set()
        self._hydration_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="mod-hydrate")

        self.config = self._load_config()
        self.app_ids = {}
        self._load_app_ids()
        self._load_mod_metadata_cache()

        self.download_queue = []
        self._queue_mod_ids = set()
        self._queue_mod_map = {}
        self.is_downloading = False
        self.canceled = False
        self.current_process = None
        self.successful_downloads_this_session = set()
        self.session_webapi_files = {}
        self.pending_login_context = None
        self.steamcmd_login_session = None
        self.steamcmd_login_lock = threading.RLock()
        self._remote_update_cache_lock = threading.Lock()
        self._remote_mod_update_cache = {}
        self._remote_mod_update_cache_ttl_sec = 600.0
        self.last_clipboard_text = ""
        self._last_clipboard_trigger = 0.0
        self._clipboard_last_seq = 0
        self._clipboard_stop_event = threading.Event()
        self._clipboard_monitor_thread = None
        if self.config.get("auto_detect_urls", False):
            self._start_clipboard_monitoring()

        self.log("Web backend initialized.", tone="good", source="system", action="initialized")

    def _emit_event(self, event_type: str, payload: dict):
        if event_type == "queue":
            with self.state_lock:
                self._queue_revision += 1
        with self.events_lock:
            self.event_id += 1
            self.events.append({
                "id": self.event_id,
                "type": event_type,
                "payload": payload,
                "timestamp": time.time()
            })
            if len(self.events) > 3000:
                self.events = self.events[-1500:]

    def _emit_queue_refresh_throttled(self, force=False):
        def _flush():
            with self._queue_emit_lock:
                self._queue_emit_timer = None
                self._queue_emit_last_at = time.time()
            self._emit_event("queue", {"action": "refresh"})

        with self._queue_emit_lock:
            now = time.time()
            elapsed = now - self._queue_emit_last_at
            if force or elapsed >= self._queue_emit_interval_sec:
                self._queue_emit_last_at = now
                timer = self._queue_emit_timer
                self._queue_emit_timer = None
                if timer is not None:
                    try:
                        timer.cancel()
                    except Exception:
                        pass
                immediate = True
            else:
                immediate = False
                if self._queue_emit_timer is None or not self._queue_emit_timer.is_alive():
                    delay = max(0.01, self._queue_emit_interval_sec - elapsed)
                    self._queue_emit_timer = threading.Timer(delay, _flush)
                    self._queue_emit_timer.daemon = True
                    self._queue_emit_timer.start()
        if immediate:
            self._emit_event("queue", {"action": "refresh"})

    def poll_events(self, last_event_id: int):
        with self.events_lock:
            return [evt for evt in self.events if evt["id"] > int(last_event_id)]

    def _next_operation_id(self, prefix: str = "op"):
        key = re.sub(r"[^a-z0-9]+", "-", str(prefix or "op").lower()).strip("-") or "op"
        with self._operation_lock:
            self._operation_seq += 1
            seq = self._operation_seq
        return f"{key}-{int(time.time() * 1000)}-{seq}"

    def log(
        self,
        message: str,
        tone: str = "info",
        source: str = "system",
        action: str = "",
        context=None,
        operation_id: str = "",
    ):
        text = str(message)
        level = str(tone or "info")
        src = str(source or "system").strip().lower() or "system"
        act = str(action or "").strip().lower()
        op_id = str(operation_id or "").strip()
        safe_context = context
        if safe_context is not None and not isinstance(safe_context, (dict, list, str, int, float, bool)):
            safe_context = str(safe_context)
        entry = {
            "timestamp": time.time(),
            "tone": level,
            "message": text,
            "source": src,
            "action": act,
            "operation_id": op_id,
            "context": safe_context,
        }
        with self.state_lock:
            self.runtime_logs.append(entry)
            if len(self.runtime_logs) > 5000:
                self.runtime_logs = self.runtime_logs[-2500:]
        payload = {
            "message": text,
            "tone": level,
            "source": src,
        }
        if act:
            payload["action"] = act
        if op_id:
            payload["operation_id"] = op_id
        if safe_context is not None:
            payload["context"] = safe_context
        self._emit_event("log", payload)

    def _load_config(self):
        config = dict(self.default_settings)
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    config.update(loaded)
            except Exception as e:
                self.log(f"Failed to load config.json: {e}", tone="bad", source="system", action="config_load_failed")
        return config

    def _write_config_snapshot(self, snapshot):
        try:
            temp_path = f"{self.config_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=4)
            os.replace(temp_path, self.config_path)
            return True
        except Exception as e:
            self.log(f"Failed to save config.json: {e}", tone="bad", source="system", action="config_save_failed")
            return False

    def _flush_pending_config_save(self):
        with self._config_save_lock:
            self._config_save_timer = None
            if not self._config_dirty:
                return True
            self._config_dirty = False
        with self.state_lock:
            snapshot = dict(self.config)
        return self._write_config_snapshot(snapshot)

    def save_config(self, immediate=False):
        if immediate:
            with self._config_save_lock:
                timer = self._config_save_timer
                self._config_save_timer = None
                self._config_dirty = False
            if timer is not None:
                try:
                    timer.cancel()
                except Exception:
                    pass
            with self.state_lock:
                snapshot = dict(self.config)
            return self._write_config_snapshot(snapshot)

        with self._config_save_lock:
            self._config_dirty = True
            if self._config_save_timer is not None and self._config_save_timer.is_alive():
                return True
            self._config_save_timer = threading.Timer(self._config_save_delay_sec, self._flush_pending_config_save)
            self._config_save_timer.daemon = True
            self._config_save_timer.start()
        return True

    def _load_app_ids(self):
        self.app_ids = {}
        app_ids_path = os.path.join(self.files_dir, "AppIDs.txt")
        if not os.path.isfile(app_ids_path):
            return

        try:
            with open(app_ids_path, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line or "," not in line:
                        continue
                    game_name, app_id = line.rsplit(",", 1)
                    self.app_ids[app_id.strip()] = game_name.strip()
        except Exception as e:
            self.log(f"Failed to load AppIDs.txt: {e}", tone="bad", source="system", action="appids_load_failed")

    def _rebuild_queue_indexes_locked(self):
        mod_ids = set()
        mod_map = {}
        deduped = []
        for mod in self.download_queue:
            mod_id = str(mod.get("mod_id", "")).strip()
            if not mod_id or mod_id in mod_ids:
                continue
            mod_ids.add(mod_id)
            mod_map[mod_id] = mod
            deduped.append(mod)
        self.download_queue = deduped
        self._queue_mod_ids = mod_ids
        self._queue_mod_map = mod_map

    def _mod_name_needs_hydration(self, mod_name: str, mod_id: str):
        normalized = str(mod_name or "").strip().lower()
        if not normalized:
            return True
        if normalized in {"unknown title", "loading...", "untitled mod"}:
            return True
        if normalized == f"mod {str(mod_id).strip().lower()}":
            return True
        return False

    def _normalize_cached_mod_metadata(self, mod_id: str, payload):
        if not isinstance(payload, dict):
            return None
        safe_mod_id = str(mod_id or "").strip()
        if not safe_mod_id:
            return None
        mod_name = str(payload.get("mod_name", "")).strip()
        app_id_raw = payload.get("app_id")
        app_id = str(app_id_raw).strip() if app_id_raw else None
        game_name = str(payload.get("game_name", "")).strip() or "Unknown Game"
        ts_raw = payload.get("ts", payload.get("updated_at", 0))
        try:
            ts = float(ts_raw)
        except Exception:
            ts = 0.0
        if not mod_name and not app_id:
            return None
        return {
            "mod_id": safe_mod_id,
            "mod_name": mod_name or f"Mod {safe_mod_id}",
            "app_id": app_id,
            "game_name": game_name,
            "ts": ts,
        }

    def _load_mod_metadata_cache(self):
        loaded = {}
        if os.path.isfile(self._metadata_cache_path):
            try:
                with open(self._metadata_cache_path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                if isinstance(data, dict):
                    for mod_id, payload in data.items():
                        normalized = self._normalize_cached_mod_metadata(mod_id, payload)
                        if normalized:
                            loaded[str(mod_id)] = normalized
            except Exception as e:
                self.log(
                    f"Failed to load metadata cache: {e}",
                    tone="bad",
                    source="system",
                    action="metadata_cache_load_failed",
                )
        with self._metadata_cache_lock:
            self._metadata_cache = loaded
            self._metadata_cache_dirty = False
            self._metadata_cache_save_timer = None

    def _flush_metadata_cache_save(self):
        with self._metadata_cache_lock:
            self._metadata_cache_save_timer = None
            if not self._metadata_cache_dirty:
                return True
            self._metadata_cache_dirty = False
            snapshot = dict(self._metadata_cache)
        try:
            temp_path = f"{self._metadata_cache_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(snapshot, file, ensure_ascii=False)
            os.replace(temp_path, self._metadata_cache_path)
            return True
        except Exception as e:
            self.log(
                f"Failed to save metadata cache: {e}",
                tone="bad",
                source="system",
                action="metadata_cache_save_failed",
            )
            return False

    def _schedule_metadata_cache_save(self):
        with self._metadata_cache_lock:
            self._metadata_cache_dirty = True
            if self._metadata_cache_save_timer is not None and self._metadata_cache_save_timer.is_alive():
                return
            self._metadata_cache_save_timer = threading.Timer(
                self._metadata_cache_save_delay_sec,
                self._flush_metadata_cache_save,
            )
            self._metadata_cache_save_timer.daemon = True
            self._metadata_cache_save_timer.start()

    def _get_cached_mod_metadata(self, mod_id: str):
        key = str(mod_id or "").strip()
        if not key:
            return None
        with self._metadata_cache_lock:
            payload = self._metadata_cache.get(key)
        normalized = self._normalize_cached_mod_metadata(key, payload)
        if not normalized:
            return None
        ts = float(normalized.get("ts", 0.0) or 0.0)
        if ts and (time.time() - ts) > self._metadata_cache_ttl_sec:
            return None
        return normalized

    def _cache_mod_metadata(self, mod_id: str, info: dict):
        key = str(mod_id or "").strip()
        if not key:
            return
        mod_name = str((info or {}).get("mod_name", "")).strip()
        app_id_raw = (info or {}).get("app_id")
        app_id = str(app_id_raw).strip() if app_id_raw else None
        game_name = str((info or {}).get("game_name", "")).strip() or "Unknown Game"
        if self._mod_name_needs_hydration(mod_name, key) and not app_id:
            return
        payload = {
            "mod_name": mod_name or f"Mod {key}",
            "app_id": app_id,
            "game_name": game_name,
            "ts": time.time(),
        }
        with self._metadata_cache_lock:
            self._metadata_cache[key] = payload
        self._schedule_metadata_cache_save()

    def _apply_mod_metadata_update(self, mod_id: str, metadata: dict):
        key = str(mod_id or "").strip()
        if not key:
            return False
        updated = False
        with self.state_lock:
            queue_mod = self._queue_mod_map.get(key)
            if queue_mod is None:
                return False
            mod_name = str(metadata.get("mod_name", "")).strip()
            app_id_raw = metadata.get("app_id")
            app_id = str(app_id_raw).strip() if app_id_raw else None
            game_name = str(metadata.get("game_name", "")).strip()

            if mod_name and not self._mod_name_needs_hydration(mod_name, key):
                if self._mod_name_needs_hydration(queue_mod.get("mod_name"), key):
                    queue_mod["mod_name"] = mod_name
                    updated = True
            if app_id and not queue_mod.get("app_id"):
                queue_mod["app_id"] = app_id
                updated = True
            if game_name:
                current_game = str(queue_mod.get("game_name", "")).strip()
                if (not current_game) or current_game == "Unknown Game" or current_game.startswith("AppID "):
                    queue_mod["game_name"] = game_name
                    updated = True
        return updated

    def _hydrate_mod_metadata_worker(self, mod_id: str, collection_game_info=None):
        key = str(mod_id or "").strip()
        if not key:
            return
        try:
            metadata = self._get_cached_mod_metadata(key)
            if metadata is None:
                metadata = self._get_mod_info(key, collection_game_info=collection_game_info)
                if isinstance(metadata, dict):
                    self._cache_mod_metadata(key, metadata)
            if isinstance(metadata, dict) and self._apply_mod_metadata_update(key, metadata):
                self._emit_queue_refresh_throttled()
        except Exception:
            pass
        finally:
            with self._hydration_lock:
                self._hydration_inflight.discard(key)

    def _schedule_mod_metadata_hydration(self, mod_ids, collection_game_info=None):
        if not mod_ids:
            return
        for mod_id in mod_ids:
            key = str(mod_id or "").strip()
            if not key:
                continue
            with self._hydration_lock:
                if key in self._hydration_inflight:
                    continue
                self._hydration_inflight.add(key)
            self._hydration_executor.submit(self._hydrate_mod_metadata_worker, key, collection_game_info)

    def _compute_queue_stats(self, queue_items):
        stats = {
            "total": 0,
            "queued": 0,
            "downloaded": 0,
            "failed": 0,
            "downloading": 0,
        }
        for mod in queue_items:
            stats["total"] += 1
            status = str(mod.get("status", ""))
            if status == "Queued":
                stats["queued"] += 1
            if status == "Downloaded":
                stats["downloaded"] += 1
            if "Failed" in status:
                stats["failed"] += 1
            if status == "Downloading":
                stats["downloading"] += 1
        return stats

    def _filter_queue_for_view(self, queue_items, filter_name):
        filter_name = str(filter_name or "All")
        if filter_name == "Queued":
            return [mod for mod in queue_items if str(mod.get("status", "")) == "Queued"]
        if filter_name == "Downloaded":
            return [mod for mod in queue_items if str(mod.get("status", "")) == "Downloaded"]
        if filter_name == "Failed":
            return [mod for mod in queue_items if "Failed" in str(mod.get("status", ""))]
        return list(queue_items)

    def _search_queue_for_view(self, queue_items, search_query, regex_enabled, case_sensitive):
        query = str(search_query or "").strip()
        if not query:
            return list(queue_items), False

        regex_enabled = bool(regex_enabled)
        case_sensitive = bool(case_sensitive)

        if regex_enabled:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(query, flags)
            except re.error:
                return [], True
            return [
                mod for mod in queue_items
                if pattern.search(str(mod.get("mod_id", ""))) or pattern.search(str(mod.get("mod_name", "")))
            ], False

        if case_sensitive:
            return [
                mod for mod in queue_items
                if query in str(mod.get("mod_id", "")) or query in str(mod.get("mod_name", ""))
            ], False

        lowered = query.lower()
        return [
            mod for mod in queue_items
            if lowered in str(mod.get("mod_id", "")).lower() or lowered in str(mod.get("mod_name", "")).lower()
        ], False

    def _sort_queue_for_view(self, queue_items, sort_key, sort_direction):
        sort_key = str(sort_key or "").strip()
        if sort_key not in {"game_name", "mod_id", "mod_name", "status", "provider"}:
            return list(queue_items)

        reverse = str(sort_direction or "asc").strip().lower() == "desc"

        if sort_key == "mod_id":
            def mod_id_key(mod):
                value = str(mod.get("mod_id", "")).strip()
                if value.isdigit():
                    return (0, int(value))
                return (1, value.lower())

            return sorted(queue_items, key=mod_id_key, reverse=reverse)

        def text_key(mod):
            return str(mod.get(sort_key, "")).lower()

        return sorted(queue_items, key=text_key, reverse=reverse)

    def get_bootstrap_data(self):
        with self.state_lock:
            queue_stats = self._compute_queue_stats(self.download_queue)
        return {
            "version": self.app_version,
            "config": dict(self.config),
            "queue": [],
            "queue_stats": queue_stats,
            "queue_total": int(queue_stats.get("total", 0)),
            "download_state": {
                "is_downloading": self.is_downloading
            },
            "appids_count": len(self.app_ids),
            "warning": ""
        }

    def get_preview_queue(self):
        with self.state_lock:
            return [dict(mod) for mod in self.download_queue]

    def get_queue(self):
        return self.get_preview_queue()

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
        try:
            offset = max(0, int(offset or 0))
        except Exception:
            offset = 0
        try:
            limit = int(limit or 200)
        except Exception:
            limit = 200
        limit = max(1, min(2000, limit))

        normalized = {
            "filter_name": str(filter_name or "All"),
            "search_query": str(search_query or "").strip(),
            "regex_enabled": bool(regex_enabled),
            "case_sensitive": bool(case_sensitive),
            "sort_key": str(sort_key or "").strip(),
            "sort_direction": str(sort_direction or "asc").strip().lower(),
        }
        if normalized["sort_direction"] not in {"asc", "desc"}:
            normalized["sort_direction"] = "asc"

        with self.state_lock:
            cache = self._queue_query_cache
            revision = int(self._queue_revision)
            cache_valid = (
                isinstance(cache, dict)
                and cache.get("revision") == revision
                and cache.get("filter_name") == normalized["filter_name"]
                and cache.get("search_query") == normalized["search_query"]
                and cache.get("regex_enabled") == normalized["regex_enabled"]
                and cache.get("case_sensitive") == normalized["case_sensitive"]
                and cache.get("sort_key") == normalized["sort_key"]
                and cache.get("sort_direction") == normalized["sort_direction"]
            )

            if not cache_valid:
                base_queue = list(self.download_queue)
                queue_stats = self._compute_queue_stats(base_queue)
                filtered = self._filter_queue_for_view(base_queue, normalized["filter_name"])
                searched, regex_error = self._search_queue_for_view(
                    filtered,
                    normalized["search_query"],
                    normalized["regex_enabled"],
                    normalized["case_sensitive"],
                )
                sorted_items = self._sort_queue_for_view(
                    searched,
                    normalized["sort_key"],
                    normalized["sort_direction"],
                )
                cache = {
                    "revision": revision,
                    "filter_name": normalized["filter_name"],
                    "search_query": normalized["search_query"],
                    "regex_enabled": normalized["regex_enabled"],
                    "case_sensitive": normalized["case_sensitive"],
                    "sort_key": normalized["sort_key"],
                    "sort_direction": normalized["sort_direction"],
                    "regex_error": bool(regex_error),
                    "stats": queue_stats,
                    "items": sorted_items,
                }
                self._queue_query_cache = cache

            total = len(cache.get("items", []))
            if offset > total:
                offset = total
            end = min(total, offset + limit)
            page_items = [dict(mod) for mod in cache.get("items", [])[offset:end]]
            queue_stats = dict(cache.get("stats", {}))
            regex_error = bool(cache.get("regex_error", False))

        return {
            "success": True,
            "offset": offset,
            "limit": limit,
            "total": total,
            "items": page_items,
            "stats": queue_stats,
            "regex_error": regex_error,
        }

    def remove_mods(self, mod_ids):
        target_ids = {str(mod_id) for mod_id in (mod_ids or [])}
        with self.state_lock:
            before = len(self.download_queue)
            self.download_queue = [mod for mod in self.download_queue if str(mod.get("mod_id")) not in target_ids]
            self._rebuild_queue_indexes_locked()
            removed = before - len(self.download_queue)
        self._emit_event("queue", {"action": "refresh"})
        return {"success": True, "removed": removed}

    def move_mods(self, mod_ids, direction: str):
        ids = {str(mod_id) for mod_id in (mod_ids or [])}
        with self.state_lock:
            if direction == "top":
                selected = [mod for mod in self.download_queue if str(mod.get("mod_id")) in ids]
                unselected = [mod for mod in self.download_queue if str(mod.get("mod_id")) not in ids]
                self.download_queue = selected + unselected
            elif direction == "bottom":
                selected = [mod for mod in self.download_queue if str(mod.get("mod_id")) in ids]
                unselected = [mod for mod in self.download_queue if str(mod.get("mod_id")) not in ids]
                self.download_queue = unselected + selected
            elif direction == "up":
                for i in range(1, len(self.download_queue)):
                    if str(self.download_queue[i].get("mod_id")) in ids and str(self.download_queue[i - 1].get("mod_id")) not in ids:
                        self.download_queue[i - 1], self.download_queue[i] = self.download_queue[i], self.download_queue[i - 1]
            elif direction == "down":
                for i in range(len(self.download_queue) - 2, -1, -1):
                    if str(self.download_queue[i].get("mod_id")) in ids and str(self.download_queue[i + 1].get("mod_id")) not in ids:
                        self.download_queue[i + 1], self.download_queue[i] = self.download_queue[i], self.download_queue[i + 1]
            self._rebuild_queue_indexes_locked()
        self._emit_event("queue", {"action": "refresh"})
        return {"success": True}

    def _extract_id(self, input_str: str):
        input_str = (input_str or "").strip()
        match = re.search(r"[?&]id=(\d+)", input_str)
        if match:
            return match.group(1)
        if input_str.isdigit():
            return input_str
        num_match = re.search(r"(\d{5,})", input_str)
        return num_match.group(1) if num_match else None

    def _extract_appid(self, input_str: str):
        input_str = (input_str or "").strip()
        match = re.search(r"store\.steampowered\.com/app/(\d+)", input_str)
        if match:
            return match.group(1)
        match = re.search(r"steamcommunity\.com/app/(\d+)", input_str)
        if match:
            return match.group(1)
        match = re.search(r"[?&]appid=(\d+)", input_str)
        if match:
            return match.group(1)
        if input_str.isdigit() and input_str in self.app_ids:
            return input_str
        return None

    def _detect_input_type(self, input_text: str):
        input_text = (input_text or "").strip()
        if not input_text:
            return (None, None)

        app_id = None
        numeric_id = None

        if "store.steampowered.com/app/" in input_text:
            app_id = self._extract_appid(input_text)
        elif "steamcommunity.com/sharedfiles/filedetails/" in input_text or "steamcommunity.com/workshop/filedetails/" in input_text:
            numeric_id = self._extract_id(input_text)
        elif input_text.isdigit():
            numeric_id = input_text
            if numeric_id in self.app_ids:
                app_id = numeric_id
        else:
            app_id = self._extract_appid(input_text)
            if not app_id:
                numeric_id = self._extract_id(input_text)

        if app_id and self._check_if_appid_has_workshop(app_id):
            return ("game", app_id)

        if numeric_id and numeric_id != app_id and self._check_if_appid_has_workshop(numeric_id):
            return ("game", numeric_id)

        if numeric_id:
            if self._is_collection(numeric_id):
                return ("collection", numeric_id)
            return ("workshop_item", numeric_id)

        if app_id:
            return ("no_workshop", app_id)

        return (None, None)

    def _check_if_appid_has_workshop(self, app_id: str):
        try:
            workshop_url = f"https://steamcommunity.com/app/{app_id}/workshop/"
            response = requests.get(
                workshop_url,
                allow_redirects=True,
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            final_url = response.url
            if "store.steampowered.com" in final_url and "/workshop/" not in final_url:
                return False
            if response.status_code != 200:
                return False
            markers = ["workshopItemsContainer", "workshopBrowseItems", "workshop_browse_menu"]
            return any(marker in response.text for marker in markers)
        except Exception:
            return False

    def _is_collection(self, item_id: str):
        try:
            url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={item_id}"
            response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            tree = html.fromstring(response.text)
            collection_items = tree.xpath('//div[contains(@class, "collectionChildren")]//div[contains(@class, "collectionItem")]')
            if collection_items:
                return True
            collection_items_fallback = tree.xpath('//div[contains(@class, "collectionItem")]')
            return len(collection_items_fallback) > 0
        except Exception:
            return False

    def _extract_mod_title_from_tree(self, tree):
        invalid_titles = (
            "steam community :: error",
            "steam community :: item not found",
            "steam community :: steam workshop",
            "steam community",
            "access denied",
            "error",
            "just a moment",
            "attention required",
        )
        title_candidates = tree.xpath(
            '//div[@class="workshopItemTitle"] | '
            '//div[contains(@class, "workshopItemTitle")] | '
            '//meta[@property="og:title"]/@content | '
            "//title/text()"
        )
        for candidate in title_candidates:
            if hasattr(candidate, "text_content"):
                text = candidate.text_content().strip()
            else:
                text = str(candidate).strip()
            if not text:
                continue
            if text.startswith("Steam Workshop::"):
                text = text.replace("Steam Workshop::", "", 1).strip()
            normalized = text.strip().lower()
            if not normalized:
                continue
            if normalized in invalid_titles:
                continue
            if normalized.startswith("steam community :: error"):
                continue
            if normalized.startswith("steam community :: item not found"):
                continue
            if text:
                return text
        return "Unknown Title"

    def _get_mod_info(self, mod_id: str, collection_game_info=None, tree=None):
        try:
            cached_info = None
            if tree is None:
                cached_info = self._get_cached_mod_metadata(mod_id)
            if cached_info:
                merged = {
                    "mod_id": str(mod_id),
                    "mod_name": cached_info.get("mod_name", f"Mod {mod_id}"),
                    "app_id": cached_info.get("app_id"),
                    "game_name": cached_info.get("game_name", "Unknown Game"),
                }
                if collection_game_info:
                    if not merged.get("app_id"):
                        merged["app_id"] = collection_game_info.get("app_id")
                    if not merged.get("game_name") or merged.get("game_name") == "Unknown Game":
                        merged["game_name"] = collection_game_info.get("game_name", "Unknown Game")
                return merged

            if tree is None:
                url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
                response = None
                last_error = None
                for attempt in range(3):
                    try:
                        response = requests.get(url, timeout=(8, 20), headers={"User-Agent": "Mozilla/5.0"})
                        if response.status_code == 200:
                            break
                        if response.status_code in (429, 500, 502, 503, 504):
                            if attempt < 2:
                                time.sleep(0.35 * (attempt + 1))
                                response = None
                                continue
                        break
                    except (requests.Timeout, requests.ConnectionError) as exc:
                        last_error = exc
                        response = None
                        if attempt < 2:
                            time.sleep(0.35 * (attempt + 1))
                            continue
                        break
                    except requests.RequestException as exc:
                        last_error = exc
                        response = None
                        break
                if response is None:
                    if last_error:
                        raise last_error
                    raise RuntimeError("Failed to fetch workshop item page")
                tree = html.fromstring(response.text)

            error_messages = tree.xpath('//div[@class="error_ctn"]//h3/text()')
            for msg in error_messages:
                if "You must be logged in to view this item" in str(msg):
                    if collection_game_info:
                        return {
                            "mod_id": str(mod_id),
                            "mod_name": "UNKNOWN - Age Restricted",
                            "app_id": collection_game_info.get("app_id"),
                            "game_name": collection_game_info.get("game_name", "Unknown Game"),
                        }
                    return {
                        "mod_id": str(mod_id),
                        "mod_name": "UNKNOWN - Age Restricted",
                        "app_id": None,
                        "game_name": "Unknown Game",
                    }

            game_name, app_id = "Unknown Game", None
            game_tag = tree.xpath('//div[@class="breadcrumbs"]/a[contains(@href, "/app/")]')
            if game_tag and "href" in game_tag[0].attrib:
                href = game_tag[0].get("href")
                app_id_match = re.search(r"/app/(\d+)", href)
                if app_id_match:
                    app_id = app_id_match.group(1)
                    game_name = game_tag[0].text_content().strip()

            mod_title = self._extract_mod_title_from_tree(tree)
            if collection_game_info and not app_id:
                app_id = collection_game_info.get("app_id")
                game_name = collection_game_info.get("game_name", "Unknown Game")
            result = {"mod_id": str(mod_id), "mod_name": mod_title, "app_id": app_id, "game_name": game_name}
            self._cache_mod_metadata(str(mod_id), result)
            return result
        except Exception:
            if collection_game_info:
                return {
                    "mod_id": str(mod_id),
                    "mod_name": "Unknown Title",
                    "app_id": collection_game_info.get("app_id"),
                    "game_name": collection_game_info.get("game_name", "Unknown Game"),
                }
            return {"mod_id": str(mod_id), "mod_name": "Unknown Title", "app_id": None, "game_name": "Unknown Game"}

    def _scrape_collection_mods(self, collection_id: str, tree=None):
        mods_info = []
        try:
            if tree is None:
                url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={collection_id}"
                response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                response.raise_for_status()
                tree = html.fromstring(response.text)

            collection_game_info = None
            breadcrumb_tag = tree.xpath('//div[@class="breadcrumbs"]/a[contains(@href, "/app/")]')
            if breadcrumb_tag:
                href = breadcrumb_tag[0].get("href", "")
                app_id_match = re.search(r"/app/(\d+)", href)
                if app_id_match:
                    collection_game_info = {
                        "app_id": app_id_match.group(1),
                        "game_name": breadcrumb_tag[0].text_content().strip() or "Unknown Game",
                    }

            mod_ids = set()
            collection_items = tree.xpath('//div[contains(@class,"collectionChildren")]//div[contains(@class,"collectionItem")]')
            if not collection_items:
                collection_items = tree.xpath('//div[contains(@class,"collectionItem")]')

            for item in collection_items:
                a_tag = item.xpath('.//a[@href]')
                if not a_tag:
                    continue
                mod_id = self._extract_id(a_tag[0].get("href", ""))
                if not mod_id or mod_id in mod_ids:
                    continue
                mod_ids.add(mod_id)

                title_text = ""
                title_nodes = item.xpath(
                    './/*[contains(@class, "workshopItemTitle")] | '
                    './/*[contains(@class, "collectionItemTitle")] | '
                    './/div[contains(@class, "workshopItem")]//a'
                )
                for node in title_nodes:
                    text = node.text_content().strip() if hasattr(node, "text_content") else str(node).strip()
                    if text:
                        title_text = text
                        break

                cached = self._get_cached_mod_metadata(mod_id) or {}
                mod_name = title_text or str(cached.get("mod_name", "")).strip() or f"Mod {mod_id}"
                app_id = (collection_game_info or {}).get("app_id") or cached.get("app_id")
                game_name = (collection_game_info or {}).get("game_name") or cached.get("game_name") or "Unknown Game"
                mods_info.append({
                    "mod_id": str(mod_id),
                    "mod_name": mod_name,
                    "app_id": app_id,
                    "game_name": game_name,
                })
        except Exception as e:
            self.log(
                f"Error processing collection {collection_id}: {e}",
                tone="bad",
                source="queue",
                action="collection_processing_failed",
                context={"collection_id": str(collection_id), "error": str(e)},
            )
        return mods_info

    def _resolve_workshop_item(self, item_id: str, hinted_type: str = None):
        try:
            url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={item_id}"
            response = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            tree = html.fromstring(response.text)
        except Exception as e:
            self.log(
                f"Error processing workshop item {item_id}: {e}",
                tone="bad",
                source="queue",
                action="item_processing_failed",
                context={"item_id": str(item_id), "error": str(e)},
            )
            if hinted_type == "collection":
                return "collection", self._scrape_collection_mods(item_id)
            return "workshop_item", [self._get_mod_info(item_id)]

        collection_items = tree.xpath('//div[contains(@class,"collectionChildren")]//div[contains(@class,"collectionItem")]')
        if collection_items:
            return "collection", self._scrape_collection_mods(item_id, tree=tree)
        if hinted_type == "collection":
            return "collection", self._scrape_collection_mods(item_id, tree=tree)
        return "workshop_item", [self._get_mod_info(item_id, tree=tree)]

    def _parse_workshop_page(self, page_content: str, app_id: str, game_name: str):
        page_tree = html.fromstring(page_content)
        workshop_items = page_tree.xpath("//div[@class='workshopItem']")
        mods = []
        for item in workshop_items:
            link = item.xpath(".//a[contains(@href, 'sharedfiles/filedetails')]")
            if not link:
                continue
            mod_id = link[0].get("data-publishedfileid") or self._extract_id(link[0].get("href", ""))
            title_div = item.xpath(".//div[contains(@class,'workshopItemTitle')]")
            mod_name = title_div[0].text_content().strip() if title_div else "Unknown Title"
            if mod_id:
                mods.append({
                    "mod_id": str(mod_id),
                    "mod_name": mod_name,
                    "app_id": str(app_id),
                    "game_name": game_name,
                })
        return mods

    def _scrape_workshop_app(
        self,
        app_id: str,
        max_pages: int = 1667,
        concurrency: int = 24,
        on_batch=None,
        operation_id: str = "",
    ):
        base_url = "https://steamcommunity.com/workshop/browse/"
        params = {"appid": str(app_id), "browsesort": "toprated", "section": "readytouseitems", "p": "1"}
        mods = []
        seen_mod_ids = set()
        game_name = self.app_ids.get(str(app_id), f"AppID {app_id}")

        response = requests.get(base_url, params=params, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        tree = html.fromstring(response.text)

        if game_name.startswith("AppID "):
            game_nodes = tree.xpath('//div[@class="apphub_AppName ellipsis"]/text()')
            if game_nodes:
                game_name = game_nodes[0].strip()

        def emit_batch(batch_mods, pages_done, pages_total):
            if not batch_mods:
                return
            deduped_batch = []
            for mod in batch_mods:
                mod_id = str(mod.get("mod_id", "")).strip()
                if not mod_id or mod_id in seen_mod_ids:
                    continue
                seen_mod_ids.add(mod_id)
                deduped_batch.append(mod)
            if not deduped_batch:
                return
            mods.extend(deduped_batch)
            if on_batch:
                try:
                    on_batch(deduped_batch, pages_done, pages_total)
                except Exception as callback_error:
                    self.log(
                        f"Queue batch callback failed: {callback_error}",
                        tone="bad",
                        source="queue",
                        action="queue_batch_callback_failed",
                        context={"error": str(callback_error)},
                    )

        first_page_mods = self._parse_workshop_page(response.text, app_id=str(app_id), game_name=game_name)

        paging_info = tree.xpath("//div[@class='workshopBrowsePagingInfo']/text()")
        total_entries = 0
        for info in paging_info:
            match = re.search(r"\bof\s+([\d,]+)", info, flags=re.IGNORECASE)
            if match:
                try:
                    total_entries = int(match.group(1).replace(",", ""))
                    break
                except Exception:
                    total_entries = 0

        if total_entries <= 0:
            emit_batch(first_page_mods, 1, 1)
            return mods

        mods_per_page = 30
        total_pages = min((total_entries + mods_per_page - 1) // mods_per_page, max_pages)
        emit_batch(first_page_mods, 1, total_pages)
        if total_pages <= 1:
            return mods

        def fetch_page(page_number: int):
            page_params = dict(params)
            page_params["p"] = str(page_number)
            retries = 3
            for attempt in range(retries):
                try:
                    page_response = requests.get(
                        base_url,
                        params=page_params,
                        timeout=30,
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    if page_response.status_code == 200:
                        return page_response.text
                except Exception:
                    pass
                if attempt < (retries - 1):
                    time.sleep(0.25 * (attempt + 1))
            return None

        pages_fetched = 1
        pages_failed = 0
        for start in range(2, total_pages + 1, concurrency):
            end = min(start + concurrency - 1, total_pages)
            with ThreadPoolExecutor(max_workers=min(concurrency, end - start + 1)) as executor:
                futures = {executor.submit(fetch_page, page): page for page in range(start, end + 1)}
                batch_results = {}
                for future in as_completed(futures):
                    page_number = futures[future]
                    try:
                        page_content = future.result()
                    except Exception:
                        pages_failed += 1
                        continue
                    if not page_content:
                        pages_failed += 1
                        continue
                    batch_results[page_number] = self._parse_workshop_page(page_content, app_id=str(app_id), game_name=game_name)
                    pages_fetched += 1
                ordered_batch_mods = []
                for page_number in sorted(batch_results):
                    ordered_batch_mods.extend(batch_results[page_number])
                emit_batch(ordered_batch_mods, pages_fetched, total_pages)
            self.log(
                f"Pages fetched: {pages_fetched} / {total_pages}",
                source="queue",
                action="pages_fetched",
                context={
                    "pages_fetched": pages_fetched,
                    "total_pages": total_pages,
                    "pages_failed": pages_failed,
                    "app_id": str(app_id),
                },
                operation_id=operation_id,
            )

        return mods

    def _provider_for_mod(self, mod: dict, selected_provider: str):
        if selected_provider != "Default":
            return selected_provider
        app_id = mod.get("app_id")
        if app_id and str(app_id) in self.app_ids:
            return "SteamCMD"
        return "SteamWebAPI"

    def change_provider_for_mods(self, mod_ids, provider):
        ids = {str(mod_id) for mod_id in (mod_ids or [])}
        provider = (provider or "Default").strip() or "Default"
        changed = 0
        with self.state_lock:
            for mod in self.download_queue:
                if str(mod.get("mod_id")) in ids:
                    new_provider = self._provider_for_mod(mod, provider)
                    if mod.get("provider") != new_provider:
                        mod["provider"] = new_provider
                        changed += 1
        self._emit_event("queue", {"action": "refresh"})
        return {"success": True, "changed": changed}

    def set_global_provider(self, provider, override_existing=False):
        provider = (provider or "Default").strip() or "Default"
        self.config["download_provider"] = provider
        self.save_config()

        changed = 0
        if override_existing:
            with self.state_lock:
                for mod in self.download_queue:
                    new_provider = self._provider_for_mod(mod, provider)
                    if mod.get("provider") != new_provider:
                        mod["provider"] = new_provider
                        changed += 1
            self._emit_event("queue", {"action": "refresh"})

        return {"success": True, "changed": changed}

    def override_appid(self, mod_ids, app_id_input):
        app_id = self._extract_appid(app_id_input) or self._extract_id(app_id_input)
        if not app_id:
            return {"success": False, "error": "Invalid AppID."}

        game_name = self.app_ids.get(str(app_id), f"AppID {app_id}")
        ids = {str(mod_id) for mod_id in (mod_ids or [])}
        changed = 0

        with self.state_lock:
            for mod in self.download_queue:
                if str(mod.get("mod_id")) in ids:
                    mod["app_id"] = str(app_id)
                    mod["game_name"] = game_name
                    mod["provider"] = self._provider_for_mod(mod, self.config.get("download_provider", "Default"))
                    changed += 1

        self._emit_event("queue", {"action": "refresh"})
        return {"success": True, "changed": changed, "app_id": str(app_id), "game_name": game_name}

    def reset_status(self, mod_ids):
        ids = {str(mod_id) for mod_id in (mod_ids or [])}
        reset_count = 0
        with self.state_lock:
            for mod in self.download_queue:
                if str(mod.get("mod_id")) in ids:
                    mod["status"] = "Queued"
                    mod["retry_count"] = 0
                    reset_count += 1
        self._emit_event("queue", {"action": "refresh"})
        return {"success": True, "reset": reset_count}

    def import_queue(self, file_path):
        if not file_path or not os.path.isfile(file_path):
            return {"success": False, "error": "File not found."}

        added = 0
        skipped = 0
        with self.state_lock:
            with open(file_path, "r", encoding="utf-8") as file:
                for raw in file:
                    parts = raw.strip().split("|")
                    if len(parts) < 4:
                        continue
                    game_name, mod_id, mod_name, provider = parts[0], parts[1], parts[2], parts[3]
                    mod_id = str(mod_id).strip()
                    if not mod_id or self._is_mod_in_queue(mod_id):
                        skipped += 1
                        continue
                    queue_mod = {
                        "game_name": game_name,
                        "mod_id": mod_id,
                        "mod_name": mod_name,
                        "status": "Queued",
                        "retry_count": 0,
                        "app_id": None,
                        "provider": provider or "Default"
                    }
                    self.download_queue.append(queue_mod)
                    self._queue_mod_ids.add(mod_id)
                    self._queue_mod_map[mod_id] = queue_mod
                    added += 1
        self._emit_event("queue", {"action": "refresh"})
        return {"success": True, "added": added, "skipped": skipped}

    def export_queue(self, file_path):
        if not file_path:
            return {"success": False, "error": "Invalid export path."}
        with self.state_lock:
            queue_copy = [dict(mod) for mod in self.download_queue]

        with open(file_path, "w", encoding="utf-8") as file:
            for mod in queue_copy:
                file.write(f"{mod['game_name']}|{mod['mod_id']}|{mod['mod_name']}|{mod['provider']}\n")

        return {"success": True, "path": file_path}

    def _is_mod_in_queue(self, mod_id: str):
        key = str(mod_id or "").strip()
        if not key:
            return False
        with self.state_lock:
            return key in self._queue_mod_ids

    def _append_mod_to_queue(self, mod: dict, selected_provider: str):
        mod_id = str(mod.get("mod_id", "")).strip()
        if not mod_id or self._is_mod_in_queue(mod_id):
            return False
        queue_mod = {
            "game_name": mod.get("game_name", "Unknown Game"),
            "mod_id": mod_id,
            "mod_name": mod.get("mod_name", "Unknown Title"),
            "status": "Queued",
            "retry_count": 0,
            "app_id": mod.get("app_id"),
            "provider": self._provider_for_mod(mod, selected_provider)
        }
        self.download_queue.append(queue_mod)
        self._queue_mod_ids.add(mod_id)
        self._queue_mod_map[mod_id] = queue_mod
        return True

    def _append_mods_to_queue_bulk(self, mods, selected_provider: str):
        added = 0
        skipped = 0
        queue_size = 0
        added_mod_ids = []
        hydration_candidates = []
        collection_game_info = None

        with self.state_lock:
            for mod in (mods or []):
                mod_id = str((mod or {}).get("mod_id", "")).strip()
                if not mod_id or mod_id in self._queue_mod_ids:
                    skipped += 1
                    continue

                cached = self._get_cached_mod_metadata(mod_id)
                merged_game_name = str(mod.get("game_name", "")).strip()
                merged_mod_name = str(mod.get("mod_name", "")).strip()
                merged_app_id = mod.get("app_id")
                if cached:
                    if not merged_mod_name or self._mod_name_needs_hydration(merged_mod_name, mod_id):
                        merged_mod_name = str(cached.get("mod_name", merged_mod_name)).strip()
                    if not merged_app_id:
                        merged_app_id = cached.get("app_id")
                    if (not merged_game_name) or merged_game_name == "Unknown Game" or merged_game_name.startswith("AppID "):
                        merged_game_name = str(cached.get("game_name", merged_game_name)).strip()

                if not merged_game_name:
                    merged_game_name = "Unknown Game"
                if not merged_mod_name:
                    merged_mod_name = f"Mod {mod_id}"

                queue_mod = {
                    "game_name": merged_game_name,
                    "mod_id": mod_id,
                    "mod_name": merged_mod_name,
                    "status": "Queued",
                    "retry_count": 0,
                    "app_id": merged_app_id,
                    "provider": self._provider_for_mod(
                        {
                            "mod_id": mod_id,
                            "mod_name": merged_mod_name,
                            "app_id": merged_app_id,
                            "game_name": merged_game_name,
                        },
                        selected_provider,
                    ),
                }
                self.download_queue.append(queue_mod)
                self._queue_mod_ids.add(mod_id)
                self._queue_mod_map[mod_id] = queue_mod
                added += 1
                added_mod_ids.append(mod_id)

                if not collection_game_info and queue_mod.get("app_id"):
                    collection_game_info = {
                        "app_id": str(queue_mod.get("app_id")),
                        "game_name": str(queue_mod.get("game_name", "Unknown Game")),
                    }

                if (
                    self._mod_name_needs_hydration(queue_mod.get("mod_name"), mod_id)
                    or not queue_mod.get("app_id")
                    or str(queue_mod.get("game_name", "")) in {"", "Unknown Game"}
                ):
                    hydration_candidates.append(mod_id)

            queue_size = len(self.download_queue)

        if hydration_candidates:
            self._schedule_mod_metadata_hydration(
                hydration_candidates,
                collection_game_info=collection_game_info,
            )

        return {
            "added": added,
            "skipped": skipped,
            "queue_size": queue_size,
            "added_mod_ids": added_mod_ids,
        }

    def _queue_entire_workshop_background(
        self,
        app_id: str,
        provider: str,
        operation_id: str = "",
        parent_operation_id: str = "",
    ):
        app_id = str(app_id or "").strip()
        if not app_id:
            return
        operation_id = str(operation_id or "").strip() or self._next_operation_id("queue-build")
        parent_operation_id = str(parent_operation_id or "").strip()
        with self._queue_build_lock:
            game_name = self.app_ids.get(app_id, f"AppID {app_id}")
            start_context = {"app_id": app_id, "game_name": game_name, "provider": provider}
            if parent_operation_id:
                start_context["parent_operation_id"] = parent_operation_id
            self.log(
                f"Starting to queue entire workshop for {game_name} (AppID: {app_id})",
                source="queue",
                action="queue_build_started",
                context=start_context,
                operation_id=operation_id,
            )

            total_added = 0
            total_skipped = 0

            def on_batch(batch_mods, pages_done, pages_total):
                nonlocal total_added, total_skipped
                result = self._append_mods_to_queue_bulk(batch_mods, provider)
                total_added += int(result.get("added", 0))
                total_skipped += int(result.get("skipped", 0))
                if result.get("added", 0) or result.get("skipped", 0):
                    self._emit_queue_refresh_throttled()

            try:
                self._scrape_workshop_app(app_id, on_batch=on_batch, operation_id=operation_id)
                self._emit_queue_refresh_throttled(force=True)
                with self.state_lock:
                    queue_size = len(self.download_queue)
                self.log(
                    f"Queue build complete (AppID {app_id}): {total_added:,} added, {total_skipped:,} skipped.",
                    tone="good",
                    source="queue",
                    action="queue_build_completed",
                    context={
                        "app_id": app_id,
                        "added": total_added,
                        "skipped": total_skipped,
                        "queue_size": queue_size,
                    },
                    operation_id=operation_id,
                )
            except Exception as e:
                self.log(
                    f"Failed to queue workshop AppID {app_id}: {e}",
                    tone="bad",
                    source="queue",
                    action="queue_build_failed",
                    context={"app_id": app_id, "error": str(e)},
                    operation_id=operation_id,
                )
                self._emit_queue_refresh_throttled(force=True)

    def add_preview_queue_item(self, item_url, app_id="", provider="Default"):
        item_url = (item_url or "").strip()
        provider = (provider or "Default").strip() or "Default"
        operation_id = self._next_operation_id("queue-input")

        if not item_url:
            self.log(
                "Queue input failed: item URL is required.",
                tone="bad",
                source="queue",
                action="queue_input_failed",
                context={"reason": "missing_input", "operation_state": "error"},
                operation_id=operation_id,
            )
            return {"success": False, "error": "Item URL is required."}

        self.log(
            "Processing queue input...",
            source="queue",
            action="queue_input_started",
            context={"operation_state": "run"},
            operation_id=operation_id,
        )

        input_type, item_id = self._detect_input_type(item_url)
        if not input_type or not item_id:
            self.log(
                "Queue input failed: invalid input.",
                tone="bad",
                source="queue",
                action="queue_input_failed",
                context={"item_url": item_url, "reason": "invalid_input", "operation_state": "error"},
                operation_id=operation_id,
            )
            return {"success": False, "error": "Invalid input. Enter a Workshop URL/ID or Game AppID."}

        if input_type == "no_workshop":
            game_name = self.app_ids.get(str(item_id), f"AppID {item_id}")
            self.log(
                f"Queue input failed: {game_name} (AppID: {item_id}) has no Steam Workshop.",
                tone="bad",
                source="queue",
                action="queue_input_failed",
                context={"app_id": str(item_id), "reason": "no_workshop", "operation_state": "error"},
                operation_id=operation_id,
            )
            return {"success": False, "error": f"Game '{game_name}' (AppID: {item_id}) does not have a Steam Workshop."}

        if input_type == "game" and not self.config.get("show_queue_entire_workshop", True):
            self.log(
                "Queue input failed: Queue Entire Workshop is disabled.",
                tone="bad",
                source="queue",
                action="queue_input_failed",
                context={"app_id": str(item_id), "reason": "feature_disabled", "operation_state": "error"},
                operation_id=operation_id,
            )
            return {"success": False, "error": "Queue Entire Workshop is disabled in Settings."}

        try:
            if input_type == "game":
                with self.state_lock:
                    queue_size = len(self.download_queue)
                build_operation_id = self._next_operation_id("queue-build")
                self._queue_build_executor.submit(
                    self._queue_entire_workshop_background,
                    str(item_id),
                    provider,
                    build_operation_id,
                    operation_id,
                )
                self.log(
                    f"Queue input complete for AppID {item_id}. Started queue build in background.",
                    tone="good",
                    source="queue",
                    action="queue_input_accepted",
                    context={
                        "app_id": str(item_id),
                        "queue_build_operation_id": build_operation_id,
                        "operation_state": "done",
                    },
                    operation_id=operation_id,
                )
                return {
                    "success": True,
                    "added": 0,
                    "skipped": 0,
                    "queue_size": queue_size,
                    "queued_in_background": True,
                }
            else:
                if input_type == "collection":
                    self.log(
                        f"Processing workshop collection {item_id}...",
                        source="queue",
                        action="collection_processing",
                        context={"item_id": str(item_id), "operation_state": "run"},
                        operation_id=operation_id,
                    )
                else:
                    self.log(
                        f"Processing workshop item {item_id}...",
                        source="queue",
                        action="item_processing",
                        context={"item_id": str(item_id), "operation_state": "run"},
                        operation_id=operation_id,
                    )
                resolved_type, mods = self._resolve_workshop_item(str(item_id), hinted_type=input_type)
                if resolved_type == "collection" and input_type != "collection":
                    self.log(
                        "Collection detected. Adding to queue...",
                        source="queue",
                        action="collection_detected",
                        context={"item_id": str(item_id), "operation_state": "run"},
                        operation_id=operation_id,
                    )
                if not mods:
                    if resolved_type == "collection":
                        self.log(
                            f"Collection queue failed: no items found for {item_id}.",
                            tone="bad",
                            source="queue",
                            action="queue_input_failed",
                            context={"item_id": str(item_id), "reason": "collection_empty", "operation_state": "error"},
                            operation_id=operation_id,
                        )
                        return {"success": False, "error": f"No collection items found for ID {item_id}."}
                    self.log(
                        f"Queue failed: could not fetch workshop item {item_id}.",
                        tone="bad",
                        source="queue",
                        action="queue_input_failed",
                        context={"item_id": str(item_id), "reason": "item_fetch_failed", "operation_state": "error"},
                        operation_id=operation_id,
                    )
                    return {"success": False, "error": f"Could not fetch workshop item {item_id}."}
                input_type = resolved_type
        except Exception as e:
            self.log(
                f"Failed to queue workshop item(s): {e}",
                tone="bad",
                source="queue",
                action="queue_input_failed",
                context={"error": str(e), "operation_state": "error"},
                operation_id=operation_id,
            )
            return {"success": False, "error": f"Failed to queue workshop item(s): {e}"}

        added = 0
        skipped = 0
        queue_size = 0
        chunk_size = 400
        for start in range(0, len(mods), chunk_size):
            chunk = mods[start:start + chunk_size]
            result = self._append_mods_to_queue_bulk(chunk, provider)
            added += int(result.get("added", 0))
            skipped += int(result.get("skipped", 0))
            queue_size = int(result.get("queue_size", queue_size))
            if result.get("added", 0) or result.get("skipped", 0):
                self._emit_queue_refresh_throttled()

        self._emit_queue_refresh_throttled(force=True)
        if input_type == "game":
            self.log(
                f"Queued workshop AppID {item_id}: {added} added, {skipped} skipped.",
                tone="good",
                source="queue",
                action="game_queued",
                context={"app_id": str(item_id), "added": added, "skipped": skipped, "operation_state": "done"},
                operation_id=operation_id,
            )
        elif input_type == "collection":
            self.log(
                f"Collection processed: {added} added, {skipped} skipped.",
                tone="good",
                source="queue",
                action="collection_processed",
                context={"item_id": str(item_id), "added": added, "skipped": skipped, "operation_state": "done"},
                operation_id=operation_id,
            )
        else:
            self.log(
                f"Queue updated: {added} added, {skipped} skipped.",
                tone="good",
                source="queue",
                action="queue_updated",
                context={"item_id": str(item_id), "added": added, "skipped": skipped, "operation_state": "done"},
                operation_id=operation_id,
            )

        return {"success": True, "added": added, "skipped": skipped, "queue_size": queue_size}

    def add_workshop_item(self, item_url, app_id="", provider="Default"):
        return self.add_preview_queue_item(item_url, app_id, provider)

    def _get_download_path(self, mod):
        if mod.get("provider") == "SteamWebAPI":
            path = self.steamwebapi_download_path
        else:
            app_id = mod.get("app_id") or "unknown_app"
            path = os.path.join(self.steamcmd_download_path, str(app_id))
        os.makedirs(path, exist_ok=True)
        return path

    def _sanitize_folder_component(self, value, fallback):
        text = str(value or "").strip()
        text = re.sub(r"[\x00-\x1f]", "", text)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r'[<>:"/\\|?*]', "_", text).strip(" .")
        if not text:
            text = str(fallback or "").strip() or "mod"

        # Windows reserved names are invalid as folder names.
        if os.name == "nt":
            reserved = {
                "CON", "PRN", "AUX", "NUL",
                "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
                "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
            }
            stem = text.split(".", 1)[0].upper()
            if stem in reserved:
                text = f"{text}_"

        # Keep names reasonably short to reduce path-length failures.
        return text[:150]

    def _resolve_mod_name_for_folder(self, mod, allow_remote_lookup=True):
        mod_id = str((mod or {}).get("mod_id", "")).strip()
        if not mod_id:
            return "Unknown Mod"

        current_name = str((mod or {}).get("mod_name", "")).strip()
        if not self._mod_name_needs_hydration(current_name, mod_id):
            return current_name

        # Fast path: metadata cache
        cached = self._get_cached_mod_metadata(mod_id)
        if cached:
            cached_name = str(cached.get("mod_name", "")).strip()
            if cached_name and not self._mod_name_needs_hydration(cached_name, mod_id):
                try:
                    mod["mod_name"] = cached_name
                except Exception:
                    pass
                return cached_name

        if not allow_remote_lookup:
            if current_name and current_name.lower() != "unknown title":
                return current_name
            return f"Mod {mod_id}"

        # Slow path: fetch item metadata once if still unknown.
        collection_game_info = None
        app_id = str((mod or {}).get("app_id", "")).strip()
        game_name = str((mod or {}).get("game_name", "")).strip()
        if app_id or game_name:
            collection_game_info = {
                "app_id": app_id or None,
                "game_name": game_name or "Unknown Game",
            }

        try:
            fetched = self._get_mod_info(mod_id, collection_game_info=collection_game_info)
        except Exception:
            fetched = None

        if isinstance(fetched, dict):
            fetched_name = str(fetched.get("mod_name", "")).strip()
            if fetched_name and not self._mod_name_needs_hydration(fetched_name, mod_id):
                try:
                    mod["mod_name"] = fetched_name
                    fetched_app_id = fetched.get("app_id")
                    fetched_game_name = fetched.get("game_name")
                    if fetched_app_id and not mod.get("app_id"):
                        mod["app_id"] = str(fetched_app_id)
                    if fetched_game_name and (not mod.get("game_name") or str(mod.get("game_name")) == "Unknown Game"):
                        mod["game_name"] = str(fetched_game_name)
                except Exception:
                    pass
                return fetched_name

        # Final fallback: non-empty readable folder name.
        if current_name and current_name.lower() != "unknown title":
            return current_name
        return f"Mod {mod_id}"

    def _folder_name_for_mod(self, mod, allow_remote_lookup=False):
        mod_id = str((mod or {}).get("mod_id", "")).strip()
        if not mod_id:
            mod_id = "unknown_mod"

        format_name = self.config.get("folder_naming_format", "id")
        format_name = str(format_name or "id").strip().lower()

        safe_mod_id = self._sanitize_folder_component(mod_id, "unknown_mod")
        if format_name == "id":
            return safe_mod_id

        resolved_name = self._resolve_mod_name_for_folder(mod, allow_remote_lookup=allow_remote_lookup)
        safe_mod_name = self._sanitize_folder_component(resolved_name, safe_mod_id)
        if format_name == "name":
            return safe_mod_name
        if format_name == "combined":
            return f"{safe_mod_id} - {safe_mod_name}"
        return safe_mod_id

    def _get_steamcmd_content_path(self, mod):
        app_id = str(mod.get("app_id", ""))
        mod_id = str(mod.get("mod_id", ""))
        return os.path.join(self.steamcmd_dir, "steamapps", "workshop", "content", app_id, mod_id)

    def _get_steamcmd_target_path(self, mod, allow_remote_lookup=False):
        app_id = str(mod.get("app_id", "unknown_app"))
        return os.path.join(
            self.steamcmd_download_path,
            app_id,
            self._folder_name_for_mod(mod, allow_remote_lookup=allow_remote_lookup),
        )

    def _build_steamcmd_app_folder_index(self, app_id, mod_ids):
        app_key = str(app_id or "").strip()
        if not app_key:
            return {}

        normalized_mod_ids = []
        seen = set()
        for mod_id in (mod_ids or []):
            key = str(mod_id or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            normalized_mod_ids.append(key)
        if not normalized_mod_ids:
            return {}

        app_dir = os.path.join(self.steamcmd_download_path, app_key)
        if not os.path.isdir(app_dir):
            return {}

        index = {}
        try:
            for folder_name in os.listdir(app_dir):
                folder_path = os.path.join(app_dir, folder_name)
                if not os.path.isdir(folder_path):
                    continue
                for mod_id in normalized_mod_ids:
                    if mod_id in index:
                        continue
                    if mod_id in folder_name:
                        index[mod_id] = folder_path
        except Exception:
            return index
        return index

    def _check_mod_folder_exists(self, mod, app_folder_index=None):
        target_path = self._get_steamcmd_target_path(mod, allow_remote_lookup=False)
        if os.path.isdir(target_path):
            return True

        app_id = str(mod.get("app_id", ""))
        mod_id = str(mod.get("mod_id", ""))
        if isinstance(app_folder_index, dict):
            indexed_path = app_folder_index.get(mod_id)
            if indexed_path and os.path.isdir(indexed_path):
                return True
            if indexed_path:
                app_folder_index.pop(mod_id, None)
            return False

        app_dir = os.path.join(self.steamcmd_download_path, app_id)
        if not os.path.isdir(app_dir):
            return False
        for folder_name in os.listdir(app_dir):
            folder_path = os.path.join(app_dir, folder_name)
            if os.path.isdir(folder_path) and mod_id in folder_name:
                return True
        return False

    def _delete_existing_mod_folder(self, mod, app_folder_index=None):
        target_path = self._get_steamcmd_target_path(mod, allow_remote_lookup=False)
        mod_id = str(mod.get("mod_id", ""))
        if os.path.isdir(target_path):
            shutil.rmtree(target_path, ignore_errors=True)
            if isinstance(app_folder_index, dict):
                app_folder_index.pop(mod_id, None)
            return True

        app_id = str(mod.get("app_id", ""))
        if isinstance(app_folder_index, dict):
            indexed_path = app_folder_index.get(mod_id)
            if indexed_path and os.path.isdir(indexed_path):
                shutil.rmtree(indexed_path, ignore_errors=True)
            app_folder_index.pop(mod_id, None)
            return True

        app_dir = os.path.join(self.steamcmd_download_path, app_id)
        if not os.path.isdir(app_dir):
            return True
        for folder_name in os.listdir(app_dir):
            folder_path = os.path.join(app_dir, folder_name)
            if os.path.isdir(folder_path) and mod_id in folder_name:
                shutil.rmtree(folder_path, ignore_errors=True)
                return True
        return True

    def _move_mod_to_downloads_steamcmd(self, mod):
        source_path = self._get_steamcmd_content_path(mod)
        target_path = self._get_steamcmd_target_path(mod, allow_remote_lookup=True)
        if not os.path.isdir(source_path):
            return self._check_mod_folder_exists(mod)

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        if os.path.isdir(target_path):
            shutil.rmtree(target_path, ignore_errors=True)
        shutil.move(source_path, target_path)
        return True

    def _get_mod_log_path(self):
        return self.mod_log_path

    def _load_mod_download_logs(self):
        log_path = self._get_mod_log_path()
        if os.path.isfile(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                if isinstance(data, dict):
                    return data
            except Exception as e:
                self.log(f"Failed to read mod download logs: {e}", tone="bad", source="system", action="mod_log_read_failed")
        return {}

    def _write_mod_download_logs_snapshot(self, logs):
        try:
            log_path = self._get_mod_log_path()
            temp_path = f"{log_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(logs, file, indent=4)
            os.replace(temp_path, log_path)
            return True
        except Exception as e:
            self.log(f"Failed to save mod download logs: {e}", tone="bad", source="system", action="mod_log_save_failed")
            return False

    def _get_mod_download_logs_cache(self):
        with self._mod_logs_lock:
            cache = self._mod_logs_cache
        if cache is not None:
            return cache

        loaded = self._load_mod_download_logs()
        with self._mod_logs_lock:
            if self._mod_logs_cache is None:
                self._mod_logs_cache = loaded
            return self._mod_logs_cache

    def _flush_pending_mod_logs_save(self):
        with self._mod_logs_lock:
            self._mod_logs_save_timer = None
            if not self._mod_logs_dirty:
                return True
            self._mod_logs_dirty = False
            snapshot = dict(self._mod_logs_cache or {})
        return self._write_mod_download_logs_snapshot(snapshot)

    def _save_mod_download_logs(self, logs, immediate=False):
        with self._mod_logs_lock:
            self._mod_logs_cache = dict(logs or {})

        if immediate:
            with self._mod_logs_lock:
                timer = self._mod_logs_save_timer
                self._mod_logs_save_timer = None
                self._mod_logs_dirty = False
                snapshot = dict(self._mod_logs_cache or {})
            if timer is not None:
                try:
                    timer.cancel()
                except Exception:
                    pass
            return self._write_mod_download_logs_snapshot(snapshot)

        with self._mod_logs_lock:
            self._mod_logs_dirty = True
            if self._mod_logs_save_timer is not None and self._mod_logs_save_timer.is_alive():
                return True
            self._mod_logs_save_timer = threading.Timer(self._mod_logs_save_delay_sec, self._flush_pending_mod_logs_save)
            self._mod_logs_save_timer.daemon = True
            self._mod_logs_save_timer.start()
        return True

    def _update_mod_download_log(self, mod):
        mod_id = str(mod.get("mod_id", ""))
        if not mod_id:
            return
        logs = self._get_mod_download_logs_cache()
        with self._mod_logs_lock:
            logs[mod_id] = {
                "name": mod.get("mod_name", "Unknown"),
                "app_id": mod.get("app_id"),
                "timestamp": time.time(),
                "date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            }
            snapshot = dict(logs)
        self._save_mod_download_logs(snapshot)

    def _fetch_published_file_details_batch(self, mod_ids, timeout=20, chunk_size=100):
        normalized_ids = []
        seen = set()
        for mod_id in (mod_ids or []):
            key = str(mod_id or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            normalized_ids.append(key)
        if not normalized_ids:
            return {}

        url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
        details_by_id = {}
        safe_chunk_size = max(1, int(chunk_size or 1))

        for start in range(0, len(normalized_ids), safe_chunk_size):
            chunk = normalized_ids[start:start + safe_chunk_size]
            payload = {"itemcount": len(chunk)}
            for index, mod_id in enumerate(chunk):
                payload[f"publishedfileids[{index}]"] = mod_id

            try:
                response = requests.post(url, data=payload, timeout=timeout)
                details = response.json().get("response", {}).get("publishedfiledetails", [])
            except Exception:
                continue

            if not isinstance(details, list):
                continue

            for index, entry in enumerate(details):
                if not isinstance(entry, dict):
                    continue
                entry_mod_id = str(entry.get("publishedfileid", "")).strip()
                if not entry_mod_id and index < len(chunk):
                    entry_mod_id = chunk[index]
                if entry_mod_id:
                    details_by_id[entry_mod_id] = entry

        return details_by_id

    def _get_remote_mod_update_timestamps_bulk(self, mod_ids):
        normalized_ids = []
        seen = set()
        for mod_id in (mod_ids or []):
            key = str(mod_id or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            normalized_ids.append(key)
        if not normalized_ids:
            return {}

        now = time.time()
        values = {}
        missing = []

        with self._remote_update_cache_lock:
            for key in normalized_ids:
                cached = self._remote_mod_update_cache.get(key)
                if isinstance(cached, dict):
                    fetched_at = float(cached.get("fetched_at", 0.0) or 0.0)
                    if (now - fetched_at) <= self._remote_mod_update_cache_ttl_sec:
                        values[key] = cached.get("value")
                        continue
                missing.append(key)

        if missing:
            details_map = self._fetch_published_file_details_batch(missing, timeout=20, chunk_size=100)
            fetched_at = time.time()
            cache_updates = {}
            for key in missing:
                value = None
                details = details_map.get(key)
                if isinstance(details, dict):
                    ts = details.get("time_updated")
                    try:
                        value = int(ts) if ts is not None else None
                    except Exception:
                        value = None
                values[key] = value
                cache_updates[key] = {"fetched_at": fetched_at, "value": value}

            with self._remote_update_cache_lock:
                self._remote_mod_update_cache.update(cache_updates)
                if len(self._remote_mod_update_cache) > 6000:
                    self._remote_mod_update_cache = dict(list(self._remote_mod_update_cache.items())[-3000:])

        return values

    def _get_remote_mod_update_timestamp(self, mod_id):
        key = str(mod_id or "").strip()
        if not key:
            return None
        values = self._get_remote_mod_update_timestamps_bulk([key])
        return values.get(key)

    def _mark_session_downloaded(self, mod):
        mod_id = str(mod.get("mod_id", "")).strip()
        if not mod_id:
            return
        self.successful_downloads_this_session.add(mod_id)

    def _set_mod_status(self, mod, status, retry_count=None):
        if not isinstance(mod, dict):
            return False
        mod_id = str(mod.get("mod_id", "")).strip()
        changed = False
        status_changed = False
        previous_status = ""
        invalidate_queue_view = False
        with self.state_lock:
            if mod.get("status") != status:
                previous_status = str(mod.get("status", ""))
                mod["status"] = status
                changed = True
                status_changed = True

                # Status-only changes usually do not require rebuilding the full queue query cache.
                # Rebuild is only needed when the cached view depends on status membership/order.
                cache = self._queue_query_cache if isinstance(self._queue_query_cache, dict) else None
                if cache is not None:
                    cached_filter = str(cache.get("filter_name", "All") or "All")
                    cached_sort_key = str(cache.get("sort_key", "") or "")
                    if cached_filter != "All" or cached_sort_key == "status":
                        self._queue_revision += 1
                        invalidate_queue_view = True
            if retry_count is not None:
                retry_value = max(0, int(retry_count))
                current_retry = int(mod.get("retry_count", 0) or 0)
                if current_retry != retry_value:
                    mod["retry_count"] = retry_value
                    changed = True
                    if mod_id and mod_id in self._active_download_targets:
                        prev_retry = int(self._active_download_retry_by_mod.get(mod_id, 0) or 0)
                        if retry_value > prev_retry:
                            self._active_download_retry_by_mod[mod_id] = retry_value
        if status_changed and mod_id:
            retry_value = int(mod.get("retry_count", 0) or 0)
            self._emit_event(
                "queue_status",
                {
                    "mod_id": mod_id,
                    "status": status,
                    "previous_status": previous_status if status_changed else str(status),
                    "invalidate_queue_view": invalidate_queue_view,
                    "retry_count": retry_value,
                    "max_retries": int(self._download_max_retries),
                },
            )
            with self.state_lock:
                active_op_id = str(self._active_download_operation_id or "")
                tracked = mod_id in self._active_download_targets
            if tracked and active_op_id:
                self._maybe_log_download_progress(active_op_id, force=False)
        return changed

    def _format_duration_short(self, seconds: float):
        value = max(0.0, float(seconds or 0.0))
        if value < 60.0:
            return f"{value:.1f}s"
        total_seconds = int(value)
        minutes, secs = divmod(total_seconds, 60)
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours, mins = divmod(minutes, 60)
        return f"{hours}h {mins}m"

    def _get_active_download_progress_snapshot_locked(self):
        target_ids = set(self._active_download_targets or set())
        total = len(target_ids)
        if total <= 0:
            return None

        queue_map = {}
        for mod in self.download_queue:
            mod_id = str(mod.get("mod_id", "")).strip()
            if mod_id in target_ids:
                queue_map[mod_id] = mod

        queued = 0
        downloading = 0
        failed = 0
        downloaded_in_queue = 0
        for mod_id in target_ids:
            mod = queue_map.get(mod_id)
            if not mod:
                continue
            status = str(mod.get("status", "")).strip()
            if status == "Queued":
                queued += 1
            elif status == "Downloading":
                downloading += 1
            elif status == "Downloaded":
                downloaded_in_queue += 1
            elif status.startswith("Failed"):
                failed += 1

        completed = len(set(self.successful_downloads_this_session).intersection(target_ids))
        if downloaded_in_queue > completed:
            completed = downloaded_in_queue

        finished = max(0, completed + failed)
        untracked = max(0, total - (finished + downloading + queued))
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "finished": finished,
            "downloading": downloading,
            "queued": queued,
            "untracked": untracked,
        }

    def _maybe_log_download_progress(self, operation_id: str, force=False):
        op_id = str(operation_id or "").strip()
        if not op_id:
            return

        now = time.time()
        should_emit = False
        snapshot = None
        with self.state_lock:
            snapshot = self._get_active_download_progress_snapshot_locked()
            if not snapshot:
                return
            key = (
                f"{snapshot['finished']}|{snapshot['completed']}|{snapshot['failed']}|"
                f"{snapshot['downloading']}|{snapshot['queued']}|{snapshot['untracked']}|{snapshot['total']}"
            )
            elapsed = now - float(self._active_download_last_progress_at or 0.0)
            if force or (elapsed >= self._download_progress_log_interval_sec and key != str(self._active_download_last_progress_key or "")):
                self._active_download_last_progress_at = now
                self._active_download_last_progress_key = key
                should_emit = True
        if not should_emit or not snapshot:
            return

        total = int(snapshot.get("total", 0))
        finished = int(snapshot.get("finished", 0))
        completed = int(snapshot.get("completed", 0))
        failed = int(snapshot.get("failed", 0))
        downloading = int(snapshot.get("downloading", 0))
        queued = int(snapshot.get("queued", 0))
        untracked = int(snapshot.get("untracked", 0))

        message = (
            f"{finished:,}/{total:,} done | completed {completed:,} | failed {failed:,} | queued {queued:,}"
        )
        if untracked > 0:
            message += f" p {untracked:,}"

        self.log(
            message,
            source="download",
            action="download_progress",
            context={
                "total": total,
                "finished": finished,
                "completed": completed,
                "failed": failed,
                "downloading": downloading,
                "queued": queued,
                "pending": untracked,
                "operation_state": "run",
            },
            operation_id=op_id,
        )

    def _cleanup_appworkshop_acf_files(self):
        workshop_dir = os.path.join(self.steamcmd_dir, "steamapps", "workshop")
        if not os.path.isdir(workshop_dir):
            return
        for file_name in os.listdir(workshop_dir):
            if file_name.lower().startswith("appworkshop_") and file_name.lower().endswith(".acf"):
                try:
                    os.remove(os.path.join(workshop_dir, file_name))
                except Exception:
                    pass

    def _remove_all_workshop_content(self):
        workshop_content_path = os.path.join(self.steamcmd_dir, "steamapps", "workshop", "content")
        if not os.path.isdir(workshop_content_path):
            return
        for app_id in os.listdir(workshop_content_path):
            app_path = os.path.join(workshop_content_path, app_id)
            if not os.path.isdir(app_path):
                continue
            for mod_id in os.listdir(app_path):
                mod_path = os.path.join(app_path, mod_id)
                if os.path.isdir(mod_path):
                    shutil.rmtree(mod_path, ignore_errors=True)

    def _remove_mod_artifacts(self, mod):
        if mod.get("provider") == "SteamCMD":
            target_path = self._get_steamcmd_target_path(mod)
            source_path = self._get_steamcmd_content_path(mod)
            if os.path.isdir(target_path):
                shutil.rmtree(target_path, ignore_errors=True)
            if os.path.isdir(source_path):
                shutil.rmtree(source_path, ignore_errors=True)
            return

        exact_file = mod.get("_webapi_file_path")
        if exact_file:
            try:
                if os.path.isfile(exact_file):
                    os.remove(exact_file)
                    return
            except Exception:
                pass

        mod_id = str(mod.get("mod_id", ""))
        if not os.path.isdir(self.steamwebapi_download_path):
            return
        for name in os.listdir(self.steamwebapi_download_path):
            path = os.path.join(self.steamwebapi_download_path, name)
            if mod_id and mod_id in name:
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        os.remove(path)
                except Exception:
                    pass

    def _move_all_downloaded_mods(self):
        workshop_content_path = os.path.join(self.steamcmd_dir, "steamapps", "workshop", "content")
        if not os.path.isdir(workshop_content_path):
            return

        logs = self._load_mod_download_logs()
        queue_map = {}
        with self.state_lock:
            for mod in self.download_queue:
                queue_map[str(mod.get("mod_id", ""))] = mod

        for app_id in os.listdir(workshop_content_path):
            app_path = os.path.join(workshop_content_path, app_id)
            if not os.path.isdir(app_path):
                continue
            for mod_id in os.listdir(app_path):
                source_path = os.path.join(app_path, mod_id)
                if not os.path.isdir(source_path):
                    continue

                queue_mod = queue_map.get(str(mod_id))
                mod_name = None
                if queue_mod:
                    mod_name = queue_mod.get("mod_name")
                if not mod_name:
                    mod_name = logs.get(str(mod_id), {}).get("name") or f"Mod {mod_id}"

                move_mod = {
                    "mod_id": str(mod_id),
                    "mod_name": mod_name,
                    "app_id": str((queue_mod.get("app_id") if queue_mod and queue_mod.get("app_id") else app_id)),
                    "provider": "SteamCMD"
                }

                target_path = self._get_steamcmd_target_path(move_mod, allow_remote_lookup=True)
                try:
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    if os.path.isdir(target_path):
                        shutil.rmtree(target_path, ignore_errors=True)
                    shutil.move(source_path, target_path)
                    self._update_mod_download_log(move_mod)
                    self._mark_session_downloaded(move_mod)
                    if queue_mod and (queue_mod.get("status") == "Downloading" or "Failed" in str(queue_mod.get("status", ""))):
                        self._set_mod_status(queue_mod, "Downloaded")
                except Exception as e:
                    self.log(
                        f"Failed to move mod {mod_id} to Downloads/SteamCMD: {e}",
                        tone="bad",
                        source="download",
                        action="move_downloaded_mod_failed",
                        context={"mod_id": str(mod_id), "error": str(e)},
                    )

    def _get_steamcmd_login_parts(self):
        active_account = (self.config.get("active_account") or "Anonymous").strip() or "Anonymous"
        if active_account.lower() == "anonymous":
            return ["anonymous"]

        accounts = self.config.get("steam_accounts", [])
        account = next((acc for acc in accounts if acc.get("username") == active_account), None)
        if not account:
            return ["anonymous"]
        username = (account.get("username") or "").strip()
        if not username:
            return ["anonymous"]
        return [username]

    def _download_mod_webapi(self, mod, file_details=None):
        mod_id = str(mod["mod_id"])
        try:
            if not isinstance(file_details, dict):
                file_details = self._fetch_published_file_details_batch([mod_id], timeout=30, chunk_size=1).get(mod_id, {})
            file_url = file_details.get("file_url")
            if not file_url:
                return False

            filename = file_details.get("filename") or file_details.get("title") or f"{mod_id}.zip"
            filename = re.sub(r'[<>:"/\\|?*]', "_", filename.strip())
            file_path = os.path.join(self._get_download_path(mod), filename)

            download_response = requests.get(file_url, stream=True, timeout=120)
            if download_response.status_code != 200:
                return False

            with open(file_path, "wb") as file:
                for chunk in download_response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
            with self.state_lock:
                mod["_webapi_file_path"] = file_path
                self.session_webapi_files[mod_id] = file_path
            self._update_mod_download_log(mod)
            self._mark_session_downloaded(mod)
            return True
        except Exception:
            return False

    def _download_mods_webapi_parallel(self, mods, cancel_is_immediate=False):
        webapi_mods = list(mods or [])
        if not webapi_mods:
            return

        details_by_mod_id = self._fetch_published_file_details_batch(
            [str(mod.get("mod_id", "")).strip() for mod in webapi_mods],
            timeout=30,
            chunk_size=100,
        )
        max_workers = max(1, min(6, len(webapi_mods)))

        def download_one(mod):
            if cancel_is_immediate and self.canceled:
                return
            self._set_mod_status(mod, "Downloading")
            mod_id = str(mod.get("mod_id", "")).strip()
            success = self._download_mod_webapi(mod, details_by_mod_id.get(mod_id))
            if success:
                self._set_mod_status(mod, "Downloaded")
                return
            with self.state_lock:
                next_retry = int(mod.get("retry_count", 0) or 0) + 1
            self._set_mod_status(
                mod,
                "Queued" if next_retry < int(self._download_max_retries) else "Failed",
                retry_count=next_retry,
            )

        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="webapi-download") as executor:
            futures = [executor.submit(download_one, mod) for mod in webapi_mods]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception:
                    pass
                self._maybe_log_download_progress(str(self._active_download_operation_id or ""), force=False)

    def _download_mods_steamcmd(self, mods, cancel_is_immediate=False):
        if not os.path.isfile(self.steamcmd_exe):
            for mod in mods:
                self._set_mod_status(mod, "Failed: SteamCMD Missing")
            return

        existing_mod_behavior = self.config.get("steamcmd_existing_mod_behavior", "Only Redownload if Updated")
        download_logs = self._load_mod_download_logs()
        app_mod_ids = {}
        for mod in mods:
            app_id = str(mod.get("app_id", "")).strip()
            mod_id = str(mod.get("mod_id", "")).strip()
            if not app_id or not mod_id:
                continue
            app_mod_ids.setdefault(app_id, set()).add(mod_id)
        app_folder_indexes = {
            app_id: self._build_steamcmd_app_folder_index(app_id, mod_ids)
            for app_id, mod_ids in app_mod_ids.items()
        }

        prechecked = []
        remote_check_mod_ids = []
        if existing_mod_behavior == "Only Redownload if Updated":
            for mod in mods:
                app_id = mod.get("app_id")
                if not app_id:
                    continue
                app_id = str(app_id).strip()
                mod_id = str(mod.get("mod_id", "")).strip()
                folder_exists = self._check_mod_folder_exists(mod, app_folder_indexes.get(app_id))
                local_ts = 0.0
                if folder_exists:
                    local_ts = float(download_logs.get(mod_id, {}).get("timestamp", 0) or 0)
                    if local_ts > 0:
                        remote_check_mod_ids.append(mod_id)
                prechecked.append((mod, folder_exists, local_ts))
            remote_timestamps = self._get_remote_mod_update_timestamps_bulk(remote_check_mod_ids) if remote_check_mod_ids else {}
        else:
            remote_timestamps = {}

        download_candidates = []
        prechecked_index = 0
        for mod in mods:
            app_id = mod.get("app_id")
            if not app_id:
                self._set_mod_status(mod, "Failed: No AppID")
                continue
            app_id = str(app_id).strip()
            app_folder_index = app_folder_indexes.get(app_id)

            should_download = True
            if existing_mod_behavior == "Only Redownload if Updated":
                _, folder_exists, local_ts = prechecked[prechecked_index]
                prechecked_index += 1
            else:
                folder_exists = self._check_mod_folder_exists(mod, app_folder_index)
                local_ts = 0.0

            if folder_exists:
                if existing_mod_behavior == "Skip Existing Mods":
                    should_download = False
                elif existing_mod_behavior == "Always Redownload":
                    self._delete_existing_mod_folder(mod, app_folder_index)
                else:
                    mod_id = str(mod.get("mod_id"))
                    remote_ts = remote_timestamps.get(mod_id)
                    if local_ts and remote_ts and remote_ts <= local_ts:
                        should_download = False
                    else:
                        self._delete_existing_mod_folder(mod, app_folder_index)

            if should_download:
                download_candidates.append(mod)
            else:
                self._set_mod_status(mod, "Downloaded")
                self._update_mod_download_log(mod)
                self._mark_session_downloaded(mod)

        if not download_candidates:
            return

        cmd = [self.steamcmd_exe, "+login", *self._get_steamcmd_login_parts()]
        mod_lookup = {}
        status_map = {}
        for mod in download_candidates:
            app_id = str(mod.get("app_id"))
            mod_id = str(mod.get("mod_id"))
            mod_lookup[mod_id] = mod
            status_map[mod_id] = "Downloading"
            self._set_mod_status(mod, "Downloading")
            cmd.extend(["+workshop_download_item", app_id, mod_id])
        cmd.append("+quit")

        self.current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=self.steamcmd_dir,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system().lower() == "windows" else 0,
        )

        success_re = re.compile(r"Success\. Downloaded item (\d+)", re.IGNORECASE)
        failure_re = re.compile(r"ERROR! Download item (\d+) failed \(([^)]+)\)", re.IGNORECASE)

        if self.current_process.stdout:
            for line in self.current_process.stdout:
                clean_line = line.strip()
                if not clean_line:
                    continue
                status_updated = False

                success_match = success_re.search(clean_line)
                if success_match:
                    mod_id = str(success_match.group(1))
                    if mod_id in status_map and status_map.get(mod_id) != "Downloaded":
                        status_map[mod_id] = "Downloaded"
                        queue_mod = mod_lookup.get(mod_id)
                        if queue_mod:
                            self._set_mod_status(queue_mod, "Downloaded")
                            status_updated = True
                    if status_updated:
                        self._maybe_log_download_progress(str(self._active_download_operation_id or ""), force=False)
                    continue

                fail_match = failure_re.search(clean_line)
                if fail_match:
                    mod_id = str(fail_match.group(1))
                    if mod_id in status_map:
                        next_status = f"Failed: {fail_match.group(2)}"
                        if status_map.get(mod_id) != next_status:
                            status_map[mod_id] = next_status
                            queue_mod = mod_lookup.get(mod_id)
                            if queue_mod:
                                self._set_mod_status(queue_mod, next_status)
                                status_updated = True
                if status_updated:
                    self._maybe_log_download_progress(str(self._active_download_operation_id or ""), force=False)

        self.current_process.wait()
        self.current_process = None

        fallback_status = "Downloading" if (cancel_is_immediate and self.canceled) else "Failed No Confirmation"
        for mod in download_candidates:
            mod_id = str(mod.get("mod_id"))
            final_status = status_map.get(mod_id, fallback_status)
            self._set_mod_status(mod, final_status)
            if final_status == "Downloaded":
                self._update_mod_download_log(mod)
                self._mark_session_downloaded(mod)
        self._maybe_log_download_progress(str(self._active_download_operation_id or ""), force=True)

    def _finalize_cancellation(self, delete_downloads):
        keep_downloaded = bool(self.config.get("keep_downloaded_in_queue", False))

        if delete_downloads:
            self._remove_all_workshop_content()
            for file_path in list(self.session_webapi_files.values()):
                try:
                    if file_path and os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
            self.session_webapi_files = {}
        else:
            self._move_all_downloaded_mods()

        with self.state_lock:
            for mod in self.download_queue:
                status = str(mod.get("status", ""))
                if status == "Downloading":
                    mod["status"] = "Queued"
                elif delete_downloads and status == "Downloaded":
                    mod["status"] = "Queued"

            if not keep_downloaded:
                self.download_queue = [mod for mod in self.download_queue if mod.get("status") != "Downloaded"]
            self._rebuild_queue_indexes_locked()

        self._cleanup_appworkshop_acf_files()

    def _download_worker(self):
        with self.state_lock:
            operation_id = str(self._active_download_operation_id or "")
        try:
            self._maybe_log_download_progress(operation_id, force=True)
            while True:
                with self.state_lock:
                    if not self.is_downloading:
                        break
                    queued_mods = [mod for mod in self.download_queue if mod.get("status") == "Queued"]
                    delete_on_cancel = bool(self.config.get("delete_downloads_on_cancel", False))
                    cancel_requested = self.canceled

                if cancel_requested and delete_on_cancel:
                    self._finalize_cancellation(delete_downloads=True)
                    break
                if not queued_mods:
                    break

                batch_size = max(1, int(self.config.get("batch_size", 20)))
                selected_batch = list(queued_mods[:batch_size])

                steamcmd_mods = []
                webapi_mods = []
                provider_changed = False
                for mod in selected_batch:
                    provider = str(mod.get("provider", "")).strip()
                    if provider not in {"SteamCMD", "SteamWebAPI"}:
                        resolved = self._provider_for_mod(mod, self.config.get("download_provider", "Default"))
                        with self.state_lock:
                            mod["provider"] = resolved
                        provider = resolved
                        provider_changed = True
                    if provider == "SteamCMD":
                        steamcmd_mods.append(mod)
                    elif provider == "SteamWebAPI":
                        webapi_mods.append(mod)

                tasks = []
                with ThreadPoolExecutor(max_workers=2, thread_name_prefix="download-batch") as executor:
                    if steamcmd_mods:
                        tasks.append(executor.submit(self._download_mods_steamcmd, steamcmd_mods, delete_on_cancel))
                    if webapi_mods:
                        tasks.append(executor.submit(self._download_mods_webapi_parallel, webapi_mods, delete_on_cancel))
                    for future in as_completed(tasks):
                        future.result()
                        self._maybe_log_download_progress(operation_id, force=True)

                if provider_changed:
                    self._emit_event("queue", {"action": "refresh"})

                if self.canceled:
                    self._finalize_cancellation(delete_downloads=delete_on_cancel)
                    self._emit_event("queue", {"action": "refresh"})
                    break

                if not self.config.get("keep_downloaded_in_queue", False):
                    with self.state_lock:
                        self.download_queue = [mod for mod in self.download_queue if mod.get("status") != "Downloaded"]
                        self._rebuild_queue_indexes_locked()

                self._emit_event("queue", {"action": "refresh"})

            if not self.canceled:
                self._move_all_downloaded_mods()
                self._cleanup_appworkshop_acf_files()

            with self.state_lock:
                snapshot = self._get_active_download_progress_snapshot_locked() or {
                    "total": len(self._active_download_targets),
                    "finished": 0,
                    "completed": 0,
                    "failed": 0,
                    "downloading": 0,
                    "queued": 0,
                    "untracked": 0,
                }
                total = int(snapshot.get("total", 0))
                completed = int(snapshot.get("completed", 0))
                failed = int(snapshot.get("failed", 0))
                finished = int(snapshot.get("finished", 0))
                downloading = int(snapshot.get("downloading", 0))
                queued = int(snapshot.get("queued", 0))
                pending = int(snapshot.get("untracked", 0))
                provider_counts = dict(self._active_download_provider_counts or {})
                retry_total = 0
                for value in (self._active_download_retry_by_mod or {}).values():
                    retry_total += max(0, int(value or 0))
                started_at = float(self._active_download_started_at or 0.0)
                duration_seconds = max(0.0, time.time() - started_at) if started_at > 0 else 0.0

            duration_text = self._format_duration_short(duration_seconds)
            if self.canceled:
                summary_action = "download_run_canceled"
                summary_tone = "info"
                summary_state = "canceled"
                summary_message = (
                    f"Download run canceled: {completed:,}/{total:,} completed, {failed:,} failed "
                    f"in {duration_text}."
                )
            else:
                summary_action = "download_run_completed"
                summary_tone = "bad" if failed > 0 else "good"
                summary_state = "done" if failed <= 0 else "error"
                summary_message = (
                    f"Download run complete: {completed:,}/{total:,} completed, {failed:,} failed "
                    f"in {duration_text}."
                )

            self.log(
                summary_message,
                tone=summary_tone,
                source="download",
                action=summary_action,
                context={
                    "total": total,
                    "finished": finished,
                    "completed": completed,
                    "failed": failed,
                    "downloading": downloading,
                    "queued": queued,
                    "pending": pending,
                    "duration_seconds": duration_seconds,
                    "duration_text": duration_text,
                    "retry_total": retry_total,
                    "provider_counts": provider_counts,
                    "operation_state": summary_state,
                },
                operation_id=operation_id,
            )

            with self.state_lock:
                self.is_downloading = False
                self._active_download_operation_id = ""
                self._active_download_targets = set()
                self._active_download_provider_counts = {"SteamCMD": 0, "SteamWebAPI": 0}
                self._active_download_started_at = 0.0
                self._active_download_retry_by_mod = {}
                self._active_download_last_progress_at = 0.0
                self._active_download_last_progress_key = ""
            self._emit_event(
                "download",
                {"state": "canceled" if self.canceled else "finished", "operation_id": operation_id},
            )
            self._emit_event("queue", {"action": "refresh"})
        except Exception as e:
            with self.state_lock:
                self.is_downloading = False
                self._active_download_operation_id = ""
                self._active_download_targets = set()
                self._active_download_provider_counts = {"SteamCMD": 0, "SteamWebAPI": 0}
                self._active_download_started_at = 0.0
                self._active_download_retry_by_mod = {}
                self._active_download_last_progress_at = 0.0
                self._active_download_last_progress_key = ""
            self.log(
                f"Download worker crashed: {e}",
                tone="bad",
                source="download",
                action="worker_crashed",
                context={"error": str(e)},
                operation_id=operation_id,
            )
            self._emit_event("download", {"state": "error", "error": str(e), "operation_id": operation_id})

    def start_download(self):
        with self.state_lock:
            if self.is_downloading:
                return {"success": False, "error": "Download already in progress."}
            if not self.download_queue:
                return {"success": False, "error": "Download queue is empty."}
            queued_mods = [mod for mod in self.download_queue if mod.get("status") == "Queued"]
            if not queued_mods:
                return {"success": False, "error": "No queued mods available for download."}
            operation_id = self._next_operation_id("download")
            self.is_downloading = True
            self.canceled = False
            self.successful_downloads_this_session = set()
            self.session_webapi_files = {}
            self._active_download_operation_id = operation_id
            selected_provider = self.config.get("download_provider", "Default")
            provider_counts = {"SteamCMD": 0, "SteamWebAPI": 0}
            target_ids = set()
            for mod in queued_mods:
                mod_id = str(mod.get("mod_id", "")).strip()
                if not mod_id:
                    continue
                target_ids.add(mod_id)
                provider = str(mod.get("provider", "")).strip()
                if provider not in {"SteamCMD", "SteamWebAPI"}:
                    provider = self._provider_for_mod(mod, selected_provider)
                if provider in provider_counts:
                    provider_counts[provider] += 1
            self._active_download_targets = target_ids
            self._active_download_provider_counts = provider_counts
            self._active_download_started_at = time.time()
            self._active_download_retry_by_mod = {}
            self._active_download_last_progress_at = 0.0
            self._active_download_last_progress_key = ""
            batch_size = max(1, int(self.config.get("batch_size", 20)))
            active_account = str(self.config.get("active_account", "Anonymous") or "Anonymous")

        total_targets = len(target_ids)
        self.log(
            (
                f"Download run started: {total_targets:,} queued "
                f"(SteamCMD {provider_counts['SteamCMD']:,}, WebAPI {provider_counts['SteamWebAPI']:,}), "
                f"batch size {batch_size}."
            ),
            source="download",
            action="download_run_started",
            context={
                "queued_total": total_targets,
                "provider_counts": provider_counts,
                "batch_size": batch_size,
                "active_account": active_account,
                "operation_state": "run",
            },
            operation_id=operation_id,
        )
        with self._remote_update_cache_lock:
            self._remote_mod_update_cache = {}
        threading.Thread(target=self._download_worker, daemon=True).start()
        self._emit_event("download", {"state": "started", "operation_id": operation_id})
        return {"success": True}

    def cancel_download(self):
        delete_on_cancel = bool(self.config.get("delete_downloads_on_cancel", False))
        with self.state_lock:
            if not self.is_downloading:
                return {"success": False, "error": "No active download."}
            self.canceled = True
        if delete_on_cancel and self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
            except Exception:
                pass
        mode = "immediate" if delete_on_cancel else "after_batch"
        return {"success": True, "mode": mode}

    def open_downloads_folder(self, mod_id=None):
        target = self.downloads_root
        if mod_id:
            with self.state_lock:
                mod = next((m for m in self.download_queue if str(m.get("mod_id")) == str(mod_id)), None)
            if mod:
                target = self._get_download_path(mod)
        os.makedirs(target, exist_ok=True)
        if hasattr(os, "startfile"):
            os.startfile(target)  # type: ignore[attr-defined]
        return {"success": True, "message": target}

    def get_settings(self):
        return dict(self.config)

    def update_settings(self, settings: dict):
        for key, value in (settings or {}).items():
            if key in self.default_settings:
                self.config[key] = value
        if not self.config.get("auto_detect_urls", False):
            self.config["auto_add_to_queue"] = False
            self._stop_clipboard_monitoring()
        else:
            self._start_clipboard_monitoring()
        self.save_config()
        self._emit_event("settings", {"config": dict(self.config)})
        return {"success": True, "config": dict(self.config)}

    def _get_clipboard_sequence_windows(self):
        if platform.system().lower() != "windows":
            return 0
        try:
            return int(ctypes.windll.user32.GetClipboardSequenceNumber())
        except Exception:
            return 0

    def _start_clipboard_monitoring(self):
        if platform.system().lower() != "windows":
            return
        thread = self._clipboard_monitor_thread
        if thread is not None and thread.is_alive():
            return
        self._clipboard_stop_event = threading.Event()
        self._clipboard_last_seq = self._get_clipboard_sequence_windows()
        self._clipboard_monitor_thread = threading.Thread(
            target=self._clipboard_monitor_loop,
            name="streamline-clipboard-monitor",
            daemon=True,
        )
        self._clipboard_monitor_thread.start()

    def _stop_clipboard_monitoring(self):
        thread = self._clipboard_monitor_thread
        if thread is None:
            return
        self._clipboard_stop_event.set()
        if thread.is_alive():
            try:
                thread.join(timeout=0.75)
            except Exception:
                pass
        self._clipboard_monitor_thread = None

    def _read_clipboard_text_windows(self):
        if platform.system().lower() != "windows":
            return ""

        user32 = ctypes.windll.user32
        kernel32_local = ctypes.windll.kernel32
        cf_unicode_text = 13

        for _ in range(3):
            if not user32.OpenClipboard(None):
                time.sleep(0.03)
                continue
            try:
                handle = user32.GetClipboardData(cf_unicode_text)
                if not handle:
                    return ""
                locked = kernel32_local.GlobalLock(handle)
                if not locked:
                    return ""
                try:
                    return ctypes.wstring_at(locked) or ""
                finally:
                    kernel32_local.GlobalUnlock(handle)
            except Exception:
                return ""
            finally:
                try:
                    user32.CloseClipboard()
                except Exception:
                    pass
        return ""

    def _is_valid_workshop_clipboard_input(self, text: str):
        value = (text or "").strip()
        if not value:
            return False

        patterns = [
            r"^https?://steamcommunity\.com/sharedfiles/filedetails/\?id=\d+",
            r"^https?://steamcommunity\.com/workshop/filedetails/\?id=\d+",
            r"^https?://store\.steampowered\.com/app/\d+",
            r"^https?://steamcommunity\.com/app/\d+",
        ]
        return any(re.match(pattern, value, flags=re.IGNORECASE) for pattern in patterns)

    def _check_clipboard_for_url(self):
        if not self.config.get("auto_detect_urls", False):
            return

        current_text = (self._read_clipboard_text_windows() or "").strip()
        if not current_text:
            return

        if current_text == self.last_clipboard_text:
            return

        current_time = time.time()
        if current_time - self._last_clipboard_trigger < 0.5:
            return
        self._last_clipboard_trigger = current_time
        self.last_clipboard_text = current_text

        if not self._is_valid_workshop_clipboard_input(current_text):
            return

        self._emit_event("clipboard", {"url": current_text})

        if self.config.get("auto_add_to_queue", False):
            provider = self.config.get("download_provider", "Default")
            result = self.add_preview_queue_item(current_text, "", provider)
            if not result.get("success"):
                error_text = str(result.get("error") or "")
                if "Invalid input" not in error_text:
                    self.log(
                        f"Auto-add from clipboard failed: {error_text}",
                        tone="bad",
                        source="clipboard",
                        action="auto_add_failed",
                        context={"error": str(error_text)},
                    )

    def _clipboard_monitor_loop(self):
        last_fallback_check = 0.0
        while not self._clipboard_stop_event.is_set():
            try:
                seq = self._get_clipboard_sequence_windows()
                if seq > 0:
                    if seq != self._clipboard_last_seq:
                        self._clipboard_last_seq = seq
                        self._check_clipboard_for_url()
                else:
                    now = time.time()
                    if now - last_fallback_check >= 0.35:
                        last_fallback_check = now
                        self._check_clipboard_for_url()
            except Exception:
                pass
            self._clipboard_stop_event.wait(0.1)

    def _normalize_account_record(self, account):
        record = dict(account or {})
        record["username"] = str(record.get("username", "")).strip()
        record["steamid64"] = str(record.get("steamid64", "")).strip()
        record.pop("token_id", None)
        return record

    def _get_steamcmd_config_vdf_path(self):
        return os.path.join(self.steamcmd_dir, "config", "config.vdf")

    def _get_steamcmd_connection_log_path(self):
        return os.path.join(self.steamcmd_dir, "logs", "connection_log.txt")

    def _get_steamcmd_console_log_path(self):
        return os.path.join(self.steamcmd_dir, "logs", "console_log.txt")

    def _get_file_size(self, path):
        try:
            return os.path.getsize(path)
        except Exception:
            return 0

    def _read_file_chunk(self, path, offset=0):
        if not os.path.isfile(path):
            return ""
        try:
            with open(path, "rb") as f:
                if offset:
                    f.seek(max(0, int(offset)), os.SEEK_SET)
                return f.read().decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _extract_accounts_from_vdf_lines(self, lines):
        accounts = {}
        waiting_for_accounts_open = False
        in_accounts_block = False
        depth = 0
        current_username = None

        for raw in lines:
            stripped = raw.strip()

            if not in_accounts_block:
                if '"Accounts"' in stripped:
                    waiting_for_accounts_open = True
                    continue
                if waiting_for_accounts_open and stripped.startswith("{"):
                    in_accounts_block = True
                    waiting_for_accounts_open = False
                    depth = 1
                continue

            if stripped.startswith("{"):
                depth += 1
                continue

            if stripped.startswith("}"):
                if depth == 2:
                    current_username = None
                depth -= 1
                if depth <= 0:
                    break
                continue

            if depth == 1:
                user_match = re.match(r'^"([^"]+)"\s*$', stripped)
                if user_match:
                    current_username = user_match.group(1)
                    accounts.setdefault(current_username, {"steamid64": ""})
                continue

            if depth >= 2 and current_username:
                steamid_match = re.match(r'^"SteamID"\s+"(\d+)"', stripped)
                if steamid_match:
                    accounts[current_username]["steamid64"] = steamid_match.group(1)

        return accounts

    def _convert_account_id_to_steamid64(self, account_id):
        try:
            return str(int(account_id) + 76561197960265728)
        except Exception:
            return ""

    def _detect_login_success_from_logs(self, context):
        context = context or {}
        conn_offset = int(context.get("connection_log_offset", 0) or 0)
        console_offset = int(context.get("console_log_offset", 0) or 0)
        username = str(context.get("detected_username") or context.get("username") or "").strip().lower()

        conn_chunk = self._read_file_chunk(self._get_steamcmd_connection_log_path(), conn_offset)
        console_chunk = self._read_file_chunk(self._get_steamcmd_console_log_path(), console_offset)

        ok_marker = "RecvMsgClientLogOnResponse()" in conn_chunk and "'OK'" in conn_chunk

        account_id = None
        for line in conn_chunk.splitlines():
            if "RecvMsgClientLogOnResponse()" in line and "'OK'" in line:
                match = re.search(r"\[U:1:(\d+)\]", line)
                if match:
                    account_id = match.group(1)

        steamid64 = self._convert_account_id_to_steamid64(account_id) if account_id else str(context.get("detected_steamid64", "")).strip()
        username_seen = (f"logging in user '{username}'" in console_chunk.lower()) if username else False

        output_success = bool(context.get("output_success") or context.get("login_success"))
        return {
            "success": bool(ok_marker or output_success),
            "steamid64": steamid64,
            "username_seen": username_seen,
        }

    def get_accounts(self):
        accounts = [self._normalize_account_record(acc) for acc in self.config.get("steam_accounts", [])]
        return {"accounts": accounts, "active": self.config.get("active_account", "Anonymous")}

    def add_account(self, username, steamid64=""):
        username = (username or "").strip()
        if not username:
            return {"success": False, "error": "Username is required."}
        steamid64 = (steamid64 or "").strip()
        accounts = [self._normalize_account_record(acc) for acc in self.config.get("steam_accounts", [])]
        existing = next((acc for acc in accounts if acc.get("username", "").lower() == username.lower()), None)
        if existing:
            current_steamid64 = str(existing.get("steamid64", "")).strip()
            if steamid64 and current_steamid64 != steamid64:
                existing["steamid64"] = steamid64
                self.config["steam_accounts"] = accounts
                self.save_config()
                return {"success": True, "updated": True}
            return {"success": False, "error": "Account already exists."}
        accounts.append({
            "username": username,
            "steamid64": steamid64,
        })
        self.config["steam_accounts"] = accounts
        self.save_config()
        return {"success": True}

    def remove_account(self, username):
        accounts = self.config.get("steam_accounts", [])
        self.config["steam_accounts"] = [acc for acc in accounts if acc.get("username") != username]
        if self.config.get("active_account") == username:
            self.config["active_account"] = "Anonymous"
        self.save_config()
        return {"success": True}

    def purge_accounts(self):
        self.config["steam_accounts"] = []
        self.config["active_account"] = "Anonymous"
        self.save_config()
        return {"success": True}

    def reorder_accounts(self, usernames):
        accounts = [self._normalize_account_record(acc) for acc in self.config.get("steam_accounts", [])]
        if not isinstance(usernames, list):
            return {"success": False, "error": "Invalid account order payload."}
        if not accounts:
            return {"success": True}

        seen = set()
        requested = []
        for value in usernames:
            name = str(value or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            requested.append(key)

        accounts_by_name = {
            str(acc.get("username", "")).strip().lower(): acc
            for acc in accounts
            if str(acc.get("username", "")).strip()
        }

        reordered = []
        used = set()

        for key in requested:
            acc = accounts_by_name.get(key)
            if acc is None:
                continue
            reordered.append(acc)
            used.add(key)

        for acc in accounts:
            key = str(acc.get("username", "")).strip().lower()
            if not key or key in used:
                continue
            reordered.append(acc)
            used.add(key)

        self.config["steam_accounts"] = reordered
        self.save_config()
        return {"success": True}

    def set_active_account(self, username):
        self.config["active_account"] = (username or "Anonymous").strip() or "Anonymous"
        self.save_config()
        return {"success": True}

    def launch_steamcmd_login(self, username):
        username = (username or "").strip()
        if not username:
            return {"success": False, "error": "Username is required."}
        if not os.path.isfile(self.steamcmd_exe):
            return {"success": False, "error": "SteamCMD is not installed."}

        if platform.system().lower() != "windows":
            return {"success": False, "error": "ConPTY login is only supported on Windows."}

        with self.steamcmd_login_lock:
            if self.steamcmd_login_session is not None:
                try:
                    state = self.steamcmd_login_session.poll()
                    if state.get("running"):
                        return {"success": False, "error": "A SteamCMD login session is already running."}
                    self.steamcmd_login_session.close(force=True)
                except Exception:
                    pass
                self.steamcmd_login_session = None

        try:
            conn_offset = self._get_file_size(self._get_steamcmd_connection_log_path())
            console_offset = self._get_file_size(self._get_steamcmd_console_log_path())
            self.pending_login_context = {
                "username": username,
                "started_at": time.time(),
                "connection_log_offset": conn_offset,
                "console_log_offset": console_offset,
                "tail_connection_log_offset": conn_offset,
                "tail_console_log_offset": console_offset,
                "output_text": "",
                "output_success": False,
                "login_success": False,
                "login_failed": False,
                "detected_username": username,
                "detected_account_id": "",
                "detected_steamid64": "",
            }

            session = SteamCmdConPTYSession(self.steamcmd_exe, self.steamcmd_dir, username)
            ok, error = session.start()
            if not ok:
                self.pending_login_context = None
                return {"success": False, "error": f"Failed to start ConPTY session: {error}"}

            self.steamcmd_login_session = session
            return {"success": True, "mode": "conpty"}
        except Exception as e:
            self.pending_login_context = None
            return {"success": False, "error": str(e)}

    def _extract_latest_account_id(self, text: str):
        matches = re.findall(r"\[U:1:(\d+)\]", text or "")
        for value in reversed(matches):
            if value and value != "0":
                return value
        return ""

    def _analyze_login_output(self, output_text: str):
        ctx = self.pending_login_context
        if not ctx:
            return {
                "prompt": "",
                "status_hint": "running",
                "needs_password": False,
                "needs_guard": False,
                "ready_prompt": False,
                "login_success": False,
                "account_added": False,
                "login_failed": False,
                "detected_username": "",
                "detected_account_id": "",
                "detected_steamid64": "",
            }

        recent_text = str(output_text or "")
        recent_low = recent_text.lower()

        if output_text:
            ctx["output_text"] = (ctx.get("output_text", "") + output_text)[-160000:]
        combined = str(ctx.get("output_text", ""))
        low = combined.lower()

        username = str(ctx.get("detected_username") or ctx.get("username") or "").strip()
        username_hits = re.findall(r"logging in user '([^']+)'", combined, flags=re.IGNORECASE)
        if username_hits:
            username = str(username_hits[-1]).strip()

        account_id = str(ctx.get("detected_account_id", "")).strip()
        latest_account_id = self._extract_latest_account_id(combined)
        if latest_account_id:
            account_id = latest_account_id
        steamid64 = self._convert_account_id_to_steamid64(account_id) if account_id else str(ctx.get("detected_steamid64", "")).strip()

        needs_password_recent = "password:" in recent_low
        needs_guard_recent = any(token in recent_low for token in [
            "steam guard",
            "two-factor",
            "authenticator code",
            "waiting for confirmation",
            "updateauthsessionwithsteamguardcode",
        ])
        needs_password = "password:" in low
        needs_guard = any(token in low for token in [
            "steam guard",
            "two-factor",
            "authenticator code",
            "waiting for confirmation",
            "updateauthsessionwithsteamguardcode",
        ])
        ready_prompt = "steam>" in low
        waiting_for_user_info = "waiting for user info" in low
        waiting_idx = low.rfind("waiting for user info")
        success_after_waiting = False
        if waiting_idx >= 0:
            tail = low[waiting_idx:]
            ok_after_waiting = re.search(r"(?:^|\n)\s*(?:\[[^\]]+\]\s*)?ok\s*(?:\n|$)", tail, flags=re.IGNORECASE) is not None
            success_after_waiting = bool(ok_after_waiting or ("steam>" in tail))

        login_success = any(token in low for token in [
            "recvmsgclientlogonresponse()",
            "successfully generated token via password authentication",
            "waiting for user info",
        ])
        if ready_prompt and (waiting_for_user_info or "recvmsgclientlogonresponse()" in low):
            login_success = True
        if success_after_waiting:
            login_success = True

        account_added = bool(waiting_for_user_info or success_after_waiting or (ready_prompt and waiting_for_user_info))

        login_failed = any(token in low for token in [
            "login failure",
            "invalid password",
            "incorrect password",
            "account logon denied",
            "too many login failures",
            "failed to begin authentication session",
            "captcha",
        ])
        if login_success:
            login_failed = False

        prompt = ""
        if needs_password_recent:
            prompt = "password"
        elif needs_guard_recent:
            prompt = "steam_guard"
        elif "steam>" in recent_low:
            prompt = "command"

        status_hint = "running"
        if login_failed:
            status_hint = "failed"
        elif needs_password:
            status_hint = "password"
        elif needs_guard:
            status_hint = "steam_guard"
        elif "logging in user" in low or "proceeding with login using username/password" in low:
            status_hint = "authenticating"
        elif account_added:
            status_hint = "added"
        elif login_success and ready_prompt:
            status_hint = "ready"
        elif waiting_for_user_info:
            status_hint = "waiting_user_info"
        elif ready_prompt:
            status_hint = "command"

        ctx["detected_username"] = username
        ctx["detected_account_id"] = account_id
        ctx["detected_steamid64"] = steamid64
        ctx["output_success"] = bool(ctx.get("output_success") or login_success)
        ctx["login_success"] = bool(login_success)
        ctx["login_failed"] = bool(login_failed)

        return {
            "prompt": prompt,
            "status_hint": status_hint,
            "needs_password": needs_password,
            "needs_guard": needs_guard,
            "ready_prompt": ready_prompt,
            "login_success": login_success,
            "account_added": account_added,
            "login_failed": login_failed,
            "detected_username": username,
            "detected_account_id": account_id,
            "detected_steamid64": steamid64,
        }

    def _tail_login_log_output(self):
        ctx = self.pending_login_context
        if not ctx:
            return ""

        chunks = []
        pairs = [
            ("tail_console_log_offset", self._get_steamcmd_console_log_path()),
            ("tail_connection_log_offset", self._get_steamcmd_connection_log_path()),
        ]
        for key, path in pairs:
            start_offset = int(ctx.get(key, 0) or 0)
            file_size = self._get_file_size(path)
            if file_size < start_offset:
                start_offset = 0
            if file_size > start_offset:
                chunk = self._read_file_chunk(path, start_offset)
                if chunk:
                    chunks.append(chunk)
            ctx[key] = file_size
        return "".join(chunks)

    def poll_steamcmd_login_session(self):
        with self.steamcmd_login_lock:
            session = self.steamcmd_login_session
            if session is None:
                return {"success": True, "has_session": False, "running": False, "done": True, "output": ""}

            try:
                state = session.poll()
            except Exception as e:
                return {"success": False, "error": str(e)}

            output = (state.get("output", "") or "") + self._tail_login_log_output()
            analysis = self._analyze_login_output(output)
            ctx = self.pending_login_context or {}

            return {
                "success": True,
                "has_session": True,
                "running": bool(state.get("running")),
                "done": bool(state.get("done")),
                "exit_code": state.get("exit_code"),
                "output": output,
                "prompt": analysis.get("prompt", ""),
                "status_hint": analysis.get("status_hint", "running"),
                "login_success": bool(analysis.get("login_success")),
                "account_added": bool(analysis.get("account_added")),
                "login_failed": bool(analysis.get("login_failed")),
                "username": str(ctx.get("username", "")),
                "detected_username": str(analysis.get("detected_username", "")),
                "detected_account_id": str(analysis.get("detected_account_id", "")),
                "detected_steamid64": str(analysis.get("detected_steamid64", "")),
            }

    def send_steamcmd_login_input(self, text):
        with self.steamcmd_login_lock:
            session = self.steamcmd_login_session
            if session is None:
                return {"success": False, "error": "No active SteamCMD login session."}
            return session.send(text)

    def close_steamcmd_login_session(self, force=True):
        with self.steamcmd_login_lock:
            session = self.steamcmd_login_session
            if session is None:
                return {"success": True}
            try:
                session.close(force=bool(force))
            finally:
                self.steamcmd_login_session = None
            return {"success": True}

    def get_appids_info(self):
        appids_path = os.path.join(self.files_dir, "AppIDs.txt")
        if not os.path.isfile(appids_path):
            return {"exists": False, "count": 0, "last_updated": None}
        with open(appids_path, "r", encoding="utf-8") as f:
            count = len([line for line in f if line.strip()])
        return {
            "exists": True,
            "count": count,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(appids_path)))
        }

    def update_appids(self, selected_types):
        selected_types = selected_types or ["Game"]
        scraper = AppIDScraper(self.files_dir)
        try:
            entries = scraper.scrape_steamdb(selected_types)
        except Exception as e:
            return {"success": False, "error": f"Failed to update AppIDs via Botasaurus: {e}"}

        if not entries:
            return {"success": False, "error": "SteamDB scraping returned zero AppIDs."}

        appids_path = os.path.join(self.files_dir, "AppIDs.txt")
        with open(appids_path, "w", encoding="utf-8") as f:
            f.write("\n".join(entries))
        self._load_app_ids()
        return {"success": True, "count": len(entries)}

    def launch_documentation(self):
        webbrowser.open("https://github.com/dane-9/Streamline-Workshop-Downloader/wiki/Documentation")
        return {"success": True}

    def launch_report_issue(self):
        webbrowser.open("https://github.com/dane-9/Streamline-Workshop-Downloader/issues")
        return {"success": True}

    def launch_repository(self):
        webbrowser.open("https://github.com/dane-9/Streamline-Workshop-Downloader")
        return {"success": True}

    def clear_logs(self):
        with self.state_lock:
            self.runtime_logs = []
        self._emit_event("clear_logs", {})
        return {"success": True}
