"""Панель настроек выбранного узла."""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QPushButton, QMessageBox, QScrollArea, QTextEdit,
)
from PySide6.QtCore import Qt, Signal

from core.logger import log
from core.project_manager import ProjectManager
from core.processor_registry import ProcessorRegistry
from core.utils import load_yaml, save_yaml
from desktop.widgets.schema_form import SchemaForm


class SettingsPanel(QWidget):
    """Панель настроек выбранного узла."""

    node_updated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project: ProjectManager | None = None
        self.current_node_path: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()

        self.settings_tab = self._create_settings_tab()
        self.tabs.addTab(self.settings_tab, "Настройки")

        self.data_tab = self._create_data_tab()
        self.tabs.addTab(self.data_tab, "Данные")

        layout.addWidget(self.tabs)

    def _create_settings_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        self.settings_header = QLabel("(узел не выбран)")
        self.settings_header.setStyleSheet(
            "font-weight: bold; font-size: 11pt; padding: 4px;"
        )
        layout.addWidget(self.settings_header)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("padding: 4px;")
        layout.addWidget(self.status_label)

        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setFrameShape(QScrollArea.NoFrame)

        self.settings_container = QWidget()
        self.settings_container_layout = QVBoxLayout(self.settings_container)
        self.settings_container_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_scroll.setWidget(self.settings_container)

        layout.addWidget(self.settings_scroll, stretch=1)

        btn_layout = QHBoxLayout()

        self.btn_save = QPushButton("Сохранить")
        self.btn_save.clicked.connect(self._on_save)
        self.btn_save.setEnabled(False)
        btn_layout.addWidget(self.btn_save)

        self.btn_apply = QPushButton("Применить и перезапустить")
        self.btn_apply.clicked.connect(self._on_apply)
        self.btn_apply.setEnabled(False)
        btn_layout.addWidget(self.btn_apply)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return widget

    def _create_data_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        self.data_text = QTextEdit()
        self.data_text.setReadOnly(True)
        layout.addWidget(self.data_text)

        return widget

    # ==================== API ====================

    def set_project(self, project: ProjectManager) -> None:
        self.project = project

    def load_node(self, node_path: str) -> None:
        """Загружает узел в панель настроек."""
        self.current_node_path = node_path
        self._clear_settings_form()

        if not node_path or not Path(node_path).exists():
            self.settings_header.setText("(узел не выбран)")
            self.status_label.setText("")
            self.data_text.clear()
            self.btn_save.setEnabled(False)
            self.btn_apply.setEnabled(False)
            return

        node_path_obj = Path(node_path)
        yaml_path = node_path_obj / f"{node_path_obj.name}.yaml"
        node_data = load_yaml(yaml_path)

        processor_name = node_data.get("processor", "")
        display_name = node_data.get("display_name", node_path_obj.name)

        self.settings_header.setText(f"{display_name} ({node_path_obj.name})")

        # Статус
        if self.project:
            is_valid, _ = self.project.validate_node(node_path)
            if is_valid:
                self.status_label.setText("✅ Настройки применены")
                self.status_label.setStyleSheet("color: #6fcf6f; padding: 4px;")
            else:
                self.status_label.setText("❌ Требуется обработка")
                self.status_label.setStyleSheet("color: #ff6b6b; padding: 4px;")

        # --- source ---
        if processor_name == "source":
            self._show_source_info(node_data)
            self.btn_save.setEnabled(False)
            self.btn_apply.setEnabled(False)
        else:
            try:
                processor_class = ProcessorRegistry.get(processor_name)
                # Что показать в форме: текущие settings или defaults?
                settings_to_show = node_data.get("settings", {})
                has_snapshot = "settings_snapshot" in node_data
                if not has_snapshot:
                    # Узел не обработан — показываем defaults
                    settings_to_show = processor_class().get_default_settings()
                    self.status_label.setText(
                        "⚪ Узел ещё не обработан (показаны значения по умолчанию)"
                    )
                    self.status_label.setStyleSheet(
                        "color: #a0a0a0; padding: 4px;"
                    )

                self._build_settings_form(processor_class, settings_to_show)
                self.btn_save.setEnabled(True)
                self.btn_apply.setEnabled(True)
            except KeyError:
                label = QLabel(
                    f"Обработчик '{processor_name}' не зарегистрирован."
                )
                label.setStyleSheet("color: #ff6b6b;")
                self.settings_container_layout.addWidget(label)
                self.btn_save.setEnabled(False)
                self.btn_apply.setEnabled(False)

        self._fill_data_tab(node_data, node_path)

    def clear(self) -> None:
        self.current_node_path = ""
        self._clear_settings_form()
        self.settings_header.setText("(узел не выбран)")
        self.status_label.setText("")
        self.data_text.clear()
        self.btn_save.setEnabled(False)
        self.btn_apply.setEnabled(False)

    # ==================== ВНУТРЕННИЕ ====================

    def _clear_settings_form(self) -> None:
        while self.settings_container_layout.count():
            item = self.settings_container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _show_source_info(self, node_data: dict) -> None:
        label = QLabel(
            "<b>Исходное видео</b><br><br>"
            f"Файл: {node_data.get('input_file', '(не задан)')}<br>"
            f"Создан: {node_data.get('created', '-')}"
        )
        label.setWordWrap(True)
        self.settings_container_layout.addWidget(label)

    def _build_settings_form(
        self,
        processor_class: type,
        current_settings: dict,
    ) -> None:
        if not processor_class.settings_schema:
            label = QLabel("(у этого обработчика нет настроек)")
            label.setStyleSheet("color: #808080; font-style: italic;")
            self.settings_container_layout.addWidget(label)
            return

        self.schema_form = SchemaForm(processor_class.settings_schema)
        self.schema_form.set_values(current_settings)
        self.settings_container_layout.addWidget(self.schema_form)
        self.settings_container_layout.addStretch()

    def _fill_data_tab(self, node_data: dict, node_path: str) -> None:
        lines = []

        lines.append(f"<b>Путь:</b> {node_path}")
        lines.append(f"<b>Обработчик:</b> {node_data.get('processor', '-')}")
        lines.append(f"<b>Создан:</b> {node_data.get('created', '-')}")

        # Входные файлы
        input_files = node_data.get("input_files", {})
        input_snapshot = node_data.get("input_files_snapshot")
        if input_files:
            lines.append("<br><b>Входные файлы:</b>")
            for key, value in input_files.items():
                match = ""
                if input_snapshot is not None:
                    if input_snapshot.get(key) == value:
                        match = " (совпадает)"
                    else:
                        match = " ⚠ изменено"
                lines.append(f"  • {key}: {value}{match}")

        # Настройки
        settings = node_data.get("settings", {})
        snapshot = node_data.get("settings_snapshot")
        if settings:
            lines.append("<br><b>Настройки:</b>")
            lines.append(f"  Текущие: {settings}")
            if snapshot is not None:
                lines.append(f"  Snapshot: {snapshot}")
                # Ищем различия
                diffs = []
                all_keys = set(settings.keys()) | set(snapshot.keys())
                for key in sorted(all_keys):
                    old = snapshot.get(key, "(нет)")
                    new = settings.get(key, "(нет)")
                    if old != new:
                        diffs.append(f"    ⚠ {key}: было {old}, стало {new}")
                if diffs:
                    lines.append("<br><b>Различия:</b>")
                    lines.extend(diffs)
            else:
                lines.append("  <i>(snapshot отсутствует — узел не обработан)</i>")

        # Выходные файлы
        expected = node_data.get("expected_outputs")
        if expected:
            lines.append("<br><b>Ожидаемые выходы:</b>")
            for f in expected:
                exists = "OK" if (Path(node_path) / f).exists() else "MISS"
                lines.append(f"  [{exists}] {f}")

        # Статус
        if self.project:
            is_valid, msg = self.project.validate_node(node_path)
            status = "✅ Валидный" if is_valid else f"❌ {msg}"
            lines.append(f"<br><b>Статус:</b> {status}")

        self.data_text.setHtml("<br>".join(lines))

    # ==================== СОБЫТИЯ ====================

    def _on_save(self) -> None:
        """Сохраняет настройки без перезапуска. Узел станет красным."""
        if not self.current_node_path or not hasattr(self, "schema_form"):
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
        """Сохраняет и перезапускает обработку."""
        if not self.current_node_path or not hasattr(self, "schema_form"):
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

            log("INFO", f"Перезапуск обработки: {self.current_node_path}")

            self.project.run_node(self.current_node_path)

            log("SUCCESS", f"Обработка завершена: {self.current_node_path}")
            QMessageBox.information(self, "Готово", "Обработка завершена")
            self.node_updated.emit(self.current_node_path)
        except Exception as e:
            log("ERROR", f"Ошибка обработки: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", str(e))