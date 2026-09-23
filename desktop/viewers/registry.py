"""Реестр просмотрщиков по расширению файла."""
from pathlib import Path


class ViewerRegistry:
    """
    Реестр просмотрщиков.

    Хранит сопоставление: расширение файла → класс просмотрщика.
    """

    _viewers: dict[str, type] = {}

    @classmethod
    def register(cls, extensions: list[str], viewer_class: type) -> None:
        """
        Регистрирует просмотрщик для указанных расширений.

        extensions: [".avi", ".mp4", ".mov"]
        viewer_class: класс, наследник BaseViewer
        """
        for ext in extensions:
            ext = ext.lower()
            if not ext.startswith("."):
                ext = "." + ext
            cls._viewers[ext] = viewer_class

    @classmethod
    def get_viewer_class(cls, file_path: str) -> type | None:
        """Возвращает класс просмотрщика для файла (или None)."""
        ext = Path(file_path).suffix.lower()
        return cls._viewers.get(ext)

    @classmethod
    def can_view(cls, file_path: str) -> bool:
        """Может ли какой-нибудь просмотрщик открыть этот файл."""
        return cls.get_viewer_class(file_path) is not None

    @classmethod
    def get_all(cls) -> dict[str, type]:
        """Все зарегистрированные расширения."""
        return cls._viewers.copy()

    @classmethod
    def clear(cls) -> None:
        """Очистить реестр (для тестов)."""
        cls._viewers.clear()