"""Главное окно VideoLab."""
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter,
    QToolBar, QFileDialog, QMessageBox, QLabel, QTabWidget,
    QInputDialog,
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction

from core.project_manager import ProjectManager
from desktop.panels import TreePanel, SettingsPanel, FilesPanel, LogPanel
from desktop.styles import DARK_THEME


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project: ProjectManager | None = None
        self.settings = QSettings("VideoLab", "VideoLab")

        self.setWindowTitle("🎬 VideoLab")
        self.resize(1400, 900)
        self.setStyleSheet(DARK_THEME)

        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()

        self.log("INFO", "VideoLab запущен. Откройте или создайте проект.")
        self._restore_state()

    # ==================== СОЗДАНИЕ UI ====================

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Основные действия")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        open_action = QAction("Открыть проект", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_project)
        toolbar.addAction(open_action)

        create_action = QAction("Создать проект", self)
        create_action.setShortcut("Ctrl+N")
        create_action.triggered.connect(self._on_create_project)
        toolbar.addAction(create_action)

        toolbar.addSeparator()

        record_action = QAction("Записать", self)
        record_action.setShortcut("Ctrl+R")
        record_action.triggered.connect(self._on_record_video)
        toolbar.addAction(record_action)

        toolbar.addSeparator()

        refresh_action = QAction("Обновить", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._on_refresh)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        close_action = QAction("Закрыть проект", self)
        close_action.setShortcut("Ctrl+W")
        close_action.triggered.connect(self._on_close_project)
        toolbar.addAction(close_action)

    def _create_central_widget(self) -> None:
        self.main_tabs = QTabWidget()
        self.main_tabs.setTabPosition(QTabWidget.North)
        self.main_tabs.setMovable(False)

        self.project_tab = self._create_project_tab()
        self.main_tabs.addTab(self.project_tab, "Проект")

        self.log_panel = LogPanel()
        self.main_tabs.addTab(self.log_panel, "Лог")

        self.main_tabs.currentChanged.connect(self._on_tab_changed)

        self.setCentralWidget(self.main_tabs)

    def _create_project_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        self.main_splitter = QSplitter(Qt.Horizontal)

        self.tree_panel = TreePanel()
        self.settings_panel = SettingsPanel()
        self.files_panel = FilesPanel()

        # Подключаем сигналы
        self.files_panel.file_double_clicked.connect(self._on_file_double_clicked)
        self.files_panel.node_double_clicked.connect(self._on_node_double_clicked)

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
        self._update_log_tab_indicator()

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_project(self, project: ProjectManager) -> None:
        self.project = project
        self.project_label.setText(f"Проект: {project.project_root.name}")
        self.setWindowTitle(f"VideoLab — {project.project_root.name}")
        self.tree_panel.load_project(project)
        self.tree_panel.node_selected.connect(self._on_node_selected)
        self.log("SUCCESS", f"Проект открыт: {project.project_root}")

    def clear_project(self) -> None:
        """Закрывает текущий проект (очищает дерево)."""
        self.project = None
        self.project_label.setText("Проект: (не открыт)")
        self.setWindowTitle("VideoLab")
        if hasattr(self.tree_panel, "model"):
            self.tree_panel.model.clear()
            self.tree_panel.model.setHorizontalHeaderLabels(["Узел"])
        self.files_panel.clear()
        self.log("INFO", "Проект закрыт")

    # ==================== ОБРАБОТЧИКИ СОБЫТИЙ ====================

    def _on_tab_changed(self, index: int) -> None:
        if index == 1:
            self.log_panel.mark_as_read()
            self._update_log_tab_indicator()

    def _update_log_tab_indicator(self) -> None:
        log_tab_index = 1
        if self.log_panel.has_unread_errors():
            self.main_tabs.setTabText(log_tab_index, "Лог (ошибки)")
            self.main_tabs.tabBar().setTabTextColor(log_tab_index, Qt.red)
        elif self.log_panel.has_unread_warnings():
            self.main_tabs.setTabText(log_tab_index, "Лог (предупреждения)")
            self.main_tabs.tabBar().setTabTextColor(log_tab_index, Qt.yellow)
        else:
            self.main_tabs.setTabText(log_tab_index, "Лог")
            self.main_tabs.tabBar().setTabTextColor(log_tab_index, Qt.white)

    def _on_node_selected(self, node_path: str) -> None:
        """Обрабатывает выбор узла в дереве."""
        self.files_panel.load_path(node_path)
        self.log("INFO", f"Выбран узел: {node_path}")

    def _on_file_double_clicked(self, file_path: str) -> None:
        """Открывает просмотрщик для файла (заглушка)."""
        name = Path(file_path).name
        self.log("INFO", f"Открытие файла: {name}")
        QMessageBox.information(
            self, "Просмотр файла",
            f"Просмотрщик будет добавлен позже.\n\nФайл:\n{file_path}"
        )

    def _on_node_double_clicked(self, node_path: str) -> None:
        """Переходит в подпапку-узел."""
        self.files_panel.load_path(node_path)
        self.log("INFO", f"Переход в узел: {node_path}")

    def _on_open_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку проекта", str(Path.home())
        )
        if not folder:
            return
        try:
            project = ProjectManager(folder)
            self.set_project(project)
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))
            self.log("ERROR", str(e))

    def _on_create_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку для нового проекта", str(Path.home())
        )
        if not folder:
            return

        name, ok = QInputDialog.getText(self, "Новый проект", "Имя проекта:")
        if not ok or not name.strip():
            return

        try:
            project_dir = Path(folder) / name.strip()
            project = ProjectManager.create_project(project_dir, name.strip())
            self.set_project(project)
            self.log("SUCCESS", f"Создан проект: {project_dir}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            self.log("ERROR", f"Не удалось создать проект: {e}")

    def _on_record_video(self) -> None:
        QMessageBox.information(
            self, "Запись видео",
            "Функция записи будет добавлена позже."
        )

    def _on_refresh(self) -> None:
        if not self.project:
            self.log("WARNING", "Проект не открыт")
            return
        self.tree_panel.refresh()
        self.files_panel.refresh()
        self.log("SUCCESS", "Обновлено")

    def _on_close_project(self) -> None:
        if not self.project:
            return
        reply = QMessageBox.question(
            self, "Закрытие проекта",
            "Закрыть текущий проект?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.clear_project()

    # ==================== СОХРАНЕНИЕ СОСТОЯНИЯ ====================

    def _restore_state(self) -> None:
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        main_sizes = self.settings.value("main_splitter_sizes")
        if main_sizes:
            self.main_splitter.setSizes([int(x) for x in main_sizes])

        last_project = self.settings.value("last_project_path", "")
        if last_project and Path(last_project).exists():
            try:
                project = ProjectManager(last_project)
                self.set_project(project)
                self.log("INFO", f"Автозагрузка проекта: {last_project}")
            except Exception as e:
                self.log("WARNING", f"Не удалось загрузить последний проект: {e}")

    def closeEvent(self, event) -> None:
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("main_splitter_sizes", self.main_splitter.sizes())

        if self.project:
            self.settings.setValue(
                "last_project_path", str(self.project.project_root)
            )
        else:
            self.settings.remove("last_project_path")

        super().closeEvent(event)