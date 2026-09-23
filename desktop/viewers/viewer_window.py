"""Отдельное окно для просмотра файла."""
from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut

from core.logger import log
from desktop.viewers.registry import ViewerRegistry


class ViewerWindow(QMainWindow):
    """Отдельное окно просмотра файла."""

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)

        self.file_path = file_path
        self._viewer: QWidget | None = None

        file_name = Path(file_path).name
        self.setWindowTitle(f"Просмотр: {file_name}")
        self.resize(1200, 800)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        viewer_class = ViewerRegistry.get_viewer_class(file_path)

        if viewer_class is None:
            label = QLabel(f"Нет просмотрщика для файла:\n{file_path}")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #ff6b6b; font-size: 12pt;")
            layout.addWidget(label)
        else:
            try:
                self._viewer = viewer_class()
                self._viewer.load(file_path)
                layout.addWidget(self._viewer)
                log("INFO", f"Открыт просмотрщик {viewer_class.__name__} для {file_name}")
            except Exception as e:
                log("ERROR", f"Ошибка создания просмотрщика: {e}", exc_info=True)
                label = QLabel(f"Ошибка при открытии файла:\n{e}")
                label.setAlignment(Qt.AlignCenter)
                label.setStyleSheet("color: #ff6b6b; font-size: 12pt;")
                layout.addWidget(label)

        self.setCentralWidget(container)

        # Esc — закрыть окно
        QShortcut(
            QKeySequence("Esc"), self, self.close,
            context=Qt.WindowShortcut,
        )

        if self._viewer is not None:
            self._viewer.setFocus()

    def closeEvent(self, event):
        """Освобождаем ресурсы просмотрщика."""
        if self._viewer is not None and hasattr(self._viewer, "cleanup"):
            try:
                self._viewer.cleanup()
            except Exception as e:
                log("ERROR", f"Ошибка при закрытии просмотрщика: {e}")
        super().closeEvent(event)