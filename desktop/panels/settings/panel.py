"""Панель настроек выбранного узла."""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTabWidget, QStackedWidget,
)
from PySide6.QtCore import Signal

from core.project import ProjectManager
from core.utils import load_yaml
from desktop.panels.settings.source_tab import SourceTab
from desktop.panels.settings.processor_tab import ProcessorTab
from desktop.panels.settings.data_tab import DataTab


class SettingsPanel(QWidget):
    """Панель настроек выбранного узла."""

    node_updated = Signal(str)
    run_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project: ProjectManager | None = None
        self.current_node_path: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()

        # --- Вкладка "Настройки" ---
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setContentsMargins(8, 8, 8, 8)

        self.header_label = QLabel("(узел не выбран)")
        self.header_label.setStyleSheet(
            "font-weight: bold; font-size: 11pt; padding: 4px;"
        )
        settings_layout.addWidget(self.header_label)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("padding: 4px;")
        settings_layout.addWidget(self.status_label)

        self.stack = QStackedWidget()

        # Таб 0: source
        self.source_tab = SourceTab()
        self.source_tab.node_updated.connect(self._on_source_updated)

        # Таб 1: processor
        self.processor_tab = ProcessorTab()
        self.processor_tab.node_updated.connect(self.node_updated.emit)
        self.processor_tab.run_requested.connect(self.run_requested.emit)

        self.stack.addWidget(self.source_tab)
        self.stack.addWidget(self.processor_tab)

        settings_layout.addWidget(self.stack, stretch=1)

        self.tabs.addTab(settings_tab, "Настройки")

        # --- Вкладка "Данные" ---
        self.data_tab = DataTab()
        self.tabs.addTab(self.data_tab, "Данные")

        layout.addWidget(self.tabs)

    # ==================== API ====================

    def set_project(self, project: ProjectManager) -> None:
        self.project = project
        self.source_tab.set_project(project)
        self.processor_tab.set_project(project)
        self.data_tab.set_project(project)

    def load_node(self, node_path: str) -> None:
        self.current_node_path = node_path

        if not node_path or not Path(node_path).exists():
            self._clear_all()
            return

        node_path_obj = Path(node_path)
        yaml_path = node_path_obj / f"{node_path_obj.name}.yaml"
        node_data = load_yaml(yaml_path)

        processor_name = node_data.get("processor", "")
        display_name = node_data.get("display_name", node_path_obj.name)

        self.header_label.setText(f"{display_name} ({node_path_obj.name})")

        # Статус
        if self.project:
            is_valid, _ = self.project.validate_node(node_path)
            if is_valid:
                self.status_label.setText("✅ Настройки применены")
                self.status_label.setStyleSheet("color: #6fcf6f; padding: 4px;")
            else:
                self.status_label.setText("❌ Требуется обработка")
                self.status_label.setStyleSheet("color: #ff6b6b; padding: 4px;")

            # Обработчик не обработан — показать defaults
            if processor_name != "source" and "settings_snapshot" not in node_data:
                self.status_label.setText(
                    "⚪ Узел ещё не обработан (показаны значения по умолчанию)"
                )
                self.status_label.setStyleSheet("color: #a0a0a0; padding: 4px;")

        # Переключаем таб
        if processor_name == "source":
            self.stack.setCurrentWidget(self.source_tab)
            self.source_tab.load_node(node_path, node_data)
        else:
            self.stack.setCurrentWidget(self.processor_tab)
            self.processor_tab.load_node(node_path, node_data)

        # Данные
        self.data_tab.load_node(node_path, node_data)

    def clear(self) -> None:
        self._clear_all()

    # ==================== ВНУТРЕННИЕ ====================

    def _clear_all(self) -> None:
        self.current_node_path = ""
        self.header_label.setText("(узел не выбран)")
        self.status_label.setText("")
        self.source_tab.clear()
        self.processor_tab.clear()
        self.data_tab.clear()

    def _on_source_updated(self, node_path: str) -> None:
        self.node_updated.emit(node_path)