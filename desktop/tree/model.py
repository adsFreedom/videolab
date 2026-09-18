"""Модель дерева проекта."""
from pathlib import Path
from typing import Any

from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

from core.project import ProjectManager


PROCESSOR_ICONS = {
    "source": "📼",
    "crop": "✂️",
    "extract_frames": "🖼️",
    "detect_face": "👤",
    "relative_roi": "🎯",
    "fft": "📊",
}

ROLE_PATH = Qt.UserRole + 1
ROLE_VALID = Qt.UserRole + 2


class TreeModel(QStandardItemModel):
    """Модель дерева проекта."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeaderLabels(["Узел"])
        self.project: ProjectManager | None = None

    def load_project(self, project: ProjectManager) -> None:
        self.project = project
        self.clear()
        self.setHorizontalHeaderLabels(["Узел"])

        tree_data = project.get_tree()
        validation = project.validate_tree()

        for child_data in tree_data.get("children", []):
            item = self._create_item(child_data, validation)
            self.appendRow(item)

    def _create_item(
        self,
        node_data: dict[str, Any],
        validation: dict[str, tuple[bool, str]],
    ) -> QStandardItem:
        item = QStandardItem()

        name = node_data["name"]
        display_name = node_data.get("display_name", name)
        path = node_data["path"]
        processor_type = node_data.get("processor", "")

        is_valid, _ = validation.get(path, (False, ""))

        icon = PROCESSOR_ICONS.get(processor_type, "📁")
        status_icon = "✅" if is_valid else "❌"

        item.setText(f"{icon} {name}  {status_icon}")

        status_text = "Валидный" if is_valid else "Требуется обработка"
        item.setToolTip(f"{display_name}\nПуть: {path}\nСтатус: {status_text}")

        item.setData(path, ROLE_PATH)
        item.setData(is_valid, ROLE_VALID)

        for child_data in node_data.get("children", []):
            child_item = self._create_item(child_data, validation)
            item.appendRow(child_item)

        return item

    def get_path(self, index) -> str:
        if not index.isValid():
            return ""
        item = self.itemFromIndex(index)
        return item.data(ROLE_PATH) or ""