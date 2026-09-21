"""Обработчик: обрезка видео по кадрам."""
from pathlib import Path
import cv2

from core.processors import BaseProcessor
from core.execution import ExecutionContext
from core.processors import ProcessorRegistry


@ProcessorRegistry.register
class CropProcessor(BaseProcessor):
    name = "crop"
    display_name = "Обрезка видео"
    category = "Видео"
    icon = "✂️"

    input_spec = {
        "video": {"mask": "*.avi", "required": True},
    }
    output_mask = "crop_*.avi"

    settings_schema = {
        "start_frame": {
            "type": "spinbox",
            "label": "Начальный кадр",
            "default": 0,
            "min": 0,
        },
        "end_frame": {
            "type": "spinbox",
            "label": "Конечный кадр",
            "default": -1,
            "min": -1,
        },
    }

    def run(self, input_files, settings, output_dir, context: ExecutionContext):
        video_path = input_files["video"]
        start_frame = settings.get("start_frame", 0)
        end_frame = settings.get("end_frame", -1)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Не удалось открыть видео: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if end_frame == -1 or end_frame > total_frames:
            end_frame = total_frames

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        output_path = Path(output_dir) / "crop_001.avi"
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        if not writer.isOpened():
            raise RuntimeError(f"Не удалось создать видео: {output_path}")

        frames_to_process = end_frame - start_frame
        frame_idx = start_frame
        written = 0

        while frame_idx < end_frame:
            context.check_cancel()
            ret, frame = cap.read()
            if not ret:
                break
            writer.write(frame)
            frame_idx += 1
            written += 1

            if written % 10 == 0 or written == frames_to_process:
                context.report_progress(written, frames_to_process)

        cap.release()
        writer.release()

        return {
            "output_files": [output_path.name],
            "metadata": {
                "frames_written": written,
                "fps": fps,
                "resolution": f"{width}x{height}",
            },
        }