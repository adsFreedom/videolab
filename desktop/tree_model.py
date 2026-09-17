"""Модель дерева проекта."""
from pathlib import Path
from typing import Any

from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor
from PySide6.QtCore import Qt

from core.project_manager import ProjectManager
from core.utils import load_yaml


# Иконки для типов обработчиков
PROCESSOR_ICONS = {
    "source": "📼",
    "crop": "✂️",
    "extract_frames": "🖼️",
    "detect_face": "👤",
    "relative_roi": "🎯",
    "fft": "📊",
}

# Цвета
COLOR_VALID = QColor("#6fcf6f")
COLOR_INVALID = QColor("#ff6b6b")
COLOR_DEFAULT = QColor("#d4d4d4")

# Роли для хранения данных
ROLE_PATH = Qt.UserRole + 1


class TreeModel(QStandardItemModel):
    """Модель дерева проекта на основе QStandardItemModel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeaderLabels(["Узел"])
        self.project: ProjectManager | None = None

    def load_project(self, project: ProjectManager) -> None:
        """Загружает дерево проекта."""
        self.project = project
        self.clear()
        self.setHorizontalHeaderLabels(["Узел"])

        tree_data = project.get_tree()

        for child_data in tree_data.get("children", []):
            item = self._create_item(child_data)
            self.appendRow(item)

    def _create_item(self, node_data: dict[str, Any]) -> QStandardItem:
        """Создает QStandardItem из данных узла."""
        item = QStandardItem()

        name = node_data["name"]
        display_name = node_data.get("display_name", name)
        is_valid = node_data.get("is_valid", False)
        path = node_data["path"]

        yaml_path = Path(path) / f"{name}.yaml"
        processor_type = self._get_processor_type(yaml_path)

        icon = PROCESSOR_ICONS.get(processor_type, "📁")

        item.setText(f"{icon} {name}")

        status_text = "✅ Валидный" if is_valid else "❌ Невалидный"
        item.setToolTip(f"{display_name}\nПуть: {path}\nСтатус: {status_text}")

        item.setData(path, ROLE_PATH)

        if not is_valid:
            item.setForeground(COLOR_INVALID)
        else:
            item.setForeground(COLOR_VALID)

        for child_data in node_data.get("children", []):
            child_item = self._create_item(child_data)
            item.appendRow(child_item)

        return item

    def _get_processor_type(self, yaml_path: Path) -> str:
        """Читает тип обработчика из YAML."""
        if not yaml_path.exists():
            return ""
        data = load_yaml(yaml_path)
        return data.get("processor", "")

    def get_path(self, index) -> str:
        """Возвращает путь к узлу по QModelIndex."""
        if not index.isValid():
            return ""
        item = self.itemFromIndex(index)
        return item.data(ROLE_PATH) or ""