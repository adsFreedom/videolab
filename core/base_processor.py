"""Базовый класс для всех обработчиков."""
from abc import ABC, abstractmethod
from typing import Any

from core.execution import ExecutionContext


class BaseProcessor(ABC):
    """
    Базовый класс обработчика.

    Атрибуты:
        name            — уникальное имя (латиница, без пробелов)
        display_name    — название для UI
        category        — категория для группировки в UI
        icon            — эмодзи-иконка
        input_spec      — описание входных файлов
        output_mask     — маска выходных файлов
        settings_schema — схема настроек
    """

    name: str = "base"
    display_name: str = "Базовый обработчик"
    category: str = "Общее"
    icon: str = "📁"

    input_spec: dict[str, dict[str, Any]] = {}
    output_mask: str = "*"
    expected_outputs: list[str] | None = None
    settings_schema: dict[str, dict[str, Any]] = {}

    @abstractmethod
    def run(
        self,
        input_files: dict[str, str],
        settings: dict[str, Any],
        output_dir: str,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """
        Основная функция обработки.

        Args:
            input_files: {логическое_имя: путь_к_файлу}
            settings: настройки из YAML
            output_dir: папка для результатов
            context: контекст выполнения (прогресс + отмена)

        Returns:
            {
                "output_files": [...],
                "metadata": {...}
            }
        """
        raise NotImplementedError

    def get_default_settings(self) -> dict[str, Any]:
        return {
            key: schema.get("default")
            for key, schema in self.settings_schema.items()
        }

    def validate_settings(self, settings: dict[str, Any]) -> tuple[bool, str]:
        for key, schema in self.settings_schema.items():
            if key not in settings:
                if schema.get("required", False):
                    return False, f"Отсутствует обязательный параметр: {key}"
                continue

            value = settings[key]

            if schema.get("type") in ("spinbox", "double_spinbox"):
                if "min" in schema and value < schema["min"]:
                    return False, f"{key} < {schema['min']}"
                if "max" in schema and value > schema["max"]:
                    return False, f"{key} > {schema['max']}"

        return True, ""