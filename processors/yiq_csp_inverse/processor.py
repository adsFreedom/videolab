"""Обработчик: сборка видео из YIQ CSP."""
import numpy as np
import cv2
import json
from pathlib import Path

from core.processors import BaseProcessor, ProcessorRegistry
from core.execution import ExecutionContext
from core.utils import load_yaml
from processors.csp.utils import (
    yiq_to_rgb, merge_yiq, reconstruct_from_bands, find_frames_source,
)


@ProcessorRegistry.register
class YIQCSPInverseProcessor(BaseProcessor):
    name = "yiq_csp_inverse"
    display_name = "YIQ CSP Inverse (сборка)"
    category = "Анализ"
    icon = "🔁"

    input_spec = {
        "meta": {"mask": "meta.yaml", "required": True},
    }
    output_mask = "output.avi"

    settings_schema = {
        "max_frames": {
            "type": "spinbox",
            "label": "Макс. кадров (-1 = все)",
            "default": -1, "min": -1, "max": 100000,
        },
    }

    def run(self, input_files, settings, output_dir, context: ExecutionContext) -> dict:
        meta_path_input = Path(input_files["meta"])
        start_dir = meta_path_input.parent

        source_dir = find_frames_source(start_dir)
        if source_dir is None:
            raise RuntimeError(
                f"Не найден источник frames/ + meta.yaml вверх от {start_dir}"
            )

        meta = load_yaml(source_dir / "meta.yaml")
        fps = float(meta.get("fps", 30.0))
        levels = int(meta.get("levels", 4))
        orientations = int(meta.get("orientations", 4))
        vid_w = int(meta.get("width", 0))
        vid_h = int(meta.get("height", 0))
        frames_count = int(meta.get("frames_count", 0))

        max_frames = settings.get("max_frames", -1)
        if max_frames > 0 and max_frames < frames_count:
            frames_count = max_frames

        frames_dir = source_dir / "frames"
        frame_dirs = sorted([
            d for d in frames_dir.iterdir()
            if d.is_dir() and d.name.startswith("frame_")
        ])
        if not frame_dirs:
            raise RuntimeError(f"Нет frame_* папок в {frames_dir}")

        frame_dirs = frame_dirs[:frames_count]

        i0 = np.load(str(frame_dirs[0] / "I.npy"))
        true_h, true_w = i0.shape

        if vid_w == 0:
            vid_w = true_w
        if vid_h == 0:
            vid_h = true_h

        output_dir = Path(output_dir)
        output_path = output_dir / "output.avi"

        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (vid_w, vid_h))
        if not writer.isOpened():
            raise RuntimeError(f"Не удалось создать видео: {output_path}")

        for idx, frame_dir in enumerate(frame_dirs):
            context.check_cancel()

            lowpass = np.load(str(frame_dir / "Y_lowpass.npy"))
            hp = frame_dir / "Y_highpass.npy"
            highpass = np.load(str(hp)) if hp.exists() else None

            bands = {}
            for level in range(levels):
                for orient in range(orientations):
                    rp = frame_dir / f"Y_L{level}_O{orient}_real.npy"
                    ip = frame_dir / f"Y_L{level}_O{orient}_imag.npy"

                    if not rp.exists() or not ip.exists():
                        raise RuntimeError(
                            f"Отсутствует band L{level}_O{orient} в {frame_dir}"
                        )

                    real = np.load(str(rp))
                    imag = np.load(str(ip))
                    bands[(level, orient)] = real + 1j * imag

            y_norm = reconstruct_from_bands(
                bands=bands, lowpass=lowpass, highpass=highpass,
                levels=levels, orientations=orientations,
                output_size=(true_h, true_w),
            )

            ym = frame_dir / "Y_meta.json"
            if ym.exists():
                with open(ym, "r", encoding="utf-8") as f:
                    y_meta = json.load(f)
                y_min = float(y_meta.get("y_min", 0.0))
                y_max = float(y_meta.get("y_max", 255.0))
            else:
                y_min, y_max = 0.0, 255.0

            y = y_norm * (y_max - y_min) + y_min

            i_arr = np.load(str(frame_dir / "I.npy"))
            q_arr = np.load(str(frame_dir / "Q.npy"))

            yiq = merge_yiq(y, i_arr, q_arr)
            rgb = yiq_to_rgb(yiq)
            rgb = np.clip(rgb, 0, 255).astype(np.uint8)
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

            if bgr.shape[1] != vid_w or bgr.shape[0] != vid_h:
                bgr = cv2.resize(bgr, (vid_w, vid_h), interpolation=cv2.INTER_LINEAR)

            writer.write(bgr)
            context.report_progress(idx + 1, len(frame_dirs))

        writer.release()

        return {
            "output_files": [output_path.name],
            "metadata": {
                "frames_written": len(frame_dirs),
                "fps": fps,
                "source": str(source_dir),
            },
        }