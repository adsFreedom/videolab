"""Утилиты для работы с файловой системой и YAML."""
import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_MARKER = ".videolab"


def load_yaml(path: str | Path) -> dict:
    """Загружает YAML-файл. Возвращает пустой dict, если файла нет."""
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: str | Path, data: dict) -> None:
    """Сохраняет данные в YAML с читаемым форматированием."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )


def find_project_root(start_path: str | Path) -> Path | None:
    """
    Ищет корень проекта (папку с файлом .videolab),
    поднимаясь вверх по дереву от start_path.
    """
    current = Path(start_path).resolve()
    while True:
        if (current / PROJECT_MARKER).exists():
            return current
        if current.parent == current:  # Дошли до корня диска
            return None
        current = current.parent


def timestamp() -> str:
    """Возвращает текущую дату-время в читаемом формате."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_dir(path: str | Path) -> Path:
    """Создает директорию, если её нет. Возвращает Path."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path