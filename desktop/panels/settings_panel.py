"""Панель настроек выбранного узла."""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QPushButton, QFormLayout, QGroupBox, QMessageBox,
    QScrollArea, QTextEdit,
)
from PySide6.QtCore import Qt, Signal

from core.project_manager import ProjectManager
from core.processor_registry import ProcessorRegistry
from core.utils import load_yaml
from desktop.widgets.schema_form import SchemaForm


class SettingsPanel(QWidget):
    """Панель настроек выбранного узла."""

    node_updated = Signal(str)  # Сигнал: узел был изменен (нужно обновить дерево)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project: ProjectManager | None = None
        self.current_node_path: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()

        # --- Вкладка "Настройки" ---
        self.settings_tab = self._create_settings_tab()
        self.tabs.addTab(self.settings_tab, "Настройки")

        # --- Вкладка "Данные" ---
        self.data_tab = self._create_data_tab()
        self.tabs.addTab(self.data_tab, "Данные")

        layout.addWidget(self.tabs)

    def _create_settings_tab(self) -> QWidget:
        """Создает вкладку с настройками."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        # Заголовок
        self.settings_header = QLabel("(узел не выбран)")
        self.settings_header.setStyleSheet(
            "font-weight: bold; font-size: 11pt; padding: 4px;"
        )
        layout.addWidget(self.settings_header)

        # Область для формы настроек (заполняется динамически)
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setFrameShape(QScrollArea.NoFrame)

        self.settings_container = QWidget()
        self.settings_container_layout = QVBoxLayout(self.settings_container)
        self.settings_container_layout.setContentsMargins(0, 0, 0, 0)
        self.settings_scroll.setWidget(self.settings_container)

        layout.addWidget(self.settings_scroll, stretch=1)

        # Кнопки
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
        """Создает вкладку с данными узла."""
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
            self.data_text.clear()
            self.btn_save.setEnabled(False)
            self.btn_apply.setEnabled(False)
            return

        node_path_obj = Path(node_path)
        yaml_path = node_path_obj / f"{node_path_obj.name}.yaml"
        node_data = load_yaml(yaml_path)

        processor_name = node_data.get("processor", "")
        display_name = node_data.get("display_name", node_path_obj.name)

        self.settings_header.setText(
            f"{display_name} ({node_path_obj.name})"
        )

        # Если это source — просто показываем информацию
        if processor_name == "source":
            self._show_source_info(node_data)
            self.btn_save.setEnabled(False)
            self.btn_apply.setEnabled(False)
        else:
            # Загружаем схему обработчика и заполняем форму
            try:
                processor_class = ProcessorRegistry.get(processor_name)
                self._build_settings_form(
                    processor_class,
                    node_data.get("settings", {}),
                )
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

        # Заполняем вкладку "Данные"
        self._fill_data_tab(node_data, node_path)

    def clear(self) -> None:
        """Очищает панель."""
        self.current_node_path = ""
        self._clear_settings_form()
        self.settings_header.setText("(узел не выбран)")
        self.data_text.clear()
        self.btn_save.setEnabled(False)
        self.btn_apply.setEnabled(False)

    # ==================== ВНУТРЕННИЕ МЕТОДЫ ====================

    def _clear_settings_form(self) -> None:
        """Очищает контейнер формы настроек."""
        while self.settings_container_layout.count():
            item = self.settings_container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _show_source_info(self, node_data: dict) -> None:
        """Показывает информацию о source-узле."""
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
        """Строит форму настроек для обработчика."""
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
        """Заполняет вкладку 'Данные'."""
        lines = []

        lines.append(f"<b>Путь:</b> {node_path}")
        lines.append(f"<b>Обработчик:</b> {node_data.get('processor', '-')}")
        lines.append(f"<b>Создан:</b> {node_data.get('created', '-')}")

        # Входные файлы
        input_files = node_data.get("input_files", {})
        if input_files:
            lines.append("<br><b>Входные файлы:</b>")
            for key, value in input_files.items():
                lines.append(f"  • {key}: {value}")

        # Ожидаемые выходы
        expected = node_data.get("expected_outputs")
        if expected:
            lines.append("<br><b>Ожидаемые выходы:</b>")
            for f in expected:
                exists = "✅" if (Path(node_path) / f).exists() else "❌"
                lines.append(f"  {exists} {f}")

        # Статус
        if self.project:
            is_valid, msg = self.project.validate_node(node_path)
            status = "✅ Валидный" if is_valid else f"❌ {msg}"
            lines.append(f"<br><b>Статус:</b> {status}")

        self.data_text.setHtml("<br>".join(lines))

    # ==================== СОБЫТИЯ ====================

    def _on_save(self) -> None:
        """Сохраняет настройки без перезапуска."""
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

            from core.utils import save_yaml
            save_yaml(yaml_path, node_data)

            QMessageBox.information(self, "Сохранено", "Настройки сохранены")
            self.node_updated.emit(self.current_node_path)
        except Exception as e:
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
            # Сохраняем настройки
            new_settings = self.schema_form.get_values()
            yaml_path = (
                Path(self.current_node_path)
                / f"{Path(self.current_node_path).name}.yaml"
            )
            node_data = load_yaml(yaml_path)
            node_data["settings"] = new_settings

            from core.utils import save_yaml
            save_yaml(yaml_path, node_data)

            # Запускаем обработку
            self.project.run_node(self.current_node_path)

            QMessageBox.information(self, "Готово", "Обработка завершена")
            self.node_updated.emit(self.current_node_path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            import traceback
            traceback.print_exc()