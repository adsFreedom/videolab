"""Диалог прогресса: опрашивает ExecutionContext через QTimer."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton,
    QHBoxLayout,
)
from PySide6.QtCore import Qt, QTimer, Signal


class ProgressDialog(QDialog):
    """
    Немодальный диалог прогресса.

    Читает поля ExecutionContext раз в 100 мс и обновляет UI.
    Кнопка «Отмена» вызывает context.cancel().
    """

    # Сигнал: диалог закрылся по завершении обработки
    finished_external = Signal()

    def __init__(self, node_name: str, processor_title: str, context, parent=None):
        super().__init__(parent)

        self.context = context
        self._is_cancelled = False
        self._closed = False

        self.setWindowTitle("Обработка...")
        self.setMinimumWidth(450)
        self.setFixedHeight(220)

        # Запрещаем закрытие через крестик (обработка идёт)
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
        self.progress_bar.setRange(0, 0)  # неопределённый по умолчанию
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

        # Таймер для polling
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._poll)
        self.timer.start()

    def _poll(self) -> None:
        """Читает поля контекста и обновляет UI."""
        if self._closed:
            return

        ctx = self.context

        # 1. Прогресс
        if ctx.has_progress and ctx.total > 0:
            if self.progress_bar.maximum() != ctx.total:
                self.progress_bar.setRange(0, ctx.total)
            self.progress_bar.setValue(ctx.current)
            percent = int(100 * ctx.current / ctx.total) if ctx.total else 0
            self.status_label.setText(
                f"Прогресс: {ctx.current} / {ctx.total} ({percent}%)"
            )
        else:
            self.progress_bar.setRange(0, 0)
            if ctx.message:
                self.status_label.setText(ctx.message)
            else:
                self.status_label.setText("Пожалуйста, подождите...")

        # 2. Завершение
        if ctx.done:
            self._closed = True
            self.timer.stop()
            self.accept()
            self.finished_external.emit()

    def _on_cancel(self) -> None:
        """Запрашивает отмену через контекст."""
        self._is_cancelled = True
        self.context.cancel()
        self.status_label.setText("Отмена запрошена, ожидание...")
        self.btn_cancel.setEnabled(False)