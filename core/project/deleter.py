"""Удаление узлов с каскадом."""
import shutil
from pathlib import Path


def get_descendants(node_path: str) -> list[str]:
    """Возвращает список ВСЕХ потомков узла (рекурсивно)."""
    node_path_obj = Path(node_path)
    descendants: list[str] = []

    def _collect(path: Path) -> None:
        if path.is_dir():
            for child in sorted(path.iterdir()):
                if child.is_dir():
                    child_yaml = child / f"{child.name}.yaml"
                    if child_yaml.exists():
                        _collect(child)
                        descendants.append(str(child))

    _collect(node_path_obj)
    return descendants


def delete_node(node_path: str) -> None:
    """Удаляет узел со всеми потомками."""
    node_path_obj = Path(node_path)
    if not node_path_obj.exists():
        return
    shutil.rmtree(node_path_obj)