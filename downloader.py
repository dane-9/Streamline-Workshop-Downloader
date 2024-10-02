import sys
import os
import subprocess
import threading
import requests
import json
import re
import zipfile
import webbrowser
import time
from io import BytesIO
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QTextEdit,
    QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QMessageBox,
    QComboBox, QDialog, QSpinBox, QFormLayout, QDialogButtonBox,
    QAction, QMenu, QCheckBox, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QThread, QSize
from PyQt5.QtGui import QTextCursor
from bs4 import BeautifulSoup

class SettingsDialog(QDialog):
    def __init__(self, current_batch_size, show_logs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(350, 150)

        layout = QFormLayout(self)

        self.batch_size_spinbox = QSpinBox()
        self.batch_size_spinbox.setRange(1, 1000)
        self.batch_size_spinbox.setValue(current_batch_size)
        layout.addRow("Batch Size:", self.batch_size_spinbox)

        self.show_logs_checkbox = QCheckBox("Show Logs")
        self.show_logs_checkbox.setChecked(show_logs)
        layout.addRow(self.show_logs_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self):
        return {
            'batch_size': self.batch_size_spinbox.value(),
            'show_logs': self.show_logs_checkbox.isChecked(),
        }


class AddSteamAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Steam Account")
        self.setModal(True)
        self.resize(300, 100)

        layout = QFormLayout(self)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter Steam Username")
        layout.addRow("Username:", self.username_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_username(self):
        return self.username_input.text().strip()
        
class TokenMonitorWorker(QThread):
    token_found = pyqtSignal(str)
    timeout = pyqtSignal()

    def __init__(self, steamcmd_dir, existing_tokens, timeout_duration=300):
        super().__init__()
        self.steamcmd_dir = steamcmd_dir
        self.existing_tokens = existing_tokens
        self.timeout_duration = timeout_duration

    def run(self):
        new_token_id = None
        start_time = time.time()
        while not new_token_id and (time.time() - start_time) < self.timeout_duration:
            time.sleep(1)
            current_tokens = self.get_all_token_ids()
            new_tokens = current_tokens - self.existing_tokens
            if new_tokens:
                new_token_id = new_tokens.pop()
                self.token_found.emit(new_token_id)
                return
        self.timeout.emit()

    def get_all_token_ids(self):
        token_ids = set()
        config_vdf_path = os.path.join(self.steamcmd_dir, 'config', 'config.vdf')
        if not os.path.isfile(config_vdf_path):
            return token_ids
        try:
            with open(config_vdf_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            in_connect_cache = False
            for line in lines:
                if '"ConnectCache"' in line:
                    in_connect_cache = True
                elif in_connect_cache:
                    # End of ConnectCache section
                    if "}" in line:
                        break
                    # Look for token lines
                    match = re.match(r'\s*"([^"]+)"\s*"\d{2,}.*"', line)
                    if match:
                        token_ids.add(match.group(1))
        except Exception as e:
            print(f"Error reading config.vdf: {e}")
        return token_ids
        
class ConfigureSteamAccountsDialog(QDialog):
    def __init__(self, config, steamcmd_dir, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Steam Accounts")
        self.setModal(True)
        self.resize(500, 400)
        self.config = config  # Store the passed config
        self.steamcmd_dir = steamcmd_dir
        self.token_monitor_worker = None
        self.steamcmd_process = None

        layout = QVBoxLayout(self)

        self.accounts_list = QTreeWidget()
        self.accounts_list.setColumnCount(1)
        self.accounts_list.setHeaderLabels(['Username'])
        self.accounts_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.accounts_list.customContextMenuRequested.connect(self.open_context_menu)
        layout.addWidget(self.accounts_list)

        self.add_account_btn = QPushButton("Add Steam Account")
        self.add_account_btn.clicked.connect(self.add_steam_account)
        layout.addWidget(self.add_account_btn)

        self.purge_accounts_btn = QPushButton("Purge Accounts")
        self.purge_accounts_btn.clicked.connect(self.purge_accounts)
        layout.addWidget(self.purge_accounts_btn)

        self.load_accounts()

    def load_accounts(self):
        self.accounts_list.clear()
        for account in self.config['steam_accounts']:
            username = account.get('username', '')
            item = QTreeWidgetItem([username])
            self.accounts_list.addTopLevelItem(item)

    def add_steam_account(self):
        dialog = AddSteamAccountDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            username = dialog.get_username()
            if not username:
                QMessageBox.warning(self, 'Input Error', 'Username cannot be empty.')
                return
            if any(acc['username'] == username for acc in self.config['steam_accounts']):
                QMessageBox.warning(self, 'Duplicate Account', 'This Steam account is already added.')
                return
            existing_tokens = self.get_all_token_ids()
            self.launch_steamcmd(username)
    
            # Start the token monitoring worker
            self.token_monitor_worker = TokenMonitorWorker(self.steamcmd_dir, existing_tokens)
            self.token_monitor_worker.token_found.connect(lambda token_id: self.on_token_found(username, token_id))
            self.token_monitor_worker.timeout.connect(lambda: self.on_token_timeout(username))
            self.token_monitor_worker.start()

    def on_token_found(self, username, new_token_id):
        self.config['steam_accounts'].append({
            'username': username,
            'token_id': new_token_id
        })
        self.load_accounts()
        QMessageBox.information(self, 'Success', f"Steam account '{username}' added.")
        # Terminate SteamCMD process
        if self.steamcmd_process and self.steamcmd_process.poll() is None:
            self.steamcmd_process.terminate()
        self.token_monitor_worker = None

    def on_token_timeout(self, username):
        QMessageBox.warning(self, 'Error', f"Failed to retrieve token ID for account '{username}'. Please ensure you have logged in successfully.")
        self.token_monitor_worker = None  # Clean up the worker

    def open_context_menu(self, position):
        selected_items = self.accounts_list.selectedItems()
        if not selected_items:
            return
        menu = QMenu()
        reauth_action = QAction("Reauthenticate", self)
        reauth_action.triggered.connect(self.reauthenticate_account)
        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(self.remove_account)
        menu.addAction(reauth_action)
        menu.addAction(remove_action)
        menu.exec_(self.accounts_list.viewport().mapToGlobal(position))

    def reauthenticate_account(self):
        selected_items = self.accounts_list.selectedItems()
        if not selected_items:
            return
        item = selected_items[0]
        username = item.text(0)
        account = next((acc for acc in self.config['steam_accounts'] if acc['username'] == username), None)
        if account and self.remove_token_from_config_vdf(account.get('token_id', '')):
            existing_tokens = self.get_all_token_ids()
            self.launch_steamcmd(username)

            # Start the token monitoring worker
            self.token_monitor_worker = TokenMonitorWorker(self.steamcmd_dir, existing_tokens)
            self.token_monitor_worker.token_found.connect(lambda new_token_id: self.on_token_found_reauth(username, new_token_id))
            self.token_monitor_worker.timeout.connect(lambda: self.on_token_timeout_reauth(username))
            self.token_monitor_worker.start()
        else:
            QMessageBox.warning(self, 'Error', f"Failed to remove token for account '{username}'.")

    def on_token_found_reauth(self, username, new_token_id):
        for account in self.config['steam_accounts']:
            if account['username'] == username:
                account['token_id'] = new_token_id
                break
        self.load_accounts()
        QMessageBox.information(self, 'Success', f"Account '{username}' reauthenticated.")
        # Terminate SteamCMD process
        if self.steamcmd_process and self.steamcmd_process.poll() is None:
            self.steamcmd_process.terminate()
        self.token_monitor_worker = None

    def on_token_timeout_reauth(self, username):
        QMessageBox.warning(self, 'Error', f"Failed to retrieve new token ID for account '{username}'. Please ensure you have logged in successfully.")
        self.token_monitor_worker = None  # Clean up the worker

    def remove_account(self):
        selected_items = self.accounts_list.selectedItems()
        if not selected_items:
            return
        item = selected_items[0]
        username = item.text(0)
        account = next((acc for acc in self.config['steam_accounts'] if acc['username'] == username), None)
        if not account:
            return
        token_id = account.get('token_id', '')
        reply = QMessageBox.question(self, 'Remove Account', f"Are you sure you want to remove account '{username}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.remove_token_from_config_vdf(token_id):
                self.config['steam_accounts'] = [acc for acc in self.config['steam_accounts'] if acc['username'] != username]
                self.load_accounts()
                QMessageBox.information(self, 'Success', f"Account '{username}' removed.")
            else:
                QMessageBox.warning(self, 'Error', f"Failed to remove token for account '{username}'.")

    def purge_accounts(self):
        reply = QMessageBox.question(self, 'Purge Accounts', 'Are you sure you want to remove all accounts?', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Remove tokens from config.vdf for all accounts
            for account in self.config['steam_accounts']:
                token_id = account.get('token_id', '')
                if token_id:
                    self.remove_token_from_config_vdf(token_id)
            self.config['steam_accounts'] = []
            self.load_accounts()
            QMessageBox.information(self, 'Success', 'All accounts have been purged.')

    def get_all_token_ids(self):
        token_ids = set()
        config_vdf_path = os.path.join(self.steamcmd_dir, 'config', 'config.vdf')
        if not os.path.isfile(config_vdf_path):
            return token_ids
        try:
            with open(config_vdf_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            in_connect_cache = False
            for line in lines:
                if '"ConnectCache"' in line:
                    in_connect_cache = True
                elif in_connect_cache:
                    if "}" in line:
                        break
                    match = re.match(r'\s*"([^"]+)"\s*"\d{2,}.*"', line)
                    if match:
                        token_ids.add(match.group(1))
        except Exception as e:
            print(f"Error reading config.vdf: {e}")
        return token_ids

    def remove_token_from_config_vdf(self, token_id):
        if not token_id:
            return True
        config_vdf_path = os.path.join(self.steamcmd_dir, 'config', 'config.vdf')
        if not os.path.isfile(config_vdf_path):
            return False
        try:
            with open(config_vdf_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            new_lines = []
            in_connect_cache = False
            skip_next_line = False
            for line in lines:
                if '"ConnectCache"' in line:
                    in_connect_cache = True
                    new_lines.append(line)
                elif in_connect_cache:
                    if skip_next_line:
                        skip_next_line = False
                        continue  # Skip the line after the token line
                    if f'"{token_id}"' in line:
                        skip_next_line = True  # Skip this line and the next line
                        continue
                    elif "}" in line:
                        in_connect_cache = False
                        new_lines.append(line)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            with open(config_vdf_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return True
        except Exception as e:
            print(f"Error modifying config.vdf: {e}")
            return False

    def launch_steamcmd(self, username):
        cmd = os.path.join(self.steamcmd_dir, 'steamcmd.exe')
        if not os.path.isfile(cmd):
            QMessageBox.critical(self, 'Error', f"SteamCMD executable not found at {cmd}.")
            return
        cmd_command = [cmd, '+login', username]
        try:
            # Start SteamCMD process and keep a reference
            self.steamcmd_process = subprocess.Popen(
                cmd_command,
                cwd=self.steamcmd_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        except Exception as e:
            QMessageBox.critical(self, 'Error', f"Failed to launch SteamCMD: {e}")
    
    def get_updated_config(self):
        return self.config

class SteamWorkshopDownloader(QWidget):
    log_signal = pyqtSignal(str)
    update_queue_signal = pyqtSignal(str, str)  # ModID, Status

    def __init__(self):
        super().__init__()
        self.initUI()
        self.download_queue = []
        self.is_downloading = False
        self.config = {}
        self.config_path = self.get_config_path()
        self.steamcmd_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'steamcmd')
        self.steamcmd_executable = self.get_steamcmd_executable_path()
        self.current_process = None
        self.load_config()
        self.app_ids = self.load_app_ids()
        self.app_id_to_game = {v: k for k, v in self.app_ids.items()}
        self.populate_game_dropdown()
        self.populate_steam_accounts()
        self.apply_settings()

        self.download_counter = 0
        self.consecutive_failures = 0

        self.log_signal.connect(self.append_log)
        self.update_queue_signal.connect(self.update_queue_status)

        threading.Thread(target=self.setup_steamcmd, daemon=True).start()

        # Restore window size from config if available
        window_size = self.config.get('window_size')
        if window_size:
            self.resize(window_size.get('width', 670), window_size.get('height', 750))
        else:
            self.resize(670, 750)

    def initUI(self):
        self.setWindowTitle('STREAMLINE')
        main_layout = QVBoxLayout()

        top_layout = QHBoxLayout()

        self.settings_btn = QPushButton('Settings')
        self.settings_btn.clicked.connect(self.open_settings)
        top_layout.addWidget(self.settings_btn)

        self.configure_steam_accounts_btn = QPushButton('Configure Steam Accounts')
        self.configure_steam_accounts_btn.clicked.connect(self.open_configure_steam_accounts)
        top_layout.addWidget(self.configure_steam_accounts_btn)

        self.steam_accounts_dropdown = QComboBox()
        self.steam_accounts_dropdown.addItem("Anonymous")
        self.steam_accounts_dropdown.currentIndexChanged.connect(self.change_active_account)
        top_layout.addWidget(QLabel("Active Account:"))
        top_layout.addWidget(self.steam_accounts_dropdown)

        main_layout.addLayout(top_layout)

        game_layout = QHBoxLayout()
        self.game_label = QLabel('Select Game:')
        self.game_dropdown = QComboBox()
        game_layout.addWidget(self.game_label)
        game_layout.addWidget(self.game_dropdown)
        main_layout.addLayout(game_layout)

        mod_layout = QHBoxLayout()
        self.mod_label = QLabel('Workshop Mod:')
        self.mod_input = QLineEdit()
        self.mod_input.setPlaceholderText('Enter Mod URL or ID')

        self.download_mod_btn = QPushButton('Download')
        self.download_mod_btn.clicked.connect(self.download_mod_immediately)
        self.add_mod_btn = QPushButton('Add to Queue')
        self.add_mod_btn.clicked.connect(self.add_mod_to_queue)

        mod_layout.addWidget(self.mod_label)
        mod_layout.addWidget(self.mod_input)
        mod_layout.addWidget(self.download_mod_btn)
        mod_layout.addWidget(self.add_mod_btn)
        main_layout.addLayout(mod_layout)

        collection_layout = QHBoxLayout()
        self.collection_label = QLabel('Workshop Collection:')
        self.collection_input = QLineEdit()
        self.collection_input.setPlaceholderText('Enter Collection URL or ID')
        self.add_collection_btn = QPushButton('Add to Queue')
        self.add_collection_btn.clicked.connect(self.add_collection_to_queue)
        collection_layout.addWidget(self.collection_label)
        collection_layout.addWidget(self.collection_input)
        collection_layout.addWidget(self.add_collection_btn)
        main_layout.addLayout(collection_layout)

        self.queue_label = QLabel('Download Queue:')
        self.queue_tree = QTreeWidget()
        self.queue_tree.setColumnCount(3)
        self.queue_tree.setHeaderLabels(['Mod ID', 'Mod Name', 'Status'])
        self.queue_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.queue_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queue_tree.customContextMenuRequested.connect(self.open_context_menu)
        main_layout.addWidget(self.queue_label)
        main_layout.addWidget(self.queue_tree, stretch=3)

        button_layout = QHBoxLayout()
        self.download_btn = QPushButton('Start Download')
        self.download_btn.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_btn)

        self.open_folder_btn = QPushButton('Open Downloads Folder')
        self.open_folder_btn.clicked.connect(self.open_downloads_folder)
        button_layout.addWidget(self.open_folder_btn)
        main_layout.addLayout(button_layout)

        log_layout = QVBoxLayout()
        self.log_label = QLabel('Logs:')
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(150)
        log_layout.addWidget(self.log_label)
        log_layout.addWidget(self.log_area)
        main_layout.addLayout(log_layout, stretch=1)

        self.setLayout(main_layout)

    def get_config_path(self):
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.join(script_dir, 'config.json')

    def load_config(self):
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as file:
                    self.config = json.load(file)
                self.log_signal.emit("Configuration loaded successfully.")
            except Exception as e:
                self.log_signal.emit(f"Error loading config.json: {e}")
                self.config = {}
        else:
            self.config = {}
            self.log_signal.emit("No existing configuration found.")

        if 'steam_accounts' not in self.config:
            self.config['steam_accounts'] = []
        if 'active_account' not in self.config:
            self.config['active_account'] = "Anonymous"

    def save_config(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                json.dump(self.config, file, indent=4)
            self.log_signal.emit("Configuration saved successfully.")
        except Exception as e:
            self.log_signal.emit(f"Error saving config.json: {e}")
            
    def closeEvent(self, event):
        if self.is_downloading:
            # Ask user if they want to cancel the ongoing download before quitting
            reply = QMessageBox.question(
                self,
                'Quit Application',
                "A download is currently ongoing. Do you want to cancel it and exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
    
            if reply == QMessageBox.Yes:
                # If the user confirms, cancel the ongoing download
                self.cancel_download()
                if self.current_process and self.current_process.poll() is None:
                    self.current_process.terminate()  # Ensure SteamCMD process is terminated
                event.accept()  # Allow the window to close
            else:
                event.ignore()  # Prevent the window from closing
        else:
            event.accept()
        # Save window size before closing
        self.config['window_size'] = {'width': self.width(), 'height': self.height()}
        self.save_config()

    def load_app_ids(self):
        app_ids = {}
        appids_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'AppIDs.txt')

        if not os.path.isfile(appids_path):
            QMessageBox.critical(self, 'Error', f"'AppIDs.txt' not found in {os.path.dirname(os.path.abspath(sys.argv[0]))}.")
            sys.exit(1)

        try:
            with open(appids_path, 'r', encoding='utf-8') as file:
                for line in file:
                    if ',' not in line.strip():
                        continue
                    game_name, app_id = line.strip().split(',', 1)
                    game_name = game_name.strip()
                    app_id = app_id.strip()
                    if app_id.isdigit():
                        app_ids[game_name] = app_id
                    else:
                        self.log_signal.emit(f"Invalid App ID for game '{game_name}': '{app_id}'")
        except Exception as e:
            QMessageBox.critical(self, 'Error', f"Failed to read 'AppIDs.txt': {e}")
            sys.exit(1)

        if not app_ids:
            QMessageBox.critical(self, 'Error', "'AppIDs.txt' does not contain valid entries.")
            sys.exit(1)

        return app_ids

    def populate_game_dropdown(self):
        self.game_dropdown.clear()
        for game in sorted(self.app_ids.keys()):
            self.game_dropdown.addItem(game)

    def populate_steam_accounts(self):
        self.steam_accounts_dropdown.blockSignals(True)  # Prevent signals while updating
        self.steam_accounts_dropdown.clear()
        self.steam_accounts_dropdown.addItem("Anonymous")
        for account in self.config.get('steam_accounts', []):
            self.steam_accounts_dropdown.addItem(account['username'])
    
        # Set active account from the config
        active = self.config.get('active_account', "Anonymous")
        index = self.steam_accounts_dropdown.findText(active, Qt.MatchExactly)
        if index >= 0:
            self.steam_accounts_dropdown.setCurrentIndex(index)
        else:
            self.steam_accounts_dropdown.setCurrentIndex(0)
        self.steam_accounts_dropdown.blockSignals(False)

    def apply_settings(self):
        self.log_area.setVisible(self.config.get('show_logs', True))
        self.log_label.setVisible(self.config.get('show_logs', True))

    def open_settings(self):
        current_batch_size = self.config.get('batch_size', 20)
        show_logs = self.config.get('show_logs', True)
        dialog = SettingsDialog(current_batch_size, show_logs, self)
        if dialog.exec_() == QDialog.Accepted:
            settings = dialog.get_settings()
            self.config.update(settings)
            self.save_config()
            self.apply_settings()
            self.log_signal.emit(f"Batch size set to {settings['batch_size']}.")
            self.log_signal.emit(f"Log visibility set to {'shown' if settings['show_logs'] else 'hidden'}.")

    def open_configure_steam_accounts(self):
        dialog = ConfigureSteamAccountsDialog(self.config, self.steamcmd_dir, self)
        dialog.exec_()
        # Update the config with any changes made in the dialog
        self.config = dialog.get_updated_config()
        self.save_config()
        # Repopulate steam accounts dropdown
        self.populate_steam_accounts()
        # Ensure active account is valid
        active_account = self.config.get('active_account', 'Anonymous')
        if active_account != 'Anonymous' and active_account not in [acc['username'] for acc in self.config.get('steam_accounts', [])]:
            self.config['active_account'] = 'Anonymous'
            self.save_config()
            self.populate_steam_accounts()

    def change_active_account(self, index):
        selected_account = self.steam_accounts_dropdown.currentText()
        if self.config.get('active_account') != selected_account:
            self.config['active_account'] = selected_account
            self.save_config()
            self.log_signal.emit(f"Active account set to '{selected_account}'.")

    def setup_steamcmd(self):
        if not os.path.isdir(self.steamcmd_dir):
            self.log_signal.emit("SteamCMD not found. Downloading SteamCMD...")
            try:
                steamcmd_zip_url = 'https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip'
                response = requests.get(steamcmd_zip_url, stream=True)
                response.raise_for_status()
                with zipfile.ZipFile(BytesIO(response.content)) as zip_ref:
                    zip_ref.extractall(self.steamcmd_dir)
                self.log_signal.emit("SteamCMD downloaded and extracted successfully.")
            except Exception as e:
                self.log_signal.emit(f"Error downloading SteamCMD: {e}")
                QMessageBox.critical(self, 'Error', f"Failed to download SteamCMD: {e}")
                return

        self.steamcmd_executable = self.get_steamcmd_executable_path()
        if not os.path.isfile(self.steamcmd_executable):
            self.log_signal.emit(f"SteamCMD executable not found at {self.steamcmd_executable}.")
            QMessageBox.critical(self, 'Error', f"SteamCMD executable not found at {self.steamcmd_executable}.")
            return

    def get_steamcmd_executable_path(self):
        return os.path.join(self.steamcmd_dir, 'steamcmd.exe')

    def add_mod_to_queue(self):
        mod_input = self.mod_input.text().strip()
        if not self.validate_steamcmd():
            return
        if not mod_input:
            QMessageBox.warning(self, 'Input Error', 'Please enter a Workshop Mod URL or ID.')
            return
    
        mod_id = self.extract_id(mod_input)
        if not mod_id:
            QMessageBox.warning(self, 'Input Error', 'Invalid Workshop URL or ID.')
            return
    
        if self.is_mod_in_queue(mod_id):
            self.log_signal.emit(f"Mod {mod_id} is already in the queue.")
            return
    
        # Fetch mod info using mod_id
        game_name, app_id, mod_title = self.get_mod_info(mod_id)
        if not app_id:
            self.log_signal.emit(f"Failed to retrieve App ID for mod {mod_id}.")
            return
    
        # Update game selection in the UI
        self.update_game_selection(game_name)
    
        self.download_queue.append({'mod_id': mod_id, 'mod_name': mod_title, 'status': 'Queued', 'retry_count': 0})
        tree_item = QTreeWidgetItem([mod_id, mod_title, 'Queued'])
        self.queue_tree.addTopLevelItem(tree_item)
        self.log_signal.emit(f"Mod {mod_id} ('{mod_title}') added to the queue.")
    
        self.mod_input.clear()

    def add_collection_to_queue(self):
        collection_input = self.collection_input.text().strip()
        if not self.validate_steamcmd():
            return
        if not collection_input:
            QMessageBox.warning(self, 'Input Error', 'Please enter a Workshop Collection URL or ID.')
            return

        collection_id = self.extract_id(collection_input)
        if not collection_id:
            QMessageBox.warning(self, 'Input Error', 'Invalid Workshop Collection URL or ID.')
            return

        try:
            url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={collection_id}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            game_name, app_id = self.get_game_info_from_soup(soup)
            if not app_id:
                self.log_signal.emit(f"Failed to retrieve App ID for collection {collection_id}.")
                return

            self.update_game_selection(game_name)

            collection_items = soup.find_all('div', class_='collectionItem')
            added_count = 0
            for item in collection_items:
                # Extract mod ID
                a_tag = item.find('a', href=True)
                mod_id = self.extract_id(a_tag['href']) if a_tag else None
                if mod_id and not self.is_mod_in_queue(mod_id):
                    # Extract mod title
                    title_tag = item.find('div', class_='workshopItemTitle')
                    mod_title = title_tag.text.strip() if title_tag else 'Unknown Title'
                    # Add mod to download queue
                    self.download_queue.append({'mod_id': mod_id, 'mod_name': mod_title, 'status': 'Queued', 'retry_count': 0})
                    tree_item = QTreeWidgetItem([mod_id, mod_title, 'Queued'])
                    self.queue_tree.addTopLevelItem(tree_item)
                    added_count += 1

            self.log_signal.emit(f"Collection {collection_id} added to the queue with {added_count} mods.")
            self.collection_input.clear()
        except Exception as e:
            self.log_signal.emit(f"Error fetching collection: {e}")

    def extract_id(self, input_str):
        pattern = r'https?://steamcommunity\.com/sharedfiles/filedetails/\?id=(\d+)'
        match = re.match(pattern, input_str)
        if match:
            return match.group(1)
        elif input_str.isdigit():
            return input_str  # Directly return if it's an ID
        else:
            # Attempt to extract numbers from the input
            id_match = re.search(r'(\d+)', input_str)
            if id_match:
                return id_match.group(1)
        return None

    def is_mod_in_queue(self, mod_id):
        return any(mod['mod_id'] == mod_id for mod in self.download_queue)

    def get_mod_info(self, mod_id):
        try:
            url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            # Fetch game info
            game_tag = soup.find('a', attrs={'data-panel': '{"noFocusRing":true}'})
            game_name, app_id = None, None
            if game_tag and 'href' in game_tag.attrs:
                href = game_tag['href']
                app_id_match = re.search(r'/app/(\d+)', href)
                if app_id_match:
                    app_id = app_id_match.group(1)
                    game_name = self.app_id_to_game.get(app_id, None)
            # Fetch mod title
            title_tag = soup.find('div', class_='workshopItemTitle')
            mod_title = title_tag.text.strip() if title_tag else 'Unknown Title'
            return game_name, app_id, mod_title
        except Exception as e:
            self.log_signal.emit(f"Error fetching mod info for mod {mod_id}: {e}")
        return None, None, None

    def get_game_info_from_soup(self, soup):
        game_tag = soup.find('a', attrs={'data-panel': '{"noFocusRing":true}'})
        if game_tag and 'href' in game_tag.attrs:
            href = game_tag['href']
            app_id_match = re.search(r'/app/(\d+)', href)
            if app_id_match:
                game_app_id = app_id_match.group(1)
                game_name = self.app_id_to_game.get(game_app_id, None)
                return game_name, game_app_id
        return None, None

    def update_game_selection(self, game_name):
        if game_name:
            index = self.game_dropdown.findText(game_name, Qt.MatchFixedString)
            if index >= 0:
                self.game_dropdown.setCurrentIndex(index)
                self.log_signal.emit(f"Game set to '{game_name}'.")

    def validate_steamcmd(self):
        if not self.steamcmd_executable or not os.path.isfile(self.steamcmd_executable):
            QMessageBox.warning(self, 'Error', 'SteamCMD is not set up correctly.')
            self.log_signal.emit("Error: SteamCMD executable not found.")
            return False
        return True

    def start_download(self):
        if not self.download_queue:
            QMessageBox.information(self, 'Info', 'Download queue is empty.')
            return
        if self.is_downloading:
            self.cancel_download()
            return

        self.is_downloading = True
        self.download_btn.setText('Cancel Download')
        self.download_btn.setEnabled(True)
        self.log_signal.emit("Starting download process...")
        threading.Thread(target=self.download_worker, daemon=True).start()

    def cancel_download(self):
        if self.current_process and self.current_process.poll() is None:
            self.current_process.terminate()
            self.log_signal.emit("Download process terminated by user.")
    
        # Reset the status of all "Downloading" mods to "Queued"
        for mod in self.download_queue:
            if mod['status'] == 'Downloading':
                mod['status'] = 'Queued'
                self.update_queue_signal.emit(mod['mod_id'], 'Queued')
    
        self.is_downloading = False
        self.download_btn.setText('Start Download')
        self.download_btn.setEnabled(True)

    def download_worker(self):
        batch_size = self.config.get('batch_size', 20)
        
        while self.is_downloading:
            current_batch = [mod for mod in self.download_queue if mod['status'] == 'Queued'][:batch_size]
            if not current_batch:
                break  # No more mods to download
    
            self.log_signal.emit(f"Starting batch download of {len(current_batch)} mod(s).")
    
            steamcmd_commands = [self.steamcmd_executable]
            active_account = self.config.get('active_account', "Anonymous")
            
            # Set up login credentials
            if active_account != "Anonymous":
                account = next((acc for acc in self.config['steam_accounts'] if acc['username'] == active_account), None)
                if account:
                    username = account.get('username', '')
                    steamcmd_commands.extend(['+login', username])
                else:
                    steamcmd_commands.extend(['+login', 'anonymous'])
            else:
                steamcmd_commands.extend(['+login', 'anonymous'])
    
            # Add workshop download commands for each mod in the batch
            for mod in current_batch:
                mod_id = mod['mod_id']
                mod['status'] = 'Downloading'
                self.update_queue_signal.emit(mod_id, 'Downloading')
                steamcmd_commands.extend(['+workshop_download_item', self.get_selected_app_id(), mod_id])
    
            steamcmd_commands.append('+quit')
    
            try:
                # Start the SteamCMD process for the entire batch
                self.current_process = subprocess.Popen(
                    steamcmd_commands,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=self.steamcmd_dir
                )
    
                # Process SteamCMD output line-by-line to track progress
                for line in self.current_process.stdout:
                    clean_line = line.strip()
                    if clean_line:
                        self.log_signal.emit(clean_line)
                    
                    # Check the log line to determine success or failure
                    for mod in current_batch:
                        self.parse_log_line(clean_line, mod['mod_id'])
    
                self.current_process.stdout.close()
                self.current_process.wait()
    
                if self.current_process.returncode == 0:
                    self.log_signal.emit("Batch downloads completed successfully.")
                else:
                    self.log_signal.emit(f"SteamCMD exited with code {self.current_process.returncode}. Some downloads might have failed.")
    
            except Exception as e:
                self.log_signal.emit(f"Error during batch download: {e}")
                # Mark all mods in the current batch as failed
                for mod in current_batch:
                    mod['status'] = f'Failed: {e}'
                    self.update_queue_signal.emit(mod['mod_id'], mod['status'])
                    self.consecutive_failures += 1
    
            # Remove all mods that have the status "Downloaded"
            mods_to_remove = [mod for mod in self.download_queue if mod['status'] == 'Downloaded']
            for mod in mods_to_remove:
                self.remove_mod_from_queue(mod['mod_id'])
    
            # Check for consecutive failures and reset if needed
            if self.consecutive_failures >= 3:
                self.log_signal.emit("3 consecutive failures detected. Restarting SteamCMD.")
                self.consecutive_failures = 0
    
        # End the download process
        self.log_signal.emit("All downloads have been processed.")
        self.is_downloading = False
        self.download_btn.setText('Start Download')
        self.download_btn.setEnabled(True)

    def parse_log_line(self, log_line, mod_id):
        success_pattern = re.compile(r'Success\. Downloaded item (\d+) to .* \((\d+) bytes\)', re.IGNORECASE)
        failure_pattern = re.compile(r'ERROR! Download item (\d+) failed \((.+)\)', re.IGNORECASE)
    
        # Check for successful download
        success_match = success_pattern.search(log_line)
        if success_match:
            downloaded_mod_id = success_match.group(1)
            if downloaded_mod_id == mod_id:
                # Mark the mod as downloaded
                self.update_queue_signal.emit(mod_id, 'Downloaded')
                self.log_signal.emit(f"Mod {mod_id} downloaded successfully.")
                # Remove the mod from the download queue
                # self.remove_mod_from_queue(mod_id)
                return
    
        # Check for failed download
        failure_match = failure_pattern.search(log_line)
        if failure_match:
            failed_mod_id = failure_match.group(1)
            reason = failure_match.group(2)
            if failed_mod_id == mod_id:
                # Update the mod status as failed
                self.update_queue_signal.emit(mod_id, f'Failed: {reason}')
                self.log_signal.emit(f"Mod {mod_id} failed to download: {reason}")
                self.consecutive_failures += 1
            return

    def update_queue_status(self, mod_id, status):
        item_to_remove = None
        for index in range(self.queue_tree.topLevelItemCount()):
            item = self.queue_tree.topLevelItem(index)
            if item.text(0) == mod_id:
                item.setText(2, status)
                self.log_signal.emit(f"Mod {mod_id} status updated to {status}.")
                if status == 'Downloaded':
                    # Remove from download_queue
                    # self.download_queue = [mod for mod in self.download_queue if mod['mod_id'] != mod_id]
                    # Mark item for removal from queue_tree
                    item_to_remove = item
                    self.log_signal.emit(f"Mod {mod_id} removed from the queue.")
                elif status.startswith('Failed'):
                    for mod in self.download_queue:
                        if mod['mod_id'] == mod_id:
                            if mod['retry_count'] < 3:
                                mod['retry_count'] += 1
                                mod['status'] = 'Queued'
                                self.log_signal.emit(f"Retrying mod {mod_id}. Attempt {mod['retry_count']}.")
                            else:
                                self.log_signal.emit(f"Mod {mod_id} failed after 3 attempts.")
                            break
                break
        if item_to_remove:
            index = self.queue_tree.indexOfTopLevelItem(item_to_remove)
            self.queue_tree.takeTopLevelItem(index)
            self.download_queue = [mod for mod in self.download_queue if mod['mod_id'] != mod_id]

    def append_log(self, message):
        self.log_area.append(message)
        self.log_area.moveCursor(QTextCursor.End)

    def get_selected_app_id(self):
        return self.app_ids.get(self.game_dropdown.currentText(), '')

    def download_mod_immediately(self):
        mod_input = self.mod_input.text().strip()
        if not self.validate_steamcmd():
            return
        if not mod_input:
            QMessageBox.warning(self, 'Input Error', 'Please enter a Workshop Mod URL or ID.')
            return
    
        mod_id = self.extract_id(mod_input)
        if not mod_id:
            QMessageBox.warning(self, 'Input Error', 'Invalid Workshop URL or ID.')
            return
    
        if self.is_mod_in_queue(mod_id):
            self.log_signal.emit(f"Mod {mod_id} is already in the queue.")
            return
    
        # Fetch mod info using mod_id
        game_name, app_id, mod_title = self.get_mod_info(mod_id)
        if not app_id:
            self.log_signal.emit(f"Failed to retrieve App ID for mod {mod_id}.")
            return
    
        # Update game selection in the UI
        self.update_game_selection(game_name)
    
        self.download_queue.append({'mod_id': mod_id, 'mod_name': mod_title, 'status': 'Queued', 'retry_count': 0})
        tree_item = QTreeWidgetItem([mod_id, mod_title, 'Queued'])
        self.queue_tree.addTopLevelItem(tree_item)
        self.log_signal.emit(f"Mod {mod_id} ('{mod_title}') added to the queue.")
    
        self.mod_input.clear()
    
        self.start_download()

    def open_context_menu(self, position: QPoint):
        if self.is_downloading:
            return

        selected_items = self.queue_tree.selectedItems()
        if not selected_items:
            return

        menu = QMenu()
        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(lambda: self.remove_mods_from_queue(selected_items))
        menu.addAction(remove_action)
        menu.exec_(self.queue_tree.viewport().mapToGlobal(position))

    def remove_mod_from_queue(self, mod_id):
        self.download_queue = [mod for mod in self.download_queue if mod['mod_id'] != mod_id]
        
        # Remove from the GUI tree
        item_to_remove = None
        for index in range(self.queue_tree.topLevelItemCount()):
            item = self.queue_tree.topLevelItem(index)
            if item.text(0) == mod_id:
                item_to_remove = item
                break
        
        if item_to_remove:
            index = self.queue_tree.indexOfTopLevelItem(item_to_remove)
            self.queue_tree.takeTopLevelItem(index)
            self.log_signal.emit(f"Mod {mod_id} removed from the queue.")
            
    def remove_mods_from_queue(self, selected_items):
        mod_ids_to_remove = [item.text(0) for item in selected_items]
    
        # Remove mods from the internal download queue
        self.download_queue = [mod for mod in self.download_queue if mod['mod_id'] not in mod_ids_to_remove]
    
        # Remove items from the GUI tree
        for item in selected_items:
            index = self.queue_tree.indexOfTopLevelItem(item)
            if index != -1:
                self.queue_tree.takeTopLevelItem(index)
    
        for mod_id in mod_ids_to_remove:
            self.log_signal.emit(f"Mod {mod_id} removed from the queue.")

    def open_downloads_folder(self):
        app_id = self.get_selected_app_id()
        if not app_id:
            QMessageBox.warning(self, 'Error', 'No game selected. Please select a game.')
            return

        download_path = os.path.join(
            self.steamcmd_dir,
            'steamapps',
            'workshop',
            'content',
            app_id
        )

        if os.path.isdir(download_path):
            webbrowser.open(download_path)
        else:
            QMessageBox.warning(self, 'Error', f"Download folder does not exist: {download_path}")


if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    downloader = SteamWorkshopDownloader()
    downloader.resize(670, 750)
    downloader.show()
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()
