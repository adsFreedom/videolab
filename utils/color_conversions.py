"""Конвертации цветовых пространств.

cv2 покрывает HSV / LAB / YUV.
YIQ — реализовано вручную (cv2 не поддерживает).
"""
import numpy as np
import cv2


# ==================== YIQ ====================

_RGB_TO_YIQ = np.array([
    [ 0.299,  0.587,  0.114],
    [ 0.596, -0.274, -0.322],
    [ 0.211, -0.523,  0.312],
], dtype=np.float32)

_YIQ_TO_RGB = np.linalg.inv(_RGB_TO_YIQ).astype(np.float32)


def rgb_to_yiq(rgb: np.ndarray) -> np.ndarray:
    """RGB → YIQ через матрицу."""
    flat = rgb.reshape(-1, 3).astype(np.float32)
    result = flat @ _RGB_TO_YIQ.T
    return result.reshape(rgb.shape).astype(np.float32)


def yiq_to_rgb(yiq: np.ndarray) -> np.ndarray:
    """YIQ → RGB через обратную матрицу."""
    flat = yiq.reshape(-1, 3).astype(np.float32)
    result = flat @ _YIQ_TO_RGB.T
    return result.reshape(yiq.shape).astype(np.float32)


def split_yiq(yiq: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """YIQ → (Y, I, Q)."""
    return yiq[..., 0], yiq[..., 1], yiq[..., 2]


def merge_yiq(y: np.ndarray, i: np.ndarray, q: np.ndarray) -> np.ndarray:
    """(Y, I, Q) → YIQ."""
    return np.stack([y, i, q], axis=-1)


# ==================== HSV / LAB / YUV (через cv2) ====================

def rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    """RGB → HSV (OpenCV)."""
    return cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """RGB → LAB (OpenCV)."""
    return cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2LAB)


def rgb_to_yuv(rgb: np.ndarray) -> np.ndarray:
    """RGB → YUV (OpenCV)."""
    return cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2YUV)


# ==================== Универсальная функция ====================

def convert_rgb(rgb: np.ndarray, target_space: str) -> np.ndarray | None:
    """
    RGB → любое пространство.

    Args:
        rgb: массив shape (..., 3) со значениями 0..255
        target_space: "RGB" | "YIQ" | "HSV" | "LAB" | "YUV"

    Returns:
        Массив в целевом пространстве или None, если space неизвестно.
    """
    if target_space == "RGB":
        return rgb
    if target_space == "YIQ":
        return rgb_to_yiq(rgb)
    if target_space == "HSV":
        return rgb_to_hsv(rgb)
    if target_space == "LAB":
        return rgb_to_lab(rgb)
    if target_space == "YUV":
        return rgb_to_yuv(rgb)
    return None


# ==================== Метаданные ====================

_CHANNEL_NAMES = {
    "RGB": ["R", "G", "B"],
    "YIQ": ["Y", "I", "Q"],
    "HSV": ["H", "S", "V"],
    "LAB": ["L", "a", "b"],
    "YUV": ["Y", "U", "V"],
}


def get_channel_names(space: str) -> list[str]:
    """Возвращает имена каналов для пространства."""
    return list(_CHANNEL_NAMES.get(space, ["?", "?", "?"]))


def get_available_spaces() -> list[str]:
    """Возвращает список доступных пространств."""
    return list(_CHANNEL_NAMES.keys())