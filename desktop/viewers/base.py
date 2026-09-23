"""Базовый класс просмотрщика."""
from PySide6.QtWidgets import QWidget


class BaseViewer(QWidget):
    """
    Базовый класс для всех просмотрщиков.

    Каждый просмотрщик:
    - загружает файл через load()
    - отображает его
    - может освобождать ресурсы через cleanup()
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def load(self, file_path: str) -> None:
        """Загружает файл в просмотрщик."""
        raise NotImplementedError(
            f"{self.__class__.__name__} не реализует load()"
        )

    def cleanup(self) -> None:
        """Освобождает ресурсы (например, видео)."""
        pass