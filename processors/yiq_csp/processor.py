"""Обработчик: YIQ + Complex Steerable Pyramid (только Y)."""
import numpy as np
import cv2
import json
from pathlib import Path

from core.processors import BaseProcessor, ProcessorRegistry
from core.execution import ExecutionContext
from core.utils import save_yaml
from processors.csp.utils import (
    rgb_to_yiq, split_yiq, build_pyramid, split_real_imag,
)


@ProcessorRegistry.register
class YIQCSPProcessor(BaseProcessor):
    name = "yiq_csp"
    display_name = "YIQ CSP (разложение)"
    category = "Анализ"
    icon = "🌊"

    input_spec = {
        "video": {"mask": "*.avi", "required": True},
    }
    output_mask = "*.npy"

    settings_schema = {
        "levels": {
            "type": "spinbox",
            "label": "Уровней пирамиды",
            "default": 4, "min": 1, "max": 8,
        },
        "orientations": {
            "type": "spinbox",
            "label": "Ориентаций",
            "default": 4, "min": 2, "max": 16,
        },
        "save_png": {
            "type": "checkbox",
            "label": "PNG визуализация (только уровень 0)",
            "default": False,
        },
        "max_frames": {
            "type": "spinbox",
            "label": "Макс. кадров (-1 = все)",
            "default": -1, "min": -1, "max": 100000,
        },
    }

    def run(self, input_files, settings, output_dir, context: ExecutionContext) -> dict:
        video_path = input_files["video"]
        levels = settings.get("levels", 4)
        orientations = settings.get("orientations", 4)
        save_png = settings.get("save_png", False)
        max_frames = settings.get("max_frames", -1)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Не удалось открыть видео: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        vid_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        vid_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if max_frames > 0 and max_frames < total_frames:
            total_frames = max_frames

        output_dir = Path(output_dir)
        output_files = []

        frames_dir = output_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        frame_idx = 0

        while frame_idx < total_frames:
            context.check_cancel()

            ret, frame = cap.read()
            if not ret:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float32)
            yiq = rgb_to_yiq(rgb)
            y, i, q = split_yiq(yiq)

            frame_dir = frames_dir / f"frame_{frame_idx:04d}"
            frame_dir.mkdir(parents=True, exist_ok=True)

            y_min = float(y.min())
            y_max = float(y.max())
            y_norm = self._normalize(y, y_min, y_max).astype(np.float32)
            pyramid = build_pyramid(y_norm, levels=levels, orientations=orientations)

            if pyramid["lowpass"] is not None:
                lp = frame_dir / "Y_lowpass.npy"
                np.save(str(lp), pyramid["lowpass"])
                output_files.append(str(lp.relative_to(output_dir)))

            if pyramid["highpass"] is not None:
                hp = frame_dir / "Y_highpass.npy"
                np.save(str(hp), pyramid["highpass"])
                output_files.append(str(hp.relative_to(output_dir)))

            for (level, orient), coeff in pyramid["bands"].items():
                real, imag = split_real_imag(coeff)

                rp = frame_dir / f"Y_L{level}_O{orient}_real.npy"
                np.save(str(rp), real)
                output_files.append(str(rp.relative_to(output_dir)))

                ip = frame_dir / f"Y_L{level}_O{orient}_imag.npy"
                np.save(str(ip), imag)
                output_files.append(str(ip.relative_to(output_dir)))

                if save_png and level == 0:
                    amp = np.abs(coeff)
                    pp = frame_dir / f"Y_L{level}_O{orient}_amp.png"
                    self._save_png(amp, pp)
                    output_files.append(str(pp.relative_to(output_dir)))

            ym = frame_dir / "Y_meta.json"
            with open(ym, "w", encoding="utf-8") as f:
                json.dump({"y_min": y_min, "y_max": y_max}, f)
            output_files.append(str(ym.relative_to(output_dir)))

            ip = frame_dir / "I.npy"
            qp = frame_dir / "Q.npy"
            np.save(str(ip), i.astype(np.float32))
            np.save(str(qp), q.astype(np.float32))
            output_files.append(str(ip.relative_to(output_dir)))
            output_files.append(str(qp.relative_to(output_dir)))

            frame_idx += 1
            context.report_progress(frame_idx, total_frames)

        cap.release()

        meta_path = output_dir / "meta.yaml"
        save_yaml(meta_path, {
            "type": "yiq_csp",
            "version": 1,
            "fps": float(fps),
            "levels": int(levels),
            "orientations": int(orientations),
            "width": int(vid_w),
            "height": int(vid_h),
            "frames_count": int(frame_idx),
            "source_video": video_path,
        })
        output_files.append(str(meta_path.relative_to(output_dir)))

        return {
            "output_files": output_files,
            "metadata": {
                "frames_processed": frame_idx,
                "levels": levels,
                "orientations": orientations,
                "fps": fps,
            },
        }

    @staticmethod
    def _normalize(data, d_min, d_max):
        if d_max - d_min > 1e-8:
            return (data - d_min) / (d_max - d_min)
        return np.zeros_like(data, dtype=np.float32)

    @staticmethod
    def _save_png(data, path):
        d_min = data.min()
        d_max = data.max()
        if d_max - d_min > 1e-8:
            norm = (data - d_min) / (d_max - d_min)
        else:
            norm = np.zeros_like(data)
        img = (norm * 255).astype(np.uint8)
        cv2.imwrite(str(path), img)