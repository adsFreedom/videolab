"""Валидация узлов и дерева."""
import fnmatch
from pathlib import Path

from core.processors import ProcessorRegistry
from core.utils import load_yaml


def _get_parent_run_at(project_root: Path, node_path: Path) -> str | None:
    """Возвращает last_run_at родительского узла (или None)."""
    parent_path = node_path.parent
    parent_yaml = parent_path / f"{parent_path.name}.yaml"

    if not parent_yaml.exists():
        return None

    parent_data = load_yaml(parent_yaml)
    return parent_data.get("last_run_at")


def validate_node(node_path: str) -> tuple[bool, str]:
    """Проверяет один узел (без учёта валидности родителей)."""
    node_path_obj = Path(node_path)

    if not node_path_obj.exists():
        return False, "Требуется обработка"

    yaml_file = node_path_obj / f"{node_path_obj.name}.yaml"
    if not yaml_file.exists():
        return False, "Требуется обработка"

    node_data = load_yaml(yaml_file)
    processor_name = node_data.get("processor", "")

    # --- source ---
    if processor_name == "source":
        input_file = node_data.get("input_file")
        if not input_file or not Path(input_file).exists():
            return False, "Требуется обработка"
        return True, ""

    # --- обработчик ---
    try:
        processor_class = ProcessorRegistry.get(processor_name)
    except KeyError:
        return False, "Требуется обработка"

    # 1. Snapshot есть?
    if "settings_snapshot" not in node_data:
        return False, "Требуется обработка"

    # 2. Выходные файлы на месте?
    expected = node_data.get("expected_outputs")
    if expected:
        for filename in expected:
            if not (node_path_obj / filename).exists():
                return False, "Требуется обработка"
    else:
        output_mask = processor_class.output_mask
        matches = [
            f for f in node_path_obj.iterdir()
            if f.is_file() and fnmatch.fnmatch(f.name, output_mask)
        ]
        if not matches:
            return False, "Требуется обработка"

    # 3. Настройки совпадают со snapshot?
    if node_data.get("settings") != node_data.get("settings_snapshot"):
        return False, "Требуется обработка"

    # 4. Входные файлы совпадают со snapshot?
    if node_data.get("input_files") != node_data.get("input_files_snapshot"):
        return False, "Требуется обработка"

    # 5. Родитель обработан не позже нас?
    parent_run_at = _get_parent_run_at(None, node_path_obj)
    if parent_run_at is not None:
        my_run_at = node_data.get("last_run_at")
        if my_run_at is None:
            return False, "Требуется обработка"
        if my_run_at < parent_run_at:
            return False, "Требуется обработка"

    return True, ""


def validate_tree(project_root: Path) -> dict[str, tuple[bool, str]]:
    """Валидирует всё дерево сверху вниз."""
    result: dict[str, tuple[bool, str]] = {}

    def _walk(node_path: Path, parent_valid: bool) -> None:
        yaml_file = node_path / f"{node_path.name}.yaml"
        if not yaml_file.exists():
            return

        if not parent_valid:
            result[str(node_path)] = (False, "Требуется обработка")
            is_valid = False
        else:
            is_valid, msg = validate_node(str(node_path))
            result[str(node_path)] = (is_valid, msg)

        if node_path.is_dir():
            for child in sorted(node_path.iterdir()):
                if child.is_dir():
                    child_yaml = child / f"{child.name}.yaml"
                    if child_yaml.exists():
                        _walk(child, is_valid)

    for item in sorted(project_root.iterdir()):
        if item.is_dir():
            yaml_file = item / f"{item.name}.yaml"
            if yaml_file.exists():
                _walk(item, True)

    return result