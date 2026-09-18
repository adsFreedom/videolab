"""Панель дерева проекта."""
from pathlib import Path
import subprocess
import sys
import traceback

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QLabel,
    QPushButton, QMenu, QMessageBox, QStyle,
    QApplication, QDialog, QTextEdit, QDialogButtonBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from core.logger import log
from core.project_manager import ProjectManager
from core.processor_registry import ProcessorRegistry
from core.utils import load_yaml
from desktop.tree_model import TreeModel, ROLE_PATH, ROLE_VALID
from desktop.dialogs.processor_dialog import ProcessorChooserDialog


class TreePanel(QWidget):
    """Панель дерева проекта."""

    node_selected = Signal(str)
    tree_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project: ProjectManager | None = None

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

        is_valid = item.data(ROLE_VALID)

        node_path_obj = Path(node_path)
        yaml_path = node_path_obj / f"{node_path_obj.name}.yaml"
        node_data = load_yaml(yaml_path)
        processor_type = node_data.get("processor", "")

        menu = QMenu(self)

        if not is_valid and processor_type != "source":
            rescan_action = QAction("Пересчитать", self)
            rescan_action.triggered.connect(
                lambda: self._on_rescan(node_path)
            )
            menu.addAction(rescan_action)
            menu.addSeparator()

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

    # ==================== ДЕЙСТВИЯ ====================

    def _on_rescan(self, node_path: str) -> None:
        if not self.project:
            return

        node_data = load_yaml(Path(node_path) / f"{Path(node_path).name}.yaml")
        processor_name = node_data.get("processor", "")
        try:
            processor_class = ProcessorRegistry.get(processor_name)
        except KeyError:
            log("ERROR", f"Обработчик '{processor_name}' не зарегистрирован")
            return

        log("INFO", f"Пересчёт узла: {node_path}")
        self._run_with_progress(node_path, processor_class)

    def _on_add_processor(self, node_path: str) -> None:
        if not self.project:
            return

        available = self.project.get_available_processors(node_path)

        if not available:
            QMessageBox.information(
                self, "Обработчики",
                "Нет доступных обработчиков для этого узла.\n\n"
                "Возможно, отсутствуют подходящие входные файлы."
            )
            log("WARNING", f"Для узла {node_path} нет доступных обработчиков")
            return

        dialog = ProcessorChooserDialog(
            project=self.project,
            node_path=node_path,
            processors=available,
            parent=self,
        )

        if dialog.exec() != ProcessorChooserDialog.Accepted:
            return

        processor_name = dialog.result_processor_name
        action = dialog.result_action

        log("INFO", f"Создание обработчика '{processor_name}' для узла {node_path}")

        try:
            new_node_path = self.project.create_processor_node(
                parent_path=node_path,
                processor_name=processor_name,
                input_files=dialog.result_input_files,
                settings=dialog.result_settings,
            )

            processor_class = ProcessorRegistry.get(processor_name)

            if action == ProcessorChooserDialog.ACTION_ADD_AND_RUN:
                self._run_with_progress(new_node_path, processor_class)
                QMessageBox.information(
                    self, "Готово",
                    f"Обработчик создан:\n{new_node_path}"
                )
            else:
                log("SUCCESS", f"Обработчик создан (без обработки): {new_node_path}")
                self.refresh()
                QMessageBox.information(
                    self, "Готово",
                    f"Обработчик создан:\n{new_node_path}\n\n"
                    f"Не забудьте запустить обработку."
                )
        except Exception as e:
            error_msg = f"Ошибка обработчика '{processor_name}': {e}"
            log("ERROR", error_msg, exc_info=True)
            self._show_error_dialog("Ошибка обработки", error_msg)

    def _run_with_progress(self, node_path: str, processor_class: type) -> None:
        """Запускает обработку с модальным прогресс-диалогом."""
        from desktop.dialogs.progress_dialog import ProgressDialog
        from core.execution import ExecutionContext

        node_name = Path(node_path).name
        title = f"{processor_class.icon} {processor_class.display_name}"

        context = ExecutionContext()
        dialog = ProgressDialog(node_name, title, context, parent=self)
        dialog.show()

        QApplication.processEvents()

        try:
            result = self.project.run_node(node_path, context=context)
            dialog.accept()

            if result.get("cancelled"):
                log("WARNING", f"Обработка отменена: {node_path}")
                QMessageBox.information(
                    self, "Отменено",
                    "Обработка была отменена пользователем."
                )
            else:
                self.refresh()
                log("SUCCESS", f"Узел обработан: {node_path}")
        except Exception as e:
            dialog.accept()
            error_msg = f"Ошибка обработки '{node_name}': {e}"
            log("ERROR", error_msg, exc_info=True)
            self._show_error_dialog("Ошибка обработки", error_msg)

    def _show_error_dialog(self, title: str, message: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(750, 450)

        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        full_text = message
        tb = traceback.format_exc()
        if tb and tb.strip() != "NoneType: None":
            full_text = f"{message}\n\n{tb}"

        text_edit.setPlainText(full_text)
        text_edit.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        layout.addWidget(text_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.exec()

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
        if not self.project:
            return

        descendants = self.project.get_descendants(node_path)

        if descendants:
            preview_lines = []
            for d in descendants[:10]:
                preview_lines.append(f"  • {Path(d).name}")
            if len(descendants) > 10:
                preview_lines.append(f"  ... и ещё {len(descendants) - 10}")

            msg = (
                f"Удалить узел «{Path(node_path).name}» и все его результаты?\n\n"
                f"Будут удалены следующие узлы:\n" + "\n".join(preview_lines)
            )
        else:
            msg = f"Удалить узел «{Path(node_path).name}»?"

        reply = QMessageBox.question(
            self, "Удаление узла", msg,
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            self.project.delete_node(node_path)
            self.refresh()
            log("INFO", f"Узел удален: {node_path}")
        except Exception as e:
            log("ERROR", f"Ошибка удаления узла: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", str(e))