"""Сохранение/восстановление состояния окна."""
from pathlib import Path

from PySide6.QtCore import QSettings

from core.project import ProjectManager


class WindowState:
    """Управляет QSettings: геометрия, сплиттеры, последний проект."""

    def __init__(self, main_window):
        self.main_window = main_window
        self.settings = QSettings("VideoLab", "VideoLab")

    def restore(self) -> None:
        """Восстанавливает состояние."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.main_window.restoreGeometry(geometry)

        main_sizes = self.settings.value("main_splitter_sizes")
        if main_sizes:
            self.main_window.main_splitter.setSizes([int(x) for x in main_sizes])

        # Автозагрузка последнего проекта
        last_project = self.settings.value("last_project_path", "")
        if last_project and Path(last_project).exists():
            try:
                project = ProjectManager(last_project)
                self.main_window.set_project(project)
                self.main_window.log(
                    "INFO", f"Автозагрузка проекта: {last_project}"
                )
            except Exception as e:
                self.main_window.log(
                    "WARNING", f"Не удалось загрузить последний проект: {e}"
                )

    def save(self) -> None:
        """Сохраняет состояние."""
        self.settings.setValue("geometry", self.main_window.saveGeometry())
        self.settings.setValue(
            "main_splitter_sizes",
            self.main_window.main_splitter.sizes(),
        )

        if self.main_window.project:
            self.settings.setValue(
                "last_project_path",
                str(self.main_window.project.project_root),
            )
        else:
            self.settings.remove("last_project_path")