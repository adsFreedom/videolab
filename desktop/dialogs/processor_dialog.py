"""Диалог выбора и настройки обработчика."""
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QLineEdit, QFormLayout, QComboBox, QDialogButtonBox,
    QGroupBox, QMessageBox, QScrollArea, QWidget, QSplitter,
    QAbstractItemView,
)
from PySide6.QtCore import Qt

from core.base_processor import BaseProcessor
from core.project_manager import ProjectManager
from desktop.widgets.schema_form import SchemaForm


class ProcessorChooserDialog(QDialog):
    """
    Модальное окно: слева — список обработчиков, справа — форма настройки.
    Возвращает: processor_name, input_files, settings и выбор действия.
    """

    ACTION_ADD_ONLY = "add_only"
    ACTION_ADD_AND_RUN = "add_and_run"

    def __init__(
        self,
        project: ProjectManager,
        node_path: str,
        processors: list[type[BaseProcessor]],
        parent=None,
    ):
        super().__init__(parent)

        self.project = project
        self.node_path = node_path
        self.processors = processors
        self.selected_processor_class: type[BaseProcessor] | None = None

        self.result_processor_name: str = ""
        self.result_input_files: dict[str, str] = {}
        self.result_settings: dict = {}
        self.result_action: str = ""

        node_name = Path(node_path).name
        self.setWindowTitle(f"Добавить обработчик для «{node_name}»")
        self.setMinimumSize(900, 600)
        self.resize(1000, 650)

        self._create_ui()

    def _create_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Horizontal)

        # ЛЕВАЯ ЧАСТЬ
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск обработчиков...")
        self.search_input.textChanged.connect(self._apply_filter)
        left_layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.list_widget, stretch=1)

        self._populate_list()

        # ПРАВАЯ ЧАСТЬ
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        self.processor_title = QLabel("Выберите обработчик слева")
        self.processor_title.setStyleSheet(
            "font-weight: bold; font-size: 12pt; padding: 4px;"
        )
        right_layout.addWidget(self.processor_title)

        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setFrameShape(QScrollArea.NoFrame)

        self.right_container = QWidget()
        self.right_container_layout = QVBoxLayout(self.right_container)
        self.right_container_layout.setContentsMargins(0, 0, 0, 0)
        self.right_container_layout.setSpacing(8)
        self.right_scroll.setWidget(self.right_container)

        right_layout.addWidget(self.right_scroll, stretch=1)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 700])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, stretch=1)

        # --- Кнопки ---
        buttons = QDialogButtonBox()
        self.btn_cancel = buttons.addButton("Отмена", QDialogButtonBox.RejectRole)
        self.btn_add = buttons.addButton("Добавить", QDialogButtonBox.AcceptRole)
        self.btn_add_run = buttons.addButton(
            "Добавить и обработать", QDialogButtonBox.AcceptRole
        )

        self.btn_add.setEnabled(False)
        self.btn_add_run.setEnabled(False)

        self.btn_add.setDefault(True)
        self.btn_add.setAutoDefault(True)
        self.btn_add_run.setAutoDefault(False)

        buttons.rejected.connect(self.reject)
        self.btn_add.clicked.connect(lambda: self._on_accept(self.ACTION_ADD_ONLY))
        self.btn_add_run.clicked.connect(
            lambda: self._on_accept(self.ACTION_ADD_AND_RUN)
        )

        layout.addWidget(buttons)

    def _populate_list(self) -> None:
        self.list_widget.clear()

        by_category: dict[str, list[type[BaseProcessor]]] = {}
        for p in self.processors:
            by_category.setdefault(p.category, []).append(p)

        for category in sorted(by_category.keys()):
            header = QListWidgetItem(category)
            header.setFlags(Qt.NoItemFlags)
            font = header.font()
            font.setBold(True)
            header.setFont(font)
            self.list_widget.addItem(header)

            for p in by_category[category]:
                item = QListWidgetItem(f"  {p.icon}  {p.display_name}")
                item.setData(Qt.UserRole, p.name)
                self.list_widget.addItem(item)

    def _apply_filter(self, text: str) -> None:
        text = text.strip().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            processor_name = item.data(Qt.UserRole)
            if processor_name is None:
                item.setHidden(bool(text))
                continue
            item.setHidden(bool(text) and text not in item.text().lower())

    def _on_selection_changed(self) -> None:
        items = self.list_widget.selectedItems()
        if not items:
            return
        item = items[0]
        processor_name = item.data(Qt.UserRole)
        if not processor_name:
            return

        processor_class = next(
            (p for p in self.processors if p.name == processor_name), None
        )
        if not processor_class:
            return

        self.selected_processor_class = processor_class
        self._build_form(processor_class)

    def _clear_right_panel(self) -> None:
        while self.right_container_layout.count():
            child = self.right_container_layout.takeAt(0)
            widget = child.widget()
            if widget:
                widget.deleteLater()

    def _build_form(self, processor_class: type[BaseProcessor]) -> None:
        self._clear_right_panel()

        self.processor_title.setText(
            f"{processor_class.icon}  {processor_class.display_name}"
        )

        self.input_combos: dict[str, QComboBox] = {}
        if processor_class.input_spec:
            inputs_group = QGroupBox("Входные файлы")
            inputs_layout = QFormLayout(inputs_group)

            for input_name, spec in processor_class.input_spec.items():
                combo = QComboBox()
                mask = spec.get("mask", "*")
                files = self.project.scan_for_inputs(self.node_path, mask)
                combo.addItems(files)

                required = spec.get("required", True)
                label_text = input_name + (" *" if required else "")

                if not files:
                    combo.addItem("(нет подходящих файлов)")
                    combo.setEnabled(False)

                combo.currentTextChanged.connect(self._update_buttons)

                self.input_combos[input_name] = combo
                inputs_layout.addRow(QLabel(label_text), combo)

            self.right_container_layout.addWidget(inputs_group)

        if processor_class.settings_schema:
            settings_group = QGroupBox("Настройки")
            settings_layout = QVBoxLayout(settings_group)

            self.schema_form = SchemaForm(processor_class.settings_schema)
            settings_layout.addWidget(self.schema_form)

            self.right_container_layout.addWidget(settings_group)

        self.right_container_layout.addStretch()

        self._update_buttons()

    def _update_buttons(self) -> None:
        enabled = self._is_ready_to_add()
        self.btn_add.setEnabled(enabled)
        self.btn_add_run.setEnabled(enabled)

    def _is_ready_to_add(self) -> bool:
        if not self.selected_processor_class:
            return False

        for input_name, spec in self.selected_processor_class.input_spec.items():
            if not spec.get("required", True):
                continue
            combo = self.input_combos.get(input_name)
            if not combo or not combo.isEnabled():
                return False
            path = combo.currentText()
            if not path or path.startswith("("):
                return False

        return True

    def _collect_data(self) -> bool:
        if not self.selected_processor_class:
            return False

        input_files = {}
        for input_name, combo in self.input_combos.items():
            spec = self.selected_processor_class.input_spec[input_name]
            if not combo.isEnabled():
                if spec.get("required", True):
                    QMessageBox.warning(
                        self, "Ошибка",
                        f"Не найден обязательный вход: {input_name}"
                    )
                    return False
                continue
            path = combo.currentText()
            if path and not path.startswith("("):
                input_files[input_name] = path

        for input_name, spec in self.selected_processor_class.input_spec.items():
            if spec.get("required", True) and input_name not in input_files:
                QMessageBox.warning(
                    self, "Ошибка",
                    f"Не выбран обязательный вход: {input_name}"
                )
                return False

        settings = {}
        if hasattr(self, "schema_form"):
            settings = self.schema_form.get_values()

        self.result_processor_name = self.selected_processor_class.name
        self.result_input_files = input_files
        self.result_settings = settings
        return True

    def _on_accept(self, action: str) -> None:
        if not self._collect_data():
            return
        self.result_action = action
        self.accept()