"""Панель файлов с навигацией по подпапкам."""
from pathlib import Path
import subprocess
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMenu, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction, QColor

from core.utils import load_yaml
from desktop.file_utils import get_file_icon, format_size


class FilesPanel(QWidget):
    """Панель файлов с навигацией по подпапкам."""

    file_double_clicked = Signal(str)         # открыть файл
    folder_entered = Signal(str)              # зашли в папку (обновить статус)
    node_entered = Signal(str)                # зашли в папку-узел (показать настройки)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Корень навигации — сбрасывается при выборе узла в дереве
        self.nav_root: str = ""
        # Текущая папка
        self.current_path: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Заголовок
        self.header_label = QLabel("Файлы")
        self.header_label.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(self.header_label)

        # Путь
        self.path_label = QLabel("")
        self.path_label.setStyleSheet(
            "color: #808080; font-family: Consolas; font-size: 8pt; padding: 0 4px;"
        )
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)

        # Фильтр
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Фильтр по имени...")
        self.filter_input.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_input)

        # Список
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(24, 24))
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget, stretch=1)

        # Инфо
        self.info_label = QLabel("Файлов: 0")
        self.info_label.setStyleSheet("color: #808080; padding: 2px;")
        layout.addWidget(self.info_label)

    # ==================== API ====================

    def load_path(self, path: str) -> None:
        """
        Открывает папку узла (из дерева или из списка).
        Навигация начинается с этой папки (nav_root = path).
        """
        self.nav_root = path
        self.current_path = path
        self._load_current()

    def refresh(self) -> None:
        if self.current_path:
            self._load_current()

    def clear(self) -> None:
        self.nav_root = ""
        self.current_path = ""
        self.header_label.setText("Файлы")
        self.path_label.setText("")
        self.list_widget.clear()
        self.info_label.setText("Файлов: 0")

    # ==================== ВНУТРЕННИЕ ====================

    def _load_current(self) -> None:
        """Загружает содержимое текущей папки."""
        self.filter_input.clear()
        self.list_widget.clear()

        path_obj = Path(self.current_path)
        if not path_obj.exists() or not path_obj.is_dir():
            self.header_label.setText("Файлы")
            self.info_label.setText("Папка не найдена")
            return

        # Заголовок
        yaml_path = path_obj / f"{path_obj.name}.yaml"
        node_data = load_yaml(yaml_path)
        display_name = node_data.get("display_name", "")
        if display_name:
            self.header_label.setText(f"Файлы: {path_obj.name} ({display_name})")
        else:
            self.header_label.setText(f"Файлы: {path_obj.name}")

        # Путь относительно корня навигации
        nav_root_obj = Path(self.nav_root)
        try:
            rel = path_obj.relative_to(nav_root_obj)
            rel_str = str(rel) if str(rel) != "." else "/"
        except ValueError:
            rel_str = str(path_obj)
        self.path_label.setText(f"Путь: {rel_str}")

        # ===== Строка ".." — ВСЕГДА =====
        up_item = QListWidgetItem()
        up_item.setText("📁 ..")
        up_item.setData(Qt.UserRole, str(path_obj.parent))
        up_item.setData(Qt.UserRole + 1, "up")

        font = up_item.font()
        font.setBold(True)
        up_item.setFont(font)
        up_item.setForeground(QColor("#ffcc00"))
        up_item.setToolTip("Перейти на уровень выше")

        self.list_widget.addItem(up_item)

        # ===== Содержимое папки =====
        try:
            entries = sorted(
                path_obj.iterdir(),
                key=lambda p: (p.is_file(), p.name.lower()),
            )
        except PermissionError:
            entries = []

        for entry in entries:
            # Пропускаем YAML самого узла
            if entry.is_file() and entry.name == f"{path_obj.name}.yaml":
                continue

            if entry.is_dir():
                self._add_folder_item(entry)
            else:
                self._add_file_item(entry)

        self._update_info()

    def _add_folder_item(self, path: Path) -> None:
        """Добавляет подпапку."""
        item = QListWidgetItem()

        # Узел (есть YAML) или обычная папка
        is_node = (path / f"{path.name}.yaml").exists()

        item.setText(f"📁 {path.name}/")
        if is_node:
            item.setForeground(QColor("#6fcf6f"))
        else:
            item.setForeground(QColor("#d4d4d4"))

        font = item.font()
        font.setBold(True)
        item.setFont(font)

        item.setData(Qt.UserRole, str(path))
        item.setData(Qt.UserRole + 1, "node" if is_node else "folder")
        item.setToolTip(str(path))

        self.list_widget.addItem(item)

    def _add_file_item(self, path: Path) -> None:
        """Добавляет файл."""
        item = QListWidgetItem()

        icon = get_file_icon(path.name)
        try:
            size = format_size(path.stat().st_size)
        except OSError:
            size = "?"
        item.setText(f"{icon} {path.name}    ({size})")

        item.setData(Qt.UserRole, str(path))
        item.setData(Qt.UserRole + 1, "file")
        item.setToolTip(str(path))

        self.list_widget.addItem(item)

    def _update_info(self) -> None:
        count = self.list_widget.count()
        # Минус 1 — не считаем ".."
        self.info_label.setText(f"Элементов: {max(0, count - 1)}")

    def _apply_filter(self, text: str) -> None:
        text = text.strip().lower()
        visible_count = 0
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole + 1) == "up":
                item.setHidden(False)
                visible_count += 1
                continue
            if not text or text in item.text().lower():
                item.setHidden(False)
                visible_count += 1
            else:
                item.setHidden(True)
        self.info_label.setText(
            f"Показано: {visible_count} из {self.list_widget.count()}"
        )

    # ==================== СОБЫТИЯ ====================

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole + 1)

        if item_type == "up":
            # Переход вверх
            self.current_path = path
            self._load_current()
            # Если зашли в папку-узел — показываем настройки
            if (Path(self.current_path) / f"{Path(self.current_path).name}.yaml").exists():
                self.node_entered.emit(self.current_path)
            return

        if item_type in ("folder", "node"):
            self.current_path = path
            self._load_current()
            # Если узел — показать настройки
            if item_type == "node":
                self.node_entered.emit(path)
        else:
            self.file_double_clicked.emit(path)

    def _on_context_menu(self, pos) -> None:
        item = self.list_widget.itemAt(pos)
        if not item:
            return

        path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole + 1)

        if item_type == "up":
            return

        menu = QMenu(self)

        if item_type == "file":
            open_action = QAction("Открыть", self)
            open_action.triggered.connect(
                lambda: self.file_double_clicked.emit(path)
            )
            menu.addAction(open_action)

            open_folder_action = QAction("Открыть в проводнике", self)
            open_folder_action.triggered.connect(
                lambda: self._open_in_explorer(path)
            )
            menu.addAction(open_folder_action)

            menu.addSeparator()

            copy_path_action = QAction("Копировать путь", self)
            copy_path_action.triggered.connect(
                lambda: self._copy_to_clipboard(path)
            )
            menu.addAction(copy_path_action)

            menu.addSeparator()

            delete_action = QAction("Удалить файл", self)
            delete_action.triggered.connect(
                lambda: self._delete_file(path)
            )
            menu.addAction(delete_action)
        else:
            open_action = QAction("Открыть папку", self)
            open_action.triggered.connect(
                lambda: self._enter_folder(path, item_type)
            )
            menu.addAction(open_action)

            if item_type == "node":
                open_node_action = QAction("Показать настройки", self)
                open_node_action.triggered.connect(
                    lambda: self.node_entered.emit(path)
                )
                menu.addAction(open_node_action)

            open_folder_action = QAction("Открыть в проводнике", self)
            open_folder_action.triggered.connect(
                lambda: self._open_in_explorer(path)
            )
            menu.addAction(open_folder_action)

            menu.addSeparator()

            copy_path_action = QAction("Копировать путь", self)
            copy_path_action.triggered.connect(
                lambda: self._copy_to_clipboard(path)
            )
            menu.addAction(copy_path_action)

        menu.exec(self.list_widget.mapToGlobal(pos))

    def _enter_folder(self, path: str, item_type: str) -> None:
        self.current_path = path
        self._load_current()
        if item_type == "node":
            self.node_entered.emit(path)

    def _open_in_explorer(self, path: str) -> None:
        path_obj = Path(path)
        if not path_obj.exists():
            QMessageBox.warning(self, "Ошибка", "Путь не существует")
            return

        if sys.platform == "win32":
            if path_obj.is_file():
                subprocess.Popen(["explorer", "/select,", str(path_obj)])
            else:
                subprocess.Popen(["explorer", str(path_obj)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(path_obj)])
        else:
            target = path_obj.parent if path_obj.is_file() else path_obj
            subprocess.Popen(["xdg-open", str(target)])

    def _copy_to_clipboard(self, text: str) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def _delete_file(self, path: str) -> None:
        reply = QMessageBox.question(
            self, "Удаление файла",
            f"Удалить файл?\n\n{path}",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            Path(path).unlink()
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))