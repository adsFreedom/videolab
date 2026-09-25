"""Виджет отрисовки карты мощности."""
import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QImage, QPixmap, QColor, QPainter, QPen, QFont

from desktop.viewers.styles import HISTOGRAM_BG, HISTOGRAM_AXIS
from desktop.viewers.video.power_map.colormaps import get_colormap_lut


class PowerMapCanvas(QWidget):
    """Отрисовка карты мощности с наложением на фон."""

    PADDING = 8

    def __init__(self, parent=None):
        super().__init__(parent)

        self._map: np.ndarray | None = None
        self._background: np.ndarray | None = None
        self._alpha: float = 0.7
        self._marker_xy: tuple[int, int] | None = None
        self._colormap_name: str = "Turbo"

        self._raw_min: float = 0.0
        self._raw_max: float = 1.0

        self.setMinimumSize(480, 360)
        self.setStyleSheet(f"background-color: {HISTOGRAM_BG};")
        self.setMouseTracking(True)

    # ==================== API ====================

    def set_colormap(self, name: str) -> None:
        self._colormap_name = name
        self.update()

    def set_map(
        self,
        map_data: np.ndarray,
        background: np.ndarray | None,
        raw_min: float,
        raw_max: float,
    ) -> None:
        self._map = map_data
        self._background = background
        self._raw_min = raw_min
        self._raw_max = raw_max
        self._marker_xy = None
        self.update()

    def clear(self) -> None:
        self._map = None
        self._background = None
        self._marker_xy = None
        self.update()

    def get_map(self) -> np.ndarray | None:
        return self._map

    def get_raw_range(self) -> tuple[float, float]:
        return self._raw_min, self._raw_max

    # ==================== ГЕОМЕТРИЯ ====================

    def _display_rect(self) -> QRect | None:
        if self._map is None:
            return None

        h, w = self._map.shape
        if w <= 0 or h <= 0:
            return None

        avail_w = self.width() - 2 * self.PADDING
        avail_h = self.height() - 2 * self.PADDING

        scale = min(avail_w / w, avail_h / h)
        draw_w = max(1, int(w * scale))
        draw_h = max(1, int(h * scale))

        x = (self.width() - draw_w) // 2
        y = (self.height() - draw_h) // 2

        return QRect(x, y, draw_w, draw_h)

    def _widget_to_map(self, wx: float, wy: float) -> tuple[int, int] | None:
        if self._map is None:
            return None
        rect = self._display_rect()
        if rect is None:
            return None

        if (wx < rect.left() or wx >= rect.right() or
                wy < rect.top() or wy >= rect.bottom()):
            return None

        h, w = self._map.shape
        mx = int((wx - rect.left()) * w / rect.width())
        my = int((wy - rect.top()) * h / rect.height())
        mx = max(0, min(mx, w - 1))
        my = max(0, min(my, h - 1))
        return (mx, my)

    # ==================== РИСОВАНИЕ ====================

    def _build_pixmap(self) -> QPixmap | None:
        if self._map is None:
            return None

        h, w = self._map.shape
        colors = get_colormap_lut(self._colormap_name)

        m = self._map
        m_min = float(m.min())
        m_max = float(m.max())
        if m_max > m_min:
            norm = (m - m_min) / (m_max - m_min)
        else:
            norm = np.zeros_like(m)

        indices = (norm * 255).astype(np.uint8)
        colored = colors[indices]

        # Наложение на фон
        if self._background is not None and self._background.shape[:2] == (h, w):
            bg = self._background.astype(np.float32)
            if bg.ndim == 2:
                bg = np.stack([bg, bg, bg], axis=-1)
            fg = colored.astype(np.float32)
            a = self._alpha
            blended = (fg * a + bg * (1 - a)).astype(np.uint8)
        else:
            blended = colored

        blended = np.ascontiguousarray(blended)
        qimg = QImage(blended.data, w, h, 3 * w, QImage.Format_RGB888)
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

        scaled = pixmap.scaled(
            rect.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation,
        )
        painter.drawPixmap(rect.left(), rect.top(), scaled)

        # Маркер
        if self._marker_xy is not None:
            h, w = self._map.shape
            rx = rect.left() + int(self._marker_xy[0] * rect.width() / w)
            ry = rect.top() + int(self._marker_xy[1] * rect.height() / h)
            pen = QPen(QColor("#ffffff"), 2)
            painter.setPen(pen)
            painter.drawLine(rx - 8, ry, rx + 8, ry)
            painter.drawLine(rx, ry - 8, rx, ry + 8)

        painter.end()

    # ==================== СОБЫТИЯ ====================

    def mousePressEvent(self, event):
        if self._map is None:
            return

        pos = self._widget_to_map(event.position().x(), event.position().y())
        if pos is None:
            return

        self._marker_xy = pos
        self.update()

        value = float(self._map[pos[1], pos[0]])

        parent = self.window()
        if hasattr(parent, "_on_canvas_clicked"):
            parent._on_canvas_clicked(pos[0], pos[1], value)