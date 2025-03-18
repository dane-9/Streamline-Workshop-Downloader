import sys
import os
import requests
import zipfile
import threading
import subprocess
import time
import ctypes
from ctypes import wintypes
import platform
import shutil
import re
import json
import webbrowser
import aiohttp
import asyncio
from io import BytesIO
from lxml import html
from collections import defaultdict
import glob
from initialize import ThemedSplashScreen, AppIDScraper
from tooltip import Tooltip, TooltipPlacement, FilterTooltip, TooltipManager
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QTextEdit,
    QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QMessageBox,
    QComboBox, QDialog, QSpinBox, QFormLayout, QDialogButtonBox,
    QMenu, QCheckBox, QFileDialog, QHeaderView, QAbstractItemView, 
    QStyledItemDelegate, QStyle, QToolButton, QRadioButton, 
    QStackedWidget, QFrame, QSizePolicy, QMenuBar, QStyleOptionComboBox,
    QStyleOptionViewItem, QWidgetAction, QToolTip
)
from PySide6.QtCore import (
    Qt, Signal, QPoint, QThread, QSize, QTimer, QObject, QEvent, 
    QCoreApplication, Slot,
)
from PySide6.QtGui import (
    QTextCursor, QAction, QClipboard, QIcon, QCursor, QPainter,
    QColor, QPixmap, QPolygon, QFontMetrics, QActionGroup
)

current_version = "1.2.0"

DEFAULT_SETTINGS = {
    "current_theme": "Dark",
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
    
    "download_button": True,
    "show_menu_bar": True, 
    "show_searchbar": True,
    "show_regex_button": True,
    "show_case_button": True,
    "show_export_import_buttons": True,
    "show_sort_indicator": True,
    
    "header_locked": True,
    
    "steam_accounts": [],
    "active_account": "Anonymous",
    
    "queue_tree_default_widths": [115, 90, 230, 100, 95],
    "queue_tree_column_widths": None,
    "queue_tree_column_hidden": None,
    "show_version": True,
    "reset_provider_on_startup": False,
    "download_provider": "Default"
}

# Allows logo to be applied over pythonw.exe's own
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('streamline.app.logo')

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def load_theme(app, theme_name, files_dir):
    theme_path = resource_path(os.path.join("Files", "Themes", theme_name + ".qss"))

    if not os.path.isfile(theme_path):
        theme_path = os.path.join(files_dir, "Themes", theme_name + ".qss")

    if os.path.isfile(theme_path):
        try:
            with open(theme_path, "r", encoding="utf-8") as f:
                qss = f.read()

            checkmark_icon = resource_path("Files/checkmark.png").replace("\\", "/")
            arrow_icon = resource_path("Files/arrow.png").replace("\\", "/")

            qss = qss.replace("QMenu::indicator:checked {", f"QMenu::indicator:checked {{ image: url({checkmark_icon});")
            qss = qss.replace("QComboBox::drop-down {", f"QComboBox::drop-down {{ image: url({arrow_icon});")

            app.setStyleSheet(qss)
            return True

        except Exception as e:
            print(f"Error loading theme {theme_name}: {e}")
            app.setStyleSheet("")  # Revert to default if file not found
            return False
    else:
        app.setStyleSheet("")
        return False
        
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
    
def set_custom_clear_icon(line_edit: QLineEdit):
    line_edit.setClearButtonEnabled(True)
    clear_btn = line_edit.findChild(QToolButton)
    if clear_btn:
        clear_btn.setIcon(QIcon(resource_path('Files/clear.png')))
        
def create_separator(object_name, parent=None, width="", label="", label_alignment="center", size_policy=None, font_style="standard", margin=True):
    separator = QWidget(parent)
    layout = QHBoxLayout(separator)
    if margin==True:
        layout.setContentsMargins(0, 15, 0, 0)
    else:
        layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    
    def create_sep():
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName(object_name)
        if size_policy is not None:
            if isinstance(size_policy, tuple) and len(size_policy) == 2:
                sep.setSizePolicy(QSizePolicy(size_policy[0], size_policy[1]))
            elif isinstance(size_policy, QSizePolicy):
                sep.setSizePolicy(size_policy)
        else:
            sep.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return sep

    if not label:
        layout.addWidget(create_sep())
    else:
        lbl = QLabel(label)
        lbl.setContentsMargins(0, -4, 0, 0)
        lbl.setMargin(0)
        lbl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        
        font = lbl.font()
        style = font_style.lower()
        if style == "bold":
            font.setBold(True)
            font.setItalic(False)
        elif style == "italic":
            font.setItalic(True)
            font.setBold(False)
        elif style == "bold italic":
            font.setBold(True)
            font.setItalic(True)
        else:  # standard
            font.setBold(False)
            font.setItalic(False)
        lbl.setFont(font)
        
        if label_alignment.lower() == "left":
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            layout.addWidget(lbl)
            layout.addWidget(create_sep())
        elif label_alignment.lower() == "right":
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            layout.addWidget(create_sep())
            layout.addWidget(lbl)
        else:  # Default to center
            lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(create_sep())
            layout.addWidget(lbl)
            layout.addWidget(create_sep())
    return separator
    
def create_help_icon(self, tooltip_text: str, detailed_text: str, parent=None) -> QToolButton:
    help_btn = QToolButton(parent)
    
    icon_path = resource_path("Files/questionmark.png")
    if os.path.exists(icon_path):
        help_btn.setIcon(QIcon(icon_path))
    else:
        help_btn.setText("?")
    
    help_btn.setIconSize(QSize(8, 8))
    help_btn.setToolTip(tooltip_text)
    help_btn.setStyleSheet("QToolButton { border: none; padding: 0px; margin: 0px; }")
    
    def on_click():
        msg_box = ThemedMessageBox(parent)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("More Information")
        msg_box.setText(detailed_text)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setDefaultButton(QMessageBox.Ok)
        apply_theme_titlebar(msg_box, parent.config if parent and hasattr(parent, 'config') else {})
        msg_box.exec()
    
    help_btn.clicked.connect(on_click)
    return help_btn

class NoFocusDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if option.state & QStyle.State_HasFocus:
            option.state &= ~QStyle.State_HasFocus
        super().paint(painter, option, index)

class ActiveDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # Create a copy of the option to modify
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        
        # Get the text and active account info
        text = index.data(Qt.DisplayRole) or ""
        active_suffix = "  (Active)"
        
        combo = self.parent()
        active_account = ""
        if combo and hasattr(combo, 'config'):
            active_account = combo.config.get('active_account', "Anonymous")
            
        if text == active_account:
            super().paint(painter, opt, index)
            
            style = QApplication.style()
            text_rect = style.subElementRect(QStyle.SE_ItemViewItemText, opt, opt.widget)
            if not text_rect.isValid():
                text_rect = opt.rect.adjusted(4, 0, -4, 0)
            
            fm = painter.fontMetrics()
            text_width = fm.horizontalAdvance(text)
            
            painter.save()
            
            smaller_font = painter.font()
            smaller_font.setPointSize(max(6, smaller_font.pointSize() - 3))
            painter.setFont(smaller_font)
            
            painter.setPen(QColor("#40b6e0"))
            
            suffix_rect = text_rect
            suffix_rect.setLeft(text_rect.left() + text_width)
            painter.drawText(suffix_rect, Qt.AlignVCenter | Qt.AlignLeft, active_suffix)
            
            painter.restore()
        else:
            super().paint(painter, opt, index)

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        text = index.data(Qt.DisplayRole) or ""
        
        combo = self.parent()
        if combo and hasattr(combo, 'config'):
            active_account = combo.config.get('active_account', "Anonymous")
            if text == active_account:
                fm = QFontMetrics(option.font)
                suffix_width = fm.horizontalAdvance(" (Active)")
                size.setWidth(size.width() + suffix_width)
        
        return size

class ActiveComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = parent.config if parent and hasattr(parent, 'config') else {}
        self.delegate = ActiveDelegate(self)
        self.setItemDelegate(self.delegate)
        
    def showPopup(self):
        self.view().setItemDelegate(self.delegate)
        super().showPopup()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        option.currentText = ""

        self.style().drawComplexControl(QStyle.CC_ComboBox, option, painter, self)

        arrow_size = self.style().pixelMetric(QStyle.PM_MenuButtonIndicator, option, self)
        text_rect = option.rect.adjusted(4, 0, -arrow_size - 5, 0)

        text = self.currentText()
        active_account = self.config.get('active_account', "Anonymous")
        active_suffix = " (Active)"
        
        painter.setPen(option.palette.text().color())
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)

        if text == active_account:
            fm = painter.fontMetrics()
            text_width = fm.horizontalAdvance(text)
            suffix_rect = text_rect.adjusted(text_width, 0, 0, 0)
            
            painter.save()
            smaller_font = painter.font()
            smaller_font.setPointSize(max(6, smaller_font.pointSize() - 3))  # Match delegate size
            painter.setFont(smaller_font)
            painter.setPen(QColor("#40b6e0"))
            painter.drawText(suffix_rect, Qt.AlignVCenter | Qt.AlignLeft, active_suffix)
            painter.restore()
            
class SettingsTreeDelegate(NoFocusDelegate):
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(25)
        return size

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setFixedSize(650, 550)

        self._config = parent.config if parent else {}
        apply_theme_titlebar(self, self._config)
        
        self.pages_widget = QStackedWidget()
        QTimer.singleShot(100, self.buildPages)

        self._current_theme = self._config.get('current_theme', 'Dark')
        self._logo_style = self._config.get('logo_style', 'Light')
        self._batch_size = self._config.get('batch_size', 20)
        self._show_logs = self._config.get('show_logs', True)
        self._show_provider = self._config.get('show_provider', True)
        self._show_queue_entire_workshop = self._config.get('show_queue_entire_workshop', True)
        self._keep_downloaded_in_queue = self._config.get('keep_downloaded_in_queue', False)
        self._folder_naming_format = self._config.get('folder_naming_format', 'id')
        self._auto_detect_urls = self._config.get('auto_detect_urls', False)
        self._auto_add_to_queue = self._config.get('auto_add_to_queue', False)

        main_layout = QHBoxLayout()

        self.category_tree = QTreeWidget()
        self.category_tree.setObjectName("settings_tree")
        self.category_tree.setHeaderHidden(True)
        self.category_tree.setMinimumWidth(125)
        self.category_tree.setMaximumWidth(190)
        self.category_tree.setIconSize(QSize(16, 16))
        
        appearance_item = QTreeWidgetItem(["Appearance"])
        appearance_icon = QIcon(resource_path("Files/appearance_options.png"))
        appearance_item.setIcon(0, appearance_icon)
        
        download_item = QTreeWidgetItem(["Download Options"])
        download_icon = QIcon(resource_path("Files/download_options.png"))
        download_item.setIcon(0, download_icon)
        
        utility_item = QTreeWidgetItem(["Tools"])
        tool_icon = QIcon(resource_path("Files/tool_options.png"))
        utility_item.setIcon(0, tool_icon)
        
        system_item = QTreeWidgetItem(["System"])
        system_icon = QIcon(resource_path("Files/system_options.png"))
        system_item.setIcon(0, system_icon)
        
        self.category_tree.setRootIsDecorated(False)
        self.category_tree.addTopLevelItem(appearance_item)
        self.category_tree.addTopLevelItem(download_item)
        self.category_tree.addTopLevelItem(utility_item)
        self.category_tree.addTopLevelItem(system_item)

        self.category_tree.setItemDelegate(SettingsTreeDelegate(self.category_tree))
        
        self.category_tree.expandAll()
        self.category_tree.setCurrentItem(appearance_item)  # Default selection
        main_layout.addWidget(self.category_tree)

        main_layout.addWidget(self.pages_widget)

        # Connect tree selection to page switching
        self.category_tree.currentItemChanged.connect(self.on_category_changed)

        buttons_layout = QHBoxLayout()
        
        self.reset_defaults_btn = QPushButton("Reset to Default")
        self.reset_defaults_btn.clicked.connect(self.reset_defaults)
        buttons_layout.addWidget(self.reset_defaults_btn)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        save_button = self.button_box.button(QDialogButtonBox.Save)
        cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        
        if save_button:
            save_button.setFixedWidth(100)
            save_button.setStyleSheet("background-color: #4D8AC9; color: #FFFFFF; font-weight: bold")
        if cancel_button:
            cancel_button.setFixedWidth(100)
            
        buttons_layout.addWidget(self.button_box)

        main_vbox = QVBoxLayout()
        main_vbox.addLayout(main_layout)
        main_vbox.addLayout(buttons_layout)
        self.setLayout(main_vbox)
        
    def buildPages(self):
        self.appearance_page = self._build_appearance_page()
        self.download_page = self._build_download_options_page()
        self.utility_page = self._build_utility_page()
        self.system_page = self._build_system_page()
            
        self.pages_widget.addWidget(self.appearance_page)  # index 0
        self.pages_widget.addWidget(self.download_page)    # index 1
        self.pages_widget.addWidget(self.utility_page)     # index 2
        self.pages_widget.addWidget(self.system_page)    # index 3

    def _build_appearance_page(self):
        page = QWidget()
        layout = QFormLayout(page)
        layout.setVerticalSpacing(10)

        theme_label = QLabel("Theme:")
        self.theme_dropdown = QComboBox()
        self.theme_dropdown.setMinimumHeight(25)
        self.theme_dropdown.setMaximumWidth(125)
        if hasattr(self.parent(), 'files_dir'):
            files_dir = self.parent().files_dir
            theme_files = glob.glob(os.path.join(files_dir, "Themes", "*.qss"))
            theme_names = [os.path.splitext(os.path.basename(t))[0] for t in theme_files]

            if 'Dark' not in theme_names:
                theme_names.insert(0, 'Dark')
            if 'Light' not in theme_names:
                theme_names.append('Light')

            if 'Dark' in theme_names:
                theme_names.remove('Dark')
                sorted_names = sorted(theme_names)
                sorted_names.insert(0, 'Dark')
                theme_names = sorted_names
            else:
                theme_names = sorted(theme_names)

            self.theme_dropdown.addItems(theme_names)
        else:
            self.theme_dropdown.addItems(["Dark", "Light"])

        if self._current_theme in [self.theme_dropdown.itemText(i) for i in range(self.theme_dropdown.count())]:
            self.theme_dropdown.setCurrentText(self._current_theme)
        layout.addRow(theme_label, self.theme_dropdown)
    
        logo_label = QLabel("Logo Style:")
        logo_layout = QHBoxLayout()
        self.light_logo_radio = QRadioButton("Light")
        self.dark_logo_radio = QRadioButton("Dark")
        self.darker_logo_radio = QRadioButton("Darker")
        if self._logo_style == "Dark":
            self.dark_logo_radio.setChecked(True)
        elif self._logo_style == "Darker":
            self.darker_logo_radio.setChecked(True)
        else:
            self.light_logo_radio.setChecked(True)
        logo_layout.addWidget(self.light_logo_radio)
        logo_layout.addWidget(self.dark_logo_radio)
        logo_layout.addWidget(self.darker_logo_radio)
        layout.addRow(logo_label, logo_layout)
        
        layout.addRow(create_separator("settings_separator", parent=self, width=200, label="Show", label_alignment="left", size_policy=(QSizePolicy.Expanding, QSizePolicy.Fixed), font_style="standard", margin=True))
    
        show_version_checkbox = QCheckBox("Version in Title")
        show_version_checkbox.setChecked(self._config.get("show_version", True))
        layout.addRow(show_version_checkbox)
        self.show_version_checkbox = show_version_checkbox
    
        self.show_menu_bar_checkbox = QCheckBox("Menu Bar")
        self.show_menu_bar_checkbox.setChecked(self._config.get('show_menu_bar', True))
        layout.addRow(self.show_menu_bar_checkbox)
    
        self.show_download_button_checkbox = QCheckBox("Download Button")
        self.show_download_button_checkbox.setChecked(self._config.get('download_button', True))
        layout.addRow(self.show_download_button_checkbox)
        
        self.show_searchbar_checkbox = QCheckBox("Search Bar")
        self.show_searchbar_checkbox.setChecked(self._config.get('show_searchbar', True))
        layout.addRow(self.show_searchbar_checkbox)
        
        indent_layout = QHBoxLayout()
        indent_layout.addSpacing(20)  # Indentation
        dependent_layout = QVBoxLayout()
        dependent_layout.setSpacing(0)
        self.show_regex_checkbox = QCheckBox("Regex")
        self.show_regex_checkbox.setChecked(self._config.get('show_regex_button', True))
        self.show_case_checkbox = QCheckBox("Case Sensitivity")
        self.show_case_checkbox.setChecked(self._config.get('show_case_button', True))
        dependent_layout.addWidget(self.show_regex_checkbox)
        dependent_layout.addWidget(self.show_case_checkbox)
        indent_layout.addLayout(dependent_layout)
        layout.addRow(indent_layout)
        
        self.show_searchbar_checkbox.stateChanged.connect(self.searchbar_dependent_options)
        self.searchbar_dependent_options()
        
        self.show_export_import_buttons_checkbox = QCheckBox("Import/Export Queue Buttons")
        self.show_export_import_buttons_checkbox.setChecked(self._config.get('show_export_import_buttons', True))
        layout.addRow(self.show_export_import_buttons_checkbox)
        
        self.show_sort_indicator_checkbox = QCheckBox("Header Sort Indicator")
        self.show_sort_indicator_checkbox.setChecked(self._config.get('show_sort_indicator', True))
        layout.addRow(self.show_sort_indicator_checkbox)
    
        self.show_logs_checkbox = QCheckBox("Logs View")
        self.show_logs_checkbox.setChecked(self._show_logs)
        layout.addRow(self.show_logs_checkbox)
        
        self.show_queue_entire_workshop_checkbox = QCheckBox("Queue Entire Workshop Button")
        self.show_queue_entire_workshop_checkbox.setChecked(self._show_queue_entire_workshop)
        layout.addRow(self.show_queue_entire_workshop_checkbox)
    
        self.show_provider_checkbox = QCheckBox("Download Provider Dropdown")
        self.show_provider_checkbox.setChecked(self._show_provider)
        layout.addRow(self.show_provider_checkbox)
    
        return page

    def _build_download_options_page(self):
        page = QWidget()
        layout = QFormLayout(page)
        layout.setVerticalSpacing(10)
    
        batch_label = QLabel("Batch Size:")
        self.batch_size_spinbox = QSpinBox()
        self.batch_size_spinbox.setRange(1, 100)
        self.batch_size_spinbox.setValue(self._batch_size)
        self.batch_size_spinbox.setMaximumWidth(125)
        max_label = QLabel("Default: 20 | Max: 100")
        max_label.setStyleSheet("font-size: 10px;")
        
        spin_layout = QHBoxLayout()
        spin_layout.setContentsMargins(0, 0, 0, 0)
        spin_layout.addWidget(self.batch_size_spinbox)
        spin_layout.setSpacing(5)
        spin_layout.addWidget(max_label)
        
        # Add the row to the form layout
        layout.addRow(batch_label, spin_layout)
        
        self.keep_downloaded_in_queue_checkbox = QCheckBox("Keep Downloaded Mods in Queue")
        self.keep_downloaded_in_queue_checkbox.setChecked(self._keep_downloaded_in_queue)
        layout.addRow(self.keep_downloaded_in_queue_checkbox)
        
        self.delete_downloads_on_cancel_checkbox = QCheckBox("Delete Downloads When Canceling")
        self.delete_downloads_on_cancel_checkbox.setChecked(self._config.get("delete_downloads_on_cancel", False))
        tooltip_text = "When enabled, downloaded mods will be deleted when canceling."
        detailed_text = "By default, when you cancel a download, any downloaded mods are kept and moved to the downloads folder. Enabling this option will delete any downloaded mods when canceling instead."
        help_btn = create_help_icon(self, tooltip_text, detailed_text)
        help_layout = QHBoxLayout()
        help_layout.addWidget(self.delete_downloads_on_cancel_checkbox)
        help_layout.addWidget(help_btn)
        help_layout.addStretch()
        layout.addRow(help_layout)

        layout.addRow(create_separator("settings_separator", parent=self, width=200, label="Downloads", label_alignment="left", size_policy=(QSizePolicy.Expanding, QSizePolicy.Fixed), font_style="standard", margin=True))

        folder_name_label = QLabel("Naming Scheme: ")
        tooltip_text = "Downloaded Mods Naming Scheme"
        detailed_text = ("Choose how the folder for downloaded mods should be named:\n"
                         "• 'Mod ID': Uses the mod's numeric ID.\n"
                         "• 'Mod Name': Uses the mod's title.\n"
                         "• 'Mod ID + Mod Name': Combines both.")
        help_icon = create_help_icon(self, tooltip_text, detailed_text)

        folder_label_layout = QHBoxLayout()
        folder_label_layout.addWidget(folder_name_label)
        folder_label_layout.addWidget(help_icon)
        folder_label_layout.addStretch()

        folder_name_layout = QVBoxLayout()
        folder_name_layout.setSpacing(5)

        folder_format = self._config.get("folder_naming_format", "id")

        self.id_folder_scheme = QRadioButton("Mod ID")
        self.id_folder_scheme.setChecked(folder_format == "id")

        self.name_folder_scheme = QRadioButton("Mod Name")
        self.name_folder_scheme.setChecked(folder_format == "name")

        self.combined_folder_scheme = QRadioButton("Mod ID + Mod Name")
        self.combined_folder_scheme.setChecked(folder_format == "combined")
        
        folder_name_layout.addWidget(self.id_folder_scheme)
        folder_name_layout.addWidget(self.name_folder_scheme)
        folder_name_layout.addWidget(self.combined_folder_scheme)
        
        layout.addRow(folder_label_layout)
        layout.addRow(folder_name_layout)
    
        return page

    def _build_utility_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
    
        self.auto_detect_urls_checkbox = QCheckBox("Auto-detect URLs from Clipboard")
        self.auto_detect_urls_checkbox.setChecked(self._auto_detect_urls)
        self.auto_detect_urls_checkbox.stateChanged.connect(self.toggle_auto_add_checkbox)
        layout.addWidget(self.auto_detect_urls_checkbox)
    
        offset_layout = QHBoxLayout()
        offset_layout.addSpacing(20)  # Indents the "auto-add" checkbox
        self.auto_add_to_queue_checkbox = QCheckBox("Auto-add detected URLs to Queue")
        self.auto_add_to_queue_checkbox.setChecked(self._auto_add_to_queue)
        self.auto_add_to_queue_checkbox.setEnabled(self._auto_detect_urls)
        offset_layout.addWidget(self.auto_add_to_queue_checkbox)
        layout.addLayout(offset_layout)
    
        self.update_checkbox_style()
    
        layout.addStretch()
        return page
        
    def _build_system_page(self):
        page = QWidget()
        layout = QFormLayout(page)
        layout.setVerticalSpacing(10)

        self.reset_provider_checkbox = QCheckBox("Reset Download Provider on Startup")
        self.reset_provider_checkbox.setChecked(
            self._config.get("reset_provider_on_startup", False))
        layout.addRow(self.reset_provider_checkbox)

        return page
    
    def toggle_auto_add_checkbox(self):
        new_state = self.auto_detect_urls_checkbox.isChecked()
        self.auto_add_to_queue_checkbox.setEnabled(new_state)
        self.update_checkbox_style()
    
    
    def update_checkbox_style(self):
        if self.auto_add_to_queue_checkbox.isEnabled():
            self.auto_add_to_queue_checkbox.setStyleSheet("color: #28c64f;")
        else:
            self.auto_add_to_queue_checkbox.setStyleSheet("color: grey;")
            
    def searchbar_dependent_options(self):
        enabled = self.show_searchbar_checkbox.isChecked()
        self.show_regex_checkbox.setEnabled(enabled)
        self.show_case_checkbox.setEnabled(enabled)
        if enabled:
            self.show_regex_checkbox.setStyleSheet("")
            self.show_case_checkbox.setStyleSheet("")
        else:
            self.show_regex_checkbox.setStyleSheet("color: grey;")
            self.show_case_checkbox.setStyleSheet("color: grey;")

    def on_category_changed(self, current, previous):
        if not current:
            return
        index = self.category_tree.indexOfTopLevelItem(current)
        self.pages_widget.setCurrentIndex(index)

    def accept(self):
        selected_theme = self.theme_dropdown.currentText()
        if self.light_logo_radio.isChecked():
            logo_style = "Light"
        elif self.dark_logo_radio.isChecked():
            logo_style = "Dark"
        else:
            logo_style = "Darker"

        batch_size = self.batch_size_spinbox.value()
        keep_downloaded_in_queue = self.keep_downloaded_in_queue_checkbox.isChecked()
        delete_downloads_on_cancel = self.delete_downloads_on_cancel_checkbox.isChecked()
        folder_naming_format = self.id_folder_scheme.isChecked()

        auto_detect_urls = self.auto_detect_urls_checkbox.isChecked()
        auto_add_to_queue = self.auto_add_to_queue_checkbox.isChecked()

        show_logs = self.show_logs_checkbox.isChecked()
        show_provider = self.show_provider_checkbox.isChecked()
        show_queue_entire_workshop = self.show_queue_entire_workshop_checkbox.isChecked()

        new_settings = {
            'current_theme': selected_theme,
            'logo_style': logo_style,
            'batch_size': batch_size,
            'show_logs': show_logs,
            'show_provider': show_provider,
            'show_queue_entire_workshop': show_queue_entire_workshop,
            'keep_downloaded_in_queue': keep_downloaded_in_queue,
            'delete_downloads_on_cancel': delete_downloads_on_cancel,
            'folder_naming_format': folder_naming_format,
            'auto_detect_urls': auto_detect_urls,
            'auto_add_to_queue': auto_add_to_queue,
            'download_button': self.show_download_button_checkbox.isChecked(),
            'show_menu_bar': self.show_menu_bar_checkbox.isChecked(),
            'show_version': self.show_version_checkbox.isChecked(),
            'download_provider': self.parent().provider_dropdown.currentText()
        }
        super().accept()

    def get_settings(self):
        folder_format = "id"
        if self.name_folder_scheme.isChecked():
            folder_format = "name"
        elif self.combined_folder_scheme.isChecked():
            folder_format = "combined"
    
        return {
            'current_theme': self.theme_dropdown.currentText(),
            'logo_style': (
                "Light" if self.light_logo_radio.isChecked()
                else "Dark" if self.dark_logo_radio.isChecked()
                else "Darker"
            ),
            'batch_size': self.batch_size_spinbox.value(),
            'show_logs': self.show_logs_checkbox.isChecked(),
            'show_provider': self.show_provider_checkbox.isChecked(),
            'show_queue_entire_workshop': self.show_queue_entire_workshop_checkbox.isChecked(),
            'keep_downloaded_in_queue': self.keep_downloaded_in_queue_checkbox.isChecked(),
            'folder_naming_format': folder_format,
            'auto_detect_urls': self.auto_detect_urls_checkbox.isChecked(),
            'auto_add_to_queue': self.auto_add_to_queue_checkbox.isChecked(),
            'delete_downloads_on_cancel': self.delete_downloads_on_cancel_checkbox.isChecked(),
            'download_button': self.show_download_button_checkbox.isChecked(),
            'show_regex_button': self.show_regex_checkbox.isChecked(),
            'show_case_button': self.show_case_checkbox.isChecked(),
            'show_searchbar': self.show_searchbar_checkbox.isChecked(),
            'show_export_import_buttons': self.show_export_import_buttons_checkbox.isChecked(),
            'show_sort_indicator': self.show_sort_indicator_checkbox.isChecked(),
            'show_menu_bar': self.show_menu_bar_checkbox.isChecked(),
            'show_version': self.show_version_checkbox.isChecked(),
            'reset_provider_on_startup': self.reset_provider_checkbox.isChecked()
        }
        
    def reset_defaults(self):
        self.theme_dropdown.setCurrentText(DEFAULT_SETTINGS["current_theme"])
    
        logo_style = DEFAULT_SETTINGS["logo_style"]
        if logo_style == "Dark":
            self.dark_logo_radio.setChecked(True)
        elif logo_style == "Darker":
            self.darker_logo_radio.setChecked(True)
        else:
            self.light_logo_radio.setChecked(True)
            
        self.id_folder_scheme.setChecked(True)
    
        self.show_download_button_checkbox.setChecked(DEFAULT_SETTINGS["download_button"])
        self.show_searchbar_checkbox.setChecked(DEFAULT_SETTINGS["show_searchbar"])
        self.show_regex_checkbox.setChecked(DEFAULT_SETTINGS["show_regex_button"])
        self.show_case_checkbox.setChecked(DEFAULT_SETTINGS["show_case_button"])
        self.show_export_import_buttons_checkbox.setChecked(DEFAULT_SETTINGS["show_export_import_buttons"])
        self.show_sort_indicator_checkbox.setChecked(DEFAULT_SETTINGS["show_sort_indicator"])
        self.show_logs_checkbox.setChecked(DEFAULT_SETTINGS["show_logs"])
        self.show_queue_entire_workshop_checkbox.setChecked(DEFAULT_SETTINGS["show_queue_entire_workshop"])
        self.show_provider_checkbox.setChecked(DEFAULT_SETTINGS["show_provider"])
    
        self.batch_size_spinbox.setValue(DEFAULT_SETTINGS["batch_size"])
        self.keep_downloaded_in_queue_checkbox.setChecked(DEFAULT_SETTINGS["keep_downloaded_in_queue"])
        self.delete_downloads_on_cancel_checkbox.setChecked(DEFAULT_SETTINGS["delete_downloads_on_cancel"])
    
        self.auto_detect_urls_checkbox.setChecked(DEFAULT_SETTINGS["auto_detect_urls"])
        self.auto_add_to_queue_checkbox.setChecked(DEFAULT_SETTINGS["auto_add_to_queue"])
        self.update_checkbox_style()
        
        self.reset_provider_checkbox.setChecked(DEFAULT_SETTINGS["reset_provider_on_startup"])

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Streamline")
        self.setModal(True)
        self.setFixedSize(450, 350)
        
        apply_theme_titlebar(self, self.parent().config)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        logo_container = QWidget()
        logo_container.setFixedHeight(80)
        logo_container_layout = QVBoxLayout(logo_container)
        logo_container_layout.setContentsMargins(0, 0, 0, 0)
        
        logo_label = QLabel()
        logo_style = self.parent().config.get("logo_style", "Light")
        if logo_style == "Dark":
            logo = "logo_dark.png"
        elif logo_style == "Darker":
            logo = "logo_darker.png"
        else:
            logo = "logo.png"

        logo_path = resource_path(f'Files/{logo}')
        pixmap = QPixmap(logo_path)
        logo_label.setPixmap(pixmap.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        logo_container_layout.addWidget(logo_label)
        layout.addWidget(logo_container)

        title_label = QLabel("Streamline - Steam Workshop Downloader")
        title_label.setAlignment(Qt.AlignCenter)
        font = title_label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 3)
        title_label.setFont(font)
        title_label.setObjectName("about_title_label")
        layout.addWidget(title_label)

        version_label = QLabel(f"Version {current_version}")
        version_label.setAlignment(Qt.AlignCenter)
        version_font = version_label.font()
        version_font.setItalic(True)
        version_label.setFont(version_font)
        layout.addWidget(version_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        description = QLabel(
            "A modern Steam Workshop Downloader with queue management,\n"
            "supporting both SteamCMD and SteamWebAPI."
        )
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        description.setObjectName("about_description")
        description_font = description.font()
        description_font.setPointSize(description_font.pointSize() + 1)
        description.setFont(description_font)
        layout.addWidget(description)

        creator_label = QLabel("Created by <b>dane-9</b>")
        creator_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(creator_label)

        github_link = QLabel("<a style='color: #40b6e0; text-decoration: none;' href='https://github.com/dane-9/Streamline-Workshop-Downloader'>GitHub Repository</a>")
        github_link.setOpenExternalLinks(True)
        github_link.setAlignment(Qt.AlignCenter)
        link_font = github_link.font()
        link_font.setPointSize(link_font.pointSize() + 1)
        github_link.setFont(link_font)
        layout.addWidget(github_link)

        layout.addStretch(1)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setFixedWidth(100)
        ok_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(button_box, alignment=Qt.AlignCenter)

class ThemedMessageBox(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        if parent and hasattr(parent, 'config'):
            apply_theme_titlebar(self, parent.config)

    @staticmethod
    def question(parent, title, text, buttons=QMessageBox.Yes | QMessageBox.No, default_button=QMessageBox.No):
        msg_box = ThemedMessageBox(parent)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setStandardButtons(buttons)
        msg_box.setDefaultButton(default_button)
        return msg_box.exec()

    @staticmethod
    def information(parent, title, text, buttons=QMessageBox.Ok, default_button=QMessageBox.Ok):
        msg_box = ThemedMessageBox(parent)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setStandardButtons(buttons)
        msg_box.setDefaultButton(default_button)
        return msg_box.exec()

    @staticmethod
    def warning(parent, title, text, buttons=QMessageBox.Ok, default_button=QMessageBox.Ok):
        msg_box = ThemedMessageBox(parent)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setStandardButtons(buttons)
        msg_box.setDefaultButton(default_button)
        return msg_box.exec()

    @staticmethod
    def critical(parent, title, text, buttons=QMessageBox.Ok, default_button=QMessageBox.Ok):
        msg_box = ThemedMessageBox(parent)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setStandardButtons(buttons)
        msg_box.setDefaultButton(default_button)
        return msg_box.exec()
        
class AddSteamAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Steam Account")
        self.setModal(True)
        self.setFixedSize(300, 100)

        apply_theme_titlebar(self, self.parent().config)

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.username_input = QLineEdit()
        set_custom_clear_icon(self.username_input)
        self.username_input.setPlaceholderText("Enter Steam Username")
        form_layout.addRow("Username:", self.username_input)
        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()

        tooltip_label = QLabel(" After pressing \"OK\",\n SteamCMD won't visibly show\n the password being typed. ")
        tooltip_label.setStyleSheet("font-size: 10px;")
        tooltip_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        button_layout.addWidget(tooltip_label, alignment=Qt.AlignLeft)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        button_layout.addWidget(buttons, alignment=Qt.AlignRight)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_username(self):
        return self.username_input.text().strip()
        
class OverrideAppIDDialog(QDialog):
    def __init__(self, current_app_id="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Override AppID")
        self.setModal(True)
        self.setFixedSize(350, 100)
        
        apply_theme_titlebar(self, self.parent().config)

        layout = QVBoxLayout(self)
        
        self.label = QLabel("Enter AppID:")
        layout.addWidget(self.label)

        self.appid_input = QLineEdit()
        set_custom_clear_icon(self.appid_input)
        self.appid_input.setPlaceholderText("e.g., 108600 or a Steam URL with an AppID")
        layout.addWidget(self.appid_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel, parent=self)
        self.start_button = QPushButton("Set")
        buttons.addButton(self.start_button, QDialogButtonBox.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_new_app_id(self):
        return self.appid_input.text().strip()

class ItemFetcher(QThread):
    # Outputs messages
    item_processed = Signal(dict)
    error_occurred = Signal(str)
    mod_or_collection_detected = Signal(bool, str)

    def __init__(self, item_id, existing_mod_ids, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.existing_mod_ids = existing_mod_ids

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.process_item())

    async def process_item(self):
        try:
            async with aiohttp.ClientSession() as session:
                item_url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={self.item_id}"
                async with session.get(item_url) as response:
                    if response.status != 200:
                        self.error_occurred.emit(f"Failed to fetch item page. HTTP status: {response.status}")
                        return
                    page_content = await response.text()

                # Parse the HTML using lxml
                tree = html.fromstring(page_content)

                # Detects if it's a collection
                collection_items = tree.xpath('//div[contains(@class,"collectionChildren")]//div[contains(@class,"collectionItem")]')

                if collection_items:
                    # collection
                    self.mod_or_collection_detected.emit(True, self.item_id)
                    await self.process_collection(tree, session)
                else:
                    # mod
                    self.mod_or_collection_detected.emit(False, self.item_id)
                    await self.process_mod(tree)
        except Exception as e:
            self.error_occurred.emit(f"Error processing item: {e}")

    async def process_collection(self, tree, session):
        try:
            # get the collection's game info to pass to age-restricted mods
            collection_game_info = None
            breadcrumb_tag = tree.xpath('//div[@class="breadcrumbs"]/a[contains(@href, "/app/")]')
            if breadcrumb_tag:
                href = breadcrumb_tag[0].get('href')
                app_id_match = re.search(r'/app/(\d+)', href)
                if app_id_match:
                    app_id = app_id_match.group(1)
                    game_name = breadcrumb_tag[0].text_content().strip()
                    collection_game_info = {
                        'app_id': app_id,
                        'game_name': game_name
                    }
    
            # Fetch all the collection items in one go
            collection_items = tree.xpath('//div[contains(@class,"collectionChildren")]//div[contains(@class,"collectionItem")]')
            mod_ids = set()
            for item in collection_items:
                a_tag = item.xpath('.//a[@href]')
                if a_tag:
                    mod_id = self.extract_id(a_tag[0].get('href'))
                    if mod_id and mod_id not in self.existing_mod_ids:
                        mod_ids.add(mod_id)
    
            # Gather all mod info concurrently
            tasks = [self.fetch_mod_info(session, mod_id, collection_game_info=collection_game_info) for mod_id in mod_ids]
            mods_info = await asyncio.gather(*tasks)
    
            self.item_processed.emit({
                'type': 'collection',
                'mods_info': mods_info,
            })
        except Exception as e:
            self.error_occurred.emit(f"Error processing collection: {e}")

    async def process_mod(self, tree):
        try:
            mod_info = await self.fetch_mod_info(None, self.item_id, tree=tree)
            self.item_processed.emit({
                'type': 'mod',
                'mod_info': mod_info
            })
        except Exception as e:
            self.error_occurred.emit(f"Error processing mod: {e}")

    async def fetch_mod_info(self, session, mod_id, tree=None, collection_game_info=None):
        try:
            if tree is None:
                url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={mod_id}"
                async with session.get(url) as response:
                    if response.status != 200:
                        if collection_game_info:
                            return {'mod_id': mod_id, 'mod_name': 'Unknown Title', 'app_id': collection_game_info.get('app_id'), 'game_name': collection_game_info.get('game_name', 'Unknown Game')}
                        else:
                            return {'mod_id': mod_id, 'mod_name': 'Unknown Title', 'app_id': None, 'game_name': 'Unknown Game'}
                    page_content = await response.text()
                    tree = html.fromstring(page_content)
    
            # Check if this is a login-required/age-restricted page
            error_messages = tree.xpath('//div[@class="error_ctn"]//h3/text()')
            login_required = False
            for msg in error_messages:
                if "You must be logged in to view this item" in msg:
                    login_required = True
                    break
    
            if login_required:
                if collection_game_info:
                    return {
                        'mod_id': mod_id, 
                        'mod_name': 'UNKNOWN - Age Restricted', 
                        'app_id': collection_game_info.get('app_id'), 
                        'game_name': collection_game_info.get('game_name', 'Unknown Game')
                    }

                app_id = None
                app_id_match = re.search(r'appid=(\d+)', tree.base_url) if hasattr(tree, 'base_url') else None
                if app_id_match:
                    app_id = app_id_match.group(1)
                    game_name = 'Unknown Game'
                    if hasattr(self, 'app_ids') and app_id in self.app_ids:
                        game_name = self.app_ids[app_id]
                    
                    return {
                        'mod_id': mod_id, 
                        'mod_name': 'UNKNOWN - Age Restricted', 
                        'app_id': app_id, 
                        'game_name': game_name
                    }
                else:
                    return {
                        'mod_id': mod_id, 
                        'mod_name': 'UNKNOWN - Age Restricted', 
                        'app_id': None, 
                        'game_name': 'Unknown Game'
                    }
                    
            breadcrumb_tag = tree.xpath('//div[@class="breadcrumbs"]/a[contains(@href, "/app/")]')
            title_tag = tree.xpath('//div[@class="workshopItemTitle"]')
    
            # Fetch game info from breadcrumbs
            game_name, app_id = 'Unknown Game', None
            if breadcrumb_tag:
                href = breadcrumb_tag[0].get('href')
                app_id_match = re.search(r'/app/(\d+)', href)  # Extract the app ID from the href
                if app_id_match:
                    app_id = app_id_match.group(1)
                    game_name = breadcrumb_tag[0].text_content().strip()
    
            mod_title = title_tag[0].text.strip() if title_tag else 'Unknown Title'
    
            return {'mod_id': mod_id, 'mod_name': mod_title, 'app_id': app_id, 'game_name': game_name}
    
        except Exception as e:
            return {'mod_id': mod_id, 'mod_name': 'Unknown Title', 'app_id': None, 'game_name': 'Unknown Game'}

    def extract_id(self, input_str):
        pattern = r'https?://steamcommunity\.com/sharedfiles/filedetails/\?id=(\d+)'
        match = re.match(pattern, input_str)
        if match:
            return match.group(1)
        elif input_str.isdigit():
            return input_str
        else:
            id_match = re.search(r'(\d+)', input_str)
            if id_match:
                return id_match.group(1)
        return None

class TokenMonitorWorker(QThread):
    token_found = Signal(str)
    timeout = Signal()

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
                    if "}" in line:
                        break
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
        self.config = config
        self.steamcmd_dir = steamcmd_dir
        self.token_monitor_worker = None
        self.steamcmd_process = None
        
        apply_theme_titlebar(self, self.parent().config)

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
        if dialog.exec() == QDialog.Accepted:
            username = dialog.get_username()
            if not username:
                ThemedMessageBox.warning(self, 'Input Error', 'Username cannot be empty.')
                return
            if any(acc['username'] == username for acc in self.config['steam_accounts']):
                ThemedMessageBox.warning(self, 'Duplicate Account', 'This Steam account is already added.')
                return
            existing_tokens = self.get_all_token_ids()
            self.launch_steamcmd(username)

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
        ThemedMessageBox.information(self, 'Success', f"Steam account '{username}' added.")
        if self.steamcmd_process and self.steamcmd_process.poll() is None:
            self.steamcmd_process.terminate()
        self.token_monitor_worker = None

    def on_token_timeout(self, username):
        ThemedMessageBox.warning(self, 'Error', f"Failed to retrieve token ID for account '{username}'. Please ensure you have logged in successfully.")
        self.token_monitor_worker = None

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
        menu.exec(self.accounts_list.viewport().mapToGlobal(position))

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

            self.token_monitor_worker = TokenMonitorWorker(self.steamcmd_dir, existing_tokens)
            self.token_monitor_worker.token_found.connect(lambda new_token_id: self.on_token_found_reauth(username, new_token_id))
            self.token_monitor_worker.timeout.connect(lambda: self.on_token_timeout_reauth(username))
            self.token_monitor_worker.start()
        else:
            ThemedMessageBox.warning(self, 'Error', f"Failed to remove token for account '{username}'.")

    def on_token_found_reauth(self, username, new_token_id):
        for account in self.config['steam_accounts']:
            if account['username'] == username:
                account['token_id'] = new_token_id
                break
        self.load_accounts()
        ThemedMessageBox.information(self, 'Success', f"Account '{username}' reauthenticated.")
        if self.steamcmd_process and self.steamcmd_process.poll() is None:
            self.steamcmd_process.terminate()
        self.token_monitor_worker = None

    def on_token_timeout_reauth(self, username):
        ThemedMessageBox.warning(self, 'Error', f"Failed to retrieve new token ID for account '{username}'. Please ensure you have logged in successfully.")
        self.token_monitor_worker = None

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
        reply = ThemedMessageBox.question(self, 'Remove Account', f"Are you sure you want to remove account '{username}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # First remove the token entry and the associated account block from the config.vdf
            if self.remove_token_from_config_vdf(token_id):
                # Remove the account from the internal config
                self.config['steam_accounts'] = [acc for acc in self.config['steam_accounts'] if acc['username'] != username]
                self.load_accounts()
                ThemedMessageBox.information(self, 'Success', f"Account '{username}' removed.")
            else:
                ThemedMessageBox.warning(self, 'Error', f"Failed to remove token for account '{username}'.")

    def purge_accounts(self):
        reply = ThemedMessageBox.question(self, 'Purge Accounts', 'Are you sure you want to remove all accounts?', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            for account in self.config['steam_accounts']:
                token_id = account.get('token_id', '')
                if token_id:
                    self.remove_token_from_config_vdf(token_id)
            self.config['steam_accounts'] = []
            self.load_accounts()
            ThemedMessageBox.information(self, 'Success', 'All accounts have been purged.')

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
            new_lines = []
            in_connect_cache = False
            in_accounts_section = False
            current_account = None
            account_to_remove = None
            token_to_remove = f'"{token_id}"'
            skip_account_block = False
            brace_depth = 0
    
            with open(config_vdf_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
    
            # Traverse the file and identify which sections to modify
            for line in lines:
                stripped_line = line.strip()
    
                # Determine when we are inside the "ConnectCache" section
                if '"ConnectCache"' in stripped_line:
                    in_connect_cache = True
                    new_lines.append(line)
                    continue
    
                if in_connect_cache:
                    # Detect the end of the "ConnectCache" section
                    if "}" in stripped_line:
                        in_connect_cache = False
    
                    # Skip the line if it's the token we want to remove
                    if token_to_remove in stripped_line:
                        continue
    
                # Determine when we are inside the "Accounts" section
                if '"Accounts"' in stripped_line:
                    in_accounts_section = True
                    new_lines.append(line)
                    continue
    
                if in_accounts_section:
                    # Detect the end of the "Accounts" section
                    if "}" in stripped_line and brace_depth == 0:
                        in_accounts_section = False
    
                    # Check if we're at the start of a new account block
                    if stripped_line.startswith('"') and not stripped_line.endswith("{"):
                        current_account = stripped_line.split('"')[1]
                        brace_depth = 0
    
                    # Detect the start of the account block and track depth
                    if "{" in stripped_line:
                        brace_depth += 1
    
                    # Detect the end of the account block and adjust depth
                    if "}" in stripped_line:
                        brace_depth -= 1
                        # If we've closed the account block, reset the tracking
                        if brace_depth == 0 and skip_account_block:
                            skip_account_block = False
                            continue
    
                    # Identify which account to remove based on the token ID
                    if token_id and current_account and self.is_account_in_config_json(current_account, token_id):
                        account_to_remove = current_account
                        skip_account_block = True
    
                    # Skip lines belonging to the account block that is marked for removal
                    if skip_account_block:
                        continue
    
                # Add the line to the new lines if not skipped
                new_lines.append(line)
    
            # Write the updated lines back to the file
            with open(config_vdf_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
    
            return True
    
        except Exception as e:
            print(f"Error modifying config.vdf: {e}")
            return False
    
    def is_account_in_config_json(self, account_name, token_id):
        # This function checks if the given account name in the config JSON matches the token ID we are trying to remove.
        account = next((acc for acc in self.config['steam_accounts'] if acc['username'] == account_name), None)
        return account is not None and account.get('token_id', '') == token_id

    def launch_steamcmd(self, username):
        cmd = os.path.join(self.steamcmd_dir, 'steamcmd.exe')
        if not os.path.isfile(cmd):
            ThemedMessageBox.critical(self, 'Error', f"SteamCMD executable not found at {cmd}.")
            return
        cmd_command = [cmd, '+login', username, '+quit']
        try:
            self.steamcmd_process = subprocess.Popen(
                cmd_command,
                cwd=self.steamcmd_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        except Exception as e:
            ThemedMessageBox.critical(self, 'Error', f"Failed to launch SteamCMD: {e}")

    def get_updated_config(self):
        return self.config
        
def create_custom_cursor(direction):
    # Get the scaling factor based on DPI
    screen = QApplication.primaryScreen()
    scaling_factor = screen.devicePixelRatio()

    # Define base sizes
    base_pixmap_size = 24
    base_circle_radius = 2
    base_arrow_offset = 8

    # Scale the sizes according to the screen scaling factor
    pixmap_size = int(base_pixmap_size * scaling_factor)
    circle_radius = int(base_circle_radius * scaling_factor)
    arrow_offset = int(base_arrow_offset * scaling_factor)

    pixmap = QPixmap(pixmap_size, pixmap_size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    outline_color = QColor(255, 255, 255)
    fill_color = QColor(0, 0, 0)

    center = QPoint(pixmap_size // 2, pixmap_size // 2)

    # Draw circle in the center for all cursors
    painter.setPen(fill_color)
    painter.setBrush(fill_color)
    painter.drawEllipse(center, circle_radius, circle_radius)

    # Helper function to draw outlined arrows
    def draw_outlined_arrow(arrow):
        painter.setPen(outline_color)
        painter.setBrush(outline_color)
        painter.drawPolygon(arrow)

        painter.setPen(fill_color)
        painter.setBrush(fill_color)
        painter.drawPolygon(arrow)

    if direction == 'stationary':

        up_arrow_tip_y = center.y() - circle_radius - arrow_offset
        up_arrow_base_y = center.y() - circle_radius - int(arrow_offset / 2)
        up_arrow = QPolygon([
            QPoint(center.x(), up_arrow_tip_y),                 # Tip of the arrow
            QPoint(center.x() - 4 * scaling_factor, up_arrow_base_y),  # Bottom left
            QPoint(center.x() + 4 * scaling_factor, up_arrow_base_y)   # Bottom right
        ])
        draw_outlined_arrow(up_arrow)

        down_arrow_tip_y = center.y() + circle_radius + arrow_offset
        down_arrow_base_y = center.y() + circle_radius + int(arrow_offset / 2)
        down_arrow = QPolygon([
            QPoint(center.x(), down_arrow_tip_y),               # Tip of the arrow
            QPoint(center.x() - 4 * scaling_factor, down_arrow_base_y),  # Top left
            QPoint(center.x() + 4 * scaling_factor, down_arrow_base_y)   # Top right
        ])
        draw_outlined_arrow(down_arrow)

    elif direction == 'up':
        up_arrow_tip_y = center.y() - circle_radius - arrow_offset
        up_arrow_base_y = center.y() - circle_radius - int(arrow_offset / 2)
        up_arrow = QPolygon([
            QPoint(center.x(), up_arrow_tip_y),                 # Tip of the arrow
            QPoint(center.x() - 4 * scaling_factor, up_arrow_base_y),  # Bottom left
            QPoint(center.x() + 4 * scaling_factor, up_arrow_base_y)   # Bottom right
        ])
        draw_outlined_arrow(up_arrow)

    elif direction == 'down':
        down_arrow_tip_y = center.y() + circle_radius + arrow_offset
        down_arrow_base_y = center.y() + circle_radius + int(arrow_offset / 2)
        down_arrow = QPolygon([
            QPoint(center.x(), down_arrow_tip_y),               # Tip of the arrow
            QPoint(center.x() - 4 * scaling_factor, down_arrow_base_y),  # Top left
            QPoint(center.x() + 4 * scaling_factor, down_arrow_base_y)   # Top right
        ])
        draw_outlined_arrow(down_arrow)

    painter.end()

    cursor = QCursor(pixmap, pixmap_size // 2, pixmap_size // 2)
    return cursor

class OutsideClickFilter(QObject):
    def __init__(self, tree_widget):
        super().__init__()
        self.tree_widget = tree_widget

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if self.tree_widget.auto_scroll_active:

                global_pos = event.globalPosition().toPoint()
                widget_pos = self.tree_widget.mapFromGlobal(global_pos)
                if not self.tree_widget.rect().contains(widget_pos):
                    self.tree_widget.exit_auto_scroll()
        return False
        
class UpdateAppIDsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update AppIDs")
        self.setModal(True)
        self.setFixedSize(400, 200)
        
        apply_theme_titlebar(self, self.parent().config)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 25, 10, 10)
        
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.StyledPanel)
        info_frame.setObjectName("appid_info_frame")
        
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(8)
        
        self.last_updated_label = QLabel()
        self.last_updated_label.setStyleSheet("font-weight: normal;")
        
        self.total_appids_label = QLabel()
        self.total_appids_label.setStyleSheet("font-weight: normal;")
        
        info_layout.addWidget(self.last_updated_label)
        info_layout.addWidget(self.total_appids_label)
        
        self.update_file_info()
        main_layout.addWidget(info_frame)
        
        types_label = QLabel("Select Types to Update:")
        font = types_label.font()
        font.setBold(True)
        types_label.setFont(font)
        main_layout.addWidget(types_label)
        
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(15)
        
        self.games_checkbox = QCheckBox("Games")
        self.games_checkbox.setChecked(True)
        
        self.applications_checkbox = QCheckBox("Applications")
        self.applications_checkbox.setChecked(False)
        
        self.tools_checkbox = QCheckBox("Tools")
        self.tools_checkbox.setChecked(False)
        
        checkbox_layout.addWidget(self.games_checkbox)
        checkbox_layout.addWidget(self.applications_checkbox)
        checkbox_layout.addWidget(self.tools_checkbox)
        checkbox_layout.addStretch()
        
        main_layout.addLayout(checkbox_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        start_button = buttons.addButton("Start Update", QDialogButtonBox.AcceptRole)
        
        start_button.setFixedWidth(100)
        start_button.setStyleSheet("background-color: #4D8AC9; color: #FFFFFF; font-weight: bold;")
        
        cancel_button = buttons.button(QDialogButtonBox.Cancel)
        cancel_button.setFixedWidth(100)
        
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        main_layout.addWidget(buttons, alignment=Qt.AlignRight)
    
    def update_file_info(self):
        appids_path = os.path.join(self.parent().files_dir, 'AppIDs.txt')
        if os.path.isfile(appids_path):
            # Get last modified time
            mtime = os.path.getmtime(appids_path)
            last_updated_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
            self.last_updated_label.setText(f"Last Updated: {last_updated_str}")
            
            # Count non-empty lines
            with open(appids_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            total_count = len([line for line in lines if line.strip()])
            self.total_appids_label.setText(f"Current AppIDs: {total_count}")
        else:
            self.last_updated_label.setText("Last Updated: N/A")
            self.total_appids_label.setText("Current AppIDs: 0")
    
    def get_selected_types(self):
        types = []
        if self.games_checkbox.isChecked():
            types.append("Game")
        if self.applications_checkbox.isChecked():
            types.append("Application")
        if self.tools_checkbox.isChecked():
            types.append("Tool")
        return types

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        # Remove the hover state if the item is not selected
        if not (option.state & QStyle.State_Selected):
            option.state &= ~QStyle.State_MouseOver

class CustomizableTreeWidgets(QTreeWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.auto_scroll_active = False
        self.auto_scroll_start_pos = QPoint()
        self.scroll_timer = QTimer()
        self.scroll_timer.timeout.connect(self.auto_scroll)
        self.setMouseTracking(True)

        # Initialize accumulated scroll position
        self.accumulated_scroll_y = 0.0

        # Create an instance of the outside click filter
        self.outside_click_filter = OutsideClickFilter(self)

        # Create custom cursors
        self.stationary_cursor = create_custom_cursor('stationary')
        self.up_cursor = create_custom_cursor('up')
        self.down_cursor = create_custom_cursor('down')

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            if not self.auto_scroll_active:
                # Start auto-scroll mode
                self.auto_scroll_active = True
                self.auto_scroll_start_pos = QCursor.pos()

                # Set the override cursor to show custom cursor globally
                QApplication.setOverrideCursor(self.stationary_cursor)
                self.current_cursor_shape = 'stationary'

                self.scroll_timer.start(10)

                # Install the event filter to detect clicks outside
                QApplication.instance().installEventFilter(self.outside_click_filter)

                event.accept()
            else:
                # Exit auto-scroll mode
                self.exit_auto_scroll()
                event.accept()
        else:
            if self.auto_scroll_active:
                # Exit auto-scroll mode on any mouse button press
                self.exit_auto_scroll()
                event.accept()
            else:
                super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.auto_scroll_active:
            # No need to handle mouse movements here
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def exit_auto_scroll(self):
        if self.auto_scroll_active:
            self.auto_scroll_active = False

            # Restore the original cursor
            QApplication.restoreOverrideCursor()

            self.scroll_timer.stop()

            # Reset accumulated scroll position
            self.accumulated_scroll_y = 0.0

            # Remove the event filter
            QApplication.instance().removeEventFilter(self.outside_click_filter)

    def auto_scroll(self):
        if self.auto_scroll_active:
            current_pos = QCursor.pos()
            delta = current_pos - self.auto_scroll_start_pos

            # Compute scroll speed based on custom acceleration
            scroll_speed_y = self.compute_scroll_speed(delta.y())

            # Update cursor based on scroll direction
            if scroll_speed_y == 0 and self.current_cursor_shape != 'stationary':
                QApplication.changeOverrideCursor(self.stationary_cursor)
                self.current_cursor_shape = 'stationary'
            elif scroll_speed_y < 0 and self.current_cursor_shape != 'up':
                QApplication.changeOverrideCursor(self.up_cursor)
                self.current_cursor_shape = 'up'
            elif scroll_speed_y > 0 and self.current_cursor_shape != 'down':
                QApplication.changeOverrideCursor(self.down_cursor)
                self.current_cursor_shape = 'down'

            # Add the speed to accumulated scroll position
            self.accumulated_scroll_y += scroll_speed_y

            # Determine integer scroll amount
            scroll_amount_y = int(self.accumulated_scroll_y)

            # Update the vertical scrollbar with integer
            if scroll_amount_y != 0:
                self.verticalScrollBar().setValue(self.verticalScrollBar().value() + scroll_amount_y)
                self.accumulated_scroll_y -= scroll_amount_y

    def compute_scroll_speed(self, delta):
        deadzone = 15  # pixels

        if abs(delta) < deadzone:
            return 0.0

        max_speed = 12.0
        max_distance = 200

        # Calculate distance from deadzone
        distance = abs(delta) - deadzone

        # Clamp distance to max_distance
        distance = min(distance, max_distance)

        # Linear acceleration
        speed = (distance / max_distance) * max_speed

        return speed if delta > 0 else -speed
        
class QueueInsertionWorker(QThread):
    batch_ready = Signal(list)
    progress_update = Signal(int, int)
    finished = Signal()

    def __init__(self, mods, game_name, appid, provider, parent=None):
        super().__init__(parent)
        self.mods = mods
        self.game_name = game_name
        self.appid = appid
        self.provider = provider

    def run(self):
        batch_size = 200
        total_mods = len(self.mods)
        processed_count = 0
        batch = []

        for mod_id, mod_title in self.mods:
            mod_info = {
                'game_name': self.game_name,
                'mod_id': mod_id,
                'mod_name': mod_title,
                'status': 'Queued',
                'retry_count': 0,
                'app_id': self.appid,
                'provider': self.provider
            }
            batch.append(mod_info)

            if len(batch) >= batch_size:
                self.batch_ready.emit(batch)
                processed_count += len(batch)
                batch = []
                self.progress_update.emit(processed_count, total_mods)

        if batch:
            self.batch_ready.emit(batch)
            processed_count += len(batch)
            self.progress_update.emit(processed_count, total_mods)

        self.finished.emit()

class QueueEntireWorkshopDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Queue Entire Workshop")
        self.setModal(True)
        self.setFixedSize(350, 100)
        
        apply_theme_titlebar(self, self.parent().config)

        layout = QVBoxLayout(self)

        self.label = QLabel("Enter AppID:")
        layout.addWidget(self.label)

        self.input_line = QLineEdit()
        set_custom_clear_icon(self.input_line)
        self.input_line.setPlaceholderText("e.g., 108600 or a Steam URL with an AppID")
        layout.addWidget(self.input_line)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel, parent=self)
        self.start_button = QPushButton("Start")
        buttons.addButton(self.start_button, QDialogButtonBox.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_input(self):
        return self.input_line.text().strip()

async def fetch_page(session, url, params, log_signal=None):
    try:
        async with session.get(url, params=params) as response:
            if response.status != 200:
                if log_signal:
                    log_signal.emit(f"Failed to fetch page {params['p']}: HTTP {response.status}")
                return None
            return await response.text()
    except Exception as e:
        if log_signal:
            log_signal.emit(f"Error fetching page {params['p']}: {e}")
        return None

async def parse_page(page_content, page_number, log_signal=None):
    mods = []
    try:
        tree = html.fromstring(page_content)
        workshop_items = tree.xpath("//div[@class='workshopItem']")
        for item in workshop_items:
            link = item.xpath(".//a[contains(@href, 'sharedfiles/filedetails')]")
            if not link:
                if log_signal:
                    log_signal(f"Page {page_number}: Skipped item, no link found.")
                continue
            mod_id = link[0].get("data-publishedfileid")
            if not mod_id:
                mod_id = link[0].get("href").split("?id=")[-1]
            title_div = item.xpath(".//div[contains(@class,'workshopItemTitle')]")
            if not title_div:
                if log_signal:
                    log_signal(f"Page {page_number}: Skipped item, no title found.")
                continue
            mod_name = title_div[0].text_content().strip()
            mods.append((mod_id, mod_name))
    except Exception as e:
        if log_signal:
            log_signal(f"Error parsing page {page_number}: {e}")
    return mods

async def scrape_workshop_data(appid, sort="toprated", section="readytouseitems", concurrency=100, log_signal=None, app_ids=None, queue_entire_workshop_btn=None):
    base_url = "https://steamcommunity.com/workshop/browse/"
    params = {"appid": str(appid), "browsesort": sort, "section": section, "p": "1"}
    all_mods = []
    game_name = "Unknown Game"

    if queue_entire_workshop_btn:
        queue_entire_workshop_btn.setEnabled(False)

    async with aiohttp.ClientSession() as session:
        first_page_content = await fetch_page(session, base_url, params, log_signal=log_signal)
        if not first_page_content:
            if log_signal:
                log_signal("Failed to fetch the first page.")
            if queue_entire_workshop_btn:
                queue_entire_workshop_btn.setEnabled(True)
            return game_name, []

        tree = html.fromstring(first_page_content)
        paging_info = tree.xpath("//div[@class='workshopBrowsePagingInfo']/text()")
        if not paging_info:
            if log_signal:
                log_signal("Could not find paging info on the first page. Possibly no results.")
            if queue_entire_workshop_btn:
                queue_entire_workshop_btn.setEnabled(True)
            return game_name, []

        # Determine game_name
        if app_ids and appid in app_ids:
            game_name = app_ids[appid]
        else:
            gn = tree.xpath('//div[@class="apphub_AppName ellipsis"]/text()')
            if gn:
                game_name = gn[0].strip()

        # Extract total entries
        total_entries = 0
        for text_line in paging_info:
            if "of" in text_line.lower():
                parts = text_line.split()
                try:
                    total_entries = int(parts[parts.index("of") + 1].replace(",", ""))
                except (ValueError, IndexError):
                    if log_signal:
                        log_signal("Failed to parse total entries.")
                    if queue_entire_workshop_btn:
                        queue_entire_workshop_btn.setEnabled(True)
                    return game_name, []
        if total_entries == 0:
            if log_signal:
                log_signal("No entries found for this workshop.")
            if queue_entire_workshop_btn:
                queue_entire_workshop_btn.setEnabled(True)
            return game_name, []

        mods_per_page = 30
        total_pages = (total_entries + mods_per_page - 1) // mods_per_page
        max_page_count = 1667
        total_pages = min(total_pages, max_page_count)
        if log_signal:
            log_signal(f"Total mods: {total_entries}, Total pages: {total_pages} (capped at {max_page_count})")

        pages_fetched = 0

        # Fetch all pages in blocks of "concurrency"
        for start_page in range(1, total_pages + 1, concurrency):
            end_page = min(start_page + concurrency - 1, total_pages)

            if log_signal and pages_fetched > 0:
                log_signal(f"Pages fetched: {pages_fetched} / {total_pages}")

            tasks = []
            for page in range(start_page, end_page + 1):
                page_params = {
                    "appid": str(appid),
                    "browsesort": sort,
                    "section": section,
                    "p": str(page)
                }
                tasks.append(fetch_page(session, base_url, page_params, log_signal=log_signal))

            pages_content = await asyncio.gather(*tasks)

            parse_tasks = []
            for content in pages_content:
                if content:
                    parse_tasks.append(parse_page(content, 0, log_signal=None))  # page_number = 0, silent

            results = await asyncio.gather(*parse_tasks)
            for result in results:
                all_mods.extend(result)
            pages_fetched += len(results)

        if log_signal and pages_fetched > 0:
            # Final update for pages_fetched
            log_signal(f"Pages fetched: {pages_fetched} / {total_pages}")

    if queue_entire_workshop_btn:
        queue_entire_workshop_btn.setEnabled(True)

    return game_name, all_mods


class WorkshopScraperWorker(QThread):
    finished_scraping = Signal(str, list)  # Emit game_name and mods
    log_signal = Signal(str)

    def __init__(self, appid, app_ids, queue_entire_workshop_btn=None):
        super().__init__()
        self.appid = appid
        self.app_ids = app_ids
        self.queue_entire_workshop_btn = queue_entire_workshop_btn

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        def log_message(msg):
            self.log_signal.emit(msg)

        game_name, mods = loop.run_until_complete(scrape_workshop_data( appid=self.appid, log_signal=log_message, app_ids=self.app_ids, queue_entire_workshop_btn=self.queue_entire_workshop_btn ))
        self.finished_scraping.emit(game_name, mods)

class SteamWorkshopDownloader(QWidget):
    log_signal = Signal(str)
    update_queue_signal = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.download_queue = []
        self.downloaded_mods_info = {}
        self.is_downloading = False
        self.header_locked = True
        self.lock_action = None
        self.files_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'Files')
        os.makedirs(self.files_dir, exist_ok=True)
        self.themes_dir = os.path.join(self.files_dir, 'Themes')
        os.makedirs(self.themes_dir, exist_ok=True)
        self.config = {}
        self.config_path = self.get_config_path()
        self.load_config()
        if self.config.get("reset_provider_on_startup", False):
            self.config["download_provider"] = "Default"
            self.save_config()
        self.updateWindowTitle()
        self.steamcmd_dir = os.path.join(self.files_dir, 'steamcmd')
        self.steamcmd_executable = self.get_steamcmd_executable_path()
        self.current_process = None
        self.tooltip_manager = TooltipManager.instance()
        
        self.status_updates = {}
        self.status_update_timer = QTimer()
        self.status_update_timer.setSingleShot(True)
        self.status_update_timer.timeout.connect(self.log_status_updates)

        self.clipboard = QApplication.clipboard()
        self.last_clipboard_text = ""
        self.clipboard_signal_connected = False
        self.item_fetchers = []

        logo_style = self.config.get("logo_style", DEFAULT_SETTINGS["logo_style"])
        if logo_style == "Dark":
            logo = "logo_dark.png"
        elif logo_style == "Darker":
            logo = "logo_darker.png"
        else:
            logo = "logo.png"
        self.setWindowIcon(QIcon(resource_path(f'Files/{logo}')))

        current_theme = self.config.get("current_theme", DEFAULT_SETTINGS["current_theme"])
        self.config.setdefault("current_theme", current_theme)
        load_theme(QApplication.instance(), self.config['current_theme'], self.files_dir)

        is_dark = "dark" in current_theme.lower()
        set_windows_dark_titlebar(int(self.winId()), is_dark)

        self.downloads_root_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'Downloads')
        self.steamcmd_download_path = os.path.join(self.downloads_root_path, 'SteamCMD')
        self.steamwebapi_download_path = os.path.join(self.downloads_root_path, 'SteamWebAPI')
        os.makedirs(self.steamcmd_download_path, exist_ok=True)
        os.makedirs(self.steamwebapi_download_path, exist_ok=True)

        # Load App IDs from AppIDs.txt
        self.app_ids = {}
        self.load_app_ids()

        # Initialize the UI after loading config
        self.column_width_backup = {}
        self.initUI()
        self.adjust_widget_heights()

        self.apply_settings()
        self.populate_steam_accounts()

        self.download_counter = 0
        self.consecutive_failures = 0

        # Set up signals and threads
        self.log_signal.connect(self.append_log)
        self.update_queue_signal.connect(self.update_queue_status)

        window_size = self.config.get('window_size')
        if window_size:
            self.resize(window_size.get('width', 670), window_size.get('height', 750))
        else:
            self.resize(670, 750)

    def initUI(self):
        self.setWindowTitle('Streamline')
        self.main_layout = QVBoxLayout(self)
        if self.config.get("show_menu_bar", True):
            self.main_layout.setContentsMargins(6, 0, 6, 6)
            self.main_layout.setSpacing(6)
        else:
            self.main_layout.setContentsMargins(6, 6, 6, 6)
            self.main_layout.setSpacing(6)
            
        self.current_filter = "All"

        self.menu_bar = QMenuBar()
        self.menu_bar.setObjectName("menuBar")
        self.main_layout.setMenuBar(self.menu_bar)

        self.appearance_menu = self.menu_bar.addMenu("Appearance")
        self.tools_menu = self.menu_bar.addMenu("Tools")
        self.help_menu = self.menu_bar.addMenu("Help")

        self.theme_submenu = QMenu("Theme", self)
        self.appearance_menu.addMenu(self.theme_submenu)

        themes_available = []
        if hasattr(self, 'files_dir'):
            theme_dir = os.path.join(self.files_dir, "Themes")
            if os.path.isdir(theme_dir):
                for f in os.listdir(theme_dir):
                    if f.endswith(".qss"):
                        themes_available.append(os.path.splitext(f)[0])
        if not themes_available:
            themes_available = ["Dark", "Light"]

        self.theme_actions = []
        current_theme_name = self.config.get("current_theme", "Dark")
        for theme_name in themes_available:
            action = QAction(theme_name, self, checkable=True)
            action.setChecked(theme_name == current_theme_name)
            action.triggered.connect(lambda checked, tn=theme_name: self.set_theme(tn) if checked else None)
            self.theme_submenu.addAction(action)
            self.theme_actions.append(action)

        self.logo_submenu = QMenu("Logo Style", self)
        self.appearance_menu.addMenu(self.logo_submenu)

        self.logo_styles = ["Light", "Dark", "Darker"]
        current_logo_style = self.config.get("logo_style", "Light")
        self.logo_actions = []
        for ls in self.logo_styles:
            logo_action = QAction(ls, self, checkable=True)
            logo_action.setChecked(ls == current_logo_style)
            logo_action.triggered.connect(lambda checked, style=ls: self.set_logo_style(style) if checked else None)
            self.logo_submenu.addAction(logo_action)
            self.logo_actions.append(logo_action)

        self.show_download_button_act = QAction("Download Button", self, checkable=True)
        self.show_download_button_act.setChecked(self.config["download_button"])
        self.show_download_button_act.triggered.connect(lambda checked: self.toggle_config("download_button", checked))

        self.show_searchbar_act = QAction("Search Bar", self, checkable=True)
        self.show_searchbar_act.setChecked(self.config["show_searchbar"])
        self.show_searchbar_act.triggered.connect(lambda checked: self.toggle_config("show_searchbar", checked))

        self.show_regex_act = QAction("Regex", self, checkable=True)
        self.show_regex_act.setChecked(self.config["show_regex_button"])
        self.show_regex_act.triggered.connect(lambda checked: self.toggle_config("show_regex_button", checked))

        self.show_case_act = QAction("Case-Sensitivity", self, checkable=True)
        self.show_case_act.setChecked(self.config["show_case_button"])
        self.show_case_act.triggered.connect(lambda checked: self.toggle_config("show_case_button", checked))

        self.show_import_export_act = QAction("Import/Export Buttons", self, checkable=True)
        self.show_import_export_act.setChecked(self.config["show_export_import_buttons"])
        self.show_import_export_act.triggered.connect(lambda checked: self.toggle_config("show_export_import_buttons", checked))

        self.show_sort_act = QAction("Header Sort Indicator", self, checkable=True)
        self.show_sort_act.setChecked(self.config["show_sort_indicator"])
        self.show_sort_act.triggered.connect(lambda checked: self.toggle_config("show_sort_indicator", checked))

        self.show_logs_act = QAction("Logs View", self, checkable=True)
        self.show_logs_act.setChecked(self.config["show_logs"])
        self.show_logs_act.triggered.connect(lambda checked: self.toggle_config("show_logs", checked))

        self.show_workshop_btn_act = QAction("Queue Entire Workshop Button", self, checkable=True)
        self.show_workshop_btn_act.setChecked(self.config["show_queue_entire_workshop"])
        self.show_workshop_btn_act.triggered.connect(lambda checked: self.toggle_config("show_queue_entire_workshop", checked))

        self.show_provider_act = QAction("Provider Dropdown", self, checkable=True)
        self.show_provider_act.setChecked(self.config["show_provider"])
        self.show_provider_act.triggered.connect(lambda checked: self.toggle_config("show_provider", checked))

        self.appearance_menu.addSeparator()
        self.show_submenu = QMenu("Show", self)
        self.appearance_menu.addMenu(self.show_submenu)

        self.show_submenu.addAction(self.show_download_button_act)
        self.show_submenu.addAction(self.show_searchbar_act)

        self.searchbar_options_menu = QMenu("Search Bar Options", self)
        self.searchbar_options_menu.addAction(self.show_regex_act)
        self.searchbar_options_menu.addAction(self.show_case_act)

        self.show_searchbar_act.toggled.connect(lambda checked: self.searchbar_options_menu.setEnabled(checked))
        self.show_submenu.addMenu(self.searchbar_options_menu)

        self.show_submenu.addAction(self.show_import_export_act)
        self.show_submenu.addAction(self.show_sort_act)
        self.show_submenu.addAction(self.show_logs_act)
        self.show_submenu.addAction(self.show_workshop_btn_act)
        self.show_submenu.addAction(self.show_provider_act)

        self.auto_detect_urls_act = QAction("Auto-detect URLs from Clipboard", self, checkable=True)
        self.auto_detect_urls_act.setChecked(self.config["auto_detect_urls"])
        self.auto_detect_urls_act.triggered.connect(lambda checked: self.toggle_config("auto_detect_urls", checked))

        self.auto_add_to_queue_act = QAction("     Auto-add detected URLs to Queue", self, checkable=True)
        self.auto_add_to_queue_act.setChecked(self.config["auto_add_to_queue"])
        self.auto_add_to_queue_act.setEnabled(self.config["auto_detect_urls"])
        self.auto_add_to_queue_act.triggered.connect(lambda checked: self.toggle_config("auto_add_to_queue", checked))

        self.tools_menu.addAction(self.auto_detect_urls_act)
        self.tools_menu.addAction(self.auto_add_to_queue_act)
        
        report_issue_action = QAction("Report Issue...", self)
        report_issue_action.triggered.connect(lambda: webbrowser.open("https://github.com/dane-9/Streamline-Workshop-Downloader/issues/new/choose"))
        self.help_menu.addAction(report_issue_action)
        
        doc_action = QAction("Documentation", self)
        doc_action.triggered.connect(lambda: webbrowser.open("https://github.com/dane-9/Streamline-Workshop-Downloader/wiki/Documentation"))
        self.help_menu.addAction(doc_action)
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        self.help_menu.addAction(about_action)

        top_layout = QHBoxLayout()
        settings_icon = QIcon(resource_path('Files/settings.png'))
        self.settings_btn = QPushButton()
        self.settings_btn.setIcon(settings_icon)
        self.settings_btn.setIconSize(QSize(20, 20))
        self.settings_btn.setFixedSize(32, 32)
        self.settings_btn.clicked.connect(self.open_settings)
        top_layout.addWidget(self.settings_btn)

        accounts_icon = QIcon(resource_path('Files/accounts.png'))
        self.configure_steam_accounts_btn = QPushButton()
        self.configure_steam_accounts_btn.setIcon(accounts_icon)
        self.configure_steam_accounts_btn.setIconSize(QSize(16, 16))
        self.configure_steam_accounts_btn.setFixedWidth(32)
        self.configure_steam_accounts_btn.clicked.connect(self.open_configure_steam_accounts)
        top_layout.addWidget(self.configure_steam_accounts_btn)

        self.update_appids_btn = QPushButton(' AppIDs')
        appids_icon = QIcon(resource_path('Files/update_appids.png'))
        self.update_appids_btn.setIcon(QIcon(appids_icon))
        self.update_appids_btn.setIconSize(QSize(20, 20))
        self.update_appids_btn.setFixedWidth(80)
        self.update_appids_btn.clicked.connect(self.open_update_appids)
        top_layout.addWidget(self.update_appids_btn)

        account_layout = QHBoxLayout()
        account_layout.addStretch() # Pushes the dropdown to the right

        self.steam_accounts_dropdown = ActiveComboBox()
        self.steam_accounts_dropdown.setItemDelegate(ActiveDelegate())
        self.steam_accounts_dropdown.addItem("Anonymous")
        self.steam_accounts_dropdown.setFixedWidth(186)
        self.steam_accounts_dropdown.currentIndexChanged.connect(self.change_active_account)
        account_layout.addWidget(self.steam_accounts_dropdown)

        top_layout.addLayout(account_layout)
        self.main_layout.addLayout(top_layout)

        mod_layout = QHBoxLayout()
        self.workshop_input = QLineEdit()
        set_custom_clear_icon(self.workshop_input)
        self.workshop_input.setPlaceholderText('Enter Workshop Mod or Collection URL / ID')
        self.download_btn = QPushButton('Download')
        self.download_btn.setFixedWidth(90)
        self.download_btn.clicked.connect(self.download_workshop_immediately)
        self.add_to_queue_btn = QPushButton('Add to Queue')
        self.add_to_queue_btn.setFixedWidth(90)
        self.add_to_queue_btn.clicked.connect(self.add_workshop_to_queue)
        mod_layout.addWidget(self.workshop_input)
        mod_layout.addWidget(self.download_btn)
        mod_layout.addWidget(self.add_to_queue_btn)
        self.main_layout.addLayout(mod_layout)

        queue_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.update_queue_count()
        set_custom_clear_icon(self.search_input)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        queue_layout.addWidget(self.search_input)

        self.filter_action = self.search_input.addAction(QIcon(resource_path("Files/filter_queue_status.png")), QLineEdit.LeadingPosition)

        self.filter_menu = QMenu()

        self.show_all_action = QAction("All Mods", self)
        self.show_all_action.setCheckable(True)
        self.show_all_action.setChecked(True)
        self.show_all_action.triggered.connect(lambda: self.filter_queue_by_status("All"))

        self.show_queued_action = QAction("Mods Queued", self)
        self.show_queued_action.setCheckable(True)
        self.show_queued_action.triggered.connect(lambda: self.filter_queue_by_status("Queued"))

        self.show_downloaded_action = QAction("Downloaded", self)
        self.show_downloaded_action.setCheckable(True)
        self.show_downloaded_action.triggered.connect(lambda: self.filter_queue_by_status("Downloaded"))
        
        self.show_failed_action = QAction("Failed", self)
        self.show_failed_action.setCheckable(True)
        self.show_failed_action.triggered.connect(lambda: self.filter_queue_by_status("Failed"))

        self.filter_action_group = QActionGroup(self)
        self.filter_action_group.addAction(self.show_all_action)
        self.filter_action_group.addAction(self.show_queued_action)
        self.filter_action_group.addAction(self.show_downloaded_action)
        self.filter_action_group.addAction(self.show_failed_action)
        self.filter_action_group.setExclusive(True)

        self.filter_menu.addAction(self.show_all_action)
        self.filter_menu.addAction(self.show_queued_action)
        self.filter_menu.addAction(self.show_downloaded_action)
        self.filter_menu.addAction(self.show_failed_action)

        self.filter_tooltip = FilterTooltip(self)
        self.filter_tooltip.setup(self.filter_action, self.filter_menu)

        self.filter_action.triggered.disconnect()
        self.filter_action.triggered.connect(self.filter_tooltip.show_filter_menu)

        self.update_filter_tooltip()

        self.caseButton = QToolButton()
        self.caseButton.setCheckable(True)
        self.case_tooltip = Tooltip(self.caseButton, "Case sensitivity")
        self.case_tooltip.setPlacement(TooltipPlacement.BOTTOM)
        self.case_tooltip.setShowDelay(500)
        self.case_tooltip.setHideDelay(100)
        self.caseButton.setIcon(QIcon(resource_path("Files/case_disabled.png")))
        self.caseButton.setIconSize(QSize(16, 16))
        self.caseButton.setStyleSheet("QToolButton { border: none; }")
        self.caseButton.toggled.connect(self.updateCaseIcon)
        queue_layout.addWidget(self.caseButton)

        self.regexButton = QToolButton()
        self.regexButton.setCheckable(True)
        self.regex_tooltip = Tooltip(self.regexButton, "Regex")
        self.regex_tooltip.setPlacement(TooltipPlacement.BOTTOM)
        self.regex_tooltip.setShowDelay(500)
        self.regex_tooltip.setHideDelay(100)
        self.regexButton.setIcon(QIcon(resource_path("Files/regex_disabled.png")))
        self.regexButton.setIconSize(QSize(16, 16))
        self.regexButton.setStyleSheet("QToolButton { border: none; }")
        self.regexButton.toggled.connect(self.updateRegexIcon)
        queue_layout.addWidget(self.regexButton)
        
        import_export_spacer = QWidget()
        import_export_spacer.setFixedWidth(14)
        queue_layout.addWidget(import_export_spacer)

        buttonContainer = QWidget()
        hbox = QHBoxLayout(buttonContainer)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(6)

        self.import_queue_btn = QPushButton()
        self.import_queue_btn.setIcon(QIcon(resource_path('Files/import.png')))
        self.import_queue_btn.setIconSize(QSize(20, 20))
        self.import_queue_btn.setToolTip('Import Queue')
        self.import_queue_btn.clicked.connect(self.import_queue)
        self.import_queue_btn.setFixedSize(32, 32)

        self.export_queue_btn = QPushButton()
        self.export_queue_btn.setIcon(QIcon(resource_path('Files/export.png')))
        self.export_queue_btn.setIconSize(QSize(20, 20))
        self.export_queue_btn.setToolTip('Export Queue')
        self.export_queue_btn.clicked.connect(self.export_queue)
        self.export_queue_btn.setEnabled(False)
        self.export_queue_btn.setFixedSize(32, 32)

        hbox.addWidget(self.import_queue_btn)
        hbox.addWidget(self.export_queue_btn)
        queue_layout.addWidget(buttonContainer)
        self.queue_layout = queue_layout
        self.import_export_container = buttonContainer
        self.import_export_spacer = import_export_spacer
        self.main_layout.addLayout(queue_layout)

        self.reset_action = QAction("Reset", self)
        self.reset_action.setEnabled(not self.header_locked)  # Disable when locked
        self.reset_action.triggered.connect(self.reset_columns)

        self.queue_tree = CustomizableTreeWidgets()
        self.queue_tree.setSelectionBehavior(QTreeWidget.SelectRows)
        self.queue_tree.setEditTriggers(QTreeWidget.NoEditTriggers)
        self.queue_tree.setItemDelegate(NoFocusDelegate(self.queue_tree))
        self.queue_tree.setRootIsDecorated(False)
        self.queue_tree.setUniformRowHeights(True)
        self.queue_tree.setExpandsOnDoubleClick(False)
        self.queue_tree.setColumnCount(5)
        self.queue_tree.setHeaderLabels(['Game', 'Mod ID', 'Mod Name', 'Status', 'Provider'])
        self.queue_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.queue_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queue_tree.customContextMenuRequested.connect(self.open_context_menu)
        self.queue_tree.header().setStretchLastSection(False)
        self._sortClicked = False
        self.queue_tree.setSortingEnabled(True)
        self.queue_tree.header().setSortIndicatorShown(False)
        self.queue_tree.header().sectionClicked.connect(self.sort_column_indicator)
        header = self.queue_tree.header()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.open_header_context_menu)
        self.toggle_header_lock(self.header_locked)

        default_widths = self.config["queue_tree_default_widths"]
        saved_widths = self.config["queue_tree_column_widths"]
        if not saved_widths:
            saved_widths = default_widths
        saved_hidden = self.config["queue_tree_column_hidden"]
        if not saved_hidden:
            saved_hidden = [False] * self.queue_tree.columnCount()

        for i in range(self.queue_tree.columnCount()):
            if i < len(saved_widths):
                self.queue_tree.setColumnWidth(i, saved_widths[i])
            else:
                self.queue_tree.setColumnWidth(i, default_widths[i])
            if i < len(saved_hidden):
                self.queue_tree.setColumnHidden(i, saved_hidden[i])
            else:
                self.queue_tree.setColumnHidden(i, False)

        self.main_layout.addWidget(self.queue_tree, stretch=3)

        button_layout = QHBoxLayout()
        self.download_start_btn = QPushButton('Start Download')
        self.download_start_btn.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_start_btn)

        self.open_folder_btn = QPushButton('Open Downloads Folder')
        self.open_folder_btn.clicked.connect(self.open_downloads_folder)
        button_layout.addWidget(self.open_folder_btn)
        self.main_layout.addLayout(button_layout)

        self.log_area = QTextEdit()
        self.log_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.log_area.customContextMenuRequested.connect(self.showLogContextMenu)
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(150)
        self.log_area.setPlaceholderText("Logs")
        self.main_layout.addWidget(self.log_area, stretch=1)

        self.provider_layout = QHBoxLayout()
        self.queue_entire_workshop_btn = QPushButton("Queue Entire Workshop")
        self.queue_entire_workshop_btn.setFixedWidth(145)
        self.queue_entire_workshop_btn.clicked.connect(self.open_queue_entire_workshop_dialog)
        self.provider_layout.addWidget(self.queue_entire_workshop_btn)

        self.provider_layout.addStretch()
        self.provider_label = QLabel('Download Provider:')
        self.provider_layout.addWidget(self.provider_label)
        self.provider_dropdown = QComboBox()
        self.provider_dropdown.addItems(['Default', 'SteamCMD', 'SteamWebAPI'])
        self.provider_dropdown.currentIndexChanged.connect(self.on_provider_changed)
        self.provider_layout.addWidget(self.provider_dropdown)
        self.main_layout.addLayout(self.provider_layout)

        stored_provider = self.config.get("download_provider", "Default")
        self.provider_dropdown.setCurrentText(stored_provider)

        apply_theme_titlebar(self, self.config)
        self.setLayout(self.main_layout)
        
    def adjust_widget_heights(self):
        button_height = 28
        dropdown_height = 27
    
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, QPushButton):
                if "_btn" in attr_name:
                    attr.setFixedHeight(button_height)
            elif isinstance(attr, QComboBox) and "_dropdown" in attr_name:
                attr.setFixedHeight(dropdown_height)
                
    def sort_column_indicator(self, index):
        if self.config.get('show_sort_indicator', False):
            self._sortClicked = True
            self.queue_tree.header().setSortIndicatorShown(True)
                
    def filter_queue_items(self, text: str):
        regex_enabled = self.regexButton.isChecked()
        case_sensitive = self.caseButton.isChecked()
        
        # If regex is enabled, try to compile the pattern
        if regex_enabled and text:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(text, flags)
            except re.error:
                pattern = None
        else:
            # For non-regex searches, adjust the text if not case sensitive
            if not case_sensitive:
                text = text.lower()
        
        for i in range(self.queue_tree.topLevelItemCount()):
            item = self.queue_tree.topLevelItem(i)
            mod_id = item.text(1)
            mod_name = item.text(2)
            item_status = item.text(3)
            
            # First check if status matches the current filter
            status_match = (self.current_filter == "All" or 
                           (self.current_filter == "Queued" and item_status == "Queued") or
                           (self.current_filter == "Downloaded" and item_status == "Downloaded") or
                           (self.current_filter == "Failed" and "Failed" in item_status))
            
            # If status doesn't match, hide the item
            if not status_match:
                item.setHidden(True)
                continue
            
            # Then check if text matches (if search text exists)
            if text:
                if regex_enabled and pattern:
                    text_match = bool(pattern.search(mod_id) or pattern.search(mod_name))
                else:
                    if not case_sensitive:
                        mod_id_lower = mod_id.lower()
                        mod_name_lower = mod_name.lower()
                        text_match = text in mod_id_lower or text in mod_name_lower
                    else:
                        text_match = text in mod_id or text in mod_name
                
                item.setHidden(not text_match)
            else:
                # No search text, show all items that match the status filter
                item.setHidden(False)
                
    def update_queue_count(self):
        total_count = len(self.download_queue)
        
        if not hasattr(self, 'current_filter') or self.current_filter == "All":
            placeholder = f"Mods in Queue: {total_count}     /     Search by Mod ID or Name"
        elif self.current_filter == "Queued":
            queued_count = sum(1 for mod in self.download_queue if mod['status'] == 'Queued')
            placeholder = f"Queued Mods: {queued_count} / {total_count}     /     Search by Mod ID or Name"
        elif self.current_filter == "Downloaded":
            downloaded_count = sum(1 for mod in self.download_queue if mod['status'] == 'Downloaded')
            placeholder = f"Downloaded Mods: {downloaded_count} / {total_count}     /     Search by Mod ID or Name"
        elif self.current_filter == "Failed":
            failed_count = sum(1 for mod in self.download_queue if 'Failed' in mod['status'])
            placeholder = f"Failed Mods: {failed_count} / {total_count}     /     Search by Mod ID or Name"
        
        self.search_input.setPlaceholderText(placeholder)
        
        if hasattr(self, 'filter_action'):
            self.update_filter_tooltip()
                
    def open_queue_entire_workshop_dialog(self):
        dialog = QueueEntireWorkshopDialog(self)
        if dialog.exec() == QDialog.Accepted:
            user_input = dialog.get_input()
            if not user_input:
                ThemedMessageBox.warning(self, 'Input Error', 'Please enter an AppID or a related URL.')
                return
            appid = self.extract_appid(user_input)
            if not appid:
                ThemedMessageBox.warning(self, 'Input Error', 'Could not parse an AppID from the given input.')
                return
            self.log_signal.emit(f"Starting to queue entire workshop for AppID: '{appid}'")

            self.queue_entire_workshop_btn.setEnabled(False)

            self.workshop_scraper = WorkshopScraperWorker(appid, self.app_ids, queue_entire_workshop_btn=self.queue_entire_workshop_btn)

            self.workshop_scraper.log_signal.connect(self.append_log)
            self.workshop_scraper.finished_scraping.connect(self.on_entire_workshop_fetched)
            self.workshop_scraper.start()

    def on_entire_workshop_fetched(self, game_name, mods):
        if not mods:
            self.log_signal.emit("No mods found or failed to scrape.")
            return
    
        appid = self.workshop_scraper.appid
        
        # Determine the provider once we know the app_id
        provider = self.get_provider_for_mod({'app_id': appid})

        self.log_signal.emit(f"Adding {len(mods)} mods from '{game_name}' (AppID: {appid}) to the queue...")

        self.queue_progress_last_update = 0  # To avoid too frequent updates
        self.queue_insertion_finished = False

        self.queue_insertion_worker = QueueInsertionWorker(
            mods=mods,
            game_name=game_name,
            appid=appid,
            provider=provider
        )
        self.queue_insertion_worker.batch_ready.connect(self.on_batch_ready)
        self.queue_insertion_worker.finished.connect(self.on_queue_insertion_finished)
        self.queue_insertion_worker.start()
    
    @Slot(list)
    def on_batch_ready(self, mod_batch):
        self.queue_tree.setSortingEnabled(False)

        self.download_queue.extend(mod_batch)

        tree_items = [QTreeWidgetItem([mod['game_name'], mod['mod_id'], mod['mod_name'], mod['status'], mod['provider']]) for mod in mod_batch]

        self.queue_tree.setUpdatesEnabled(False)
        try:
            self.queue_tree.addTopLevelItems(tree_items)
        finally:
            self.queue_tree.setUpdatesEnabled(True)

        self.queue_tree.setSortingEnabled(True)
        # If the header has not been clicked yet, keep the sort indicator hidden
        if not self._sortClicked:
            self.queue_tree.header().setSortIndicatorShown(False)

        self.update_queue_count()
        self.export_queue_btn.setEnabled(bool(self.download_queue))

    @Slot()
    def on_queue_insertion_finished(self):
        if hasattr(self, 'queue_insertion_finished') and self.queue_insertion_finished:
            return

        self.queue_insertion_finished = True
        
        # Called when the worker has finished inserting all batches
        total_count = len(self.download_queue)
        self.log_signal.emit(f"Workshop queuing complete: {total_count} total mods in queue")
        
        # Reset progress tracking
        self.queue_progress_last_update = 0


    def extract_appid(self, input_str):
        # If it's purely digits, return directly
        if input_str.isdigit():
            return input_str
        # If 'appid=' in the URL
        match = re.search(r'appid=(\d+)', input_str)
        if match:
            return match.group(1)
        # If URL contains /app/ID/
        match = re.search(r'/app/(\d+)/', input_str)
        if match:
            return match.group(1)
        # If URL ends with /app/ID or similar
        match = re.search(r'/app/(\d+)', input_str)
        if match:
            return match.group(1)
        # If none matched, try to find any number
        match = re.search(r'(\d+)', input_str)
        if match:
            return match.group(1)
        return None

    def open_header_context_menu(self, position: QPoint):
        menu = QMenu()
    
        # Submenu for hiding columns
        hide_submenu = menu.addMenu("Hide")
        for column in range(self.queue_tree.columnCount()):
            column_name = self.queue_tree.headerItem().text(column)
            action = QAction(f"{column_name}", self)
            action.setCheckable(True)
            action.setChecked(self.queue_tree.header().isSectionHidden(column))
            action.toggled.connect(lambda checked, col=column: self.toggle_column_visibility(col, checked))
            hide_submenu.addAction(action)
            
        self.reset_action = QAction("Reset", self)
        self.reset_action.setEnabled(not self.header_locked)
        self.reset_action.triggered.connect(self.reset_header_layout)
        menu.addAction(self.reset_action)
    
        # Lock/Unlock action
        lock_action_text = "Locked" if self.header_locked else "Lock"
        self.lock_action = QAction(lock_action_text, self)
        self.lock_action.setCheckable(True)
        self.lock_action.setChecked(self.header_locked)
        self.lock_action.toggled.connect(lambda: self.toggle_header_lock(not self.header_locked))
        menu.addAction(self.lock_action)
    
        menu.exec(self.queue_tree.header().viewport().mapToGlobal(position))
        
    def reset_header_layout(self):
        default_widths = DEFAULT_SETTINGS["queue_tree_default_widths"]
    
        for i in range(self.queue_tree.columnCount()):
            self.queue_tree.setColumnHidden(i, False)
            if i < len(default_widths):
                self.queue_tree.setColumnWidth(i, default_widths[i])
    
        # Reset the column order
        header = self.queue_tree.header()
        for col in range(self.queue_tree.columnCount()):
            header.moveSection(header.visualIndex(col), col)
    
        self.log_signal.emit("Header layout reset to default.")
    
        # Update config so next run uses these defaults
        self.config["queue_tree_column_widths"] = list(default_widths)
        self.config["queue_tree_column_hidden"] = [False] * self.queue_tree.columnCount()
        self.save_config()
        
    def reset_columns(self):
        self.queue_tree.header().restoreState(self.queue_tree.header().saveState())  
        default_widths = DEFAULT_SETTINGS["queue_tree_default_widths"]
        for i, width in enumerate(default_widths):
            self.queue_tree.setColumnWidth(i, width)
        
        self.log_signal.emit("Columns have been reset to their default widths and positions.")

    def toggle_column_visibility(self, column: int, hide: bool):
        if hide:
            current_width = self.queue_tree.columnWidth(column)
            self.column_width_backup[column] = current_width
    
            if self.config.get("queue_tree_column_widths") is None:
                self.config["queue_tree_column_widths"] = list(DEFAULT_SETTINGS["queue_tree_default_widths"])
            self.config["queue_tree_column_widths"][column] = current_width
    
            self.queue_tree.setColumnHidden(column, True)
        else:
            self.queue_tree.setColumnHidden(column, False)
            if column in self.column_width_backup:
                self.queue_tree.setColumnWidth(column, self.column_width_backup[column])
            else:
                column_widths = self.config.get("queue_tree_column_widths")
                if column_widths is None:
                    column_widths = DEFAULT_SETTINGS["queue_tree_default_widths"]
                if len(column_widths) > column:
                    self.queue_tree.setColumnWidth(column, column_widths[column])
                    
    def toggle_header_lock(self, locked: bool):
        self.header_locked = locked
        header = self.queue_tree.header()
    
        if locked:
            header.setSectionsMovable(False)
            header.setStretchLastSection(False)
            for col in range(self.queue_tree.columnCount()):
                header.setSectionResizeMode(col, QHeaderView.Fixed)
            if self.lock_action:
                self.lock_action.setText("Locked")
            if self.reset_action:
                self.reset_action.setEnabled(False)  # Disable Reset when locked
        else:
            header.setSectionsMovable(True)
            header.setStretchLastSection(False)
            for col in range(self.queue_tree.columnCount()):
                header.setSectionResizeMode(col, QHeaderView.Interactive)
            if self.lock_action:
                self.lock_action.setText("Lock")
            if self.reset_action:
                self.reset_action.setEnabled(True)  # Enable Reset when unlocked
    
        self.save_config()
                    
    def import_queue(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Queue", "", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    for line in file:
                        parts = line.strip().split('|')
                        if len(parts) < 4:
                            continue  # Skip invalid lines
                        game_name, mod_id, mod_name, provider = parts[0], parts[1], parts[2], parts[3]
                        
                        if not self.is_mod_in_queue(mod_id):
                            self.download_queue.append({
                                'game_name': game_name,
                                'mod_id': mod_id,
                                'mod_name': mod_name,
                                'status': 'Queued',
                                'retry_count': 0,
                                'provider': provider
                            })
                            tree_item = QTreeWidgetItem([game_name, mod_id, mod_name, 'Queued', provider])
                            self.queue_tree.addTopLevelItem(tree_item)
                    
                    self.log_signal.emit(f"Queue imported from {file_path}.")
                    self.export_queue_btn.setEnabled(bool(self.download_queue))
                    self.update_queue_count()
            except Exception as e:
                ThemedMessageBox.critical(self, "Import Error", f"Failed to import queue: {e}")

    def export_queue(self):
        if not self.download_queue:
            ThemedMessageBox.information(self, "No Items to Export", "There are no items in the queue to export.")
            return
    
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Queue", "", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    for mod in self.download_queue:
                        file.write(f"{mod['game_name']}|{mod['mod_id']}|{mod['mod_name']}|{mod['provider']}\n")
                self.log_signal.emit(f"Queue exported to {file_path}.")
            except Exception as e:
                ThemedMessageBox.critical(self, "Export Error", f"Failed to export queue: {e}")

    def get_config_path(self):
        return os.path.join(self.files_dir, 'config.json')

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

        for key, default_value in DEFAULT_SETTINGS.items():
            self.config.setdefault(key, default_value)

    def save_config(self):
        try:
            self.config['header_locked'] = self.header_locked
            
            with open(self.config_path, 'w', encoding='utf-8') as file:
                json.dump(self.config, file, indent=4)
        except Exception as e:
            self.log_signal.emit(f"Error saving config.json: {e}")
             
    def closeEvent(self, event):
        if hasattr(self, 'tooltip_manager'):
            self.tooltip_manager.hide_all_tooltips()
        
        if self.is_downloading:
            reply = ThemedMessageBox.question(
                self,
                'Quit Application',
                "A download is currently ongoing. Do you want to cancel it and exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.cancel_download()
                if self.current_process and self.current_process.poll() is None:
                    self.current_process.terminate()
                event.accept()
            else:
                event.ignore()
                return
        else:
            event.accept()

        self.config['window_size'] = {'width': self.width(), 'height': self.height()}

        column_widths = self.config.get('queue_tree_column_widths')
        if not column_widths:
            column_widths = [self.queue_tree.columnWidth(i) for i in range(self.queue_tree.columnCount())]

        for i in range(self.queue_tree.columnCount()):
            if not self.queue_tree.isColumnHidden(i):
                column_widths[i] = self.queue_tree.columnWidth(i)

        self.config['queue_tree_column_widths'] = column_widths

        column_hidden = [self.queue_tree.isColumnHidden(i) for i in range(self.queue_tree.columnCount())]
        self.config['queue_tree_column_hidden'] = column_hidden

        self.save_config()

    async def fetch_game_name(self, app_id: str, log_signal=None):
        base_url = "https://steamcommunity.com/workshop/browse/"
        params = {"appid": str(app_id), "p": "1"}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(base_url, params=params) as response:
                    if response.status != 200:
                        if log_signal:
                            log_signal(f"Failed to fetch workshop front page for appid={app_id}, status={response.status}")
                        return None
                    page_html = await response.text()
            except Exception as e:
                if log_signal:
                    log_signal(f"Error fetching page for appid={app_id}: {e}")
                return None
    
        tree = html.fromstring(page_html)
        gn = tree.xpath('//div[@class="apphub_AppName ellipsis"]/text()')
        if gn:
            return gn[0].strip()
        return None
    
    def fetch_game_name_for_appid(self, app_id: str) -> str:
        if app_id in self.app_ids:
            return self.app_ids[app_id]
    
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.fetch_game_name(app_id, self.log_signal))
        loop.close()
    
        if result:
            return result

        return "Unknown Game"
    
    def on_override_appid(self, selected_items):
        if not selected_items:
            return

        first_item = selected_items[0]
        first_mod_id = first_item.text(1)
    
        # Find the matching mod in self.download_queue
        mod = next((m for m in self.download_queue if m['mod_id'] == first_mod_id), None)
        if not mod:
            ThemedMessageBox.warning(self, 'Not Found', 'Selected mod not found in the queue.')
            return
    
        old_app_id = mod.get('app_id', "")
    
        dialog = OverrideAppIDDialog(current_app_id=old_app_id, parent=self)
        if dialog.exec() == QDialog.Accepted:
            user_input = dialog.get_new_app_id().strip()
    
            extracted_app_id = self.extract_appid(user_input)
            if not extracted_app_id:
                ThemedMessageBox.warning(self, 'Invalid AppID', 'Could not parse a valid AppID from your input. Please enter an ID or URL.')
                return

            new_game_name = self.fetch_game_name_for_appid(extracted_app_id)

            for item in selected_items:
                mod_id = item.text(1)
                queue_mod = next((m for m in self.download_queue if m['mod_id'] == mod_id), None)
                if queue_mod:
                    queue_mod['app_id'] = extracted_app_id
                    queue_mod['game_name'] = new_game_name
                    item.setText(0, new_game_name)

            self.log_signal.emit(f"Selected mod(s) changed to '{new_game_name}' / '{extracted_app_id}'.")

    def populate_steam_accounts(self):
        self.steam_accounts_dropdown.blockSignals(True)
        self.steam_accounts_dropdown.clear()
        
        active_account = self.config.get('active_account', "Anonymous")
        
        self.steam_accounts_dropdown.config = self.config
        
        self.steam_accounts_dropdown.addItem("Anonymous")
        
        for account in self.config.get('steam_accounts', []):
            username = account.get('username', '')
            self.steam_accounts_dropdown.addItem(username)
        
        # Set the current index
        index = self.steam_accounts_dropdown.findText(active_account, Qt.MatchFixedString)
        if index >= 0:
            self.steam_accounts_dropdown.setCurrentIndex(index)
        else:
            self.steam_accounts_dropdown.setCurrentIndex(0)
        
        self.steam_accounts_dropdown.blockSignals(False)

        self.steam_accounts_dropdown.repaint()
        
    def set_theme(self, theme_name):
        self.config["current_theme"] = theme_name
        self.save_config()
        load_theme(QApplication.instance(), theme_name, self.files_dir)
        apply_theme_titlebar(self, self.config)
        self.log_signal.emit(f"Theme changed to '{theme_name}'.")

        for action in self.theme_actions:
            action.setChecked(action.text() == theme_name)

    def set_logo_style(self, style_name):
        self.config["logo_style"] = style_name
        self.save_config()

        if style_name == "Dark":
            logo = "logo_dark.png"
        elif style_name == "Darker":
            logo = "logo_darker.png"
        else:
            logo = "logo.png"
        self.setWindowIcon(QIcon(resource_path(f'Files/{logo}')))
        self.log_signal.emit(f"Logo style changed to '{style_name}'.")

        for action in self.logo_actions:
            action.setChecked(action.text() == style_name)

    def toggle_config(self, key, checked):
        self.config[key] = checked
        self.save_config()

        if key == "auto_detect_urls":
            self.auto_add_to_queue_act.setEnabled(checked)
        self.apply_settings()
        self.log_signal.emit(f"Option '{key}' set to {checked}.")

    def apply_settings(self):
        self.download_btn.setVisible(self.config["download_button"])
        self.search_input.setVisible(self.config["show_searchbar"])
        self.regexButton.setVisible(self.config["show_regex_button"])
        self.caseButton.setVisible(self.config["show_case_button"])
        self.import_export_container.setVisible(self.config["show_export_import_buttons"])
        self.import_export_spacer.setVisible(self.config["show_export_import_buttons"])
        self.log_area.setVisible(self.config["show_logs"])
        self.provider_label.setVisible(self.config["show_provider"])
        self.provider_dropdown.setVisible(self.config["show_provider"])
        self.queue_entire_workshop_btn.setVisible(self.config["show_queue_entire_workshop"])
        self.menu_bar.setVisible(self.config["show_menu_bar"])
        
        if self.config.get("show_menu_bar", True):
            self.main_layout.setContentsMargins(6, 0, 6, 6)
            self.main_layout.setSpacing(6)
        else:
            self.main_layout.setContentsMargins(6, 6, 6, 6)
            self.main_layout.setSpacing(6)

        if not self.config["show_sort_indicator"]:
            self.queue_tree.header().setSortIndicatorShown(False)

        if self.config["show_searchbar"]:
            self.regexButton.setVisible(self.config["show_regex_button"])
            self.caseButton.setVisible(self.config["show_case_button"])
            self.queue_layout.setAlignment(self.import_export_container, Qt.AlignLeft)
        else:
            self.regexButton.setVisible(False)
            self.caseButton.setVisible(False)
            self.queue_layout.setAlignment(self.import_export_container, Qt.AlignRight)

        if self.config["auto_detect_urls"]:
            self.start_clipboard_monitoring()
        else:
            self.stop_clipboard_monitoring()

        if not self.config["auto_detect_urls"]:
            self.config["auto_add_to_queue"] = False
            self.auto_add_to_queue_act.setChecked(False)
            self.save_config()
            
        self.updateWindowTitle()
            
    def update_menubar(self):
        self.show_download_button_act.setChecked(self.config["download_button"])
        self.show_searchbar_act.setChecked(self.config["show_searchbar"])
        self.show_regex_act.setChecked(self.config["show_regex_button"])
        self.show_case_act.setChecked(self.config["show_case_button"])
        self.show_import_export_act.setChecked(self.config["show_export_import_buttons"])
        self.show_sort_act.setChecked(self.config["show_sort_indicator"])
        self.show_logs_act.setChecked(self.config["show_logs"])
        self.show_workshop_btn_act.setChecked(self.config["show_queue_entire_workshop"])
        self.show_provider_act.setChecked(self.config["show_provider"])

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            new_settings = dialog.get_settings()
    
            self.config.update(new_settings)
            self.save_config()
    
            selected_theme = new_settings.get('current_theme', 'Dark')
            load_theme(QApplication.instance(), selected_theme, self.files_dir)

            self.apply_settings()
    
            logo_style = new_settings.get("logo_style", "Light")
            if logo_style == "Dark":
                logo = "logo_dark.png"
            elif logo_style == "Darker":
                logo = "logo_darker.png"
            else:
                logo = "logo.png"
            self.setWindowIcon(QIcon(resource_path(f'Files/{logo}')))
    
            apply_theme_titlebar(self, self.config)
            
            self.update_menubar()
            self.updateWindowTitle()
    
            self.log_signal.emit("Settings updated successfully.")

    def open_configure_steam_accounts(self):
        dialog = ConfigureSteamAccountsDialog(self.config, self.steamcmd_dir, self)
        dialog.exec()
        self.config = dialog.get_updated_config()
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                json.dump(self.config, file, indent=4)
        except Exception as e:
            self.log_signal.emit(f"Error saving config.json: {e}")
    
        # Repopulate steam accounts dropdown
        self.populate_steam_accounts()
        
        # If the active account is no longer valid, revert to 'Anonymous'
        active_account = self.config.get('active_account', 'Anonymous')
        if active_account != 'Anonymous' and active_account not in [acc['username'] for acc in self.config.get('steam_accounts', [])]:
            self.config['active_account'] = 'Anonymous'
            # Save silently
            try:
                with open(self.config_path, 'w', encoding='utf-8') as file:
                    json.dump(self.config, file, indent=4)
            except Exception as e:
                self.log_signal.emit(f"Error saving config.json: {e}")
            self.populate_steam_accounts()

    def change_active_account(self, index):
        selected_account = self.steam_accounts_dropdown.currentText()
        if self.config.get('active_account') != selected_account:
            self.config['active_account'] = selected_account
            self.save_config()
            self.log_signal.emit(f"Active account set to '{selected_account}'.")
            
    def initialize_steamcmd(self):
        self.log_signal.emit("Initializing SteamCMD...")
        try:
            steamcmd_process = subprocess.Popen(
                [self.steamcmd_executable, '+quit'],
                cwd=self.steamcmd_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            important_messages = []

            for line in steamcmd_process.stdout:
                clean_line = line.strip()
                if clean_line and any(keyword in clean_line.lower() for keyword in ['error', 'warn', 'fail', 'success', 'update']):
                    important_messages.append(clean_line)

            steamcmd_process.stdout.close()
            steamcmd_process.wait()

            if important_messages:
                self.log_signal.emit(f"SteamCMD initialization: {len(important_messages)} message(s) received")

            self.log_signal.emit("SteamCMD initialized successfully.")
        except Exception as e:
            self.log_signal.emit(f"Error initializing SteamCMD: {e}")
            ThemedMessageBox.critical(self, 'Error', f"Failed to initialize SteamCMD: {e}")

    def get_steamcmd_executable_path(self):
        return os.path.join(self.steamcmd_dir, 'steamcmd.exe')

    def on_item_error(self, error_message):
        ThemedMessageBox.critical(self, 'Error', error_message)
        self.log_signal.emit(error_message)

    def add_workshop_to_queue(self):
        input_text = self.workshop_input.text().strip()
        if not input_text:
            ThemedMessageBox.warning(self, 'Input Error', 'Please enter a Workshop URL or ID.')
            return
    
        workshop_id = self.extract_id(input_text)
        if not workshop_id:
            ThemedMessageBox.warning(self, 'Input Error', 'Invalid Workshop URL or ID.')
            return
    
        # Disable the button while processing
        self.add_to_queue_btn.setEnabled(False)
    
        existing_ids = [mod['mod_id'] for mod in self.download_queue]
        item_fetcher = ItemFetcher(item_id=workshop_id, existing_mod_ids=existing_ids)
        # Connect signals to a unified handler:
        item_fetcher.mod_or_collection_detected.connect(self.on_workshop_item_detected)
        item_fetcher.item_processed.connect(self.on_item_processed)
        item_fetcher.error_occurred.connect(self.on_item_error)
        item_fetcher.finished.connect(lambda: self.on_item_fetcher_finished(item_fetcher))
        item_fetcher.start()
        self.log_signal.emit(f"Processing input {workshop_id}...")
        
    def on_workshop_item_detected(self, is_collection, item_id):
        if is_collection:
            self.log_signal.emit("Collection detected. Adding to queue...")
    
    def on_item_processed(self, result):
        if result['type'] == 'mod':
            mod_info = result['mod_info']
            mod_id = mod_info['mod_id']
            mod_title = mod_info['mod_name']
            app_id = mod_info['app_id']
            game_name = mod_info['game_name']
            self.add_to_queue_btn.setEnabled(True)
            if self.is_mod_in_queue(mod_id):
                self.log_signal.emit(f"Item {mod_id} is already in the queue.")
                return
            provider = self.get_provider_for_mod({'app_id': app_id})
            self.download_queue.append({
                'game_name': game_name,
                'mod_id': mod_id,
                'mod_name': mod_title,
                'status': 'Queued',
                'retry_count': 0,
                'app_id': app_id,
                'provider': provider
            })
            tree_item = QTreeWidgetItem([game_name, mod_id, mod_title, 'Queued', provider])
            self.queue_tree.addTopLevelItem(tree_item)
            self.update_queue_count()
            self.export_queue_btn.setEnabled(bool(self.download_queue))
            self.workshop_input.clear()
            self.log_signal.emit(f"Item {mod_id} ('{mod_title}') added to the queue.")

        elif result['type'] == 'collection':
            mods_info = result['mods_info']
            added_count = 0
            skipped_count = 0

            self.queue_tree.setUpdatesEnabled(False)

            try:
                for mod_info in mods_info:
                    mod_id = mod_info['mod_id']
                    mod_title = mod_info['mod_name']
                    app_id = mod_info['app_id']
                    game_name = mod_info['game_name']
                    if self.is_mod_in_queue(mod_id):
                        skipped_count += 1
                        continue

                    provider = self.get_provider_for_mod({'app_id': app_id})
                    self.download_queue.append({
                        'game_name': game_name,
                        'mod_id': mod_id,
                        'mod_name': mod_title,
                        'status': 'Queued',
                        'retry_count': 0,
                        'app_id': app_id,
                        'provider': provider
                    })
                    tree_item = QTreeWidgetItem([game_name, mod_id, mod_title, 'Queued', provider])
                    self.queue_tree.addTopLevelItem(tree_item)
                    added_count += 1
            finally:
                self.queue_tree.setUpdatesEnabled(True)

            self.update_queue_count()
            self.workshop_input.clear()

            summary_parts = []
            if added_count > 0:
                summary_parts.append(f"{added_count} items added")
            if skipped_count > 0:
                summary_parts.append(f"{skipped_count} duplicates skipped")

            self.log_signal.emit(f"Collection processed: {', '.join(summary_parts)}")

            if self.download_queue:
                self.export_queue_btn.setEnabled(True)
                self.add_to_queue_btn.setEnabled(True)

    def on_item_fetcher_finished(self, item_fetcher):
        if item_fetcher in self.item_fetchers:
            self.item_fetchers.remove(item_fetcher)

    def get_provider_for_mod(self, mod):
        selected_provider = self.provider_dropdown.currentText()
        if selected_provider == 'Default':
            app_id = mod.get('app_id')
            if app_id and app_id in self.app_ids:
                return 'SteamCMD'
            else:
                return 'SteamWebAPI'
        else:
            return selected_provider

    def load_app_ids(self):
        app_ids_path = os.path.join(self.files_dir, 'AppIDs.txt')
        if not os.path.isfile(app_ids_path):
            self.log_signal.emit("AppIDs.txt not found. Please update AppIDs from the 'Update AppIDs' option.")
            return
        try:
            with open(app_ids_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            game_name = parts[0].strip()
                            app_id = parts[1].strip()
                            self.app_ids[app_id] = game_name
            self.log_signal.emit("AppIDs loaded successfully.")
        except Exception as e:
            self.log_signal.emit(f"Failed to load AppIDs.txt: {e}")
            ThemedMessageBox.critical(self, 'Error', f"Failed to load AppIDs.txt: {e}")

    def find_queue_item(self, mod_id):
        for index in range(self.queue_tree.topLevelItemCount()):
            item = self.queue_tree.topLevelItem(index)
            if item.text(1) == mod_id:
                return item
        return None

    def is_collection(self, item_id):
        try:
            url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={item_id}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            tree = html.fromstring(response.text)
            # Check for collection-specific elements
            collection_items = tree.xpath('//div[contains(@class, "collectionItem")]')
            return len(collection_items) > 0
        except Exception as e:
            self.log_signal.emit(f"Error determining if item {item_id} is a collection: {e}")
            return False

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
            tree = html.fromstring(response.text)
    
            # Fetch game info
            game_tag = tree.xpath('//div[@class="breadcrumbs"]/a[contains(@href, "/app/")]')
            game_name, app_id = 'Unknown Game', None
            if game_tag and 'href' in game_tag[0].attrib:
                href = game_tag[0].get('href')
                app_id_match = re.search(r'/app/(\d+)', href)
                if app_id_match:
                    app_id = app_id_match.group(1)
                    game_name = game_tag[0].text_content().strip()
    
            # Fetch mod title
            title_tag = tree.xpath('//div[@class="workshopItemTitle"]')
            mod_title = title_tag[0].text.strip() if title_tag else 'Unknown Title'
    
            return game_name, app_id, mod_title
        except Exception as e:
            self.log_signal.emit(f"Error fetching mod info for mod {mod_id}: {e}")
        return 'Unknown Game', None, 'Unknown Title'

    def validate_steamcmd(self):
        if not self.steamcmd_executable or not os.path.isfile(self.steamcmd_executable):
            ThemedMessageBox.warning(self, 'Error', 'SteamCMD is not set up correctly.')
            self.log_signal.emit("Error: SteamCMD executable not found.")
            return False
        return True

    def start_download(self):
        if not self.download_queue:
            ThemedMessageBox.information(self, 'Info', 'Download queue is empty.')
            return
        if self.is_downloading:
            self.cancel_download()
            return

        self.is_downloading = True
        self.canceled = False
        self.download_start_btn.setText('Cancel Download')
        self.download_start_btn.setEnabled(True)
        self.log_signal.emit("Starting download process...")
        threading.Thread(target=self.download_worker, daemon=True).start()

    def cancel_download(self):
        self.canceled = True

        delete_downloads = self.config.get("delete_downloads_on_cancel", False)

        if delete_downloads:

            if self.current_process and self.current_process.poll() is None:
                self.current_process.terminate()
                self.log_signal.emit("Download process terminated by user.")

                self.log_signal.emit("Waiting for files to be released...")
                time.sleep(2)

            for mod in self.download_queue:
                if mod['status'] in ['Downloading', 'Downloaded']:
                    mod['status'] = 'Queued'
                    self.update_queue_signal.emit(mod['mod_id'], 'Queued')

            self.log_signal.emit("Removing downloaded mods due to cancellation...")
            self.remove_all_downloaded_mods()

            # Cleanup .acf files
            self.remove_appworkshop_acf_files()

            if not self.config.get("keep_downloaded_in_queue", False):
                downloaded_mods = [mod for mod in self.download_queue if mod['status'] == 'Downloaded']
                for mod in downloaded_mods:
                    self.remove_mod_from_queue(mod['mod_id'])
        else:
            self.cancellation_pending = True
            self.log_signal.emit("Cancellation requested. Waiting for current batch to complete...")

        self.is_downloading = False
        self.download_start_btn.setText('Start Download')
        self.download_start_btn.setEnabled(True)
        
        if delete_downloads:
            self.log_signal.emit("Cancellation completed.")
        else:
            self.download_start_btn.setText('Canceling...')
            self.download_start_btn.setEnabled(False)

    def download_worker(self):
        batch_size = self.config["batch_size"]
        keep_downloaded = self.config["keep_downloaded_in_queue"]

        self.cancellation_pending = False

        while self.is_downloading:
            queued_mods = [mod for mod in self.download_queue if mod['status'] == 'Queued']
            if not queued_mods:
                break

            if self.canceled and not self.cancellation_pending:
                break

            # Separate mods by provider
            steamcmd_mods = [mod for mod in queued_mods if mod['provider'] == 'SteamCMD'][:batch_size]
            webapi_mods = [mod for mod in queued_mods if mod['provider'] == 'SteamWebAPI'][:batch_size]

            # Process SteamCMD mods
            if steamcmd_mods and not self.cancellation_pending:
                self.log_signal.emit(f"Starting SteamCMD download of {len(steamcmd_mods)} mod(s).")
                self.download_mods_steamcmd(steamcmd_mods)
            # Process SteamWebAPI mods
            if webapi_mods and not self.cancellation_pending:
                self.log_signal.emit(f"Starting SteamWebAPI download of {len(webapi_mods)} mod(s).")

                successful_count = 0
                failed_count = 0

                for mod in webapi_mods:
                    if self.cancellation_pending:
                        break

                    mod_id = mod['mod_id']
                    mod['status'] = 'Downloading'
                    self.update_queue_signal.emit(mod_id, 'Downloading')
                    success = self.download_mod_webapi(mod)
                    if success:
                        mod['status'] = 'Downloaded'
                        self.update_queue_signal.emit(mod_id, 'Downloaded')
                        successful_count += 1
                        if not keep_downloaded:
                            self.remove_mod_from_queue(mod['mod_id'])
                    else:
                        mod['retry_count'] += 1
                        if mod['retry_count'] < 3:
                            mod['status'] = 'Queued'
                            self.update_queue_signal.emit(mod_id, 'Queued')
                        else:
                            mod['status'] = 'Failed'
                            self.update_queue_signal.emit(mod_id, 'Failed')
                            failed_count += 1
    
                summary_parts = []
                if successful_count > 0:
                    summary_parts.append(f"{successful_count} mod(s) downloaded successfully")
                if failed_count > 0:
                    summary_parts.append(f"{failed_count} mod(s) failed")
                    
                if summary_parts:
                    self.log_signal.emit(f"SteamWebAPI batch completed: {', '.join(summary_parts)}")

            if self.cancellation_pending:
                self.log_signal.emit("Current batch completed. Processing cancellation...")
                self.handle_cancellation()
                break
                
            # Remove all mods that have the status "Downloaded" if the setting is not enabled
            if not keep_downloaded:
                mods_to_remove = [mod for mod in self.download_queue if mod['status'] == 'Downloaded']
                for mod in mods_to_remove:
                    self.remove_mod_from_queue(mod['mod_id'])
    
        # Ensure all remaining mods are moved
        if not self.canceled:
            self.move_all_downloaded_mods()
            
            # Cleanup .acf files 
            self.remove_appworkshop_acf_files()

            self.log_signal.emit("All downloads have been processed.")
            self.is_downloading = False
            self.download_start_btn.setText('Start Download')
            self.download_start_btn.setEnabled(True)

    def handle_cancellation(self):
        delete_downloads = self.config.get("delete_downloads_on_cancel", False)
        keep_downloaded_in_queue = self.config.get("keep_downloaded_in_queue", False)

        status_updates = []

        workshop_content_path = os.path.join(self.steamcmd_dir, 'steamapps', 'workshop', 'content')
        if os.path.exists(workshop_content_path):
            for app_id in os.listdir(workshop_content_path):
                app_path = os.path.join(workshop_content_path, app_id)
                if os.path.isdir(app_path):
                    for mod_id in os.listdir(app_path):
                        mod_path = os.path.join(app_path, mod_id)
                        if os.path.isdir(mod_path):
                            mod = next((m for m in self.download_queue if m['mod_id'] == mod_id), None)
                            if mod and (mod['status'] == 'Downloading' or 'Failed' in mod['status']):
                                mod['status'] = 'Downloaded'
                                status_updates.append((mod_id, 'Downloaded'))
                                self.downloaded_mods_info[mod_id] = mod.get('mod_name', mod_id)

        for mod in self.download_queue:
            if mod['status'] == 'Downloading':
                mod['status'] = 'Queued'
                status_updates.append((mod['mod_id'], 'Queued'))

        for mod_id, status in status_updates:
            self.update_queue_signal.emit(mod_id, status)

        if delete_downloads:
            self.log_signal.emit("Removing downloaded mods due to cancellation...")
            self.remove_all_downloaded_mods()
        else:
            self.log_signal.emit("Keeping downloaded mods and moving them to Downloads folder...")
            self.move_all_downloaded_mods()

        if not keep_downloaded_in_queue:
            downloaded_mods = [mod for mod in self.download_queue if mod['status'] == 'Downloaded']

            if downloaded_mods:
                for mod in downloaded_mods:
                    self.remove_mod_from_queue(mod['mod_id'])

        self.cancellation_pending = False

        self.download_start_btn.setText('Start Download')
        self.download_start_btn.setEnabled(True)
        self.log_signal.emit("Cancellation completed.")

    def change_provider_for_mods(self, selected_items, new_provider):
        for item in selected_items:
            mod_id = item.text(1)
            mod = next((mod for mod in self.download_queue if mod['mod_id'] == mod_id), None)
            if mod:
                mod['provider'] = new_provider
                item.setText(4, new_provider)
                self.log_signal.emit(f"Mod {mod_id} provider changed to {new_provider}.")
        
    def download_mods_steamcmd(self, steamcmd_mods):
        # Group mods by app_id
        mods_by_app_id = defaultdict(list)
        for mod in steamcmd_mods:
            app_id = mod.get('app_id')
            if app_id:
                mods_by_app_id[app_id].append(mod)
            else:
                self.log_signal.emit(f"No app_id for mod {mod['mod_id']}. Skipping.")
                mod['status'] = 'Failed'
                self.update_queue_signal.emit(mod['mod_id'], 'Failed')
    
        if not hasattr(self, 'downloaded_mods_info'):
            self.downloaded_mods_info = {}
    
        # Process each group of mods (by app_id)
        for app_id, mods in mods_by_app_id.items():
            for mod in mods:
                mod['status'] = 'Downloading'
                self.update_queue_signal.emit(mod['mod_id'], 'Downloading')
    
            # Build the SteamCMD command
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
            for mod in mods:
                mod_id = mod['mod_id']
                steamcmd_commands.extend(['+workshop_download_item', app_id, mod_id])

            steamcmd_commands.append('+quit')

            # Debugging output
            # self.log_signal.emit(f"Executing SteamCMD command: {steamcmd_command}")
            try:
                self.log_signal.emit(f"Starting download of {len(mods)} mod(s) for AppID {app_id}...")

                # Start the SteamCMD process for the batch
                self.current_process = subprocess.Popen(
                    steamcmd_commands,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    cwd=self.steamcmd_dir,
                    shell=False, # Keep false otherwise it can't terminate
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

                successful_downloads = []
                failed_downloads = []

                important_messages = []
                current_downloads = set()

                # Process SteamCMD output line-by-line
                for line in self.current_process.stdout:
                    clean_line = line.strip()

                    if clean_line:
                        is_important = False

                        if any(keyword in clean_line.lower() for keyword in ['error', 'failed', 'warning', 'critical']):
                            is_important = True

                        if any(state in clean_line.lower() for state in ['initializing', 'logged in', 'connecting', 'license']):
                            is_important = True


                        if "Downloading item" in clean_line:
                            download_match = re.search(r'Downloading item (\d+)', clean_line)
                            if download_match:
                                current_downloads.add(download_match.group(1))
                            is_important = False

                        if "Success. Downloaded item" in clean_line:
                            is_important = False

                        if is_important:
                            important_messages.append(clean_line)
                            self.log_signal.emit(clean_line)


                    for mod in mods:
                        mod_id = mod['mod_id']

                        # Check for successful downloads
                        if f"Downloaded item {mod_id}" in clean_line:
                            mod['status'] = 'Downloaded'
                            # Save the mod name so we can use it later when moving the folder
                            self.downloaded_mods_info[mod_id] = mod.get('mod_name', mod_id)
                            self.update_queue_signal.emit(mod_id, 'Downloaded')
                            successful_downloads.append(mod_id)
                            if mod_id in current_downloads:
                                current_downloads.remove(mod_id)

                        # Check for failed downloads
                        elif f"ERROR! Download item {mod_id} failed" in clean_line:
                            reason = "Unknown error"
                            match = re.search(r'ERROR! Download item \d+ failed \(([^)]+)\)', clean_line)
                            if match:
                                reason = match.group(1)
                            mod['status'] = f'Failed: {reason}'
                            self.update_queue_signal.emit(mod_id, mod['status'])
                            failed_downloads.append(mod_id)
                            if mod_id in current_downloads:
                                current_downloads.remove(mod_id)
    
                self.current_process.stdout.close()
                self.current_process.wait()

                if self.canceled:
                    return

                summary_parts = []
                if successful_downloads:
                    summary_parts.append(f"{len(successful_downloads)} mod(s) downloaded successfully")
                if failed_downloads:
                    summary_parts.append(f"{len(failed_downloads)} mod(s) failed")

                if summary_parts:
                    self.log_signal.emit(f"Batch for AppID {app_id} completed: {', '.join(summary_parts)}")
                else:
                    self.log_signal.emit(f"Batch for AppID {app_id} completed with no status changes")
    
            except Exception as e:
                error_message = f"Error processing batch for AppID {app_id}: {e}"
                self.log_signal.emit(error_message)
                for mod in mods:
                    mod['status'] = 'Failed'
                    self.update_queue_signal.emit(mod['mod_id'], 'Failed')
                    mod['retry_count'] += 1
    
            # Keep downloaded mods in queue if the setting is enabled
            if not self.config.get('keep_downloaded_in_queue', False):
                # Remove all mods that have the status "Downloaded" from the queue
                downloaded_mods = [mod for mod in mods if mod['status'] == 'Downloaded']
                for mod in downloaded_mods:
                    self.remove_mod_from_queue(mod['mod_id'])

    def download_mod_webapi(self, mod):
        mod_id = mod['mod_id']
        mod_details = self.get_published_file_details(mod_id)
        # Extracting file URL and details from the JSON response
        try:
            file_details = mod_details['response']['publishedfiledetails'][0]
            if 'file_url' not in file_details or not file_details['file_url']:
                raise ValueError(f"Error: File URL not available for mod {mod_id}. The file might not be downloadable or doesn't exist.")
    
            file_url = file_details['file_url']
            filename = file_details.get('filename', None)
            title = file_details.get('title', 'Unnamed Mod')
    
            if filename and filename.strip():
                filename = filename.strip()
            else:
                # If filename is not available, use title with appropriate extension based on URL
                filename = f"{title}.zip" if file_url.endswith('.zip') else f"{title}"

            # Remove illegal characters from filename
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

            download_path = self.get_download_path(mod)
            file_path = os.path.join(download_path, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            self.log_signal.emit(f"Downloading mod {mod_id} via SteamWebAPI...")
            response = requests.get(file_url, stream=True)
            if response.status_code == 200:
                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                return True
            else:
                self.log_signal.emit(f"Failed to download mod {mod_id} via SteamWebAPI. HTTP Status Code: {response.status_code}")
                return False
        except KeyError:
            self.log_signal.emit(f"Error: Invalid response structure while fetching details for mod {mod_id}.")
            return False
        except ValueError as ve:
            self.log_signal.emit(str(ve))
            return False
        except Exception as e:
            self.log_signal.emit(f"An error occurred while downloading mod {mod_id}: {e}")
            return False

    def get_published_file_details(self, file_id):
        url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
        payload = {
            'itemcount': 1,
            'publishedfileids[0]': file_id,
        }
        response = requests.post(url, data=payload)
        return response.json()

    def get_download_path(self, mod):
        provider = mod.get('provider')
        if provider == 'SteamWebAPI':
            # Use Downloads folder for SteamWebAPI mods
            download_path = self.steamwebapi_download_path
        elif provider == 'SteamCMD':
            app_id = mod.get('app_id')
            if app_id:
                download_path = os.path.join(self.steamcmd_download_path, app_id)
            else:
                # If app_id is not available, use a default download folder inside SteamCMD downloads
                download_path = os.path.join(self.steamcmd_download_path, 'unknown_app')
        else:
            download_path = self.downloads_root_path
    
        # Ensure the path exists before returning
        os.makedirs(download_path, exist_ok=True)
        return download_path
        
    def move_mod_to_downloads_steamcmd(self, mod):
        app_id = mod.get('app_id')
        mod_id = mod.get('mod_id')
        if not app_id or not mod_id:
            return False
    
        original_path = os.path.join(self.steamcmd_dir, 'steamapps', 'workshop', 'content', app_id, mod_id)

        folder_naming_format = self.config.get('folder_naming_format', 'id')

        if folder_naming_format == 'id':
            # Just use the mod ID
            folder_name = mod_id
        else:
            # Get mod name (or fallback to mod_id)
            mod_name = mod.get('mod_name', mod_id)
            # Convert to UTF-8, ignoring characters that can't be encoded
            mod_name_utf8 = mod_name.encode('utf-8', 'ignore').decode('utf-8')
            # Replace illegal filename characters with an underscore
            safe_mod_name = re.sub(r'[<>:"/\\|?*]', '_', mod_name_utf8)

            if folder_naming_format == 'name':
                # Use just the mod name
                folder_name = safe_mod_name
            elif folder_naming_format == 'combined':
                # Use "AppID - Mod Name" format
                folder_name = f"{app_id} - {safe_mod_name}"

        target_path = os.path.join(self.steamcmd_download_path, app_id, folder_name)

        if os.path.exists(original_path):
            try:
                if not os.path.exists(os.path.dirname(target_path)):
                    os.makedirs(os.path.dirname(target_path))
                shutil.move(original_path, target_path)
    
                return True
            except Exception as e:
                self.log_signal.emit(f"Failed to move mod {mod_id} to Downloads/SteamCMD: {e}")
                return False
        return False

    def parse_log_line(self, log_line, mod):
        success_pattern = re.compile(r'Success\. Downloaded item (\d+) to .* \((\d+) bytes\)', re.IGNORECASE)
        failure_pattern = re.compile(r'ERROR! Download item (\d+) failed \(([^)]+)\)', re.IGNORECASE)
    
        success_match = success_pattern.search(log_line)
        if success_match:
            downloaded_mod_id = success_match.group(1)
            if downloaded_mod_id == mod['mod_id']:
                mod['status'] = 'Downloaded'
                self.update_queue_signal.emit(mod['mod_id'], 'Downloaded')
                return
    
        failure_match = failure_pattern.search(log_line)
        if failure_match:
            failed_mod_id = failure_match.group(1)
            reason = failure_match.group(2)
            if failed_mod_id == mod['mod_id']:
                # Update the mod status as failed
                mod['status'] = f'Failed: {reason}'
                self.update_queue_signal.emit(mod['mod_id'], mod['status'])
                mod['retry_count'] += 1
                return

    def update_queue_status(self, mod_id, status):
        for index in range(self.queue_tree.topLevelItemCount()):
            item = self.queue_tree.topLevelItem(index)
            if item.text(1) == mod_id:
                item.setText(3, status)

                self.status_updates[mod_id] = status

                if not self.status_update_timer.isActive():
                    self.status_update_timer.start(300)

                if hasattr(self, 'filter_action'):
                    self.update_filter_tooltip()
                break

    def log_status_updates(self):
        if not self.status_updates:
            return
    
        # Count each unique status
        status_counts = defaultdict(int)
        for mod_id, status in self.status_updates.items():
            status_counts[status] += 1

        update_parts = []
        for status, count in status_counts.items():
            if count == 1:
                update_parts.append(f"1 mod → {status}")
            else:
                update_parts.append(f"{count} mods → {status}")

        log_message = "Status updates: " + ", ".join(update_parts)
        self.log_signal.emit(log_message)

        self.status_updates.clear()

    def append_log(self, message):
        self.log_area.append(message)
        self.log_area.moveCursor(QTextCursor.End)

    def download_workshop_immediately(self):
        input_text = self.workshop_input.text().strip()
        if not self.validate_steamcmd():
            return
        if not input_text:
            ThemedMessageBox.warning(self, 'Input Error', 'Please enter a Workshop URL or ID.')
            return
        workshop_id = self.extract_id(input_text)
        if not workshop_id:
            ThemedMessageBox.warning(self, 'Input Error', 'Invalid Workshop URL or ID.')
            return
        existing_ids = [mod['mod_id'] for mod in self.download_queue]
        item_fetcher = ItemFetcher(item_id=workshop_id, existing_mod_ids=existing_ids)
        item_fetcher.mod_or_collection_detected.connect(self.on_workshop_item_detected)
        def immediate_processed(result):
            self.on_item_processed(result)
            self.workshop_input.clear()
            self.start_download()
        item_fetcher.item_processed.connect(immediate_processed)
        item_fetcher.error_occurred.connect(self.on_item_error)
        item_fetcher.finished.connect(lambda: self.on_item_fetcher_finished(item_fetcher))
        item_fetcher.start()
        self.log_signal.emit(f"Processing input {workshop_id}...")
        
    def on_provider_changed(self):
        selected_provider = self.provider_dropdown.currentText()
        if selected_provider != 'Default' and self.download_queue:
            # Check if there are mods with different providers in the queue
            mods_with_different_providers = any(mod['provider'] != selected_provider for mod in self.download_queue)
            if mods_with_different_providers:
                reply = ThemedMessageBox.question(
                    self,
                    'Override Providers',
                    'Doing this will override all providers for mods in the queue. Are you sure?',
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    # Override providers for all mods in the queue
                    for mod in self.download_queue:
                        mod['provider'] = selected_provider
                    # Update the provider column in the queue_tree
                    for index in range(self.queue_tree.topLevelItemCount()):
                        item = self.queue_tree.topLevelItem(index)
                        item.setText(4, selected_provider)
                    self.log_signal.emit(f"All mod providers have been set to '{selected_provider}'.")
                else:
                    # Revert to previous selection
                    self.provider_dropdown.blockSignals(True)
                    previous_provider = 'Default'
                    self.provider_dropdown.setCurrentText(previous_provider)
                    self.provider_dropdown.blockSignals(False)
        elif selected_provider == 'Default' and self.download_queue:
            # Check if all mods have the same provider
            mods_with_steamcmd = all(mod['provider'] == 'SteamCMD' for mod in self.download_queue)
            mods_with_webapi = all(mod['provider'] == 'SteamWebAPI' for mod in self.download_queue)
            if mods_with_steamcmd or mods_with_webapi:
                reply = ThemedMessageBox.question(
                    self,
                    'Override Providers',
                    'Doing this will override all providers for mods in the queue. Are you sure?',
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    # Reset providers to default behavior
                    for mod in self.download_queue:
                        mod['provider'] = self.get_provider_for_mod(mod)
                        # Update the provider display in the queue_tree
                        provider_display = mod['provider']
                        item = self.find_queue_item(mod['mod_id'])
                        if item:
                            item.setText(4, provider_display)
                    self.log_signal.emit("Mod providers have been reset to default behavior.")
                else:
                    # Revert to previous selection
                    self.provider_dropdown.blockSignals(True)
                    previous_provider = 'SteamCMD' if mods_with_steamcmd else 'SteamWebAPI'
                    self.provider_dropdown.setCurrentText(previous_provider)
                    self.provider_dropdown.blockSignals(False)
                    
        self.config["download_provider"] = self.provider_dropdown.currentText()
        self.save_config()
                    
    def reset_status_of_mods(self, selected_items):
        for item in selected_items:
            mod_id = item.text(1)
            mod = next((mod for mod in self.download_queue if mod['mod_id'] == mod_id), None)
            if mod:
                mod['status'] = 'Queued'
                mod['retry_count'] = 0
                item.setText(3, 'Queued')
                self.log_signal.emit(f"Mod {mod_id} status reset to 'Queued'.")

    def move_all_downloaded_mods(self):
        workshop_content_path = os.path.join(self.steamcmd_dir, 'steamapps', 'workshop', 'content')
        if not os.path.exists(workshop_content_path):
            return
    
        moved_count = 0
        failed_count = 0
        app_id_stats = defaultdict(int)
        status_updates = []
    
        # Iterate over each App ID folder
        for app_id in os.listdir(workshop_content_path):
            app_path = os.path.join(workshop_content_path, app_id)
            if not os.path.isdir(app_path):
                continue
    
            # Iterate over each mod folder within the App folder
            for mod_id in os.listdir(app_path):
                mod_path = os.path.join(app_path, mod_id)
                if os.path.isdir(mod_path):
                    if mod_id not in self.downloaded_mods_info:
                        mod = next((m for m in self.download_queue if m['mod_id'] == mod_id), None)
                        if mod:
                            self.downloaded_mods_info[mod_id] = mod.get('mod_name', mod_id)

                            if 'Failed' in mod['status'] or mod['status'] == 'Downloading':
                                mod['status'] = 'Downloaded'
                                status_updates.append((mod_id, 'Downloaded'))

                    folder_naming_format = self.config.get('folder_naming_format', 'id')

                    if folder_naming_format == 'id':
                        folder_name = mod_id
                    else:
                        safe_mod_name = self.downloaded_mods_info.get(mod_id, mod_id)
                        
                        # If the mod is age-restricted, always use mod_id
                        if safe_mod_name == "UNKNOWN - Age Restricted":
                            safe_mod_name = mod_id
                        else:
                            # Remove characters that are illegal in file/folder names
                            safe_mod_name = re.sub(r'[<>:"/\\|?*]', '_', safe_mod_name)
                        
                        if folder_naming_format == 'name':
                            # Use just the mod name
                            folder_name = safe_mod_name
                        elif folder_naming_format == 'combined':
                            # Use "AppID - Mod Name" format
                            folder_name = f"{app_id} - {safe_mod_name}"
        
                    target_path = os.path.join(self.steamcmd_download_path, app_id, folder_name)
                    try:
                        if not os.path.exists(os.path.dirname(target_path)):
                            os.makedirs(os.path.dirname(target_path))
                        shutil.move(mod_path, target_path)
                        moved_count += 1
                        app_id_stats[app_id] += 1
                    except Exception as e:
                        failed_count += 1
                        # Only log individual failures
                        self.log_signal.emit(f"Failed to move mod {mod_id} to Downloads/SteamCMD: {e}")

        if moved_count > 0:
            if len(app_id_stats) == 1:
                # Single app ID
                app_id = next(iter(app_id_stats))
                self.log_signal.emit(f"Moved {moved_count} mod(s) to Downloads/SteamCMD/{app_id}")
            else:
                # Multiple app IDs
                app_details = []
                for app_id, count in app_id_stats.items():
                    app_details.append(f"{count} to {app_id}")

                self.log_signal.emit(f"Moved {moved_count} mod(s) to Downloads/SteamCMD: {', '.join(app_details)}")

        if failed_count > 0:
            self.log_signal.emit(f"Failed to move {failed_count} mod(s)")

        for mod_id, status in status_updates:
            self.update_queue_signal.emit(mod_id, status)

    def open_context_menu(self, position: QPoint):
        if self.is_downloading:
            return

        selected_items = self.queue_tree.selectedItems()
        if not selected_items:
            return

        menu = QMenu()
        
        # Move to Top action
        move_top_action = QAction("Move to Top", self)
        move_top_action.triggered.connect(lambda: self.move_mod_to_top(selected_items))
        menu.addAction(move_top_action)
        
        # Move Up action
        move_up_action = QAction("Move Up", self)
        move_up_action.triggered.connect(lambda: self.move_mod_up(selected_items))
        menu.addAction(move_up_action)
    
        # Move Down action
        move_down_action = QAction("Move Down", self)
        move_down_action.triggered.connect(lambda: self.move_mod_down(selected_items))
        menu.addAction(move_down_action)
        
        # Move to Bottom action
        move_bottom_action = QAction("Move to Bottom", self)
        move_bottom_action.triggered.connect(lambda: self.move_mod_to_bottom(selected_items))
        menu.addAction(move_bottom_action)
        
        menu.addSeparator()
        
        # Override AppID
        override_appid_action = QAction("Override AppID", self)
        override_appid_action.triggered.connect(lambda: self.on_override_appid(selected_items))
        menu.addAction(override_appid_action)
        
        # Change Provider submenu
        change_provider_menu = menu.addMenu("Change Provider")
        steamcmd_action = QAction("SteamCMD", self)
        steamcmd_action.triggered.connect(lambda: self.change_provider_for_mods(selected_items, "SteamCMD"))
        change_provider_menu.addAction(steamcmd_action)

        steamwebapi_action = QAction("SteamWebAPI", self)
        steamwebapi_action.triggered.connect(lambda: self.change_provider_for_mods(selected_items, "SteamWebAPI"))
        change_provider_menu.addAction(steamwebapi_action)

        # Check if any selected item has a status other than "Queued"
        show_reset_status = any(item.text(3) != 'Queued' for item in selected_items)

        # Add Reset Status action only if needed
        if show_reset_status:
            reset_status_action = QAction("Reset Status", self)
            reset_status_action.triggered.connect(lambda: self.reset_status_of_mods(selected_items))
            menu.addAction(reset_status_action)

        # Remove action
        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(lambda: self.remove_mods_from_queue(selected_items))
        menu.addAction(remove_action)

        menu.exec(self.queue_tree.viewport().mapToGlobal(position))

        def change_provider_for_mods(self, selected_items, new_provider):
            for item in selected_items:
                mod_id = item.text(0)
                mod = next((mod for mod in self.download_queue if mod['mod_id'] == mod_id), None)
                if mod:
                    mod['provider'] = new_provider
                    item.setText(3, new_provider)  # Update the provider column in the UI
                    self.log_signal.emit(f"Mod {mod_id} provider changed to {new_provider}.")
                    
    def move_mod_up(self, selected_items):
        for item in selected_items:
            index = self.queue_tree.indexOfTopLevelItem(item)
            if index > 0:
                self.queue_tree.takeTopLevelItem(index)
                self.queue_tree.insertTopLevelItem(index - 1, item)
    
                mod_id = item.text(1)
                mod = next((mod for mod in self.download_queue if mod['mod_id'] == mod_id), None)
                if mod:
                    self.download_queue.remove(mod)
                    self.download_queue.insert(index - 1, mod)
                self.update_queue_count()
    
    def move_mod_down(self, selected_items):
        for item in reversed(selected_items):
            index = self.queue_tree.indexOfTopLevelItem(item)
            if index < self.queue_tree.topLevelItemCount() - 1:
                self.queue_tree.takeTopLevelItem(index)
                self.queue_tree.insertTopLevelItem(index + 1, item)
    
                mod_id = item.text(1)
                mod = next((mod for mod in self.download_queue if mod['mod_id'] == mod_id), None)
                if mod:
                    self.download_queue.remove(mod)
                    self.download_queue.insert(index + 1, mod)
                self.update_queue_count()
                
    def move_mod_to_top(self, selected_items):
        items_with_indexes = sorted(
            [(self.queue_tree.indexOfTopLevelItem(item), item) for item in selected_items],
            key=lambda x: x[0]
        )
        
        for index, item in items_with_indexes:
            if index > 0:
                self.queue_tree.takeTopLevelItem(index)
                self.queue_tree.insertTopLevelItem(0, item)
                
                mod_id = item.text(1)
                mod = next((mod for mod in self.download_queue if mod['mod_id'] == mod_id), None)
                if mod:
                    self.download_queue.remove(mod)
                    self.download_queue.insert(0, mod)
        
        self.update_queue_count()
    
    def move_mod_to_bottom(self, selected_items):
        items_with_indexes = sorted(
            [(self.queue_tree.indexOfTopLevelItem(item), item) for item in selected_items],
            key=lambda x: x[0],
            reverse=True
        )
        
        total_items = self.queue_tree.topLevelItemCount()
        
        for index, item in items_with_indexes:
            if index < total_items - 1:
                self.queue_tree.takeTopLevelItem(index)
                self.queue_tree.insertTopLevelItem(self.queue_tree.topLevelItemCount(), item)
                
                mod_id = item.text(1)
                mod = next((mod for mod in self.download_queue if mod['mod_id'] == mod_id), None)
                if mod:
                    self.download_queue.remove(mod)
                    self.download_queue.append(mod)
        
        self.update_queue_count()

    def remove_mod_from_queue(self, mod_id):
        self.download_queue = [mod for mod in self.download_queue if mod['mod_id'] != mod_id]
        keep_downloaded = self.config.get('keep_downloaded_in_queue', False)
        
        # Remove from the GUI tree
        item_to_remove = None
        for index in range(self.queue_tree.topLevelItemCount()):
            item = self.queue_tree.topLevelItem(index)
            if item.text(1) == mod_id and not keep_downloaded:
                item_to_remove = item
                break
    
        if item_to_remove:
            index = self.queue_tree.indexOfTopLevelItem(item_to_remove)
            self.queue_tree.takeTopLevelItem(index)
            self.update_queue_count()
    
        # Disable the export button if the queue is empty
        self.export_queue_btn.setEnabled(bool(self.download_queue))
        
    def remove_mods_from_queue(self, selected_items):
        if not selected_items:
            return
        
        self.queue_tree.setUpdatesEnabled(False)
        try:
            # Extract mod_ids from selected items once
            mod_ids_to_remove = [item.text(1) for item in selected_items]
            count_removed = len(mod_ids_to_remove)  # log once
    
            # Remove from internal download queue in one pass
            self.download_queue = [mod for mod in self.download_queue if mod['mod_id'] not in mod_ids_to_remove]
    
            # Remove items from the GUI
            items_with_indexes = [(self.queue_tree.indexOfTopLevelItem(item), item) for item in selected_items]
            items_with_indexes.sort(key=lambda x: x[0], reverse=True)
    
            for idx, it in items_with_indexes:
                if idx != -1:
                    self.queue_tree.takeTopLevelItem(idx)
            
            # Log the removal operation with the appropriate message
            if count_removed == 1:
                self.log_signal.emit(f"Removed 1 mod from the queue")
            else:
                self.log_signal.emit(f"Removed {count_removed} mods from the queue")
                
            self.update_queue_count()
            # Disable the export button if the queue is empty
            self.export_queue_btn.setEnabled(bool(self.download_queue))
        
        finally:
            self.queue_tree.setUpdatesEnabled(True)
            
    def remove_all_downloaded_mods(self):
        # path to the SteamCMD workshop content folder
        workshop_content_path = os.path.join(self.steamcmd_dir, 'steamapps', 'workshop', 'content')
        if not os.path.exists(workshop_content_path):
            return
        
        removed_count = 0
        
        # For each app_id folder in workshop_content_path
        for app_id in os.listdir(workshop_content_path):
            app_path = os.path.join(workshop_content_path, app_id)
            if os.path.isdir(app_path):
                # For each mod_id folder in app_path
                for mod_id in os.listdir(app_path):
                    mod_path = os.path.join(app_path, mod_id)
                    if os.path.isdir(mod_path):
                        # Remove the entire mod directory
                        try:
                            shutil.rmtree(mod_path)
                            removed_count += 1
                        except Exception as e:
                            self.log_signal.emit(f"Failed to remove mod {mod_id}: {e}")
        
        if removed_count > 0:
            self.log_signal.emit(f"Removed {removed_count} downloaded mod folders due to cancellation")
                            
    def remove_appworkshop_acf_files(self):
        workshop_path = os.path.join(self.steamcmd_dir, 'steamapps', 'workshop')
        
        if not os.path.exists(workshop_path):
            return
            
        try:
            for file_name in os.listdir(workshop_path):
                if file_name.startswith("appworkshop_") and file_name.endswith(".acf"):
                    file_path = os.path.join(workshop_path, file_name)
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        self.log_signal.emit(f"Failed to delete {file_path}: {e}")
        except Exception as e:
            self.log_signal.emit(f"Error during .acf file cleanup: {e}")

    def open_downloads_folder(self):
        selected_items = self.queue_tree.selectedItems()
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        downloads_root_path = os.path.join(script_dir, 'Downloads')
    
        # No mod is highlighted, open the "Downloads" folder.
        if not selected_items:
            if not self.download_queue:
                # No mod highlighted and queue is empty, just open the "Downloads" folder
                if not os.path.isdir(downloads_root_path):
                    os.makedirs(downloads_root_path)
                webbrowser.open(downloads_root_path)
                return
    
            # No mods are highlighted, but all mods in queue have the same provider
            providers_in_queue = {mod['provider'] for mod in self.download_queue}
            if len(providers_in_queue) == 1:
                provider = providers_in_queue.pop()
                if provider == "SteamCMD":
                    provider_path = os.path.join(downloads_root_path, 'SteamCMD')
                elif provider == "SteamWebAPI":
                    provider_path = os.path.join(downloads_root_path, 'SteamWebAPI')
                else:
                    provider_path = downloads_root_path
    
                if not os.path.isdir(provider_path):
                    os.makedirs(provider_path)
                webbrowser.open(provider_path)
                return
    
            # Default case if no specific behavior is triggered
            if not os.path.isdir(downloads_root_path):
                os.makedirs(downloads_root_path)
            webbrowser.open(downloads_root_path)
            return
    
            # If a mod is highlighted, open the specific folder where the mod is located.
            mod_id = selected_items[0].text(1)
            mod = next((mod for mod in self.download_queue if mod['mod_id'] == mod_id), None)
            if not mod:
                ThemedMessageBox.warning(self, 'Error', 'Selected mod not found in the download queue.')
                return
        
            provider = mod.get('provider')
            
            if provider == 'SteamWebAPI':
                # Open Downloads/SteamWebAPI folder
                download_path = os.path.join(downloads_root_path, 'SteamWebAPI')
                if not os.path.isdir(download_path):
                    os.makedirs(download_path)
                webbrowser.open(download_path)
        
            elif provider == 'SteamCMD':
                # Open Downloads/SteamCMD/app_id folder
                app_id = mod.get('app_id')
                if not app_id:
                    ThemedMessageBox.warning(self, 'Error', 'AppID not found for the selected mod.')
                    return
        
                download_path = os.path.join(downloads_root_path, 'SteamCMD', app_id)
                if not os.path.isdir(download_path):
                    os.makedirs(download_path)
                webbrowser.open(download_path)
            
    def start_clipboard_monitoring(self):
        if not self.clipboard_signal_connected:
            self.clipboard.dataChanged.connect(self.check_clipboard_for_url)
            self.clipboard_signal_connected = True

    def stop_clipboard_monitoring(self):
        if self.clipboard_signal_connected:
            self.clipboard.dataChanged.disconnect(self.check_clipboard_for_url)
            self.clipboard_signal_connected = False

    def check_clipboard_for_url(self):
        if not self.add_to_queue_btn.isEnabled():
            return
    
        current_time = time.time()
        if hasattr(self, '_last_clipboard_trigger'):
            if current_time - self._last_clipboard_trigger < 0.5:
                return
        self._last_clipboard_trigger = current_time
    
        current_text = self.clipboard.text().strip()
        if self.is_valid_workshop_url(current_text):
            # Paste the URL into the input field
            self.workshop_input.setText(current_text)

            if self.config.get('auto_add_to_queue', False):
                QTimer.singleShot(200, self.add_workshop_to_queue)

    def is_valid_workshop_url(self, text):
        return re.match(r'https?://steamcommunity\.com/sharedfiles/filedetails/\?id=\d+', text)
            
    def open_update_appids(self):
        dialog = UpdateAppIDsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            selected_types = dialog.get_selected_types()
            if not selected_types:
                ThemedMessageBox.warning(self, 'Input Error', 'Please select at least one type.')
                return
            self.log_signal.emit(f"Updating AppIDs for types: {', '.join(selected_types)}")
            threading.Thread(target=self.update_appids_worker, args=(selected_types,), daemon=True).start()
            
    def update_appids_worker(self, selected_types):
        self.log_signal.emit("Starting AppIDs update...")
        try:
            scraper = AppIDScraper(self.files_dir)

            chrome_win64_dir = os.path.join(self.files_dir, 'chromium', 'chrome-win64')
            chromedriver_win64_dir = os.path.join(self.files_dir, 'chromium', 'chromedriver-win64')

            if not (os.path.exists(chrome_win64_dir) and os.path.exists(chromedriver_win64_dir)):
                self.log_signal.emit("Chromium or ChromeDriver not found. Installing...")
                chromium_url, chromedriver_url = scraper.get_download_links()

                def download_and_extract(url, extract_to, component_name):
                    try:
                        self.log_signal.emit(f"Downloading {component_name}...")
                        response = requests.get(url)
                        zip_filename = os.path.join(extract_to, "download.zip")

                        with open(zip_filename, 'wb') as f:
                            f.write(response.content)

                        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
                            zip_ref.extractall(extract_to)

                        os.remove(zip_filename)
                        self.log_signal.emit(f"{component_name} downloaded and extracted.")
                    except Exception as e:
                        self.log_signal.emit(f"Error downloading {component_name}: {e}")
                        raise

                if not os.path.exists(chrome_win64_dir):
                    download_and_extract(chromium_url, os.path.join(self.files_dir, 'chromium'), "Chromium")

                if not os.path.exists(chromedriver_win64_dir):
                    download_and_extract(chromedriver_url, os.path.join(self.files_dir, 'chromium'), "ChromeDriver")

            self.log_signal.emit("Scraping SteamDB for AppIDs...")
            entries = scraper.scrape_steamdb(selected_types)

            appids_path = os.path.join(self.files_dir, 'AppIDs.txt')
            with open(appids_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(entries))
            self.log_signal.emit("AppIDs updated successfully.")

            self.load_app_ids()
        except Exception as e:
            self.log_signal.emit(f"Error updating AppIDs: {e}")
            ThemedMessageBox.critical(self, 'Error', f"Failed to update AppIDs: {e}")
            
    def on_search_text_changed(self, text: str):
        self.search_timer.start(300)
    
    def perform_search(self):
        current_text = self.search_input.text()
        self.filter_queue_items(current_text)
        
    def updateRegexIcon(self, checked: bool):
        if checked:
            self.regexButton.setIcon(QIcon(resource_path('Files/regex_enabled.png')))
        else:
            self.regexButton.setIcon(QIcon(resource_path('Files/regex_disabled.png')))
        self.perform_search()
    
    def updateCaseIcon(self, checked: bool):
        if checked:
            self.caseButton.setIcon(QIcon(resource_path('Files/case_enabled.png')))
        else:
            self.caseButton.setIcon(QIcon(resource_path('Files/case_disabled.png')))
        self.perform_search()
        
    def show_about_dialog(self):
        dialog = AboutDialog(self)
        dialog.exec()
        
    def showLogContextMenu(self, pos):
        menu = self.log_area.createStandardContextMenu()
        
        clear_logs_action = QAction("Clear Logs", self)
        clear_logs_action.triggered.connect(self.clearLogs)
        menu.addAction(clear_logs_action)
        menu.exec(self.log_area.mapToGlobal(pos))

    def clearLogs(self):
        self.log_area.clear()
        
    def updateWindowTitle(self):
        base_title = "Streamline"
        if self.config.get("show_version", True):
            base_title += f" v{current_version}"
        self.setWindowTitle(base_title)
    
    def filter_queue_by_status(self, status):
        self.current_filter = status
        self.update_queue_count()
        self.perform_search()

    def update_filter_tooltip(self):
        if not hasattr(self, 'filter_tooltip'):
            return
            
        total_count = len(self.download_queue)
        queued_count = sum(1 for mod in self.download_queue if mod['status'] == 'Queued')
        downloaded_count = sum(1 for mod in self.download_queue if mod['status'] == 'Downloaded')
        failed_count = sum(1 for mod in self.download_queue if 'Failed' in mod['status'])
        downloading_count = sum(1 for mod in self.download_queue if mod['status'] == 'Downloading')
    
        tooltip = f"All Mods: {total_count}\n" \
                  f"Queued: {queued_count}\n" \
                  f"Downloaded: {downloaded_count}\n" \
                  f"Failed: {failed_count}"
    
        if downloading_count > 0:
            tooltip += f"\nDownloading: {downloading_count}"
        if failed_count > 0:
            tooltip += f"\nFailed: {failed_count}"
    
        self.filter_tooltip.update_tooltip_text(tooltip)

if __name__ == '__main__':
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)

    app_icon = QIcon(resource_path('Files/logo.png'))
    app.setWindowIcon(app_icon)

    splash = ThemedSplashScreen()
    splash.show()

    downloader = None

    def on_setup_complete(success):
        if success:
            downloader = SteamWorkshopDownloader()
            downloader.resize(670, 750)
            downloader.show()
        else:
            app.quit()

    splash.setup_completed.connect(on_setup_complete)

    sys.exit(app.exec())