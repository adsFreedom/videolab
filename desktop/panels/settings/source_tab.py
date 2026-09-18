"""Вкладка настроек source-узла."""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, QFileDialog,
)
from PySide6.QtCore import Signal

from core.logger import log
from core.utils import load_yaml, save_yaml
from core.project import ProjectManager


class SourceTab(QWidget):
    """Вкладка настроек для source_0."""

    node_updated = Signal(str)  # путь к узлу, который изменился

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project: ProjectManager | None = None
        self.current_node_path: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.info_label = QLabel("(файл не выбран)")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        self.btn_select = QPushButton("Выбрать видео...")
        self.btn_select.clicked.connect(self._on_select_video)
        layout.addWidget(self.btn_select)

        layout.addStretch()

    def set_project(self, project: ProjectManager) -> None:
        self.project = project

    def load_node(self, node_path: str, node_data: dict) -> None:
        """Загружает узел source в форму."""
        self.current_node_path = node_path
        current = node_data.get("input_file") or "(видео не выбрано)"
        self.info_label.setText(f"<b>Текущий файл:</b><br>{current}")

    def _on_select_video(self) -> None:
        if not self.project or not self.current_node_path:
            return

        video_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите видео",
            "", "Video files (*.avi *.mp4 *.mov *.mkv);;All files (*)"
        )
        if not video_path:
            return

        try:
            self.project.register_source_video(self.current_node_path, video_path)
            log("SUCCESS", f"Видео зарегистрировано: {video_path}")
            self.node_updated.emit(self.current_node_path)
            QMessageBox.information(self, "Успех", "Видео добавлено")
        except Exception as e:
            log("ERROR", f"Ошибка добавления видео: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", str(e))