"""Тулбар главного окна."""
from PySide6.QtWidgets import QToolBar
from PySide6.QtGui import QAction


class MainToolbar(QToolBar):
    """Тулбар с основными действиями."""

    def __init__(self, main_window):
        super().__init__("Основные действия", main_window)
        self.main_window = main_window

        self.setMovable(False)

        open_action = QAction("Открыть проект", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(main_window.project_actions.open_project)
        self.addAction(open_action)

        create_action = QAction("Создать проект", self)
        create_action.setShortcut("Ctrl+N")
        create_action.triggered.connect(main_window.project_actions.create_project)
        self.addAction(create_action)

        self.addSeparator()

        record_action = QAction("Записать", self)
        record_action.setShortcut("Ctrl+R")
        record_action.triggered.connect(main_window.on_record_video)
        self.addAction(record_action)

        self.addSeparator()

        refresh_action = QAction("Обновить", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(main_window.on_refresh)
        self.addAction(refresh_action)

        self.addSeparator()

        close_action = QAction("Закрыть проект", self)
        close_action.setShortcut("Ctrl+W")
        close_action.triggered.connect(main_window.project_actions.close_project)
        self.addAction(close_action)