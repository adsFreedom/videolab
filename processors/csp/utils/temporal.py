"""Временная обработка сигналов (bandpass, FFT)."""
import numpy as np


def temporal_bandpass(
    signal: np.ndarray,
    fps: float,
    fmin: float,
    fmax: float,
    axis: int = 0,
) -> np.ndarray:
    """
    Полосовой фильтр по времени.

    Args:
        signal: массив, где ось `axis` — время (кадры).
        fps: частота кадров.
        fmin, fmax: границы полосы (Гц).
        axis: ось времени (по умолчанию 0).

    Returns:
        Отфильтрованный сигнал той же формы.
    """
    n = signal.shape[axis]
    if n < 2:
        return signal

    # FFT по времени
    fft = np.fft.rfft(signal, axis=axis)
    freqs = np.fft.rfftfreq(n, d=1.0 / fps)

    # Маска полосового фильтра
    mask = (freqs >= fmin) & (freqs <= fmax)
    mask_shape = [1] * signal.ndim
    mask_shape[axis] = len(freqs)
    mask = mask.reshape(mask_shape)

    # Применяем маску
    fft_filtered = fft * mask

    # Обратно во времени
    filtered = np.fft.irfft(fft_filtered, n=n, axis=axis)

    return filtered.astype(signal.dtype)