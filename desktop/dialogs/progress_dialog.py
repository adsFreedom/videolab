"""Модальный диалог прогресса обработки с кнопкой отмены."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton,
    QHBoxLayout,
)
from PySide6.QtCore import Qt


class ProgressDialog(QDialog):
    """
    Модальный диалог прогресса.

    Использует ExecutionContext для получения обновлений прогресса.
    Кнопка «Отмена» вызывает context.cancel().
    """

    def __init__(self, node_name: str, processor_title: str, context, parent=None):
        super().__init__(parent)

        self.context = context
        self._is_cancelled = False

        self.setWindowTitle("Обработка...")
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setFixedHeight(220)

        self.setWindowFlag(Qt.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(f"<b>{processor_title}</b>")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 12pt;")
        layout.addWidget(title)

        node_label = QLabel(f"Узел: {node_name}")
        node_label.setAlignment(Qt.AlignCenter)
        node_label.setStyleSheet("color: #a0a0a0;")
        layout.addWidget(node_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Пожалуйста, подождите...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #a0a0a0; font-style: italic;")
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        context._progress_callback = self._on_progress

    def _on_progress(self, current: int, total: int) -> None:
        """Обновляет прогресс-бар."""
        if current == -1 and total == -1:
            self.progress_bar.setRange(0, 0)
            self.status_label.setText("Пожалуйста, подождите...")
        else:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            percent = int(100 * current / total) if total > 0 else 0
            self.status_label.setText(f"Прогресс: {current} / {total} ({percent}%)")

    def _on_cancel(self) -> None:
        """Запрашивает отмену через контекст."""
        self._is_cancelled = True
        self.context.cancel()
        self.status_label.setText("Отмена запрошена, ожидание...")
        self.btn_cancel.setEnabled(False)

    def closeEvent(self, event):
        """Блокируем закрытие через крестик."""
        event.ignore()