"""Действия с проектом: открыть, создать, закрыть."""
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QInputDialog

from core.project import ProjectManager


class ProjectActions:
    """Логика открытия, создания, закрытия проекта. Не UI — только действия."""

    def __init__(self, main_window):
        self.main_window = main_window

    # ==================== ОТКРЫТЬ ====================

    def open_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self.main_window, "Выберите папку проекта", str(Path.home())
        )
        if not folder:
            return
        try:
            project = ProjectManager(folder)
            self.main_window.set_project(project)
        except ValueError as e:
            QMessageBox.warning(self.main_window, "Ошибка", str(e))
            self.main_window.log("ERROR", str(e))

    # ==================== СОЗДАТЬ ====================

    def create_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self.main_window, "Выберите папку для нового проекта",
            str(Path.home())
        )
        if not folder:
            return

        name, ok = QInputDialog.getText(
            self.main_window, "Новый проект", "Имя проекта:"
        )
        if not ok or not name.strip():
            return

        try:
            project_dir = Path(folder) / name.strip()
            project = ProjectManager.create_project(project_dir, name.strip())
            self.main_window.set_project(project)
            self.main_window.log("SUCCESS", f"Создан проект: {project_dir}")
        except Exception as e:
            QMessageBox.critical(self.main_window, "Ошибка", str(e))
            self.main_window.log("ERROR", f"Не удалось создать проект: {e}")

    # ==================== ЗАКРЫТЬ ====================

    def close_project(self) -> None:
        if not self.main_window.project:
            return
        reply = QMessageBox.question(
            self.main_window, "Закрытие проекта",
            "Закрыть текущий проект?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.main_window.clear_project()