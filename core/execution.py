"""Контекст выполнения обработчика: прогресс и отмена."""
from dataclasses import dataclass, field
from typing import Callable
import threading


class CancelledError(Exception):
    """Исключение, выбрасываемое при отмене обработки."""
    pass


@dataclass
class ExecutionContext:
    """
    Контекст выполнения обработчика.

    Обработчик может:
    - вызывать report_progress(current, total) — для определённого прогресса
    - вызывать report_progress_unknown() — для неопределённого
    - проверять is_cancelled() — и прерывать работу
    - вызывать check_cancel() — выбросит CancelledError, если отменено
    """
    _progress_callback: Callable[[int, int], None] | None = None
    _cancel_event: threading.Event = field(default_factory=threading.Event)
    _unknown_progress: bool = False

    def report_progress(self, current: int, total: int) -> None:
        """Сообщает о прогрессе (current из total)."""
        if self._progress_callback:
            self._progress_callback(current, total)

    def report_progress_unknown(self) -> None:
        """Сообщает, что прогресс неопределён."""
        self._unknown_progress = True
        if self._progress_callback:
            self._progress_callback(-1, -1)

    def is_cancelled(self) -> bool:
        """Проверяет, отменена ли обработка."""
        return self._cancel_event.is_set()

    def check_cancel(self) -> None:
        """Выбрасывает CancelledError, если отмена запрошена."""
        if self.is_cancelled():
            raise CancelledError("Обработка отменена пользователем")

    def cancel(self) -> None:
        """Запросить отмену (вызывается из UI)."""
        self._cancel_event.set()