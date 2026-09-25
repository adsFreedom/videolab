"""Расчёт карты мощности — чистая логика без UI."""
import numpy as np
import cv2
from pathlib import Path
from typing import Callable

from utils.color_conversions import rgb_to_yiq


def extract_channel(frame_rgb: np.ndarray, space: str, idx: int) -> np.ndarray:
    """Извлекает канал из RGB-кадра."""
    if space == "RGB":
        return frame_rgb[:, :, idx]
    if space == "YIQ":
        yiq = rgb_to_yiq(frame_rgb)
        return yiq[:, :, idx]

    if space == "HSV":
        conv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
    elif space == "LAB":
        conv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2LAB)
    elif space == "YUV":
        conv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2YUV)
    else:
        conv = frame_rgb
    return conv[:, :, idx]


def compute_magnitude(
    frames: list[np.ndarray],
    fps: float,
    target_freq: float,
    freq_width: float,
) -> tuple[np.ndarray, float, float]:
    """
    Вычисляет magnitude на частоте + min/max.

    Returns:
        (magnitude_at_freq, mag_min, mag_max)
    """
    data = np.stack(frames, axis=0).astype(np.float32)
    n = data.shape[0]

    # Убираем DC и применяем Hann
    data = data - data.mean(axis=0, keepdims=True)
    window = np.hanning(n).astype(np.float32)
    data = data * window[:, None, None]

    # FFT по времени
    spectrum = np.fft.rfft(data, axis=0)
    magnitude = np.abs(spectrum)
    freqs = np.fft.rfftfreq(n, d=1.0 / fps)

    # Диапазон
    if freq_width > 0:
        mask = (freqs >= target_freq - freq_width) & (freqs <= target_freq + freq_width)
    else:
        step = freqs[1] - freqs[0] if len(freqs) > 1 else 1e-3
        mask = np.isclose(freqs, target_freq, atol=step)

    if not mask.any():
        idx = int(np.argmin(np.abs(freqs - target_freq)))
        magnitude_at_freq = magnitude[idx]
    else:
        magnitude_at_freq = magnitude[mask].mean(axis=0)

    return (
        magnitude_at_freq,
        float(magnitude_at_freq.min()),
        float(magnitude_at_freq.max()),
    )


def get_background(
    video_path: str,
    first_frame: np.ndarray | None,
    roi: tuple[int, int, int, int] | None,
) -> np.ndarray | None:
    """Возвращает фон — обрезанный первый кадр по ROI."""
    if first_frame is not None:
        if roi is None:
            return first_frame
        rx, ry, rw, rh = roi
        fh, fw = first_frame.shape[:2]
        if fh >= ry + rh and fw >= rx + rw:
            return first_frame[ry:ry + rh, rx:rx + rw]
        return first_frame

    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    if roi is None:
        return frame_rgb
    rx, ry, rw, rh = roi
    return frame_rgb[ry:ry + rh, rx:rx + rw]


def compute_power_map(
    video_path: str,
    fps: float,
    roi: tuple[int, int, int, int] | None,
    space: str,
    channel_idx: int,
    target_freq: float,
    freq_width: float,
    first_frame: np.ndarray | None = None,
    progress_callback: Callable[[int, int], bool] | None = None,
) -> dict | None:
    """
    Полный расчёт карты мощности.

    Args:
        progress_callback: callback(current_frame, total_frames) -> continue (bool).
                           Если возвращает False — прервать.

    Returns:
        dict:
          - "map": нормализованная карта (0..1)
          - "background": фон (RGB) или None
          - "raw_min": абсолютный минимум
          - "raw_max": абсолютный максимум
          - "frames_count": число кадров
          - "roi": использованный ROI (x, y, w, h)
        или None, если прервано / ошибка.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    vid_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if fps <= 0:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    # Определяем ROI
    if roi is not None:
        rx, ry, rw, rh = roi
    else:
        rx, ry, rw, rh = 0, 0, vid_w, vid_h

    rx = max(0, min(rx, vid_w - 1))
    ry = max(0, min(ry, vid_h - 1))
    rw = min(rw, vid_w - rx)
    rh = min(rh, vid_h - ry)

    if rw < 2 or rh < 2:
        cap.release()
        return None

    frames = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if progress_callback and frame_idx % 20 == 0:
            if not progress_callback(frame_idx, frame_count):
                cap.release()
                return None

        frame_crop = frame[ry:ry + rh, rx:rx + rw]
        frame_rgb = cv2.cvtColor(frame_crop, cv2.COLOR_BGR2RGB)
        ch = extract_channel(frame_rgb, space, channel_idx)
        frames.append(ch)
        frame_idx += 1

    cap.release()

    if len(frames) < 4:
        return None

    magnitude_at_freq, mag_min, mag_max = compute_magnitude(
        frames, fps, target_freq, freq_width,
    )

    if mag_max > mag_min:
        normalized = (magnitude_at_freq - mag_min) / (mag_max - mag_min)
    else:
        normalized = magnitude_at_freq * 0.0

    background = get_background(video_path, first_frame, (rx, ry, rw, rh))

    return {
        "map": normalized,
        "background": background,
        "raw_min": mag_min,
        "raw_max": mag_max,
        "frames_count": len(frames),
        "roi": (rx, ry, rw, rh),
    }