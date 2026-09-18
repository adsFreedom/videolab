"""Сканирование дерева проекта."""
from pathlib import Path
from typing import Any

from core.utils import load_yaml


def get_tree(project_root: Path) -> dict[str, Any]:
    """Возвращает дерево проекта начиная с project_root."""
    return _scan_node(project_root, project_root)


def _scan_node(node_path: Path, project_root: Path) -> dict[str, Any]:
    """Рекурсивно сканирует узел и его потомков."""
    yaml_file = node_path / f"{node_path.name}.yaml"
    node_data = load_yaml(yaml_file)

    if not node_data and node_path != project_root:
        return None

    children = []
    if node_path.is_dir():
        for child in sorted(node_path.iterdir()):
            if child.is_dir():
                child_yaml = child / f"{child.name}.yaml"
                if child_yaml.exists():
                    child_node = _scan_node(child, project_root)
                    if child_node:
                        children.append(child_node)

    return {
        "path": str(node_path),
        "name": node_path.name,
        "display_name": node_data.get("display_name", node_path.name),
        "processor": node_data.get("processor", ""),
        "children": children,
    }


def get_node_info(node_path: str) -> dict[str, Any]:
    """Возвращает YAML-данные узла."""
    path = Path(node_path)
    yaml_file = path / f"{path.name}.yaml"
    return load_yaml(yaml_file)