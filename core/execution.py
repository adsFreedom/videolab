"""Контекст выполнения обработчика: отмена и результат."""
import threading

from core.progress_registry import progress_registry


class CancelledError(Exception):
    """Исключение, выбрасываемое при отмене обработки."""
    pass


class ExecutionContext:
    """
    Общий объект между UI-потоком и рабочим потоком.

    Прогресс — в ProgressRegistry (глобально).
    Отмена / ошибки / результат — здесь.
    """

    def __init__(self, node_path: str = ""):
        self.node_path = node_path

        # Флаги состояния (пишет worker, читает UI)
        self.done: bool = False
        self.cancelled: bool = False
        self.error: str | None = None
        self.traceback: str | None = None
        self.result: dict | None = None

        self._cancel_event = threading.Event()

    # ==================== API ДЛЯ ОБРАБОТЧИКА ====================

    def report_progress(self, current: int, total: int, message: str = "") -> None:
        """Обработчик сообщает о прогрессе. Пишет в ProgressRegistry."""
        if self.node_path:
            progress_registry.set(self.node_path, current, total)

    def report_message(self, message: str) -> None:
        """Заглушка — на будущее, если понадобится."""
        pass

    def check_cancel(self) -> None:
        """Выбрасывает CancelledError, если отмена запрошена."""
        if self._cancel_event.is_set():
            raise CancelledError("Обработка отменена пользователем")

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    # ==================== API ДЛЯ UI ====================

    def cancel(self) -> None:
        """Запросить отмену."""
        self._cancel_event.set()
        self.cancelled = True