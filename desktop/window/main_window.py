"""Главное окно VideoLab."""
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QLabel,
    QMessageBox,
)
from PySide6.QtGui import QKeySequence, QShortcut

from core.logger import logger
from core.project import ProjectManager
from core.processors import ProcessorRegistry
from core.utils import load_yaml
from desktop.styles import DARK_THEME
from desktop.tree import TreePanel
from desktop.panels import SettingsPanel, FilesPanel, LogPanel
from desktop.window.toolbar import MainToolbar
from desktop.window.tabs import MainTabs
from desktop.window.project_actions import ProjectActions
from desktop.window.state import WindowState


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project: ProjectManager | None = None

        self.setWindowTitle("VideoLab")
        self.resize(1400, 900)
        self.setStyleSheet(DARK_THEME)

        self._create_central_widget()

        self.project_actions = ProjectActions(self)
        self.state = WindowState(self)

        self.toolbar = MainToolbar(self)
        self.addToolBar(self.toolbar)

        self._create_status_bar()

        logger.subscribe(self._on_global_log)

        # Esc — отмена активной обработки
        self._esc_shortcut = QShortcut(QKeySequence("Esc"), self)
        self._esc_shortcut.activated.connect(self._on_escape)

        self.log("INFO", "VideoLab запущен. Откройте или создайте проект.")
        self.state.restore()

    # ==================== СОЗДАНИЕ UI ====================

    def _create_central_widget(self) -> None:
        self.tabs = MainTabs(self)

        self.project_tab = self._create_project_tab()
        self.tabs.addTab(self.project_tab, "Проект")

        self.log_panel = LogPanel()
        self.tabs.addTab(self.log_panel, "Лог")

        self.setCentralWidget(self.tabs)

    def _create_project_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        self.main_splitter = QSplitter()

        self.tree_panel = TreePanel(self)
        self.settings_panel = SettingsPanel()
        self.files_panel = FilesPanel()

        self.files_panel.file_double_clicked.connect(self._on_file_double_clicked)
        self.files_panel.node_double_clicked.connect(self._on_node_double_clicked)
        self.settings_panel.node_updated.connect(self._on_node_updated)
        self.settings_panel.run_requested.connect(self._on_run_requested)

        self.main_splitter.addWidget(self.tree_panel)
        self.main_splitter.addWidget(self.settings_panel)
        self.main_splitter.addWidget(self.files_panel)

        self.main_splitter.setSizes([300, 550, 400])
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setStretchFactor(2, 0)

        layout.addWidget(self.main_splitter)
        return tab

    def _create_status_bar(self) -> None:
        self.status_label = QLabel("Готово")
        self.statusBar().addWidget(self.status_label)

        self.project_label = QLabel("Проект: (не открыт)")
        self.statusBar().addPermanentWidget(self.project_label)

    # ==================== API ====================

    def log(self, level: str, message: str) -> None:
        self.log_panel.add_log(level, message)
        if hasattr(self, "tabs"):
            self.tabs.update_log_indicator()

    def _on_global_log(self, level: str, message: str) -> None:
        self.log(level, message)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_project(self, project: ProjectManager) -> None:
        self.project = project
        self.project_label.setText(f"Проект: {project.project_root.name}")
        self.setWindowTitle(f"VideoLab — {project.project_root.name}")

        self.tree_panel.load_project(project)
        self.tree_panel.node_selected.connect(self._on_node_selected)

        self.settings_panel.set_project(project)

        self.log("SUCCESS", f"Проект открыт: {project.project_root}")

    def clear_project(self) -> None:
        self.project = None
        self.project_label.setText("Проект: (не открыт)")
        self.setWindowTitle("VideoLab")

        if hasattr(self.tree_panel, "model"):
            self.tree_panel.model.clear()
            self.tree_panel.model.setHorizontalHeaderLabels(["Узел"])

        self.files_panel.clear()
        self.settings_panel.clear()

        self.log("INFO", "Проект закрыт")

    # ==================== ОБРАБОТЧИКИ СОБЫТИЙ ====================

    def _on_node_selected(self, node_path: str) -> None:
        if not node_path:
            self.files_panel.clear()
            self.settings_panel.clear()
            return
        self.files_panel.load_path(node_path)
        if self.project:
            self.settings_panel.set_project(self.project)
        self.settings_panel.load_node(node_path)

    def _on_node_updated(self, node_path: str) -> None:
        self.tree_panel.refresh()
        self.files_panel.load_path(node_path)
        self.settings_panel.load_node(node_path)

    def _on_run_requested(self, node_path: str) -> None:
        node_data = load_yaml(Path(node_path) / f"{Path(node_path).name}.yaml")
        processor_name = node_data.get("processor", "")
        try:
            processor_class = ProcessorRegistry.get(processor_name)
        except KeyError:
            self.log("ERROR", f"Обработчик '{processor_name}' не зарегистрирован")
            return

        self.tree_panel.actions.run_with_progress(node_path, processor_class)

    def _on_file_double_clicked(self, file_path: str) -> None:
        name = Path(file_path).name
        self.log("INFO", f"Открытие файла: {name}")
        QMessageBox.information(
            self, "Просмотр файла",
            f"Просмотрщик будет добавлен позже.\n\nФайл:\n{file_path}"
        )

    def _on_node_double_clicked(self, node_path: str) -> None:
        self.files_panel.load_path(node_path)
        self.settings_panel.load_node(node_path)

    def _on_escape(self) -> None:
        """Esc — отмена активной обработки."""
        if self.tree_panel._current_context is not None:
            self.tree_panel.actions.cancel_processing()

    def on_record_video(self) -> None:
        QMessageBox.information(
            self, "Запись видео",
            "Функция записи будет добавлена позже."
        )

    def on_refresh(self) -> None:
        if not self.project:
            self.log("WARNING", "Проект не открыт")
            return
        self.tree_panel.refresh()
        self.files_panel.refresh()
        self.log("SUCCESS", "Обновлено")

    # ==================== ЗАКРЫТИЕ ====================

    def closeEvent(self, event) -> None:
        if self.tree_panel._current_context is not None:
            reply = QMessageBox.question(
                self, "Обработка выполняется",
                "Идёт обработка узла. Отменить её и закрыть приложение?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            self.tree_panel.actions.cancel_processing()
            thread = self.tree_panel._current_thread
            if thread:
                thread.quit()
                thread.wait(3000)

        self.state.save()
        logger.unsubscribe(self._on_global_log)
        super().closeEvent(event)