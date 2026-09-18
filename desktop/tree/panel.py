"""Панель дерева проекта."""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QLabel,
    QPushButton, QStyle, QApplication,
)
from PySide6.QtCore import Qt, Signal

from core.project import ProjectManager
from desktop.tree.model import TreeModel, ROLE_PATH
from desktop.tree.actions import TreeActions
from desktop.tree import context_menu


class TreePanel(QWidget):
    """Панель дерева проекта."""

    node_selected = Signal(str)
    tree_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project: ProjectManager | None = None
        self.actions = TreeActions(self)

        # Ссылки для активных потоков (используются в actions)
        self._current_thread = None
        self._current_worker = None
        self._current_dialog = None
        self._current_context = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QLabel("Дерево проекта")
        header.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(header)

        # --- Кнопки управления ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        style = QApplication.style()

        self.btn_refresh = QPushButton()
        self.btn_refresh.setIcon(style.standardIcon(QStyle.SP_BrowserReload))
        self.btn_refresh.setToolTip("Обновить дерево")
        self.btn_refresh.setFixedWidth(32)
        self.btn_refresh.clicked.connect(self.refresh)
        btn_layout.addWidget(self.btn_refresh)

        self.btn_expand = QPushButton()
        self.btn_expand.setIcon(style.standardIcon(QStyle.SP_ArrowDown))
        self.btn_expand.setToolTip("Развернуть всё")
        self.btn_expand.setFixedWidth(32)
        self.btn_expand.clicked.connect(lambda: self.tree_view.expandAll())
        btn_layout.addWidget(self.btn_expand)

        self.btn_collapse = QPushButton()
        self.btn_collapse.setIcon(style.standardIcon(QStyle.SP_ArrowUp))
        self.btn_collapse.setToolTip("Свернуть всё")
        self.btn_collapse.setFixedWidth(32)
        self.btn_collapse.clicked.connect(lambda: self.tree_view.collapseAll())
        btn_layout.addWidget(self.btn_collapse)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- Дерево ---
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)

        self.tree_view.setIndentation(16)
        self.tree_view.setRootIsDecorated(True)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.setAnimated(True)
        self.tree_view.setExpandsOnDoubleClick(True)
        self.tree_view.setEditTriggers(QTreeView.NoEditTriggers)
        self.tree_view.setSelectionMode(QTreeView.SingleSelection)
        self.tree_view.setAllColumnsShowFocus(True)

        self.model = TreeModel(self)
        self.tree_view.setModel(self.model)

        self.tree_view.customContextMenuRequested.connect(self._on_context_menu)
        self.tree_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )

        layout.addWidget(self.tree_view)

    # ==================== API ====================

    def load_project(self, project: ProjectManager) -> None:
        self.project = project
        self.model.load_project(project)
        self.tree_view.expandAll()

    def refresh(self) -> None:
        if not self.project:
            return
        current_path = self.get_selected_path()
        self.model.load_project(self.project)
        self.tree_view.expandAll()
        if current_path and Path(current_path).exists():
            self._select_by_path(current_path)
        self.tree_changed.emit()

    def get_selected_path(self) -> str:
        index = self.tree_view.currentIndex()
        if not index.isValid():
            return ""
        item = self.model.itemFromIndex(index)
        return item.data(ROLE_PATH) or ""

    # ==================== ВНУТРЕННИЕ ====================

    def _select_by_path(self, path: str) -> None:
        for row in range(self.model.rowCount()):
            index = self.model.index(row, 0)
            found = self._find_index(index, path)
            if found:
                self.tree_view.setCurrentIndex(found)
                return

    def _find_index(self, index, path: str):
        if not index.isValid():
            return None
        item = self.model.itemFromIndex(index)
        if item.data(ROLE_PATH) == path:
            return index
        for row in range(self.model.rowCount(index)):
            child = self.model.index(row, 0, index)
            result = self._find_index(child, path)
            if result:
                return result
        return None

    # ==================== СОБЫТИЯ ====================

    def _on_selection_changed(self, selected, deselected) -> None:
        indexes = selected.indexes()
        if not indexes:
            return
        index = indexes[0]
        item = self.model.itemFromIndex(index)
        path = item.data(ROLE_PATH) or ""
        if path:
            self.node_selected.emit(path)

    def _on_context_menu(self, pos) -> None:
        context_menu.build_context_menu(self, pos)