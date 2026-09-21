"""Тесты реальных обработчиков (crop, extract_frames)."""
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from core.processor_registry import ProcessorRegistry


# ==================== ФИКСТУРА: ПЕРЕРЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ====================

@pytest.fixture(autouse=True)
def fresh_registry():
    """Очищает реестр и регистрирует нужные обработчики."""
    ProcessorRegistry.clear()

    from processors.crop import CropProcessor
    from processors.extract_frames import ExtractFramesProcessor

    try:
        ProcessorRegistry.register(CropProcessor)
    except ValueError:
        pass

    try:
        ProcessorRegistry.register(ExtractFramesProcessor)
    except ValueError:
        pass

    yield
    ProcessorRegistry.clear()


# ==================== ФИКСТУРА: ТЕСТОВОЕ ВИДЕО ====================

@pytest.fixture
def sample_video():
    """Создает тестовое видео 30 кадров, 64x64."""
    tmpdir = Path(tempfile.mkdtemp())
    video_path = tmpdir / "sample.avi"

    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    writer = cv2.VideoWriter(str(video_path), fourcc, 10.0, (64, 64))

    for i in range(30):
        frame = np.full((64, 64, 3), i * 8, dtype=np.uint8)
        writer.write(frame)

    writer.release()
    yield video_path
    shutil.rmtree(tmpdir, ignore_errors=True)


# ==================== ТЕСТЫ ====================

class TestCropProcessor:
    def test_crop_video(self, sample_video, tmp_path):
        from core.execution import ExecutionContext

        processor = ProcessorRegistry.get("crop")()
        context = ExecutionContext()

        result = processor.run(
            input_files={"video": str(sample_video)},
            settings={"start_frame": 5, "end_frame": 15},
            output_dir=str(tmp_path),
            context=context,
        )

        assert "output_files" in result
        assert len(result["output_files"]) == 1

        output_file = tmp_path / result["output_files"][0]
        assert output_file.exists()

        cap = cv2.VideoCapture(str(output_file))
        assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 10
        cap.release()

        assert result["metadata"]["frames_written"] == 10


class TestExtractFramesProcessor:
    def test_extract_frames(self, sample_video, tmp_path):
        from core.execution import ExecutionContext

        processor = ProcessorRegistry.get("extract_frames")()
        context = ExecutionContext()

        result = processor.run(
            input_files={"video": str(sample_video)},
            settings={"step": 5, "max_frames": 10},
            output_dir=str(tmp_path),
            context=context,
        )

        # 30 кадров / шаг 5 = 6 кадров
        assert len(result["output_files"]) == 6

        for filename in result["output_files"]:
            assert (tmp_path / filename).exists()