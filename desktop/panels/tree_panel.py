"""Панель дерева проекта."""
from pathlib import Path
import shutil
import subprocess
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QLabel,
    QPushButton, QMenu, QMessageBox, QFileDialog, QStyle,
    QApplication,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from core.project_manager import ProjectManager
from core.utils import load_yaml
from desktop.tree_model import TreeModel, ROLE_PATH


class TreePanel(QWidget):
    """Панель дерева проекта."""

    node_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project: ProjectManager | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # --- Заголовок ---
        header = QLabel("Дерево проекта")
        header.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(header)

        # --- Кнопки управления ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        style = QApplication.style()

        # Кнопка "Обновить" — стандартная иконка Qt
        self.btn_refresh = QPushButton()
        self.btn_refresh.setIcon(style.standardIcon(QStyle.SP_BrowserReload))
        self.btn_refresh.setToolTip("Обновить дерево")
        self.btn_refresh.setFixedWidth(32)
        self.btn_refresh.clicked.connect(self.refresh)
        btn_layout.addWidget(self.btn_refresh)

        # Кнопка "Развернуть всё" — стрелка вниз
        self.btn_expand = QPushButton()
        self.btn_expand.setIcon(style.standardIcon(QStyle.SP_ArrowDown))
        self.btn_expand.setToolTip("Развернуть всё")
        self.btn_expand.setFixedWidth(32)
        self.btn_expand.clicked.connect(lambda: self.tree_view.expandAll())
        btn_layout.addWidget(self.btn_expand)

        # Кнопка "Свернуть всё" — стрелка вверх
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

        # Визуальные настройки
        self.tree_view.setIndentation(16)
        self.tree_view.setRootIsDecorated(True)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.setAnimated(True)
        self.tree_view.setExpandsOnDoubleClick(True)
        self.tree_view.setEditTriggers(QTreeView.NoEditTriggers)
        self.tree_view.setSelectionMode(QTreeView.SingleSelection)
        self.tree_view.setAllColumnsShowFocus(True)

        # Модель ДО сигналов
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
        self.model.load_project(self.project)
        self.tree_view.expandAll()

    def get_selected_path(self) -> str:
        index = self.tree_view.currentIndex()
        if not index.isValid():
            return ""
        item = self.model.itemFromIndex(index)
        return item.data(ROLE_PATH) or ""

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
        index = self.tree_view.indexAt(pos)
        if not index.isValid():
            return

        item = self.model.itemFromIndex(index)
        node_path = item.data(ROLE_PATH) or ""
        if not node_path:
            return

        node_path_obj = Path(node_path)
        yaml_path = node_path_obj / f"{node_path_obj.name}.yaml"
        node_data = load_yaml(yaml_path)
        processor_type = node_data.get("processor", "")

        menu = QMenu(self)

        header_action = QAction(f"{item.text()}", self)
        header_action.setEnabled(False)
        menu.addAction(header_action)
        menu.addSeparator()

        if processor_type == "source":
            add_video_action = QAction("Добавить видео", self)
            add_video_action.triggered.connect(
                lambda: self._on_add_video(node_path)
            )
            menu.addAction(add_video_action)
            menu.addSeparator()
        else:
            add_processor_action = QAction("Добавить обработчик", self)
            add_processor_action.triggered.connect(
                lambda: self._on_add_processor(node_path)
            )
            menu.addAction(add_processor_action)
            menu.addSeparator()

        open_folder_action = QAction("Открыть в проводнике", self)
        open_folder_action.triggered.connect(
            lambda: self._open_in_explorer(node_path)
        )
        menu.addAction(open_folder_action)

        if processor_type != "source":
            delete_action = QAction("Удалить узел", self)
            delete_action.triggered.connect(
                lambda: self._on_delete_node(node_path)
            )
            menu.addAction(delete_action)

        menu.exec(self.tree_view.mapToGlobal(pos))

    def _on_add_processor(self, node_path: str) -> None:
        if not self.project:
            return
        available = self.project.get_available_processors(node_path)
        names = [p.display_name for p in available]
        if not names:
            QMessageBox.information(
                self, "Обработчики",
                "Нет доступных обработчиков для этого узла."
            )
            return
        QMessageBox.information(
            self, "Доступные обработчики",
            "Для узла доступно:\n\n" + "\n".join(f"• {n}" for n in names)
        )

    def _on_add_video(self, source_path: str) -> None:
        video_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите видео",
            "", "Video files (*.avi *.mp4 *.mov *.mkv);;All files (*)"
        )
        if not video_path:
            return
        try:
            self.project.register_source_video(source_path, video_path)
            self.refresh()
            QMessageBox.information(self, "Успех", "Видео добавлено")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _open_in_explorer(self, node_path: str) -> None:
        path = Path(node_path)
        if not path.exists():
            QMessageBox.warning(self, "Ошибка", "Папка не существует")
            return
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _on_delete_node(self, node_path: str) -> None:
        reply = QMessageBox.question(
            self, "Удаление узла",
            f"Удалить узел и все его результаты?\n\n{node_path}",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            shutil.rmtree(node_path)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))