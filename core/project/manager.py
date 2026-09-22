"""Менеджер проекта — тонкий фасад над подмодулями."""
from pathlib import Path
from typing import Any

from core.processors import BaseProcessor
from core.execution import ExecutionContext, CancelledError
from core.processors import ProcessorRegistry
from core.utils import (
    PROJECT_MARKER,
    load_yaml,
    save_yaml,
    timestamp,
    ensure_dir,
)

from core.project import tree_scanner
from core.project import node_creator
from core.project import input_scanner
from core.project import validator
from core.project import deleter
from core.project import source_registrar


class ProjectManager:
    """Управляет проектом VideoLab."""

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

    # ==================== ДЕРЕВО ====================

    def get_tree(self) -> dict[str, Any]:
        return tree_scanner.get_tree(self.project_root)

    def get_node_info(self, node_path: str) -> dict[str, Any]:
        return tree_scanner.get_node_info(node_path)

    # ==================== УЗЛЫ ====================

    def create_processor_node(
        self,
        parent_path: str,
        processor_name: str,
        input_files: dict[str, str],
        settings: dict[str, Any],
    ) -> str:
        return node_creator.create_processor_node(
            parent_path, processor_name, input_files, settings
        )

    # ==================== SOURCE ====================

    def register_source_video(self, source_node_path: str, video_path: str) -> None:
        source_registrar.register_source_video(source_node_path, video_path)

    # ==================== ПОИСК ====================

    def scan_for_inputs(self, start_path: str, mask: str) -> list[str]:
        return input_scanner.scan_for_inputs(
            self.project_root, start_path, mask
        )

    def get_available_processors(self, node_path: str) -> list[type[BaseProcessor]]:
        return input_scanner.get_available_processors(
            self.project_root, node_path
        )

    # ==================== ОБРАБОТКА ====================

    def get_node_processor(self, node_path: str) -> BaseProcessor:
        """Возвращает экземпляр обработчика для узла."""
        node_data = self.get_node_info(node_path)
        processor_name = node_data.get("processor", "")
        processor_class = ProcessorRegistry.get(processor_name)
        return processor_class()

    def run_node(self, node_path: str, context: ExecutionContext | None = None) -> dict:
        """Запускает обработку узла (синхронно, без потока)."""
        import time

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
        return validator.validate_node(node_path)

    def validate_subtree(self, node_path: str) -> dict[str, tuple[bool, str]]:
        """Валидирует узел и всех его потомков сверху вниз."""
        return validator.validate_subtree(node_path)

    def validate_tree(self) -> dict[str, tuple[bool, str]]:
        return validator.validate_tree(self.project_root)

    # ==================== УДАЛЕНИЕ ====================

    def get_descendants(self, node_path: str) -> list[str]:
        return deleter.get_descendants(node_path)

    def delete_node(self, node_path: str) -> None:
        deleter.delete_node(node_path)