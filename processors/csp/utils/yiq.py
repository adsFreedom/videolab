"""Конвертация RGB ↔ YIQ."""
import numpy as np


_RGB_TO_YIQ = np.array([
    [ 0.299,  0.587,  0.114],
    [ 0.596, -0.274, -0.322],
    [ 0.211, -0.523,  0.312],
], dtype=np.float32)

_YIQ_TO_RGB = np.linalg.inv(_RGB_TO_YIQ).astype(np.float32)


def rgb_to_yiq(rgb: np.ndarray) -> np.ndarray:
    return _apply_matrix(rgb, _RGB_TO_YIQ)


def yiq_to_rgb(yiq: np.ndarray) -> np.ndarray:
    return _apply_matrix(yiq, _YIQ_TO_RGB)


def _apply_matrix(arr: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    original_shape = arr.shape
    flat = arr.reshape(-1, 3).astype(np.float32)
    result = flat @ matrix.T
    return result.reshape(original_shape).astype(np.float32)


def split_yiq(yiq: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return yiq[..., 0], yiq[..., 1], yiq[..., 2]


def merge_yiq(y: np.ndarray, i: np.ndarray, q: np.ndarray) -> np.ndarray:
    return np.stack([y, i, q], axis=-1)