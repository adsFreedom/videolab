"""Глобальный логгер VideoLab.

Позволяет любому модулю отправлять сообщения в UI-лог
без прямой ссылки на MainWindow. Использует паттерн Observer.

Использование:
    from core.logger import log
    log("ERROR", "Что-то сломалось")
    log("ERROR", "Что-то сломалось", exc_info=True)  # с traceback
"""
import traceback
from typing import Callable


class Logger:
    """Глобальный логгер. Хранит подписчиков и рассылает сообщения."""

    _instance: "Logger | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers: list[Callable] = []
        return cls._instance

    def subscribe(self, callback: Callable[[str, str], None]) -> None:
        """Подписывает callback(level, message) на лог."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable) -> None:
        """Отписывает callback."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def log(self, level: str, message: str, exc_info: bool = False) -> None:
        """
        Отправляет сообщение всем подписчикам.

        Args:
            level: "INFO" | "SUCCESS" | "WARNING" | "ERROR"
            message: текст сообщения
            exc_info: если True — добавляет полный traceback
        """
        if exc_info:
            tb = traceback.format_exc()
            if tb and tb.strip() != "NoneType: None":
                message = f"{message}\n\n{tb}"

        for callback in self._subscribers:
            try:
                callback(level, message)
            except Exception as e:
                # Не даем логгеру упасть, если один из подписчиков сломан
                print(f"[logger] Ошибка в подписчике: {e}")


# Глобальный синглтон
logger = Logger()


def log(level: str, message: str, exc_info: bool = False) -> None:
    """Удобная функция для логирования."""
    logger.log(level, message, exc_info=exc_info)