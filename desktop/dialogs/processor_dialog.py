"""Диалог создания обработчика."""
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLabel,
    QDialogButtonBox, QGroupBox, QMessageBox, QScrollArea, QWidget,
)
from PySide6.QtCore import Qt

from core.base_processor import BaseProcessor
from core.project_manager import ProjectManager
from desktop.widgets.schema_form import SchemaForm


class ProcessorDialog(QDialog):
    """Диалог настройки и запуска обработчика."""

    def __init__(
        self,
        project: ProjectManager,
        node_path: str,
        processor_class: type[BaseProcessor],
        parent=None,
    ):
        super().__init__(parent)

        self.project = project
        self.node_path = node_path
        self.processor_class = processor_class

        self.setWindowTitle(f"Создание обработчика: {processor_class.display_name}")
        self.setMinimumWidth(600)
        self.resize(700, 600)

        # Результат (заполняется при нажатии "Запустить")
        self.result_input_files: dict[str, str] = {}
        self.result_settings: dict = {}

        self._create_ui()

    def _create_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Заголовок ---
        header = QLabel(
            f"<b>{self.processor_class.display_name}</b><br>"
            f"<span style='color: #808080;'>Обработчик: {self.processor_class.name}</span>"
        )
        header.setStyleSheet("font-size: 11pt; padding: 4px;")
        layout.addWidget(header)

        # --- Входные файлы ---
        if self.processor_class.input_spec:
            inputs_group = QGroupBox("Входные файлы")
            inputs_layout = QFormLayout(inputs_group)

            self.input_combos: dict[str, QComboBox] = {}

            for input_name, spec in self.processor_class.input_spec.items():
                combo = QComboBox()
                mask = spec.get("mask", "*")

                # Ищем файлы вверх по дереву
                files = self.project.scan_for_inputs(self.node_path, mask)
                combo.addItems(files)

                required = spec.get("required", True)
                label_text = input_name + (" *" if required else "")

                if not files:
                    combo.addItem("(нет подходящих файлов)")
                    combo.setEnabled(False)

                self.input_combos[input_name] = combo
                inputs_layout.addRow(QLabel(label_text), combo)

            layout.addWidget(inputs_group)

        # --- Настройки ---
        if self.processor_class.settings_schema:
            settings_group = QGroupBox("Настройки")
            settings_layout = QVBoxLayout(settings_group)

            # Оборачиваем в скролл на случай большого количества настроек
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.NoFrame)

            self.schema_form = SchemaForm(self.processor_class.settings_schema)
            scroll.setWidget(self.schema_form)

            settings_layout.addWidget(scroll)
            layout.addWidget(settings_group, stretch=1)

        # --- Кнопки ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Ok).setText("Запустить")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        """Собирает данные и закрывает диалог."""
        # Проверяем входные файлы
        input_files = {}
        for input_name, combo in self.input_combos.items():
            spec = self.processor_class.input_spec[input_name]
            if not combo.isEnabled():
                if spec.get("required", True):
                    QMessageBox.warning(
                        self, "Ошибка",
                        f"Не найден обязательный вход: {input_name}"
                    )
                    return
                continue
            path = combo.currentText()
            if path and not path.startswith("("):
                input_files[input_name] = path

        # Проверяем обязательные входы
        for input_name, spec in self.processor_class.input_spec.items():
            if spec.get("required", True) and input_name not in input_files:
                QMessageBox.warning(
                    self, "Ошибка",
                    f"Не выбран обязательный вход: {input_name}"
                )
                return

        # Собираем настройки
        settings = {}
        if hasattr(self, "schema_form"):
            settings = self.schema_form.get_values()

        self.result_input_files = input_files
        self.result_settings = settings

        self.accept()