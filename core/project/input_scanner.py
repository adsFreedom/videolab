"""Поиск входных файлов и доступных обработчиков."""
import fnmatch
from pathlib import Path

from core.processors import ProcessorRegistry


def scan_for_inputs(project_root: Path, start_path: str, mask: str) -> list[str]:
    """Ищет файлы по маске вверх по дереву до корня проекта."""
    start_path = Path(start_path).resolve()
    results = []

    current = start_path
    while True:
        if current.is_dir():
            for item in sorted(current.iterdir()):
                if item.is_file() and fnmatch.fnmatch(item.name, mask):
                    results.append(str(item))

        if current == project_root:
            break

        parent = current.parent
        if parent == current or not str(parent).startswith(str(project_root)):
            break
        current = parent

    return results


def get_available_processors(project_root: Path, node_path: str) -> list[type]:
    """Возвращает список обработчиков, доступных для узла."""
    available = []

    for name, processor_class in ProcessorRegistry.get_all().items():
        if name == "source":
            continue

        all_found = True
        for input_name, spec in processor_class.input_spec.items():
            if not spec.get("required", True):
                continue

            mask = spec["mask"]
            found = scan_for_inputs(project_root, node_path, mask)
            if not found:
                all_found = False
                break

        if all_found:
            available.append(processor_class)

    return available