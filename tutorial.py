import os
from initialize import apply_theme_titlebar
from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, 
    QDialog, QFrame, QApplication, QCheckBox
)
from PySide6.QtCore import (
    Qt, QRect, QPoint, QTimer, QObject, QPropertyAnimation,
    QEasingCurve, QEvent
)
from PySide6.QtGui import (
    QPainter, QColor, QPen
)

class EventBlockingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 10);")

        if parent:
            self.setGeometry(parent.rect())
            parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize and obj == self.parent():
            self.setGeometry(self.parent().rect())
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()

    def mouseMoveEvent(self, event):
        event.accept()

class WidgetHighlighter(QWidget):
    def __init__(self, parent, target_widget):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.target_widget = target_widget
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.update_position()
        
    def update_position(self):
        if hasattr(self.target_widget, 'menuAction') and callable(self.target_widget.menuAction):
            menu_bar = self.parent()
            action = self.target_widget.menuAction()
            rect = menu_bar.actionGeometry(action)
            self.setGeometry(rect)
        else:
            global_pos = self.target_widget.mapToGlobal(QPoint(0, 0))
            global_rect = QRect(global_pos, self.target_widget.size())
            self.setGeometry(global_rect)
    
    def reposition(self):
        self.update_position()
        self.show()
        self.raise_()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen = QPen(QColor("#4D8AC9"), 3)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.drawRoundedRect(rect, 2, 2)
        
        glow_color = QColor("#4D8AC9")
        glow_color.setAlpha(50)
        glow_pen = QPen(glow_color, 6)
        painter.setPen(glow_pen)
        painter.drawRoundedRect(rect, 5, 5)

    def showEvent(self, event):
        self.raise_()
        super().showEvent(event)


class TutorialDialog(QDialog):
    # Frameless dialog used to display tutorial messages
    def __init__(self, parent, target_widget, message, arrow_direction="down", is_last_step=False):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.target_widget = target_widget
        self.arrow_direction = arrow_direction
        self.is_last_step = is_last_step
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.highlight = None
        self.highlight_widget = None
        self.setup_ui(message)

    def setup_ui(self, message):
        layout = QVBoxLayout(self)

        content_frame = QFrame(self)
        content_frame.setObjectName("tutorialFrame")
        content_frame.setStyleSheet("""
            #tutorialFrame {
                background-color: #2C2C2C;
                border: 1px solid #555555;
                border-radius: 3px;
            }
            QLabel {
                color: #A0A0A0;
            }
            QPushButton {
                background-color: #333333;
                color: #A0A0A0;
                border: none;
                padding: 8px 16px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #555555;
                color: #E0E0E0;
            }
            QPushButton#nextButton {
                background-color: #4D8AC9;
                color: #FFFFFF;
                font-weight: bold;
            }
            QPushButton#nextButton:hover {
                background-color: #5A9AD9;
            }
        """)

        content_layout = QVBoxLayout(content_frame)

        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        self.message_label.setMinimumWidth(250)
        self.message_label.setMaximumWidth(350)
        content_layout.addWidget(self.message_label)

        button_layout = QHBoxLayout()

        self.next_button = QPushButton("Next" if not self.is_last_step else "Finish")
        self.next_button.setObjectName("nextButton")
        self.next_button.setFixedWidth(100)
        self.next_button.setCursor(Qt.PointingHandCursor)
        
        self.skip_button = QPushButton("Skip")
        self.skip_button.setFixedWidth(100)
        self.skip_button.setCursor(Qt.PointingHandCursor)
        
        if self.is_last_step:
            self.skip_button.hide()
            button_layout.addStretch()
            button_layout.addWidget(self.next_button)
            button_layout.addStretch()
        else:
            button_layout.addWidget(self.skip_button)
            button_layout.addStretch()
            button_layout.addWidget(self.next_button)
        
        content_layout.addLayout(button_layout)
        layout.addWidget(content_frame)
        
        self.adjustSize()

    def position_relative_to_target(self):
        if not self.target_widget:
            return

        if hasattr(self.target_widget, 'menuAction') and callable(self.target_widget.menuAction):
            menu_bar = self.parent().menu_bar
            action = self.target_widget.menuAction()
            action_rect = menu_bar.actionGeometry(action)
            target_pos = menu_bar.mapToGlobal(action_rect.topLeft())
            target_rect = action_rect
        else:
            target_rect = self.target_widget.rect()
            target_pos = self.target_widget.mapToGlobal(QPoint(0, 0))
            
        dialog_size = self.size()
        
        if self.arrow_direction == "up":
            pos = QPoint(
                target_pos.x() + target_rect.width() // 2 - dialog_size.width() // 2,
                target_pos.y() + target_rect.height() + 5
            )
        elif self.arrow_direction == "down":
            pos = QPoint(
                target_pos.x() + target_rect.width() // 2 - dialog_size.width() // 2,
                target_pos.y() - dialog_size.height() - 5
            )
        elif self.arrow_direction == "left":
            pos = QPoint(
                target_pos.x() + target_rect.width() + 5,
                target_pos.y() + target_rect.height() // 2 - dialog_size.height() // 2
            )
        else:  # "right"
            pos = QPoint(
                target_pos.x() - dialog_size.width() - 5,
                target_pos.y() + target_rect.height() // 2 - dialog_size.height() // 2
            )

        screen_rect = QApplication.primaryScreen().availableGeometry()

        if pos.x() < screen_rect.left():
            pos.setX(screen_rect.left() + 5)
        elif pos.x() + dialog_size.width() > screen_rect.right():
            pos.setX(screen_rect.right() - dialog_size.width() - 5)

        if pos.y() < screen_rect.top():
            pos.setY(screen_rect.top() + 5)
        elif pos.y() + dialog_size.height() > screen_rect.bottom():
            pos.setY(screen_rect.bottom() - dialog_size.height() - 5)

        self.move(pos)
        
    def update_positions(self):
        if not self.target_widget or not self.target_widget.isVisible():
            return
        current_pos = self.target_widget.mapToGlobal(QPoint(0, 0))
        if hasattr(self, '_last_target_pos') and self._last_target_pos == current_pos:
            return
        self._last_target_pos = current_pos
        self.position_relative_to_target()
        if self.highlight:
            self.highlight.update_position()

    def show_with_highlight(self):
        if hasattr(self.target_widget, 'menuAction') and callable(self.target_widget.menuAction):
            menu_bar = self.parent().menu_bar
            action = self.target_widget.menuAction()
            action_rect = menu_bar.actionGeometry(action)

            highlight_widget = QWidget(menu_bar)
            highlight_widget.setGeometry(action_rect)
            highlight_widget.setStyleSheet("background-color: rgba(0,0,0,0);")
            highlight_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
            highlight_widget.lower()
            highlight_widget.show()

            self.highlight = WidgetHighlighter(menu_bar, highlight_widget)
            self.highlight_widget = highlight_widget

            self._highlighted_menu_action = action
            self._highlighted_menu_bar = menu_bar
        elif self.target_widget:
            self.highlight = WidgetHighlighter(None, self.target_widget)

        if self.highlight:
            self.highlight.show()
            self.highlight.raise_()

        self.position_relative_to_target()
        self.show()
        self.raise_()

        self.opacity_effect = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_effect.setDuration(250)
        self.opacity_effect.setStartValue(0.0)
        self.opacity_effect.setEndValue(1.0)
        self.opacity_effect.setEasingCurve(QEasingCurve.InOutQuad)
        self.opacity_effect.start()

        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Move, QEvent.Resize, QEvent.WindowActivate, 
                           QEvent.WindowDeactivate, QEvent.ApplicationActivate,
                           QEvent.ApplicationDeactivate):
            self.update_positions()
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        if self.highlight:
            self.highlight.close()
            self.highlight.deleteLater()
            self.highlight = None

        QApplication.instance().removeEventFilter(self)
        event.accept()


class WelcomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Streamline")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setFixedWidth(450)

        if parent and hasattr(parent, 'config'):
            apply_theme_titlebar(self, parent.config)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        title_label = QLabel("<h2>Welcome to Streamline!</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #A0A0A0;")
        layout.addWidget(title_label)

        desc_label = QLabel("<p>Would you like to take a quick tour to learn the basics?</p>")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 14px; color: #A0A0A0;")
        layout.addWidget(desc_label)
        
        features_label = QLabel(
            "<p>The tutorial will cover basic navigation of the interface:</p>"
            "<ul>"
            "<li>Adding and managing workshop items(AppIDs, Mods, Collections)</li>"
            "<li>Download configuration options</li>"
            "<li>Filtering and searching your queue</li>"
            "<li>General navigation</li>"
            "</ul>"
        )
        features_label.setWordWrap(True)
        features_label.setStyleSheet("font-size: 14px; color: #A0A0A0;")
        layout.addWidget(features_label)
        
        note_label = QLabel(
            "<p><i>Note: During the tutorial, all UI elements will be temporarily enabled "
            "for demonstration purposes and will be restored to your preferences afterward.</i></p>"
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("font-size: 12px; color: #797979;")
        layout.addWidget(note_label)
        
        self.show_on_startup_checkbox = QCheckBox("Show on Startup")
        self.show_on_startup_checkbox.setChecked(True)
        if self.parent and hasattr(self.parent, 'config'):
            self.show_on_startup_checkbox.setChecked(parent.config.get('show_tutorial_on_startup', True))
        layout.addWidget(self.show_on_startup_checkbox)
        
        button_layout = QHBoxLayout()
        
        skip_button = QPushButton("Skip")
        skip_button.setFixedWidth(120)
        skip_button.setCursor(Qt.PointingHandCursor)
        skip_button.setStyleSheet("padding: 8px 16px;")
        skip_button.clicked.connect(self.reject)

        tutorial_button = QPushButton("Take the Tour")
        tutorial_button.setCursor(Qt.PointingHandCursor)
        tutorial_button.setStyleSheet("""
            QPushButton{
                background-color: #4D8AC9;
                color: #FFFFFF;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #5A9AD9;
            }""")
        tutorial_button.clicked.connect(self.accept)

        button_layout.addWidget(tutorial_button)
        button_layout.addWidget(skip_button)
        layout.addLayout(button_layout)


class Tutorial(QObject):
    # Main tutorial manager
    def __init__(self, main_app):
        super().__init__(main_app)
        self.main_app = main_app
        self.current_step = 0
        self.current_dialog = None
        self.original_visibility_states = {}
    
    def save_visibility_states(self):
        app = self.main_app
        self.original_visibility_states = {
            'download_button': app.download_btn.isVisible(),
            'search_input': app.search_input.isVisible(),
            'regex_button': app.regexButton.isVisible(),
            'case_button': app.caseButton.isVisible(),
            'import_export_container': app.import_export_container.isVisible(),
            'log_area': app.log_area.isVisible(),
            'provider_dropdown': app.provider_dropdown.isVisible(),
            'menu_bar': app.menu_bar.isVisible(),
        }
        if hasattr(app, 'import_export_spacer'):
            self.original_visibility_states['import_export_spacer'] = app.import_export_spacer.isVisible()
        
    def show_all_ui_elements(self):
        app = self.main_app
        app.download_btn.setVisible(True)
        app.search_input.setVisible(True)
        app.regexButton.setVisible(True)
        app.caseButton.setVisible(True)
        app.import_export_container.setVisible(True)
        app.log_area.setVisible(True)
        app.provider_dropdown.setVisible(True)
        app.menu_bar.setVisible(True)
        if hasattr(app, 'import_export_spacer'):
            app.import_export_spacer.setVisible(True)
        
    def restore_visibility_states(self):
        if not self.original_visibility_states:
            return
            
        app = self.main_app
        app.download_btn.setVisible(self.original_visibility_states.get('download_button', True))
        app.search_input.setVisible(self.original_visibility_states.get('search_input', True))
        app.regexButton.setVisible(self.original_visibility_states.get('regex_button', True))
        app.caseButton.setVisible(self.original_visibility_states.get('case_button', True))
        app.import_export_container.setVisible(self.original_visibility_states.get('import_export_container', True))
        app.log_area.setVisible(self.original_visibility_states.get('log_area', True))
        app.provider_dropdown.setVisible(self.original_visibility_states.get('provider_dropdown', True))
        app.menu_bar.setVisible(self.original_visibility_states.get('menu_bar', True))
        if hasattr(app, 'import_export_spacer'):
            app.import_export_spacer.setVisible(self.original_visibility_states.get('import_export_spacer', True))
        if hasattr(app, 'apply_settings'):
            app.apply_settings()
        
    def start_tutorial(self):
        self.current_step = 0
        self.save_visibility_states()
        self.show_all_ui_elements()

        self.overlay = EventBlockingOverlay(self.main_app)
        self.overlay.show()
        self.overlay.raise_()

        self.main_app.activateWindow()
        self.main_app.raise_()
        QTimer.singleShot(100, self.show_current_step)
        
    def show_current_step(self):
        if self.current_dialog:
            try:
                self.current_dialog.close()
            except:
                self.current_dialog.hide()
            self.current_dialog = None
    
        if self.current_step >= len(self.get_tutorial_steps()):
            return
    
        step = self.get_tutorial_steps()[self.current_step]
        widget = step['widget']
        message = step['message']
        position = step.get('position', 'bottom')
    
        arrow_map = {
            'top': 'down',
            'bottom': 'up',
            'left': 'right',
            'right': 'left'
        }
        arrow_direction = arrow_map.get(position, 'down')

        is_last_step = (self.current_step == len(self.get_tutorial_steps()) - 1)

        dialog = TutorialDialog(self.main_app, widget, message, arrow_direction, is_last_step)

        dialog.next_button.clicked.connect(self.next_step)
        dialog.skip_button.clicked.connect(self.finish_tutorial)

        dialog.show_with_highlight()
        self.current_dialog = dialog

    def next_step(self):
        if self.current_dialog:
            try:
                self.current_dialog.close()
            except:
                self.current_dialog.hide()
            self.current_dialog = None

        self.current_step += 1
        if self.current_step < len(self.get_tutorial_steps()):
            QTimer.singleShot(0, self.show_current_step)
        else:
            self.finish_tutorial()

    def finish_tutorial(self):
        if self.current_dialog:
            try:
                self.current_dialog.close()
            except:
                self.current_dialog.hide()
            self.current_dialog = None
        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.close()
            self.overlay.deleteLater()
            self.overlay = None
        QTimer.singleShot(200, self.restore_visibility_states)
        
    def get_tutorial_steps(self):
        return [
            {
                'widget': self.main_app.workshop_input,
                'message': "Here you can enter Steam Workshop content by pasting a mod URL, collection URL, or game AppID to download specific items or entire game workshops.",
                'position': 'bottom'
            },
            {
                'widget': self.main_app.add_to_queue_btn,
                'message': "After entering your URL or ID, click this button to add it to your download queue. This lets you build up a list of items before starting the download process, giving you time to review and organize your selections.",
                'position': 'bottom'
            },
            {
                'widget': self.main_app.steam_accounts_dropdown,
                'message': "This dropdown lets you select which Steam account to use for downloading. You can choose between 'Anonymous' access or your own Steam accounts that you've added.",
                'position': 'bottom'
            },
            {
                'widget': self.main_app.queue_tree,
                'message': "Here's your download queue. It shows all your queued mods with their details. You can right-click items for more options, or right-click the header to customize which columns are displayed.",
                'position': 'top'
            },
            {
                'widget': self.main_app.search_input,
                'message': "Use this search bar to filter your queue by mod name or ID. The buttons to the right enable case-sensitivity and regular expressions for more advanced filtering.",
                'position': 'bottom'
            },
            {
                'widget': self.main_app.provider_dropdown,
                'message': "This dropdown controls how Streamline downloads your content. 'Default' uses SteamCMD for games that support 'anonymous' downloads and SteamWebAPI for others. You can also manually select a specific provider if needed. SteamCMD should always be used for owned games.",
                'position': 'top'
            },
            {
                'widget': self.main_app.download_start_btn,
                'message': "When you're ready, click this button to begin downloading everything in your queue. Streamline will process items in batches according to your settings.",
                'position': 'top'
            },
            {
                'widget': self.main_app.log_area,
                'message': "This logs panel keeps you informed about what's happening. It shows real-time download progress, any errors encountered, and status messages so you always know what Streamline is doing.",
                'position': 'top'
            },
            {
                'widget': self.main_app.settings_btn,
                'message': "Click this gear icon to access Streamline's settings. You can customize the appearance, download behavior, file naming conventions, and many other options to suit your preferences.",
                'position': 'right'
            },
            {
                'widget': self.main_app.configure_steam_accounts_btn,
                'message': "This button opens the Steam accounts manager where you can add, remove, or update the Steam accounts that Streamline can use for downloading mods.",
                'position': 'right'
            },
            {
                'widget': self.main_app.update_appids_btn,
                'message': "This button updates Streamline's database of Steam AppIDs. This is important as it helps identify which games support anonymous downloads, ensuring the optimal download method is used.",
                'position': 'right'
            },
            {
                'widget': self.main_app.help_menu,
                'message': "That's it! You can show the tutorial again by accessing this menu",
                'position': 'right'
            },
        ]

    def show_welcome_dialog(self):
        dialog = WelcomeDialog(self.main_app)
        result = dialog.exec()
        if result == QDialog.Accepted:
            QTimer.singleShot(300, self.start_tutorial)
        else:
            QTimer.singleShot(200, self.restore_visibility_states)


def check_first_run(app):
    config = getattr(app, 'config', {})

    tutorial = Tutorial(app)
    app._tutorial_instance = tutorial

    show_tutorial = not config.get('tutorial_shown', False) or config.get('show_tutorial_on_startup', True)

    if show_tutorial:
        tutorial.save_visibility_states()

        dialog = WelcomeDialog(app)
        dialog_result = dialog.exec()

        if hasattr(dialog, 'show_on_startup_checkbox'):
            config['show_tutorial_on_startup'] = dialog.show_on_startup_checkbox.isChecked()

        config['tutorial_shown'] = True

        save_config = getattr(app, 'save_config', None)
        if save_config and callable(save_config):
            save_config()

        return True

    return False

def show_tutorial(app):
    if hasattr(app, '_tutorial_instance') and app._tutorial_instance:
        tutorial = app._tutorial_instance
        if tutorial.current_dialog:
            tutorial.current_dialog.close()
            tutorial.current_dialog = None
        tutorial.start_tutorial()
    else:
        tutorial = Tutorial(app)
        app._tutorial_instance = tutorial
        tutorial.start_tutorial()
    return True
