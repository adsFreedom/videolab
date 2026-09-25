"""Обработчик: конвертация видео в AVI (XVID)."""
import cv2
from pathlib import Path

from core.processors import BaseProcessor, ProcessorRegistry
from core.execution import ExecutionContext


@ProcessorRegistry.register
class ConvertToAviProcessor(BaseProcessor):
    name = "convert_to_avi"
    display_name = "Конвертация в AVI"
    category = "Видео"
    icon = "🎞️"

    input_spec = {
        "video": {
            # Поддерживает '|' для нескольких форматов
            "mask": "*.mp4|*.mov|*.mkv|*.webm|*.m4v|*.flv|*.wmv|*.mpg|*.mpeg|*.3gp",
            "required": True,
        },
    }
    output_mask = "converted_*.avi"

    settings_schema = {
        "max_frames": {
            "type": "spinbox",
            "label": "Макс. кадров (-1 = все)",
            "default": -1,
            "min": -1,
            "max": 1000000,
        },
    }

    def run(self, input_files, settings, output_dir, context: ExecutionContext) -> dict:
        video_path = input_files["video"]
        max_frames = settings.get("max_frames", -1)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Не удалось открыть видео: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if fps <= 0:
            fps = 30.0

        if max_frames > 0 and max_frames < total_frames:
            total_frames = max_frames

        output_path = Path(output_dir) / "converted_001.avi"
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

        if not writer.isOpened():
            cap.release()
            raise RuntimeError(f"Не удалось создать видео: {output_path}")

        frame_idx = 0
        written = 0

        while frame_idx < total_frames:
            context.check_cancel()

            ret, frame = cap.read()
            if not ret:
                break

            writer.write(frame)
            frame_idx += 1
            written += 1

            if frame_idx % 20 == 0 or frame_idx == total_frames:
                context.report_progress(frame_idx, total_frames)

        cap.release()
        writer.release()

        return {
            "output_files": [output_path.name],
            "metadata": {
                "frames_written": written,
                "fps": fps,
                "resolution": f"{w}x{h}",
                "source": video_path,
            },
        }