"""Обработчик: обрезка прямоугольной области видео."""
import cv2
from pathlib import Path

from core.processors import BaseProcessor, ProcessorRegistry
from core.execution import ExecutionContext


@ProcessorRegistry.register
class CropRegionProcessor(BaseProcessor):
    name = "crop_region"
    display_name = "Обрезка области"
    category = "Видео"
    icon = "🔲"

    input_spec = {
        "video": {"mask": "*.avi", "required": True},
    }
    output_mask = "cropped_*.avi"

    settings_schema = {
        "x": {
            "type": "spinbox",
            "label": "X (левый верхний угол)",
            "default": 0,
            "min": 0,
            "max": 10000,
        },
        "y": {
            "type": "spinbox",
            "label": "Y (левый верхний угол)",
            "default": 0,
            "min": 0,
            "max": 10000,
        },
        "width": {
            "type": "spinbox",
            "label": "Ширина",
            "default": 640,
            "min": 2,
            "max": 10000,
        },
        "height": {
            "type": "spinbox",
            "label": "Высота",
            "default": 360,
            "min": 2,
            "max": 10000,
        },
        "clamp": {
            "type": "checkbox",
            "label": "Клампить к границам (иначе ошибка)",
            "default": True,
        },
    }

    def run(self, input_files, settings, output_dir, context: ExecutionContext) -> dict:
        video_path = input_files["video"]
        x = settings.get("x", 0)
        y = settings.get("y", 0)
        w = settings.get("width", 640)
        h = settings.get("height", 360)
        clamp = settings.get("clamp", True)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Не удалось открыть видео: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        vid_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        vid_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if fps <= 0:
            fps = 30.0

        # Проверка границ
        if x < 0 or y < 0 or x >= vid_w or y >= vid_h:
            cap.release()
            raise RuntimeError(
                f"Начало ({x},{y}) вне границ видео ({vid_w}x{vid_h})"
            )

        if x + w > vid_w or y + h > vid_h:
            if clamp:
                w = min(w, vid_w - x)
                h = min(h, vid_h - y)
            else:
                cap.release()
                raise RuntimeError(
                    f"Область ({x},{y},{w},{h}) вне границ видео ({vid_w}x{vid_h})"
                )

        if w < 2 or h < 2:
            cap.release()
            raise RuntimeError(f"Слишком маленькая область: {w}x{h}")

        output_path = Path(output_dir) / "cropped_001.avi"
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

        if not writer.isOpened():
            cap.release()
            raise RuntimeError(f"Не удалось создать видео: {output_path}")

        frame_idx = 0
        written = 0

        while True:
            context.check_cancel()

            ret, frame = cap.read()
            if not ret:
                break

            cropped = frame[y:y + h, x:x + w]
            writer.write(cropped)
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
                "source_resolution": f"{vid_w}x{vid_h}",
                "crop_region": f"({x},{y}) {w}x{h}",
                "output_resolution": f"{w}x{h}",
            },
        }