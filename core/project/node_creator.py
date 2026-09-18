"""Создание узлов-обработчиков."""
from pathlib import Path
from typing import Any

from core.processor_registry import ProcessorRegistry
from core.utils import save_yaml, timestamp, ensure_dir


def get_next_counter(parent_path: Path, processor_name: str) -> int:
    """Вычисляет следующий номер для имени обработчика."""
    if not parent_path.exists():
        return 1

    max_num = 0
    pattern = f"{processor_name}_"

    for item in parent_path.iterdir():
        if item.is_dir() and item.name.startswith(pattern):
            suffix = item.name[len(pattern):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))

    return max_num + 1


def create_processor_node(
    parent_path: str,
    processor_name: str,
    input_files: dict[str, str],
    settings: dict[str, Any],
) -> str:
    """Создает новый узел-обработчик. Возвращает путь к нему."""
    parent_path = Path(parent_path)
    processor_class = ProcessorRegistry.get(processor_name)

    counter = get_next_counter(parent_path, processor_name)
    node_name = f"{processor_name}_{counter}"
    node_path = parent_path / node_name

    ensure_dir(node_path)

    yaml_data = {
        "processor": processor_name,
        "display_name": processor_class.display_name,
        "created": timestamp(),
        "input_files": input_files,
        "settings": settings,
    }

    save_yaml(node_path / f"{node_name}.yaml", yaml_data)

    return str(node_path)