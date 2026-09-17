"""Управление проектом: создание узлов, валидация, поиск файлов."""
import os
import shutil
import fnmatch
from pathlib import Path
from typing import Any

from core.base_processor import BaseProcessor
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
    def create_project(cls, project_path: str | Path,
                       project_name: str) -> "ProjectManager":
        """
        Создает новый проект:
        - Создает папку проекта
        - Создает файл .videolab
        - Создает корневую папку source_0
        """
        project_path = Path(project_path).resolve()
        ensure_dir(project_path)

        # Создаем маркер проекта
        marker_file = project_path / PROJECT_MARKER
        if not marker_file.exists():
            save_yaml(marker_file, {
                "project_name": project_name,
                "created": timestamp(),
                "version": 1,
            })

        # Создаем корневую папку source_0
        source_dir = project_path / "source_0"
        if not source_dir.exists():
            ensure_dir(source_dir)
            save_yaml(source_dir / "source_0.yaml", {
                "processor": "source",
                "display_name": "Исходное видео",
                "created": timestamp(),
                "input_file": None,  # Пользователь заполнит позже
                "settings": {},
            })

        return cls(project_path)

    # ==================== ЧТЕНИЕ ДЕРЕВА ====================

    def get_tree(self) -> dict[str, Any]:
        """
        Возвращает дерево проекта.

        Формат:
        {
            "path": "/abs/path/to/node",
            "name": "source_0",
            "is_valid": True,
            "children": [ ... ]
        }
        """
        return self._scan_node(self.project_root)

    def _scan_node(self, node_path: Path) -> dict[str, Any]:
        """Рекурсивно сканирует узел и его потомков."""
        yaml_file = node_path / f"{node_path.name}.yaml"
        node_data = load_yaml(yaml_file)

        # Пропускаем папки без YAML (не узлы)
        if not node_data and node_path != self.project_root:
            return None

        is_valid, _ = self.validate_node(str(node_path))

        children = []
        if node_path.is_dir():
            for child in sorted(node_path.iterdir()):
                if child.is_dir():
                    # Ищем YAML внутри дочерней папки
                    child_yaml = child / f"{child.name}.yaml"
                    if child_yaml.exists():
                        child_node = self._scan_node(child)
                        if child_node:
                            children.append(child_node)

        return {
            "path": str(node_path),
            "name": node_path.name,
            "display_name": node_data.get("display_name", node_path.name),
            "is_valid": is_valid,
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
        """
        Создает новый узел-обработчик.

        Args:
            parent_path: путь к родительскому узлу
            processor_name: имя обработчика (из ProcessorRegistry)
            input_files: словарь {логическое_имя: абсолютный_путь}
            settings: настройки обработчика

        Returns:
            Путь к созданному узлу.
        """
        parent_path = Path(parent_path)

        # 1. Получаем класс обработчика
        processor_class = ProcessorRegistry.get(processor_name)

        # 2. Вычисляем следующий номер
        counter = self._get_next_counter(parent_path, processor_name)
        node_name = f"{processor_name}_{counter}"
        node_path = parent_path / node_name

        # 3. Создаем папку
        ensure_dir(node_path)

        # 4. Формируем YAML-данные
        yaml_data = {
            "processor": processor_name,
            "display_name": processor_class.display_name,
            "created": timestamp(),
            "input_files": input_files,
            "settings": settings,
            "expected_outputs": processor_class.expected_outputs,
        }

        # 5. Сохраняем YAML
        save_yaml(node_path / f"{node_name}.yaml", yaml_data)

        return str(node_path)

    def _get_next_counter(self, parent_path: Path, processor_name: str) -> int:
        """
        Вычисляет следующий номер для имени обработчика.

        Если в parent_path уже есть папки crop_1, crop_3,
        то следующий будет crop_4 (максимум + 1).

        Если папок нет — возвращает 1.
        """
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

    # ==================== ВАЛИДАЦИЯ ====================

    def validate_node(self, node_path: str) -> tuple[bool, str]:
        """
        Проверяет узел:
        - Существует ли папка?
        - Есть ли YAML?
        - Есть ли выходные файлы по маске?

        Returns: (is_valid, error_message)
        """
        node_path = Path(node_path)

        if not node_path.exists():
            return False, "Папка не существует"

        yaml_file = node_path / f"{node_path.name}.yaml"
        if not yaml_file.exists():
            return False, "Отсутствует YAML-файл"

        node_data = load_yaml(yaml_file)
        processor_name = node_data.get("processor", "")

        # Корневой узел source_0 — валиден, если есть input_file
        if processor_name == "source":
            input_file = node_data.get("input_file")
            if not input_file or not Path(input_file).exists():
                return False, "Не задан или не существует исходный файл"
            return True, ""

        # Для обработчиков — проверяем выходные файлы
        try:
            processor_class = ProcessorRegistry.get(processor_name)
        except KeyError:
            return False, f"Обработчик '{processor_name}' не зарегистрирован"

        # Точный список файлов?
        expected = node_data.get("expected_outputs")
        if expected:
            for filename in expected:
                if not (node_path / filename).exists():
                    return False, f"Отсутствует файл: {filename}"
            return True, ""

        # Иначе — ищем по маске
        output_mask = processor_class.output_mask
        matches = [
            f for f in node_path.iterdir()
            if f.is_file() and fnmatch.fnmatch(f.name, output_mask)
        ]

        if not matches:
            return False, f"Нет файлов по маске '{output_mask}'"

        return True, ""

    # ==================== ПОИСК ВХОДНЫХ ФАЙЛОВ ====================

    def scan_for_inputs(self, start_path: str, mask: str) -> list[str]:
        """
        Ищет файлы по маске в start_path и во всех родителях
        вверх до корня проекта.

        Returns: список абсолютных путей к найденным файлам.
        """
        start_path = Path(start_path).resolve()
        results = []

        current = start_path
        while True:
            if current.is_dir():
                for item in sorted(current.iterdir()):
                    if item.is_file() and fnmatch.fnmatch(item.name, mask):
                        results.append(str(item))

            # Остановка на корне проекта
            if current == self.project_root:
                break

            # Поднимаемся на уровень выше, но не выше корня проекта
            parent = current.parent
            if parent == current or not str(parent).startswith(
                    str(self.project_root)):
                break
            current = parent

        return results

    # ==================== РЕГИСТРАЦИЯ ИСХОДНОГО ВИДЕО ====================

    def register_source_video(self, source_node_path: str,
                              video_path: str) -> None:
        """
        Регистрирует исходное видео в корневом узле source_0.
        Копирует видео в папку проекта (или создает ссылку).
        """
        source_node_path = Path(source_node_path)
        video_path = Path(video_path).resolve()

        if not video_path.exists():
            raise FileNotFoundError(f"Видео не найдено: {video_path}")

        # Копируем видео в папку source_0
        target = source_node_path / video_path.name
        if not target.exists():
            shutil.copy2(video_path, target)

        # Обновляем YAML
        yaml_file = source_node_path / f"{source_node_path.name}.yaml"
        data = load_yaml(yaml_file)
        data["input_file"] = str(target)
        save_yaml(yaml_file, data)

    # ==================== ОБНАРУЖЕНИЕ ОБРАБОТЧИКОВ ====================

    def get_available_processors(self, node_path: str) -> list[
        type[BaseProcessor]]:
        """
        Возвращает список обработчиков, доступных для узла.

        Обработчик доступен, если:
        - Все обязательные входы (required=True) найдены
          в node_path или у родителей.
        """
        available = []

        for name, processor_class in ProcessorRegistry.get_all().items():
            # Пропускаем обработчик "source" — он только для корня
            if name == "source":
                continue

            # Проверяем все обязательные входы
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

    def get_input_files_for_processor(
            self,
            node_path: str,
            processor_class: type[BaseProcessor],
    ) -> dict[str, list[str]]:
        """
        Возвращает доступные файлы для каждого входа обработчика.

        Returns:
            {"video": ["/path/a.avi", "/path/b.avi"], "coords": [...]}
        """
        result = {}
        for input_name, spec in processor_class.input_spec.items():
            mask = spec["mask"]
            files = self.scan_for_inputs(node_path, mask)
            result[input_name] = files
        return result