"""Панель настроек обработчика (заглушка)."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTabWidget
from PySide6.QtCore import Qt


class SettingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()

        # Вкладка "Настройки"
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_placeholder = QLabel("⚙️ (здесь будут настройки обработчика)")
        settings_placeholder.setAlignment(Qt.AlignCenter)
        settings_placeholder.setStyleSheet(
            "color: #666666; font-style: italic;")
        settings_layout.addWidget(settings_placeholder)

        # Вкладка "Данные"
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        data_placeholder = QLabel("📊 (здесь будет статистика узла)")
        data_placeholder.setAlignment(Qt.AlignCenter)
        data_placeholder.setStyleSheet("color: #666666; font-style: italic;")
        data_layout.addWidget(data_placeholder)

        self.tabs.addTab(settings_tab, "⚙️ Настройки")
        self.tabs.addTab(data_tab, "📊 Данные")

        layout.addWidget(self.tabs)