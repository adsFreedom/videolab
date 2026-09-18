"""Модальный диалог с копируемым текстом ошибки."""
import traceback

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox,
)
from PySide6.QtCore import Qt


class ErrorDialog(QDialog):
    """
    Диалог отображения ошибки с возможностью копирования текста.

    Использование:
        ErrorDialog.show_error(parent, "Заголовок", "Сообщение", traceback_text)
    """

    def __init__(self, title: str, message: str, tb: str = "", parent=None):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.resize(750, 450)

        layout = QVBoxLayout(self)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        full_text = message
        if tb and tb.strip() and tb.strip() != "NoneType: None":
            full_text = f"{message}\n\n{tb}"

        text_edit.setPlainText(full_text)
        text_edit.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        layout.addWidget(text_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @classmethod
    def show_error(cls, parent, title: str, message: str, tb: str = "") -> None:
        """Удобный статический метод для показа диалога."""
        dialog = cls(title, message, tb, parent)
        dialog.exec()


def show_current_exception(parent, title: str, message: str) -> None:
    """
    Показывает диалог с ТЕКУЩИМ исключением (traceback.format_exc()).

    Используется внутри блоков except.
    """
    tb = traceback.format_exc()
    ErrorDialog.show_error(parent, title, message, tb)