"""Модель дерева проекта."""
from pathlib import Path
from typing import Any

from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

from core.project import ProjectManager
from core.progress_registry import progress_registry


PROCESSOR_ICONS = {
    "source": "📼",
    "crop": "✂️",
    "extract_frames": "🖼️",
    "detect_face": "👤",
    "relative_roi": "🎯",
    "fft": "📊",
}

# Роли
ROLE_PATH = Qt.UserRole + 1
ROLE_VALID = Qt.UserRole + 2
ROLE_STATE = Qt.UserRole + 3


class TreeModel(QStandardItemModel):
    """Модель дерева проекта. Две колонки: имя, состояние."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeaderLabels(["Узел", "Состояние"])
        self.project: ProjectManager | None = None

    # ==================== ЗАГРУЗКА ====================

    def load_project(self, project: ProjectManager) -> None:
        """Полная загрузка дерева. Используется при открытии проекта / refresh."""
        self.project = project
        self.clear()
        self.setHorizontalHeaderLabels(["Узел", "Состояние"])

        tree_data = project.get_tree()
        validation = project.validate_tree()

        for child_data in tree_data.get("children", []):
            row_items = self._create_row(child_data, validation)
            if row_items:
                self.appendRow(row_items)

    def _create_row(
        self,
        node_data: dict[str, Any],
        validation: dict[str, tuple[bool, str]],
    ) -> list[QStandardItem]:
        """Создает строку из двух элементов: [имя, состояние]."""
        name = node_data["name"]
        display_name = node_data.get("display_name", name)
        path = node_data["path"]
        processor_type = node_data.get("processor", "")

        is_valid, _ = validation.get(path, (False, ""))

        is_processing = progress_registry.get(path) is not None
        state = self._compute_state(is_processing, is_valid)

        # Колонка 0: имя
        name_item = QStandardItem()
        self._apply_name_item(name_item, name, display_name, path,
                              processor_type, is_valid, state)

        # Колонка 1: состояние
        state_item = QStandardItem()
        self._apply_state_item(state_item, path, state)

        # Дети
        for child_data in node_data.get("children", []):
            child_items = self._create_row(child_data, validation)
            if child_items:
                name_item.appendRow(child_items)

        return [name_item, state_item]

    # ==================== ОБНОВЛЕНИЕ ОДНОГО УЗЛА ====================

    def update_node_state(self, node_path: str) -> bool:
        """
        Обновляет только указанный узел: текст, иконку, состояние.
        Возвращает True, если узел найден.
        """
        name_item = self._find_item_by_path(node_path)
        if name_item is None:
            return False

        # Родитель в модели
        parent = name_item.parent()
        if parent is None:
            row = name_item.row()
            state_item = self.item(row, 1)
        else:
            row = name_item.row()
            state_item = parent.child(row, 1)

        if state_item is None:
            return False

        # Достаём данные узла
        node_path_obj = Path(node_path)
        yaml_path = node_path_obj / f"{node_path_obj.name}.yaml"
        from core.utils import load_yaml
        node_data = load_yaml(yaml_path)

        display_name = node_data.get("display_name", node_path_obj.name)
        processor_type = node_data.get("processor", "")
        name = node_path_obj.name

        # Валидность
        is_valid = False
        if self.project:
            is_valid, _ = self.project.validate_node(node_path)

        is_processing = progress_registry.get(node_path) is not None
        state = self._compute_state(is_processing, is_valid)

        # Обновляем оба item'а
        self._apply_name_item(name_item, name, display_name, node_path,
                              processor_type, is_valid, state)
        self._apply_state_item(state_item, node_path, state)

        return True

    # ==================== ВНУТРЕННИЕ ====================

    def _compute_state(self, is_processing: bool, is_valid: bool) -> str:
        """Вычисляет состояние узла."""
        if is_processing:
            return "processing"
        if is_valid:
            return "valid"
        return "invalid"

    def _apply_name_item(
        self,
        item: QStandardItem,
        name: str,
        display_name: str,
        path: str,
        processor_type: str,
        is_valid: bool,
        state: str,
    ) -> None:
        """Заполняет item колонки 0 данными узла."""
        type_icon = PROCESSOR_ICONS.get(processor_type, "📁")

        if state == "processing":
            status_icon = "⏳"
        elif state == "valid":
            status_icon = "✅"
        else:
            status_icon = "❌"

        item.setText(f"{status_icon} {type_icon} {name}")

        status_text = {
            "valid": "Валидный",
            "invalid": "Требуется обработка",
            "processing": "Обработка...",
        }[state]

        item.setToolTip(
            f"{display_name}\nПуть: {path}\nСтатус: {status_text}"
        )
        item.setData(path, ROLE_PATH)
        item.setData(is_valid, ROLE_VALID)
        item.setData(state, ROLE_STATE)

    def _apply_state_item(
        self,
        item: QStandardItem,
        path: str,
        state: str,
    ) -> None:
        """Заполняет item колонки 1."""
        if state == "valid":
            item.setText("✅")
        elif state == "invalid":
            item.setText("❌")
        else:
            item.setText("")  # для processing текст не нужен — рисует делегат

        item.setData(path, ROLE_PATH)
        item.setData(state, ROLE_STATE)

    def _find_item_by_path(self, node_path: str) -> QStandardItem | None:
        """Рекурсивно ищет QStandardItem по ROLE_PATH."""
        for row in range(self.rowCount()):
            index = self.index(row, 0)
            item = self.itemFromIndex(index)
            found = self._find_item_recursive(item, node_path)
            if found is not None:
                return found
        return None

    def _find_item_recursive(
        self, item: QStandardItem, node_path: str
    ) -> QStandardItem | None:
        """Рекурсивный обход детей."""
        if item is None:
            return None
        if item.data(ROLE_PATH) == node_path:
            return item
        for row in range(item.rowCount()):
            child = item.child(row, 0)
            found = self._find_item_recursive(child, node_path)
            if found is not None:
                return found
        return None

    def get_path(self, index) -> str:
        """Возвращает путь к узлу по QModelIndex."""
        if not index.isValid():
            return ""
        item = self.itemFromIndex(index)
        if not item:
            return ""
        return item.data(ROLE_PATH) or ""