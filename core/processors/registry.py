"""Реестр обработчиков. Хранит все зарегистрированные обработчики."""
from typing import Type
from core.processors.base import BaseProcessor


class ProcessorRegistry:
    """Глобальный реестр обработчиков (синглтон)."""

    _processors: dict[str, Type[BaseProcessor]] = {}

    @classmethod
    def register(cls, processor_class: Type[BaseProcessor]) -> Type[BaseProcessor]:
        if not issubclass(processor_class, BaseProcessor):
            raise TypeError(
                f"{processor_class.__name__} должен наследоваться от BaseProcessor"
            )

        name = processor_class.name
        if name in cls._processors:
            raise ValueError(f"Обработчик '{name}' уже зарегистрирован")

        cls._processors[name] = processor_class
        return processor_class

    @classmethod
    def get(cls, name: str) -> Type[BaseProcessor]:
        if name not in cls._processors:
            raise KeyError(f"Обработчик '{name}' не найден")
        return cls._processors[name]

    @classmethod
    def get_all(cls) -> dict[str, Type[BaseProcessor]]:
        return cls._processors.copy()

    @classmethod
    def clear(cls) -> None:
        cls._processors.clear()