"""Обработчик: усиление движения через фазовую амплификацию CSP."""
import numpy as np
import cv2
import json
import shutil
from pathlib import Path

from core.processors import BaseProcessor, ProcessorRegistry
from core.execution import ExecutionContext
from core.utils import load_yaml, save_yaml
from processors.csp.utils import find_frames_source, temporal_bandpass


@ProcessorRegistry.register
class MotionMagnifyProcessor(BaseProcessor):
    name = "motion_magnify"
    display_name = "Motion Magnify (усиление движения)"
    category = "Анализ"
    icon = "🎬"

    input_spec = {
        "meta": {"mask": "meta.yaml", "required": True},
    }
    output_mask = "meta.yaml"

    settings_schema = {
        "fmin": {
            "type": "double_spinbox",
            "label": "Нижняя частота (Гц)",
            "default": 0.8,
            "min": 0.01,
            "max": 1000.0,
            "step": 0.05,
            "decimals": 3,
        },
        "fmax": {
            "type": "double_spinbox",
            "label": "Верхняя частота (Гц)",
            "default": 1.6,
            "min": 0.01,
            "max": 1000.0,
            "step": 0.05,
            "decimals": 3,
        },
        "alpha": {
            "type": "double_spinbox",
            "label": "Усиление (α)",
            "default": 10.0,
            "min": 0.1,
            "max": 100.0,
            "step": 1.0,
            "decimals": 1,
        },
        "max_frames": {
            "type": "spinbox",
            "label": "Макс. кадров (-1 = все)",
            "default": -1,
            "min": -1,
            "max": 100000,
        },
    }

    def validate_settings(self, settings: dict) -> tuple[bool, str]:
        ok, msg = super().validate_settings(settings)
        if not ok:
            return ok, msg

        fmin = settings.get("fmin", 0.0)
        fmax = settings.get("fmax", 0.0)
        if fmin > fmax:
            return False, f"fmin ({fmin}) больше fmax ({fmax})"
        return True, ""

    def run(self, input_files, settings, output_dir, context: ExecutionContext) -> dict:
        # 1. Находим источник (ближайший узел с frames/ + meta.yaml)
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
        source_video = meta.get("source_video", "")

        # 2. Параметры обработки
        fmin = settings.get("fmin", 0.8)
        fmax = settings.get("fmax", 1.6)
        alpha = settings.get("alpha", 10.0)
        max_frames = settings.get("max_frames", -1)

        if max_frames > 0 and max_frames < frames_count:
            frames_count = max_frames

        # 3. Проверка по Найквисту
        nyquist = fps / 2.0
        if fmax >= nyquist:
            fmax = nyquist * 0.99

        # 4. Список frame_* папок
        source_frames_dir = source_dir / "frames"
        frame_dirs = sorted([
            d for d in source_frames_dir.iterdir()
            if d.is_dir() and d.name.startswith("frame_")
        ])
        if not frame_dirs:
            raise RuntimeError(f"Нет frame_* папок в {source_frames_dir}")

        frame_dirs = frame_dirs[:frames_count]
        n_frames = len(frame_dirs)

        if n_frames < 4:
            raise RuntimeError(f"Слишком мало кадров: {n_frames}")

        # 5. Выходная папка
        output_dir = Path(output_dir)
        output_frames_dir = output_dir / "frames"
        output_frames_dir.mkdir(parents=True, exist_ok=True)

        # Копируем meta.yaml источника, но с типом motion_magnify
        out_meta = dict(meta)
        out_meta["type"] = "motion_magnify"
        out_meta["source_steerable"] = str(source_dir)
        out_meta["fmin"] = float(fmin)
        out_meta["fmax"] = float(fmax)
        out_meta["alpha"] = float(alpha)
        out_meta["frames_count"] = n_frames
        save_yaml(output_dir / "meta.yaml", out_meta)

        output_files = ["meta.yaml"]

        # 6. Прогресс по bands × frames
        total_steps = levels * orientations * n_frames
        current_step = 0

        # 7. Обрабатываем каждый (level, orient)
        for level in range(levels):
            for orient in range(orientations):
                context.check_cancel()

                # Загружаем все кадры для этого band'а
                reals = []
                imags = []

                for frame_dir in frame_dirs:
                    rp = frame_dir / f"Y_L{level}_O{orient}_real.npy"
                    ip = frame_dir / f"Y_L{level}_O{orient}_imag.npy"

                    if not rp.exists() or not ip.exists():
                        raise RuntimeError(
                            f"Отсутствует band L{level}_O{orient} в {frame_dir}"
                        )

                    reals.append(np.load(str(rp)))
                    imags.append(np.load(str(ip)))

                # Стек: (N, H, W)
                real_data = np.stack(reals, axis=0).astype(np.float32)
                imag_data = np.stack(imags, axis=0).astype(np.float32)

                # Амплитуда и фаза
                amplitude = np.hypot(real_data, imag_data)
                phase = np.arctan2(imag_data, real_data)

                # Временной bandpass фазы
                filtered_phase = temporal_bandpass(
                    phase, fps=fps, fmin=fmin, fmax=fmax, axis=0,
                )

                # Усиление
                amplified_phase = phase + alpha * filtered_phase

                # Обратно в real/imag
                amplified_real = amplitude * np.cos(amplified_phase)
                amplified_imag = amplitude * np.sin(amplified_phase)

                # Сохраняем по кадрам
                for i, frame_dir in enumerate(frame_dirs):
                    out_frame_dir = output_frames_dir / frame_dir.name
                    out_frame_dir.mkdir(parents=True, exist_ok=True)

                    out_rp = out_frame_dir / f"Y_L{level}_O{orient}_real.npy"
                    out_ip = out_frame_dir / f"Y_L{level}_O{orient}_imag.npy"

                    np.save(str(out_rp), amplified_real[i].astype(np.float32))
                    np.save(str(out_ip), amplified_imag[i].astype(np.float32))

                    current_step += 1
                    if i % 5 == 0:
                        context.report_progress(current_step, total_steps)

        # 8. Копируем остальные файлы: Y_lowpass, Y_highpass, Y_meta.json, I.npy, Q.npy
        for frame_dir in frame_dirs:
            context.check_cancel()

            out_frame_dir = output_frames_dir / frame_dir.name
            out_frame_dir.mkdir(parents=True, exist_ok=True)

            # Копируем lowpass, highpass, I, Q, Y_meta.json
            for fname in ("Y_lowpass.npy", "Y_highpass.npy", "I.npy", "Q.npy", "Y_meta.json"):
                src = frame_dir / fname
                if src.exists():
                    shutil.copy2(str(src), str(out_frame_dir / fname))

        # 9. Финализация прогресса
        context.report_progress(total_steps, total_steps)

        # 10. Список файлов (упрощённо — только meta.yaml; остальное не перечисляем)
        return {
            "output_files": output_files,
            "metadata": {
                "frames": n_frames,
                "levels": levels,
                "orientations": orientations,
                "fmin": fmin,
                "fmax": fmax,
                "alpha": alpha,
                "source": str(source_dir),
            },
        }