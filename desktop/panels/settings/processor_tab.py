"""Вкладка настроек обработчика."""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QScrollArea,
)
from PySide6.QtCore import Signal

from core.logger import log
from core.project import ProjectManager
from core.processors import ProcessorRegistry
from core.utils import load_yaml, save_yaml
from desktop.widgets.schema_form import SchemaForm


class ProcessorTab(QWidget):
    """Вкладка настроек обработчика."""

    node_updated = Signal(str)
    run_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project: ProjectManager | None = None
        self.current_node_path: str = ""
        self.schema_form: SchemaForm | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.container)

        layout.addWidget(self.scroll, stretch=1)

        btn_layout = QHBoxLayout()

        self.btn_save = QPushButton("Сохранить")
        self.btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(self.btn_save)

        self.btn_apply = QPushButton("Применить и перезапустить")
        self.btn_apply.clicked.connect(self._on_apply)
        btn_layout.addWidget(self.btn_apply)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def set_project(self, project: ProjectManager) -> None:
        self.project = project

    def set_processing_state(self, is_processing: bool) -> None:
        """Блокирует кнопку 'Применить' на время обработки."""
        self.btn_apply.setEnabled(not is_processing)

    def load_node(self, node_path: str, node_data: dict) -> None:
        self.current_node_path = node_path
        self._clear_form()
        self.schema_form = None

        processor_name = node_data.get("processor", "")

        try:
            processor_class = ProcessorRegistry.get(processor_name)
        except KeyError:
            label = QLabel(f"Обработчик '{processor_name}' не зарегистрирован.")
            label.setStyleSheet("color: #ff6b6b;")
            self.container_layout.addWidget(label)
            self.btn_save.setEnabled(False)
            self.btn_apply.setEnabled(False)
            return

        settings_to_show = node_data.get("settings", {})
        has_snapshot = "settings_snapshot" in node_data
        if not has_snapshot:
            settings_to_show = processor_class().get_default_settings()

        if processor_class.settings_schema:
            self.schema_form = SchemaForm(processor_class.settings_schema)
            self.schema_form.set_values(settings_to_show)
            self.container_layout.addWidget(self.schema_form)
        else:
            label = QLabel("(у этого обработчика нет настроек)")
            label.setStyleSheet("color: #808080; font-style: italic;")
            self.container_layout.addWidget(label)

        self.container_layout.addStretch()
        self.btn_save.setEnabled(True)
        self.btn_apply.setEnabled(True)

    def clear(self) -> None:
        self.current_node_path = ""
        self._clear_form()
        self.schema_form = None

    # ==================== ВНУТРЕННИЕ ====================

    def _clear_form(self) -> None:
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # ==================== СОБЫТИЯ ====================

    def _on_save(self) -> None:
        if not self.current_node_path or not self.schema_form:
            return

        try:
            new_settings = self.schema_form.get_values()
            yaml_path = (
                Path(self.current_node_path)
                / f"{Path(self.current_node_path).name}.yaml"
            )
            node_data = load_yaml(yaml_path)
            node_data["settings"] = new_settings
            save_yaml(yaml_path, node_data)

            log("INFO", f"Настройки сохранены: {self.current_node_path}")
            QMessageBox.information(
                self, "Сохранено",
                "Настройки сохранены.\n\n"
                "Узел помечен красным — требуется перезапуск."
            )
            self.node_updated.emit(self.current_node_path)
        except Exception as e:
            log("ERROR", f"Ошибка сохранения настроек: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_apply(self) -> None:
        if not self.current_node_path or not self.schema_form:
            return

        reply = QMessageBox.question(
            self, "Перезапуск обработки",
            "Сохранить настройки и перезапустить обработку?\n"
            "Старые результаты будут перезаписаны.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            new_settings = self.schema_form.get_values()
            yaml_path = (
                Path(self.current_node_path)
                / f"{Path(self.current_node_path).name}.yaml"
            )
            node_data = load_yaml(yaml_path)
            node_data["settings"] = new_settings
            save_yaml(yaml_path, node_data)

            log("INFO", f"Запуск обработки: {self.current_node_path}")
            self.run_requested.emit(self.current_node_path)
        except Exception as e:
            log("ERROR", f"Ошибка подготовки к запуску: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", str(e))