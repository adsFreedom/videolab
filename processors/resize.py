"""Обработчик: изменение разрешения видео."""
from pathlib import Path
import cv2

from core.processors import BaseProcessor, ProcessorRegistry
from core.execution import ExecutionContext


@ProcessorRegistry.register
class ResizeProcessor(BaseProcessor):
    name = "resize"
    display_name = "Изменение разрешения"
    category = "Видео"
    icon = "📐"

    input_spec = {
        "video": {"mask": "*.avi", "required": True},
    }
    output_mask = "resized_*.avi"

    settings_schema = {
        "width": {
            "type": "spinbox",
            "label": "Ширина (px)",
            "default": 640,
            "min": 16,
            "max": 7680,
        },
        "height": {
            "type": "spinbox",
            "label": "Высота (px)",
            "default": 360,
            "min": 16,
            "max": 4320,
        },
        "interpolation": {
            "type": "combobox",
            "label": "Интерполяция",
            "options": ["Area (уменьшение)", "Linear", "Cubic", "Nearest"],
            "default": "Area (уменьшение)",
        },
    }

    INTERPOLATIONS = {
        "Area (уменьшение)": cv2.INTER_AREA,
        "Linear": cv2.INTER_LINEAR,
        "Cubic": cv2.INTER_CUBIC,
        "Nearest": cv2.INTER_NEAREST,
    }

    def run(
        self,
        input_files: dict,
        settings: dict,
        output_dir: str,
        context: ExecutionContext,
    ) -> dict:
        video_path = input_files["video"]
        target_w = settings.get("width", 640)
        target_h = settings.get("height", 360)
        interp_name = settings.get("interpolation", "Area (уменьшение)")
        interp = self.INTERPOLATIONS.get(interp_name, cv2.INTER_AREA)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Не удалось открыть видео: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        output_path = Path(output_dir) / "resized_001.avi"
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(
            str(output_path), fourcc, fps, (target_w, target_h),
        )

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

            resized = cv2.resize(frame, (target_w, target_h), interpolation=interp)
            writer.write(resized)

            frame_idx += 1
            written += 1

            if frame_idx % 10 == 0 or frame_idx == total_frames:
                context.report_progress(frame_idx, total_frames)

        cap.release()
        writer.release()

        return {
            "output_files": [output_path.name],
            "metadata": {
                "frames_written": written,
                "source_resolution": f"{src_w}x{src_h}",
                "target_resolution": f"{target_w}x{target_h}",
                "fps": fps,
                "interpolation": interp_name,
            },
        }