"""Обработчик: извлечение кадров из видео в PNG."""
from pathlib import Path
import cv2

from core.base_processor import BaseProcessor
from core.processor_registry import ProcessorRegistry


@ProcessorRegistry.register
class ExtractFramesProcessor(BaseProcessor):
    name = "extract_frames"
    display_name = "Извлечение кадров"
    category = "Видео"
    icon = "🖼️"

    input_spec = {
        "video": {"mask": "*.avi", "required": True},
    }
    output_mask = "frame_*.png"

    settings_schema = {
        "step": {
            "type": "spinbox",
            "label": "Шаг (каждый N-й кадр)",
            "default": 1,
            "min": 1,
            "max": 100,
        },
        "max_frames": {
            "type": "spinbox",
            "label": "Максимум кадров",
            "default": 100,
            "min": 1,
            "max": 10000,
        },
    }

    def run(self, input_files, settings, output_dir):
        video_path = input_files["video"]
        step = settings.get("step", 1)
        max_frames = settings.get("max_frames", 100)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Не удалось открыть видео: {video_path}")

        output_files = []
        frame_idx = 0
        saved = 0

        while saved < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % step == 0:
                filename = f"frame_{saved:04d}.png"
                filepath = Path(output_dir) / filename
                cv2.imwrite(str(filepath), frame)
                output_files.append(filename)
                saved += 1

            frame_idx += 1

        cap.release()

        return {
            "output_files": output_files,
            "metadata": {
                "total_frames_read": frame_idx,
                "frames_saved": saved,
            },
        }