"""Модель дерева проекта."""
from pathlib import Path
from typing import Any

from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

from core.project import ProjectManager
from core.progress_registry import progress_registry
from core.utils import load_yaml


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
ROLE_STATE = Qt.UserRole + 3


class TreeModel(QStandardItemModel):
    """Модель дерева проекта. Одна колонка: имя + состояние."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeaderLabels(["Узел"])
        self.project: ProjectManager | None = None

    # ==================== ЗАГРУЗКА ====================

    def load_project(self, project: ProjectManager) -> None:
        self.project = project
        self.clear()
        self.setHorizontalHeaderLabels(["Узел"])

        tree_data = project.get_tree()
        validation = project.validate_tree()

        for child_data in tree_data.get("children", []):
            item = self._create_item(child_data, validation)
            if item:
                self.appendRow(item)

    def _create_item(
        self,
        node_data: dict[str, Any],
        validation: dict[str, tuple[bool, str]],
    ) -> QStandardItem:
        name = node_data["name"]
        display_name = node_data.get("display_name", name)
        path = node_data["path"]
        processor_type = node_data.get("processor", "")

        is_valid, _ = validation.get(path, (False, ""))
        is_processing = progress_registry.get(path) is not None
        state = self._compute_state(is_processing, is_valid)

        item = QStandardItem()
        self._apply_item(item, name, display_name, path,
                         processor_type, is_valid, state)

        for child_data in node_data.get("children", []):
            child_item = self._create_item(child_data, validation)
            if child_item:
                item.appendRow(child_item)

        return item

    # ==================== ОБНОВЛЕНИЕ УЗЛА ====================

    def update_node_state(self, node_path: str) -> bool:
        """Обновляет только указанный узел."""
        item = self._find_item_by_path(node_path)
        if item is None:
            return False

        is_valid = False
        if self.project:
            is_valid, _ = self.project.validate_node(node_path)

        is_processing = progress_registry.get(node_path) is not None
        state = self._compute_state(is_processing, is_valid)

        self._apply_item_from_node_data(item, node_path, is_valid, state)
        return True

    def update_node_and_descendants(self, node_path: str) -> bool:
        """
        Обновляет узел и всех потомков.
        Валидация — через validate_subtree (каскад сверху вниз в ядре).
        """
        item = self._find_item_by_path(node_path)
        if item is None:
            return False

        # Один вызов — получаем валидность всей ветки
        if self.project:
            validation = self.project.validate_subtree(node_path)
        else:
            validation = {}

        # Обновляем сам узел
        self._apply_validation(item, node_path, validation)

        # Обновляем всех потомков
        self._update_descendants_from_validation(item, validation)

        return True

    # ==================== ВНУТРЕННИЕ ====================

    def _update_descendants_from_validation(
        self,
        parent_item: QStandardItem,
        validation: dict[str, tuple[bool, str]],
    ) -> None:
        """Обходит всё поддерево и обновляет по готовому validation-словарю."""
        for row in range(parent_item.rowCount()):
            child = parent_item.child(row, 0)
            if child is None:
                continue
            child_path = child.data(ROLE_PATH)
            if child_path:
                self._apply_validation(child, child_path, validation)
            self._update_descendants_from_validation(child, validation)

    def _apply_validation(
        self,
        item: QStandardItem,
        node_path: str,
        validation: dict[str, tuple[bool, str]],
    ) -> None:
        """Применяет результат валидации к item."""
        is_valid, _ = validation.get(node_path, (False, ""))
        is_processing = progress_registry.get(node_path) is not None
        state = self._compute_state(is_processing, is_valid)
        self._apply_item_from_node_data(item, node_path, is_valid, state)

    def _apply_item_from_node_data(
        self,
        item: QStandardItem,
        node_path: str,
        is_valid: bool,
        state: str,
    ) -> None:
        """Достаёт данные из YAML и вызывает _apply_item."""
        node_path_obj = Path(node_path)
        yaml_path = node_path_obj / f"{node_path_obj.name}.yaml"
        node_data = load_yaml(yaml_path)

        display_name = node_data.get("display_name", node_path_obj.name)
        processor_type = node_data.get("processor", "")
        name = node_path_obj.name

        self._apply_item(item, name, display_name, node_path,
                         processor_type, is_valid, state)

    def _compute_state(self, is_processing: bool, is_valid: bool) -> str:
        if is_processing:
            return "processing"
        if is_valid:
            return "valid"
        return "invalid"

    def _apply_item(
        self,
        item: QStandardItem,
        name: str,
        display_name: str,
        path: str,
        processor_type: str,
        is_valid: bool,
        state: str,
    ) -> None:
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

        item.setToolTip(f"{display_name}\nПуть: {path}\nСтатус: {status_text}")
        item.setData(path, ROLE_PATH)
        item.setData(is_valid, ROLE_VALID)
        item.setData(state, ROLE_STATE)

    def _find_item_by_path(self, node_path: str) -> QStandardItem | None:
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
        if not index.isValid():
            return ""
        item = self.itemFromIndex(index)
        if not item:
            return ""
        return item.data(ROLE_PATH) or ""