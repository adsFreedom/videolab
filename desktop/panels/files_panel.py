"""Панель файлов и превью (заглушка)."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class FilesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        label = QLabel("📄 Файлы / Превью")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-weight: bold; padding: 8px;")

        layout.addWidget(label)
        layout.addStretch()

        placeholder = QLabel("(здесь будут файлы текущей папки)")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #666666; font-style: italic;")
        layout.addWidget(placeholder)