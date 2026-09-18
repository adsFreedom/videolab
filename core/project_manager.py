"""Управление проектом: создание узлов, валидация, поиск файлов."""
import os
import shutil
import fnmatch
import time
from pathlib import Path
from typing import Any

from core.base_processor import BaseProcessor
from core.execution import ExecutionContext, CancelledError
from core.processor_registry import ProcessorRegistry
from core.utils import (
    PROJECT_MARKER,
    load_yaml,
    save_yaml,
    find_project_root,
    timestamp,
    ensure_dir,
)


class ProjectManager:
    """
    Управляет проектом VideoLab.

    Проект = папка с файлом .videolab в корне.
    Каждый узел = папка с YAML-файлом {name}.yaml.
    """

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()

        if not (self.project_root / PROJECT_MARKER).exists():
            raise ValueError(
                f"Папка {self.project_root} не является проектом VideoLab "
                f"(отсутствует {PROJECT_MARKER})"
            )

    # ==================== СОЗДАНИЕ ПРОЕКТА ====================

    @classmethod
    def create_project(
        cls, project_path: str | Path, project_name: str
    ) -> "ProjectManager":
        """Создает новый проект."""
        project_path = Path(project_path).resolve()
        ensure_dir(project_path)

        marker_file = project_path / PROJECT_MARKER
        if not marker_file.exists():
            save_yaml(marker_file, {
                "project_name": project_name,
                "created": timestamp(),
                "version": 1,
            })

        source_dir = project_path / "source_0"
        if not source_dir.exists():
            ensure_dir(source_dir)
            save_yaml(source_dir / "source_0.yaml", {
                "processor": "source",
                "display_name": "Исходное видео",
                "created": timestamp(),
                "input_file": None,
                "settings": {},
                "last_run_at": None,
            })

        return cls(project_path)

    # ==================== ЧТЕНИЕ ДЕРЕВА ====================

    def get_tree(self) -> dict[str, Any]:
        """Возвращает дерево проекта."""
        return self._scan_node(self.project_root)

    def _scan_node(self, node_path: Path) -> dict[str, Any]:
        """Рекурсивно сканирует узел и его потомков."""
        yaml_file = node_path / f"{node_path.name}.yaml"
        node_data = load_yaml(yaml_file)

        if not node_data and node_path != self.project_root:
            return None

        children = []
        if node_path.is_dir():
            for child in sorted(node_path.iterdir()):
                if child.is_dir():
                    child_yaml = child / f"{child.name}.yaml"
                    if child_yaml.exists():
                        child_node = self._scan_node(child)
                        if child_node:
                            children.append(child_node)

        return {
            "path": str(node_path),
            "name": node_path.name,
            "display_name": node_data.get("display_name", node_path.name),
            "processor": node_data.get("processor", ""),
            "children": children,
        }

    def get_node_info(self, node_path: str) -> dict[str, Any]:
        """Возвращает YAML-данные узла."""
        node_path = Path(node_path)
        yaml_file = node_path / f"{node_path.name}.yaml"
        return load_yaml(yaml_file)

    # ==================== СОЗДАНИЕ ОБРАБОТЧИКА ====================

    def create_processor_node(
        self,
        parent_path: str,
        processor_name: str,
        input_files: dict[str, str],
        settings: dict[str, Any],
    ) -> str:
        """Создает новый узел-обработчик."""
        parent_path = Path(parent_path)

        processor_class = ProcessorRegistry.get(processor_name)

        counter = self._get_next_counter(parent_path, processor_name)
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

    def _get_next_counter(self, parent_path: Path, processor_name: str) -> int:
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

    # ==================== РЕГИСТРАЦИЯ ИСХОДНОГО ВИДЕО ====================

    def register_source_video(self, source_node_path: str, video_path: str) -> None:
        """Регистрирует исходное видео в корневом узле source_0."""
        source_node_path = Path(source_node_path)
        video_path = Path(video_path).resolve()

        if not video_path.exists():
            raise FileNotFoundError(f"Видео не найдено: {video_path}")

        target = source_node_path / video_path.name
        if not target.exists():
            shutil.copy2(video_path, target)

        yaml_file = source_node_path / f"{source_node_path.name}.yaml"
        data = load_yaml(yaml_file)
        data["input_file"] = str(target)
        data["last_run_at"] = timestamp()
        save_yaml(yaml_file, data)

    # ==================== ПОИСК ВХОДНЫХ ФАЙЛОВ ====================

    def scan_for_inputs(self, start_path: str, mask: str) -> list[str]:
        """Ищет файлы по маске вверх по дереву до корня проекта."""
        start_path = Path(start_path).resolve()
        results = []

        current = start_path
        while True:
            if current.is_dir():
                for item in sorted(current.iterdir()):
                    if item.is_file() and fnmatch.fnmatch(item.name, mask):
                        results.append(str(item))

            if current == self.project_root:
                break

            parent = current.parent
            if parent == current or not str(parent).startswith(str(self.project_root)):
                break
            current = parent

        return results

    # ==================== ОБНАРУЖЕНИЕ ОБРАБОТЧИКОВ ====================

    def get_available_processors(self, node_path: str) -> list[type[BaseProcessor]]:
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
                found = self.scan_for_inputs(node_path, mask)
                if not found:
                    all_found = False
                    break

            if all_found:
                available.append(processor_class)

        return available

    # ==================== ЗАПУСК ОБРАБОТКИ ====================

    def get_node_processor(self, node_path: str) -> BaseProcessor:
        """Возвращает ЭКЗЕМПЛЯР обработчика для узла."""
        node_data = self.get_node_info(node_path)
        processor_name = node_data.get("processor", "")
        processor_class = ProcessorRegistry.get(processor_name)
        return processor_class()

    def _get_parent_run_at(self, node_path: Path) -> str | None:
        """Возвращает last_run_at родительского узла (или None)."""
        parent_path = node_path.parent
        parent_yaml = parent_path / f"{parent_path.name}.yaml"

        if not parent_yaml.exists():
            return None

        parent_data = load_yaml(parent_yaml)
        return parent_data.get("last_run_at")

    def run_node(self, node_path: str, context: ExecutionContext | None = None) -> dict:
        """
        Запускает обработку узла.

        Если context=None — создаётся пустой (без прогресса и отмены).
        Если обработка отменена — возвращает {"cancelled": True}, snapshot НЕ пишется.
        """
        if context is None:
            context = ExecutionContext()

        node_path_obj = Path(node_path)
        node_data = self.get_node_info(node_path)
        processor = self.get_node_processor(node_path)

        start_time = time.time()

        try:
            result = processor.run(
                input_files=node_data.get("input_files", {}),
                settings=node_data.get("settings", {}),
                output_dir=node_path,
                context=context,
            )
        except CancelledError:
            duration = time.time() - start_time
            return {
                "cancelled": True,
                "duration_seconds": round(duration, 3),
            }

        duration = time.time() - start_time

        yaml_file = node_path_obj / f"{node_path_obj.name}.yaml"

        if result.get("output_files"):
            node_data["expected_outputs"] = result["output_files"]

        node_data["settings_snapshot"] = dict(node_data.get("settings", {}))
        node_data["input_files_snapshot"] = dict(node_data.get("input_files", {}))
        node_data["last_run_at"] = timestamp()
        node_data["last_duration_seconds"] = round(duration, 3)

        save_yaml(yaml_file, node_data)

        return result

    # ==================== ВАЛИДАЦИЯ ====================

    def validate_node(self, node_path: str) -> tuple[bool, str]:
        """Проверяет ОДИН узел (без учёта валидности родителей)."""
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
        parent_run_at = self._get_parent_run_at(node_path_obj)
        if parent_run_at is not None:
            my_run_at = node_data.get("last_run_at")
            if my_run_at is None:
                return False, "Требуется обработка"
            if my_run_at < parent_run_at:
                return False, "Требуется обработка"

        return True, ""

    def validate_tree(self) -> dict[str, tuple[bool, str]]:
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
                is_valid, msg = self.validate_node(str(node_path))
                result[str(node_path)] = (is_valid, msg)

            if node_path.is_dir():
                for child in sorted(node_path.iterdir()):
                    if child.is_dir():
                        child_yaml = child / f"{child.name}.yaml"
                        if child_yaml.exists():
                            _walk(child, is_valid)

        for item in sorted(self.project_root.iterdir()):
            if item.is_dir():
                yaml_file = item / f"{item.name}.yaml"
                if yaml_file.exists():
                    _walk(item, True)

        return result

    # ==================== УДАЛЕНИЕ С КАСКАДОМ ====================

    def get_descendants(self, node_path: str) -> list[str]:
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

    def delete_node(self, node_path: str) -> None:
        """Удаляет узел со всеми потомками."""
        node_path_obj = Path(node_path)
        if not node_path_obj.exists():
            return
        shutil.rmtree(node_path_obj)