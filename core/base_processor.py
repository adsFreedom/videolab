"""Базовый класс для всех обработчиков."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseProcessor(ABC):
    """
    Базовый класс обработчика.

    Каждый обработчик должен определить:
    - name: уникальное имя (латиница, без пробелов)
    - display_name: название для UI
    - input_spec: описание входных файлов
    - output_mask: маска выходных файлов
    - settings_schema: схема настроек для генерации UI
    """

    # --- Обязательные атрибуты (переопределяются в наследниках) ---
    name: str = "base"
    display_name: str = "Базовый обработчик"

    # input_spec: словарь {логическое_имя: {"mask": "*.avi", "required": True}}
    # Пример: {"video": {"mask": "*.avi", "required": True}}
    input_spec: dict[str, dict[str, Any]] = {}

    # output_mask: маска для валидации выходных файлов
    # Пример: "output_*.avi"
    output_mask: str = "*"

    # expected_outputs: точный список ожидаемых файлов (опционально)
    # Если задан — валидация проверяет наличие ВСЕХ файлов из списка
    expected_outputs: list[str] | None = None

    # settings_schema: описание настроек для генерации UI
    # Пример: {"start_frame": {"type": "spinbox", "label": "...", "default": 0}}
    settings_schema: dict[str, dict[str, Any]] = {}

    # --- Методы ---

    @abstractmethod
    def run(
            self,
            input_files: dict[str, str],
            settings: dict[str, Any],
            output_dir: str,
    ) -> dict[str, Any]:
        """
        Основная функция обработки.

        Args:
            input_files: словарь {логическое_имя: абсолютный_путь}
                         Например: {"video": "/path/to/video.avi"}
            settings: словарь с настройками из YAML
            output_dir: папка, куда сохранять результаты

        Returns:
            Словарь с результатами:
            {
                "output_files": ["output_001.avi", ...],
                "metadata": {"frames": 100, "fps": 30}
            }
        """
        raise NotImplementedError

    def get_default_settings(self) -> dict[str, Any]:
        """Возвращает настройки по умолчанию из settings_schema."""
        return {
            key: schema.get("default")
            for key, schema in self.settings_schema.items()
        }

    def validate_settings(self, settings: dict[str, Any]) -> tuple[bool, str]:
        """
        Проверяет корректность настроек.
        Наследники могут переопределить для кастомной валидации.

        Returns: (is_valid, error_message)
        """
        for key, schema in self.settings_schema.items():
            if key not in settings:
                if schema.get("required", False):
                    return False, f"Отсутствует обязательный параметр: {key}"
                continue

            value = settings[key]

            # Проверка min/max для чисел
            if schema.get("type") in ("spinbox", "double_spinbox"):
                if "min" in schema and value < schema["min"]:
                    return False, f"{key} < {schema['min']}"
                if "max" in schema and value > schema["max"]:
                    return False, f"{key} > {schema['max']}"

        return True, ""