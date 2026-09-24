"""Виджет отрисовки numpy-массива."""
import numpy as np
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont

from desktop.viewers.styles import HISTOGRAM_BG, HISTOGRAM_AXIS


def build_grayscale_lut() -> np.ndarray:
    """Серая палитра 256×3."""
    x = np.arange(256, dtype=np.uint8)
    return np.stack([x, x, x], axis=-1)


def build_turbo_lut() -> np.ndarray:
    """Turbo палитра."""
    x = np.linspace(0, 1, 256)
    r = np.clip(0.13572138 + x * (4.61539260 + x * (-42.66032258 +
                x * (132.13108234 + x * (-152.94239396 + x * 59.28637943)))), 0, 1)
    g = np.clip(0.09140261 + x * (2.19418839 + x * (4.84296658 +
                x * (-14.18503333 + x * (4.27729857 + x * 2.82956604)))), 0, 1)
    b = np.clip(0.10667330 + x * (12.64194608 + x * (-60.58204836 +
                x * (110.36276771 + x * (-89.90310912 + x * 27.34824973)))), 0, 1)
    return (np.stack([r, g, b], axis=-1) * 255).astype(np.uint8)


def build_jet_lut() -> np.ndarray:
    """Jet палитра."""
    x = np.linspace(0, 1, 256)
    r = np.clip(1.5 - np.abs(4 * x - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * x - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * x - 1), 0, 1)
    return (np.stack([r, g, b], axis=-1) * 255).astype(np.uint8)


def build_viridis_lut() -> np.ndarray:
    """Viridis палитра (приближение)."""
    points = [
        (0.0, (68, 1, 84)),
        (0.25, (59, 82, 139)),
        (0.5, (33, 145, 140)),
        (0.75, (94, 201, 98)),
        (1.0, (253, 231, 37)),
    ]
    x = np.linspace(0, 1, 256)
    result = np.zeros((256, 3), dtype=np.float32)
    for i in range(len(points) - 1):
        x0, c0 = points[i]
        x1, c1 = points[i + 1]
        mask = (x >= x0) & (x <= x1)
        t = (x[mask] - x0) / (x1 - x0)
        for ch in range(3):
            result[mask, ch] = c0[ch] + t * (c1[ch] - c0[ch])
    return result.astype(np.uint8)


COLORMAPS = {
    "Gray": build_grayscale_lut,
    "Turbo": build_turbo_lut,
    "Jet": build_jet_lut,
    "Viridis": build_viridis_lut,
}

_COLORMAP_CACHE: dict[str, np.ndarray] = {}


def get_lut(name: str) -> np.ndarray:
    if name not in _COLORMAP_CACHE:
        builder = COLORMAPS.get(name, build_grayscale_lut)
        _COLORMAP_CACHE[name] = builder()
    return _COLORMAP_CACHE[name]


class NumpyCanvas(QWidget):
    """Виджет отрисовки 2D numpy-массива."""

    PADDING = 8

    clicked = Signal(int, int, float)   # x, y, value

    def __init__(self, parent=None):
        super().__init__(parent)

        self._data: np.ndarray | None = None       # 2D float
        self._colormap_name: str = "Gray"
        self._value_min: float = 0.0
        self._value_max: float = 1.0
        self._auto_range: bool = True

        self._marker_xy: tuple[int, int] | None = None

        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(f"background-color: {HISTOGRAM_BG};")
        self.setMouseTracking(True)

    # ==================== API ====================

    def set_data(self, data: np.ndarray, colormap: str = "Gray",
                 value_min: float | None = None,
                 value_max: float | None = None) -> None:
        """Устанавливает 2D массив."""
        self._data = data.astype(np.float32)
        self._colormap_name = colormap
        self._marker_xy = None

        if value_min is None or value_max is None:
            self._auto_range = True
            self._value_min = float(self._data.min())
            self._value_max = float(self._data.max())
        else:
            self._auto_range = False
            self._value_min = value_min
            self._value_max = value_max

        self.update()

    def set_colormap(self, name: str) -> None:
        self._colormap_name = name
        self.update()

    def set_range(self, vmin: float, vmax: float) -> None:
        self._value_min = vmin
        self._value_max = vmax
        self._auto_range = False
        self.update()

    def clear(self) -> None:
        self._data = None
        self._marker_xy = None
        self.update()

    def get_data(self) -> np.ndarray | None:
        return self._data

    def get_range(self) -> tuple[float, float]:
        return self._value_min, self._value_max

    # ==================== ГЕОМЕТРИЯ ====================

    def _display_rect(self) -> QRect | None:
        if self._data is None:
            return None

        h, w = self._data.shape
        avail_w = self.width() - 2 * self.PADDING
        avail_h = self.height() - 2 * self.PADDING
        if avail_w <= 0 or avail_h <= 0:
            return None

        scale = min(avail_w / w, avail_h / h)
        draw_w = max(1, int(w * scale))
        draw_h = max(1, int(h * scale))

        x = (self.width() - draw_w) // 2
        y = (self.height() - draw_h) // 2
        return QRect(x, y, draw_w, draw_h)

    def _widget_to_data(self, wx: float, wy: float) -> tuple[int, int] | None:
        if self._data is None:
            return None
        rect = self._display_rect()
        if rect is None:
            return None
        if (wx < rect.left() or wx >= rect.right() or
                wy < rect.top() or wy >= rect.bottom()):
            return None

        h, w = self._data.shape
        mx = int((wx - rect.left()) * w / rect.width())
        my = int((wy - rect.top()) * h / rect.height())
        mx = max(0, min(mx, w - 1))
        my = max(0, min(my, h - 1))
        return (mx, my)

    # ==================== РИСОВАНИЕ ====================

    def _build_pixmap(self) -> QPixmap | None:
        if self._data is None:
            return None

        h, w = self._data.shape
        lut = get_lut(self._colormap_name)

        d = self._data
        if self._value_max > self._value_min:
            norm = (d - self._value_min) / (self._value_max - self._value_min)
        else:
            norm = np.zeros_like(d)
        norm = np.clip(norm, 0, 1)
        indices = (norm * 255).astype(np.uint8)

        colored = lut[indices]
        colored = np.ascontiguousarray(colored)

        qimg = QImage(colored.data, w, h, 3 * w, QImage.Format_RGB888)
        return QPixmap.fromImage(qimg)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(HISTOGRAM_BG))

        pixmap = self._build_pixmap()
        if pixmap is None:
            painter.setPen(QPen(QColor(HISTOGRAM_AXIS)))
            font = QFont()
            font.setItalic(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            painter.end()
            return

        rect = self._display_rect()
        if rect is None:
            painter.end()
            return

        scaled = pixmap.scaled(rect.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(rect.left(), rect.top(), scaled)

        # Маркер
        if self._marker_xy is not None:
            h, w = self._data.shape
            rx = rect.left() + int(self._marker_xy[0] * rect.width() / w)
            ry = rect.top() + int(self._marker_xy[1] * rect.height() / h)
            pen = QPen(QColor("#ffcc00"), 2)
            painter.setPen(pen)
            painter.drawLine(rx - 8, ry, rx + 8, ry)
            painter.drawLine(rx, ry - 8, rx, ry + 8)

        painter.end()

    # ==================== СОБЫТИЯ ====================

    def mousePressEvent(self, event):
        if self._data is None:
            return
        pos = self._widget_to_data(event.position().x(), event.position().y())
        if pos is None:
            return
        self._marker_xy = pos
        self.update()
        value = float(self._data[pos[1], pos[0]])
        self.clicked.emit(pos[0], pos[1], value)