"""Тесты ядра ProjectManager и ProcessorRegistry."""
import shutil
import tempfile
from pathlib import Path

import pytest

from core.project import ProjectManager
from core.processor_registry import ProcessorRegistry
from core.base_processor import BaseProcessor


# ==================== ТЕСТОВЫЙ ОБРАБОТЧИК ====================

class DummyProcessor(BaseProcessor):
    name = "dummy"
    display_name = "Тестовый обработчик"
    category = "Тест"
    icon = "🧪"
    input_spec = {"video": {"mask": "*.avi", "required": True}}
    output_mask = "output_*.avi"
    settings_schema = {
        "param1": {"type": "spinbox", "label": "Параметр", "default": 10, "min": 0},
    }

    def run(self, input_files, settings, output_dir, context):
        output_file = Path(output_dir) / "output_001.avi"
        output_file.write_text("fake video")
        return {"output_files": ["output_001.avi"]}


# ==================== ФИКСТУРЫ ====================

@pytest.fixture(autouse=True)
def fresh_registry():
    """Очищает реестр и перерегистрирует DummyProcessor перед каждым тестом."""
    ProcessorRegistry.clear()
    ProcessorRegistry.register(DummyProcessor)
    yield
    ProcessorRegistry.clear()


@pytest.fixture
def temp_project():
    """Создает временный проект и удаляет его после теста."""
    tmpdir = Path(tempfile.mkdtemp())
    project = ProjectManager.create_project(tmpdir, "TestProject")
    yield project
    shutil.rmtree(tmpdir, ignore_errors=True)


# ==================== ТЕСТЫ ====================

class TestProjectCreation:
    def test_create_project(self, temp_project):
        assert (temp_project.project_root / ".videolab").exists()
        assert (temp_project.project_root / "source_0").exists()
        assert (temp_project.project_root / "source_0" / "source_0.yaml").exists()

    def test_open_nonexistent_project(self):
        with pytest.raises(ValueError):
            ProjectManager("/nonexistent/path")


class TestTreeScanning:
    def test_get_tree(self, temp_project):
        tree = temp_project.get_tree()
        assert tree["name"] == temp_project.project_root.name
        assert len(tree["children"]) == 1
        assert tree["children"][0]["name"] == "source_0"

    def test_source_is_invalid_without_video(self, temp_project):
        source_path = temp_project.project_root / "source_0"
        is_valid, msg = temp_project.validate_node(str(source_path))
        assert not is_valid


class TestProcessorNodeCreation:
    def test_create_processor_node(self, temp_project):
        source_path = temp_project.project_root / "source_0"

        fake_video = source_path / "video.avi"
        fake_video.write_text("fake")

        temp_project.register_source_video(str(source_path), str(fake_video))

        node_path = temp_project.create_processor_node(
            parent_path=str(source_path),
            processor_name="dummy",
            input_files={"video": str(fake_video)},
            settings={"param1": 42},
        )

        assert Path(node_path).exists()
        assert Path(node_path).name == "dummy_1"
        assert (Path(node_path) / "dummy_1.yaml").exists()

    def test_counter_increment(self, temp_project):
        source_path = temp_project.project_root / "source_0"

        path1 = temp_project.create_processor_node(
            str(source_path), "dummy", {}, {}
        )
        path2 = temp_project.create_processor_node(
            str(source_path), "dummy", {}, {}
        )

        assert Path(path1).name == "dummy_1"
        assert Path(path2).name == "dummy_2"

    def test_counter_reset_after_delete(self, temp_project):
        source_path = temp_project.project_root / "source_0"

        path1 = temp_project.create_processor_node(
            str(source_path), "dummy", {}, {}
        )
        shutil.rmtree(path1)

        path2 = temp_project.create_processor_node(
            str(source_path), "dummy", {}, {}
        )

        assert Path(path2).name == "dummy_1"


class TestValidation:
    def test_valid_after_run(self, temp_project):
        source_path = temp_project.project_root / "source_0"
        node_path = temp_project.create_processor_node(
            str(source_path), "dummy", {}, {}
        )

        is_valid, _ = temp_project.validate_node(node_path)
        assert not is_valid

        # Создаём файл И snapshot (как будто run_node отработал)
        (Path(node_path) / "output_001.avi").write_text("done")
        temp_project.run_node(node_path)  # ← это создаст snapshot

        is_valid, _ = temp_project.validate_node(node_path)
        assert is_valid


class TestInputScanning:
    def test_scan_for_inputs_up_the_tree(self, temp_project):
        source_path = temp_project.project_root / "source_0"

        video = source_path / "video.avi"
        video.write_text("fake")

        node_path = temp_project.create_processor_node(
            str(source_path), "dummy", {}, {}
        )

        found = temp_project.scan_for_inputs(node_path, "*.avi")

        assert str(video) in found

    def test_scan_stops_at_project_root(self, temp_project):
        source_path = temp_project.project_root / "source_0"

        outside = temp_project.project_root.parent / "outside.avi"
        outside.write_text("fake")

        found = temp_project.scan_for_inputs(str(source_path), "*.avi")

        assert str(outside) not in found


class TestProcessorRegistry:
    def test_register_and_get(self):
        assert ProcessorRegistry.get("dummy") == DummyProcessor

    def test_get_nonexistent(self):
        with pytest.raises(KeyError):
            ProcessorRegistry.get("nonexistent")

    def test_double_registration_fails(self):
        with pytest.raises(ValueError):
            ProcessorRegistry.register(DummyProcessor)  # Уже зарегистрирован