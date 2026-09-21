"""Глобальный реестр прогресса обработки.

Используется:
- Worker пишет прогресс: set(node_path, current, total).
- TreeDelegate читает прогресс: get(node_path).
- TreePanel опрашивает: has_active() для запуска таймера обновления.

Потокобезопасность: атомарные операции (dict на уровне Python + GIL).
Достаточно для нашей задачи.
"""


class ProgressRegistry:
    """
    Глобальный реестр прогресса (синглтон).

    Формат записи: {node_path: (current, total)}
    - total > 0 — определённый прогресс
    - total == 0 — неопределённый (пульсация/волна)
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._entries: dict[str, tuple[int, int]] = {}
            cls._instance._active_node: str | None = None
        return cls._instance

    # ==================== ДЛЯ WORKER ====================

    def set(self, node_path: str, current: int, total: int) -> None:
        """Устанавливает прогресс для узла. Вызывается из worker-потока."""
        self._entries[node_path] = (current, total)
        self._active_node = node_path

    def clear(self, node_path: str) -> None:
        """Убирает запись для узла."""
        self._entries.pop(node_path, None)
        if self._active_node == node_path:
            self._active_node = None

    def clear_all(self) -> None:
        """Очищает всё (на всякий случай)."""
        self._entries.clear()
        self._active_node = None

    # ==================== ДЛЯ UI ====================

    def get(self, node_path: str) -> tuple[int, int] | None:
        """Возвращает (current, total) или None, если узел не активен."""
        return self._entries.get(node_path)

    def has_active(self) -> bool:
        """Есть ли сейчас активная обработка?"""
        return bool(self._entries)

    def get_active_node(self) -> str | None:
        """Путь к обрабатываемому узлу (или None)."""
        return self._active_node


# Глобальный синглтон
progress_registry = ProgressRegistry()