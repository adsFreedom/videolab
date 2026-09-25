"""Обработчик: YIQ + Complex Steerable Pyramid (только по Y)."""
import numpy as np
import cv2
import json
from pathlib import Path

from core.processors import BaseProcessor, ProcessorRegistry
from core.execution import ExecutionContext
from core.utils import save_yaml
from processors.yiq_steerable.yiq import rgb_to_yiq, split_yiq
from processors.yiq_steerable.steerable import build_pyramid, split_real_imag


@ProcessorRegistry.register
class YIQSteerableProcessor(BaseProcessor):
    name = "yiq_steerable"
    display_name = "YIQ Steerable Pyramid"
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
            "default": 4,
            "min": 1,
            "max": 8,
        },
        "orientations": {
            "type": "spinbox",
            "label": "Ориентаций",
            "default": 4,
            "min": 2,
            "max": 16,
        },
        "save_png": {
            "type": "checkbox",
            "label": "PNG визуализация (только уровень 0)",
            "default": False,
        },
        "max_frames": {
            "type": "spinbox",
            "label": "Макс. кадров (-1 = все)",
            "default": -1,
            "min": -1,
            "max": 100000,
        },
    }

    def run(
        self,
        input_files: dict,
        settings: dict,
        output_dir: str,
        context: ExecutionContext,
    ) -> dict:
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

            # === Y → Steerable Pyramid ===
            y_min = float(y.min())
            y_max = float(y.max())

            y_norm = self._normalize(y, y_min, y_max).astype(np.float32)
            pyramid = build_pyramid(y_norm, levels=levels, orientations=orientations)

            # Lowpass
            if pyramid["lowpass"] is not None:
                lp_path = frame_dir / "Y_lowpass.npy"
                np.save(str(lp_path), pyramid["lowpass"])
                output_files.append(str(lp_path.relative_to(output_dir)))

            # Bands
            for (level, orient), coeff in pyramid["bands"].items():
                real, imag = split_real_imag(coeff)

                real_path = frame_dir / f"Y_L{level}_O{orient}_real.npy"
                np.save(str(real_path), real)
                output_files.append(str(real_path.relative_to(output_dir)))

                imag_path = frame_dir / f"Y_L{level}_O{orient}_imag.npy"
                np.save(str(imag_path), imag)
                output_files.append(str(imag_path.relative_to(output_dir)))

                if save_png and level == 0:
                    amplitude = np.abs(coeff)
                    png_path = frame_dir / f"Y_L{level}_O{orient}_amp.png"
                    self._save_png(amplitude, png_path)
                    output_files.append(str(png_path.relative_to(output_dir)))

            # === Y_meta.json — для денормализации ===
            y_meta_path = frame_dir / "Y_meta.json"
            y_meta = {
                "y_min": y_min,
                "y_max": y_max,
            }
            with open(y_meta_path, "w", encoding="utf-8") as f:
                json.dump(y_meta, f)
            output_files.append(str(y_meta_path.relative_to(output_dir)))

            # === I и Q — как есть ===
            i_path = frame_dir / "I.npy"
            q_path = frame_dir / "Q.npy"
            np.save(str(i_path), i.astype(np.float32))
            np.save(str(q_path), q.astype(np.float32))
            output_files.append(str(i_path.relative_to(output_dir)))
            output_files.append(str(q_path.relative_to(output_dir)))

            frame_idx += 1
            context.report_progress(frame_idx, total_frames)

        cap.release()

        # ==================== META.YAML ====================

        meta_path = output_dir / "meta.yaml"
        meta_data = {
            "type": "yiq_steerable",
            "version": 1,
            "fps": float(fps),
            "levels": int(levels),
            "orientations": int(orientations),
            "width": int(vid_w),
            "height": int(vid_h),
            "frames_count": int(frame_idx),
            "source_video": video_path,
        }
        save_yaml(meta_path, meta_data)
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
    def _normalize(data: np.ndarray, d_min: float, d_max: float) -> np.ndarray:
        if d_max - d_min > 1e-8:
            return (data - d_min) / (d_max - d_min)
        return np.zeros_like(data, dtype=np.float32)

    @staticmethod
    def _save_png(data: np.ndarray, path: Path) -> None:
        d_min = data.min()
        d_max = data.max()
        if d_max - d_min > 1e-8:
            norm = (data - d_min) / (d_max - d_min)
        else:
            norm = np.zeros_like(data)

        img = (norm * 255).astype(np.uint8)
        cv2.imwrite(str(path), img)