"""Контекст выполнения обработчика: прогресс, отмена, состояние."""
import threading


class CancelledError(Exception):
    """Исключение, выбрасываемое при отмене обработки."""
    pass


class ExecutionContext:
    """
    Общий объект между UI-потоком и рабочим потоком.

    Рабочий поток ПИШЕТ в поля: current, total, message, done, error, cancelled, result.
    UI-поток ЧИТАЕТ эти поля по таймеру.

    Все поля — простые типы (int, bool, str, dict), присвоение которых атомарно
    благодаря GIL. Никаких сигналов, никаких блокировок.

    Поля:
        current      — текущий шаг прогресса
        total        — всего шагов (0 = неизвестно)
        message      — текстовое сообщение от обработчика
        done         — True, когда работа завершена (успешно или с ошибкой)
        cancelled    — True, если пользователь запросил отмену
        error        — текст ошибки (или None)
        traceback    — полный traceback ошибки (или None)
        result       — результат работы (dict, пишется один раз перед done=True)
        has_progress — True, если обработчик сообщал прогресс (иначе крутящийся индикатор)
    """

    def __init__(self):
        self.current: int = 0
        self.total: int = 0
        self.message: str = ""
        self.done: bool = False
        self.cancelled: bool = False
        self.error: str | None = None
        self.traceback: str | None = None
        self.result: dict | None = None
        self.has_progress: bool = False

        # Для отмены из UI-потока
        self._cancel_event = threading.Event()

    # ==================== API ДЛЯ ОБРАБОТЧИКА ====================

    def report_progress(self, current: int, total: int, message: str = "") -> None:
        """Обработчик сообщает о прогрессе."""
        self.current = current
        self.total = total
        if message:
            self.message = message
        self.has_progress = True

    def report_message(self, message: str) -> None:
        """Обработчик сообщает о текущем действии (без прогресса)."""
        self.message = message

    def check_cancel(self) -> None:
        """Выбрасывает CancelledError, если отмена запрошена."""
        if self._cancel_event.is_set():
            raise CancelledError("Обработка отменена пользователем")

    def is_cancelled(self) -> bool:
        """Проверяет, отменена ли обработка."""
        return self._cancel_event.is_set()

    # ==================== API ДЛЯ UI ====================

    def cancel(self) -> None:
        """Запросить отмену. Вызывается из UI-потока."""
        self._cancel_event.set()
        self.cancelled = True