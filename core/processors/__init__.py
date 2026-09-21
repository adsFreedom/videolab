"""Модуль обработчиков."""
from core.processors.base import BaseProcessor
from core.processors.registry import ProcessorRegistry

__all__ = ["BaseProcessor", "ProcessorRegistry"]