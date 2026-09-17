"""Панель лога."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QComboBox, QLabel,
)
from datetime import datetime


class LogPanel(QWidget):
    """Панель лога с фильтрацией и цветовой индикацией."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._has_unread_errors = False
        self._has_unread_warnings = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # --- Тулбар лога ---
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("Фильтр:"))
        self.level_filter = QComboBox()
        self.level_filter.addItems(["Все", "INFO", "SUCCESS", "WARNING", "ERROR"])
        self.level_filter.currentTextChanged.connect(self._apply_filter)
        toolbar.addWidget(self.level_filter)

        toolbar.addStretch()

        copy_btn = QPushButton("📋 Копировать")
        copy_btn.clicked.connect(self._copy_to_clipboard)
        toolbar.addWidget(copy_btn)

        clear_btn = QPushButton("🗑️ Очистить")
        clear_btn.clicked.connect(self.clear_log)
        toolbar.addWidget(clear_btn)

        layout.addLayout(toolbar)

        # --- Текстовое поле лога ---
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Храним все записи для фильтрации
        # [{"level": "INFO", "html": "<span>...</span>"}, ...]
        self._records: list[dict] = []

    # ==================== API ====================

    def add_log(self, level: str, message: str) -> None:
        """Добавляет запись в лог."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        color_map = {
            "INFO": "#4fc1ff",
            "SUCCESS": "#6fcf6f",
            "WARNING": "#ffcc00",
            "ERROR": "#ff6b6b",
        }
        icon_map = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
        }

        color = color_map.get(level, "#d4d4d4")
        icon = icon_map.get(level, "")

        html = (
            f'<span style="color: #808080;">[{timestamp}]</span> '
            f'<span style="color: {color};">{icon} {level}: {message}</span>'
        )

        self._records.append({"level": level, "html": html})
        self.log_text.append(html)

        # Авто-прокрутка
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

        # Обновляем индикатор (если таб лога не активен)
        if level == "ERROR":
            self._has_unread_errors = True
        elif level == "WARNING":
            self._has_unread_warnings = True

    def clear_log(self) -> None:
        """Очищает лог."""
        self.log_text.clear()
        self._records.clear()
        self._has_unread_errors = False
        self._has_unread_warnings = False

    def mark_as_read(self) -> None:
        """Сбрасывает индикацию непрочитанных ошибок."""
        self._has_unread_errors = False
        self._has_unread_warnings = False

    def has_unread_errors(self) -> bool:
        return self._has_unread_errors

    def has_unread_warnings(self) -> bool:
        return self._has_unread_warnings

    # ==================== ВНУТРЕННИЕ МЕТОДЫ ====================

    def _apply_filter(self, level: str) -> None:
        """Применяет фильтр по уровню."""
        self.log_text.clear()

        for record in self._records:
            if level == "Все" or record["level"] == level:
                self.log_text.append(record["html"])

    def _copy_to_clipboard(self) -> None:
        """Копирует лог в буфер обмена."""
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.log_text.toPlainText())