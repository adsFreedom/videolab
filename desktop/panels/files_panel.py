"""Панель файлов текущего узла."""
from pathlib import Path
import subprocess
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMenu, QMessageBox,
    QSplitter, QFrame,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction, QColor, QFont

from core.utils import load_yaml
from desktop.file_utils import (
    get_file_icon, get_file_category, format_size,
)


class FilesPanel(QWidget):
    """Панель файлов и превью."""

    file_double_clicked = Signal(str)  # Абсолютный путь к файлу
    node_double_clicked = Signal(str)  # Абсолютный путь к папке-узлу

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_path: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # --- Заголовок ---
        self.header_label = QLabel("Файлы")
        self.header_label.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(self.header_label)

        # --- Фильтр ---
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Фильтр по имени...")
        self.filter_input.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_input)

        # --- Список файлов ---
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(24, 24))
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._on_context_menu)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget, stretch=1)

        # --- Информационная строка ---
        self.info_label = QLabel("Файлов: 0")
        self.info_label.setStyleSheet("color: #808080; padding: 2px;")
        layout.addWidget(self.info_label)

    # ==================== API ====================

    def load_path(self, path: str) -> None:
        """Загружает список файлов из указанной папки."""
        self.current_path = path
        self.filter_input.clear()
        self.list_widget.clear()

        path_obj = Path(path)
        if not path_obj.exists() or not path_obj.is_dir():
            self.header_label.setText("Файлы")
            self.info_label.setText("Папка не найдена")
            return

        # Читаем YAML узла для отображения типа обработчика
        yaml_path = path_obj / f"{path_obj.name}.yaml"
        node_data = load_yaml(yaml_path)
        processor_type = node_data.get("processor", "")
        display_name = node_data.get("display_name", path_obj.name)

        self.header_label.setText(
            f"Файлы: {path_obj.name}"
            + (f" ({display_name})" if display_name else "")
        )

        # Собираем элементы (папки сначала, потом файлы)
        items = []

        # Подпапки-узлы (у которых есть свой YAML)
        for child in sorted(path_obj.iterdir()):
            if child.is_dir():
                child_yaml = child / f"{child.name}.yaml"
                if child_yaml.exists():
                    items.append(("node", child))

        # Файлы в текущей папке
        for child in sorted(path_obj.iterdir()):
            if child.is_file():
                # Пропускаем сам YAML этого узла (он уже показан в настройках)
                if child.name == f"{path_obj.name}.yaml":
                    continue
                items.append(("file", child))

        # Заполняем список
        for item_type, item_path in items:
            self._add_item(item_type, item_path)

        self._update_info()

    def refresh(self) -> None:
        """Обновляет текущую папку."""
        if self.current_path:
            self.load_path(self.current_path)

    def clear(self) -> None:
        """Очищает панель."""
        self.current_path = ""
        self.header_label.setText("Файлы")
        self.list_widget.clear()
        self.info_label.setText("Файлов: 0")

    # ==================== ВНУТРЕННИЕ МЕТОДЫ ====================

    def _add_item(self, item_type: str, path: Path) -> None:
        """Добавляет элемент в список."""
        item = QListWidgetItem()

        if item_type == "node":
            # Подпапка-узел (обработчик)
            icon = "📁"
            text = f"{icon} {path.name}/"
        else:
            # Файл
            icon = get_file_icon(path.name)
            try:
                size = format_size(path.stat().st_size)
            except OSError:
                size = "?"
            text = f"{icon} {path.name}    ({size})"

        item.setText(text)
        item.setData(Qt.UserRole, str(path))
        item.setData(Qt.UserRole + 1, item_type)

        # Цвет и жирность для узлов
        if item_type == "node":
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setForeground(QColor("#6fcf6f"))

        # Тултип
        item.setToolTip(str(path))

        self.list_widget.addItem(item)

    def _update_info(self) -> None:
        """Обновляет строку с количеством файлов."""
        count = self.list_widget.count()
        self.info_label.setText(f"Файлов: {count}")

    def _apply_filter(self, text: str) -> None:
        """Фильтрует список по имени."""
        text = text.lower()
        visible_count = 0
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
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
        """Обрабатывает двойной клик по элементу."""
        path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole + 1)

        if item_type == "node":
            self.node_double_clicked.emit(path)
        else:
            self.file_double_clicked.emit(path)

    def _on_context_menu(self, pos) -> None:
        """Показывает контекстное меню для элемента."""
        item = self.list_widget.itemAt(pos)
        if not item:
            return

        path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole + 1)

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
            open_action = QAction("Открыть узел", self)
            open_action.triggered.connect(
                lambda: self.node_double_clicked.emit(path)
            )
            menu.addAction(open_action)

            open_folder_action = QAction("Открыть в проводнике", self)
            open_folder_action.triggered.connect(
                lambda: self._open_in_explorer(path)
            )
            menu.addAction(open_folder_action)

        menu.exec(self.list_widget.mapToGlobal(pos))

    def _open_in_explorer(self, path: str) -> None:
        """Открывает файл/папку в системном проводнике."""
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
        """Копирует текст в буфер обмена."""
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)

    def _delete_file(self, path: str) -> None:
        """Удаляет файл с подтверждением."""
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