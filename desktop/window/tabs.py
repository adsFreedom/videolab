"""Управление главными табами и индикацией лога."""
from PySide6.QtWidgets import QTabWidget
from PySide6.QtCore import Qt


class MainTabs(QTabWidget):
    """Главный QTabWidget с индикацией ошибок в табе 'Лог'."""

    LOG_TAB_INDEX = 1

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window

        self.setTabPosition(QTabWidget.North)
        self.setMovable(False)

        self.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int) -> None:
        """Сбрасывает индикацию ошибок при переходе на таб лога."""
        if index == self.LOG_TAB_INDEX:
            self.main_window.log_panel.mark_as_read()
            self.update_log_indicator()

    def update_log_indicator(self) -> None:
        """Обновляет цвет/текст таба лога."""
        log_panel = self.main_window.log_panel

        if log_panel.has_unread_errors():
            self.setTabText(self.LOG_TAB_INDEX, "Лог (ошибки)")
            self.tabBar().setTabTextColor(self.LOG_TAB_INDEX, Qt.red)
        elif log_panel.has_unread_warnings():
            self.setTabText(self.LOG_TAB_INDEX, "Лог (предупреждения)")
            self.tabBar().setTabTextColor(self.LOG_TAB_INDEX, Qt.yellow)
        else:
            self.setTabText(self.LOG_TAB_INDEX, "Лог")
            self.tabBar().setTabTextColor(self.LOG_TAB_INDEX, Qt.white)