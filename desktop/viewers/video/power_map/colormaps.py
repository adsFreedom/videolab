"""Встроенные цветовые палитры для карты мощности."""
import numpy as np


def _build_jet_colormap() -> np.ndarray:
    x = np.linspace(0, 1, 256)
    r = np.clip(1.5 - np.abs(4 * x - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * x - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * x - 1), 0, 1)
    return (np.stack([r, g, b], axis=-1) * 255).astype(np.uint8)


def _build_turbo_colormap() -> np.ndarray:
    x = np.linspace(0, 1, 256)
    r = np.clip(0.13572138 + x * (4.61539260 + x * (-42.66032258 +
                x * (132.13108234 + x * (-152.94239396 + x * 59.28637943)))), 0, 1)
    g = np.clip(0.09140261 + x * (2.19418839 + x * (4.84296658 +
                x * (-14.18503333 + x * (4.27729857 + x * 2.82956604)))), 0, 1)
    b = np.clip(0.10667330 + x * (12.64194608 + x * (-60.58204836 +
                x * (110.36276771 + x * (-89.90310912 + x * 27.34824973)))), 0, 1)
    return (np.stack([r, g, b], axis=-1) * 255).astype(np.uint8)


def _build_hot_colormap() -> np.ndarray:
    x = np.linspace(0, 1, 256)
    r = np.clip(x * 3, 0, 1)
    g = np.clip(x * 3 - 1, 0, 1)
    b = np.clip(x * 3 - 2, 0, 1)
    return (np.stack([r, g, b], axis=-1) * 255).astype(np.uint8)


def _interpolate_points(points: list, n: int = 256) -> np.ndarray:
    """Линейная интерполяция ключевых точек в LUT."""
    x = np.linspace(0, 1, n)
    result = np.zeros((n, 3), dtype=np.float32)
    for i in range(len(points) - 1):
        x0, c0 = points[i]
        x1, c1 = points[i + 1]
        mask = (x >= x0) & (x <= x1)
        t = (x[mask] - x0) / (x1 - x0)
        for ch in range(3):
            result[mask, ch] = c0[ch] + t * (c1[ch] - c0[ch])
    return result.astype(np.uint8)


def _build_viridis_colormap() -> np.ndarray:
    return _interpolate_points([
        (0.0, (68, 1, 84)),
        (0.25, (59, 82, 139)),
        (0.5, (33, 145, 140)),
        (0.75, (94, 201, 98)),
        (1.0, (253, 231, 37)),
    ])


def _build_plasma_colormap() -> np.ndarray:
    return _interpolate_points([
        (0.0, (13, 8, 135)),
        (0.25, (126, 3, 168)),
        (0.5, (204, 71, 120)),
        (0.75, (248, 149, 64)),
        (1.0, (240, 249, 33)),
    ])


def _build_inferno_colormap() -> np.ndarray:
    return _interpolate_points([
        (0.0, (0, 0, 4)),
        (0.25, (87, 16, 110)),
        (0.5, (188, 55, 84)),
        (0.75, (249, 142, 9)),
        (1.0, (252, 255, 164)),
    ])


COLORMAPS = {
    "Turbo": _build_turbo_colormap,
    "Jet": _build_jet_colormap,
    "Hot": _build_hot_colormap,
    "Viridis": _build_viridis_colormap,
    "Plasma": _build_plasma_colormap,
    "Inferno": _build_inferno_colormap,
}

_CACHE: dict[str, np.ndarray] = {}


def get_colormap_lut(name: str) -> np.ndarray:
    """Возвращает LUT 256×3 (uint8) для указанной палитры."""
    if name not in _CACHE:
        builder = COLORMAPS.get(name, _build_turbo_colormap)
        _CACHE[name] = builder()
    return _CACHE[name]