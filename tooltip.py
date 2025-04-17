from enum import Enum
from PySide6.QtWidgets import QWidget, QToolTip, QApplication, QToolButton
from PySide6.QtCore import Qt, Signal, QPoint, QSize, QTimer, QEvent, QObject
from PySide6.QtGui import QColor, QFont, QPalette, QFontMetrics

class TooltipPlacement(Enum):
    LEFT = 0
    RIGHT = 1
    TOP = 2
    BOTTOM = 3

class Utils:
    @staticmethod
    def get_top_level_parent(widget: QWidget) -> QWidget:
        if widget.parent() is None:
            return widget

        parent = widget.parent()
        while parent.parent() is not None:
            parent = parent.parent()
        return parent

    @staticmethod
    def get_parents(widget: QWidget) -> list[QWidget]:
        parents = []
        while widget.parent() is not None:
            parents.append(widget.parent())
            widget = widget.parent()
        return parents

class Tooltip(QObject):
    shown = Signal()
    hidden = Signal()

    def __init__(self, widget: QWidget = None, text: str = ''):
        super(Tooltip, self).__init__()
        
        TooltipManager.instance().register_tooltip(self)
        
        self.__widget = widget
        self.__text = text
        self.__placement = TooltipPlacement.BOTTOM
        self.__offsets = {
            TooltipPlacement.LEFT:   QPoint(-14, 0),
            TooltipPlacement.RIGHT:  QPoint(0, -14),
            TooltipPlacement.TOP:    QPoint(0, 0),
            TooltipPlacement.BOTTOM: QPoint(0, -5)
        }
        self.__show_delay = 500
        self.__hide_delay = 100
        self.__duration = 0
        self.__is_showing = False
        self.__watched_widgets = []

        self.__show_delay_timer = QTimer()
        self.__show_delay_timer.setInterval(self.__show_delay)
        self.__show_delay_timer.setSingleShot(True)
        self.__show_delay_timer.timeout.connect(self.__show_tooltip)

        self.__hide_delay_timer = QTimer()
        self.__hide_delay_timer.setInterval(self.__hide_delay)
        self.__hide_delay_timer.setSingleShot(True)
        self.__hide_delay_timer.timeout.connect(self.__hide_tooltip)

        self.__duration_timer = QTimer()
        self.__duration_timer.setInterval(self.__duration)
        self.__duration_timer.setSingleShot(True)
        self.__duration_timer.timeout.connect(self.__hide_tooltip)

        if widget:
            self.__install_event_filters()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ToolTip and watched == self.__widget:
            return True

        if event.type() == QEvent.Type.HoverEnter and watched == self.__widget:
            # Mouse enters widget
            if self.__widget and self.__widget.isEnabled():
                self.show(delay=True)
        elif event.type() == QEvent.Type.HoverLeave and watched == self.__widget:
            # Mouse leaves widget
            self.hide(delay=True)

        if event.type() in (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Hide):
            if self.__is_showing:
                self.__update_position()


        if event.type() == QEvent.Type.DeferredDelete:
            self.hide()
            if watched == self.__widget:
                self.__widget = None

        return False

    def getWidget(self) -> QWidget:
        return self.__widget

    def setWidget(self, widget: QWidget):
        if self.__is_showing:
            self.hide()
        self.__remove_event_filters()
        self.__widget = widget
        self.__install_event_filters()

    def getText(self) -> str:
        return self.__text

    def setText(self, text: str):
        self.__text = text
        if self.__is_showing:
            self.hide()
            self.show()

    def getPlacement(self) -> TooltipPlacement:
        return self.__placement

    def setPlacement(self, placement: TooltipPlacement):
        self.__placement = placement
        if self.__is_showing:
            self.__update_position()

    def getOffsets(self) -> dict[TooltipPlacement, QPoint]:
        return self.__offsets

    def getOffsetByPlacement(self, placement: TooltipPlacement) -> QPoint:
        return self.__offsets[placement]

    def setOffsets(self, offsets: dict[TooltipPlacement, QPoint]):
        for placement, offset in offsets.items():
            if isinstance(offset, QPoint):
                self.__offsets[placement] = offset
            elif isinstance(offset, (int, float)):
                self.__offsets[placement] = QPoint(offset, offset)
            elif isinstance(offset, (list, tuple)) and len(offset) >= 2:
                self.__offsets[placement] = QPoint(offset[0], offset[1])
        if self.__is_showing:
            self.__update_position()

    def setOffsetByPlacement(self, placement: TooltipPlacement, offset):
        if isinstance(offset, QPoint):
            self.__offsets[placement] = offset
        elif isinstance(offset, (int, float)):
            self.__offsets[placement] = QPoint(offset, offset)
        elif isinstance(offset, (list, tuple)) and len(offset) >= 2:
            self.__offsets[placement] = QPoint(offset[0], offset[1])
        if self.__is_showing:
            self.__update_position()

    def setOffsetsAll(self, offset):
        if isinstance(offset, QPoint):
            point_offset = offset
        elif isinstance(offset, (int, float)):
            point_offset = QPoint(offset, offset)
        elif isinstance(offset, (list, tuple)) and len(offset) >= 2:
            point_offset = QPoint(offset[0], offset[1])
        else:
            return
            
        for placement in self.__offsets.keys():
            self.__offsets[placement] = point_offset
        if self.__is_showing:
            self.__update_position()

    def getShowDelay(self) -> int:
        return self.__show_delay

    def setShowDelay(self, delay: int):
        self.__show_delay = delay
        self.__show_delay_timer.setInterval(delay)

    def getHideDelay(self) -> int:
        return self.__hide_delay

    def setHideDelay(self, delay: int):
        self.__hide_delay = delay
        self.__hide_delay_timer.setInterval(delay)
        
    def getDuration(self) -> int:
        return self.__duration

    def setDuration(self, duration: int):
        self.__duration = duration
        self.__duration_timer.setInterval(duration)

    def show(self, delay: bool = False):
        self.__duration_timer.stop()
        self.__hide_delay_timer.stop()
        
        if delay:
            self.__show_delay_timer.start()
        else:
            self.__show_tooltip()

    def hide(self, delay: bool = False):
        self.__show_delay_timer.stop()
        
        if delay:
            self.__hide_delay_timer.start()
        else:
            self.__hide_tooltip()
            
    @staticmethod
    def setGlobalFont(font: QFont):

        QToolTip.setFont(font)
        
    @staticmethod
    def applyStyleSheet(stylesheet: str):
        app = QApplication.instance()
        if app:
            current_sheet = app.styleSheet()
            app.setStyleSheet(current_sheet + "\n" + stylesheet)

    def __estimate_tooltip_size(self) -> QSize:
        if not self.__text:
            return QSize(50, 20)

        font_metrics = QFontMetrics(QToolTip.font())

        lines = self.__text.split('\n')
        width = max(font_metrics.horizontalAdvance(line) for line in lines)
        height = font_metrics.height() * len(lines)

        padding = 8
        return QSize(width + padding, height + padding)
    
    def __calculate_position(self) -> QPoint:
        if not self.__widget:
            return QPoint(0, 0)
            
        placement = self.__placement
        widget_pos = self.__widget.mapToGlobal(QPoint(0, 0))
        widget_size = self.__widget.size()
        offset = self.__offsets[placement]
        tooltip_size = self.__estimate_tooltip_size()
        
        # Calculate center of widget
        widget_center_x = widget_pos.x() + widget_size.width() // 2
        widget_center_y = widget_pos.y() + widget_size.height() // 2

        if placement == TooltipPlacement.TOP:
            return QPoint(
                widget_center_x - tooltip_size.width() // 2 + offset.x(),
                widget_pos.y() - tooltip_size.height() + offset.y()
            )
        elif placement == TooltipPlacement.BOTTOM:
            return QPoint(
                widget_center_x - tooltip_size.width() // 2 + offset.x(),
                widget_pos.y() + widget_size.height() + offset.y()
            )
        elif placement == TooltipPlacement.LEFT:
            return QPoint(
                widget_pos.x() - tooltip_size.width() + offset.x(),
                widget_center_y - tooltip_size.height() // 2 + offset.y()
            )
        elif placement == TooltipPlacement.RIGHT:
            return QPoint(
                widget_pos.x() + widget_size.width() + offset.x(),
                widget_center_y - tooltip_size.height() // 2 + offset.y()
            )

        return QPoint(
            widget_center_x - tooltip_size.width() // 2 + offset.x(),
            widget_pos.y() + widget_size.height() + offset.y()
        )
    
    def __update_position(self):
        if not self.__is_showing or not self.__widget:
            return
            
        position = self.__calculate_position()
        QToolTip.hideText()
        QToolTip.showText(position, self.__text, self.__widget)
    
    def __show_tooltip(self):
        if not self.__widget:
            return
            
        position = self.__calculate_position()
        QToolTip.showText(position, self.__text, self.__widget)
        self.__is_showing = True
        self.shown.emit()
        
        # Start duration timer if needed
        if self.__duration > 0:
            self.__duration_timer.start()
    
    def __hide_tooltip(self):
        QToolTip.hideText()
        self.__is_showing = False
        self.__duration_timer.stop()
        self.hidden.emit()
        
    def __del__(self):
        TooltipManager.instance().unregister_tooltip(self)
    
    def __install_event_filters(self):
        self.__remove_event_filters()
        if not self.__widget:
            return
            
        self.__watched_widgets.append(self.__widget)
        self.__watched_widgets += Utils.get_parents(self.__widget)
        
        for widget in self.__watched_widgets:
            widget.installEventFilter(self)
    
    def __remove_event_filters(self):
        for widget in self.__watched_widgets:
            try:
                widget.removeEventFilter(self)
            except:
                pass
        self.__watched_widgets.clear()
        
    def setup_for_action(self, action, tooltip_text=""):
        self.setText(tooltip_text)
        
        if action and action.parent():
            for child in action.parent().children():
                if isinstance(child, QToolButton) and child.defaultAction() == action:
                    self.setWidget(child)
                    return True
        
        return False
        
class FilterTooltip(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filter_action = None
        self.filter_action_button = None
        self.filter_tooltip = None
        self.filter_menu = None
        self.filter_menu_is_open = False
        self._show_delay = 500
        self._hide_delay = 100
        
        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self.on_application_quit)

    def setup(self, filter_action, filter_menu, tooltip_text=""):
        self.filter_action = filter_action
        self.filter_menu = filter_menu

        if self.filter_action and self.filter_action.parent():
            for child in self.filter_action.parent().children():
                if isinstance(child, QToolButton) and child.defaultAction() == self.filter_action:
                    self.filter_action_button = child
                    break

        if self.filter_action_button:
            self.filter_action_button.installEventFilter(self)
            self.filter_tooltip = Tooltip(self.filter_action_button, tooltip_text)
            self.filter_tooltip.setPlacement(TooltipPlacement.BOTTOM)
            self.filter_tooltip.setShowDelay(self._show_delay)
            self.filter_tooltip.setHideDelay(self._hide_delay)

            left_offset = QPoint(-5, 0)
            self.filter_tooltip.setOffsetByPlacement(TooltipPlacement.BOTTOM, left_offset)

            self.filter_action.triggered.connect(self.on_filter_action_triggered)

            return True

        return False

    def update_tooltip_text(self, text):
        if self.filter_tooltip:
            self.filter_tooltip.setText(text)

    def show_filter_menu(self):
        if self.filter_tooltip:
            self.filter_tooltip.hide()

        self.filter_menu_is_open = True

        if self.filter_menu:
            self.filter_menu.aboutToHide.connect(self.on_filter_menu_hide)

            parent = self.filter_action.parent()
            if parent:
                self.filter_menu.exec(parent.mapToGlobal(QPoint(0, parent.height())))
            else:
                self.filter_menu.exec(QCursor.pos())

            try:
                self.filter_menu.aboutToHide.disconnect(self.on_filter_menu_hide)
            except:
                pass

    def on_filter_menu_hide(self):
        QTimer.singleShot(500, self.reset_filter_menu_state)

    def reset_filter_menu_state(self):
        self.filter_menu_is_open = False

    def on_filter_action_triggered(self):
        if self.filter_tooltip:
            self.filter_tooltip.hide()

    def eventFilter(self, obj, event):
        if obj == self.filter_action_button and self.filter_menu_is_open:
            if event.type() in (QEvent.HoverEnter, QEvent.ToolTip):
                return True

        if self.filter_tooltip and hasattr(self.filter_tooltip, 'getWidget'):
            if obj == self.filter_tooltip.getWidget() and self.filter_menu_is_open:
                if event.type() in (QEvent.HoverEnter, QEvent.ToolTip, QEvent.Show):
                    return True

        return super().eventFilter(obj, event)

    def setShowDelay(self, delay_ms):
        self._show_delay = delay_ms
        if self.filter_tooltip:
            self.filter_tooltip.setShowDelay(delay_ms)

    def setHideDelay(self, delay_ms):
        self._hide_delay = delay_ms
        if self.filter_tooltip:
            self.filter_tooltip.setHideDelay(delay_ms)
            
    def on_application_quit(self):
        if self.filter_tooltip:
            self.filter_tooltip.hide(delay=False)
            
class TooltipManager(QObject):
    _instance = None
    _active_tooltips = set()
    _app_filter_installed = False

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = TooltipManager()
        return cls._instance

    def __init__(self):
        super().__init__()

        if TooltipManager._instance is not None:
            raise RuntimeError("Use TooltipManager.instance() to get the singleton instance")

        if not TooltipManager._app_filter_installed:
            app = QApplication.instance()
            if app:
                app.installEventFilter(self)
                TooltipManager._app_filter_installed = True

    def register_tooltip(self, tooltip):
        TooltipManager._active_tooltips.add(tooltip)
    
    def unregister_tooltip(self, tooltip):
        if tooltip in TooltipManager._active_tooltips:
            TooltipManager._active_tooltips.remove(tooltip)
    
    def hide_all_tooltips(self):
        for tooltip in list(TooltipManager._active_tooltips):
            tooltip.hide(delay=False)
        QToolTip.hideText()
    
    def eventFilter(self, watched, event):
        if event.type() == QEvent.Close and watched == QApplication.instance():
            self.hide_all_tooltips()
        
        return False