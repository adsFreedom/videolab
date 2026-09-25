"""Вертикальная цветовая шкала с подписями."""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen, QFont

from desktop.viewers.styles import HISTOGRAM_BG, HISTOGRAM_AXIS
from desktop.viewers.video.power_map.colormaps import get_colormap_lut


class ColorbarWidget(QWidget):
    """Цветовая шкала (вертикальная, min внизу, max вверху)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._colormap_name = "Turbo"
        self._value_min = 0.0
        self._value_max = 1.0

        self.setFixedWidth(80)

    def set_colormap(self, name: str) -> None:
        self._colormap_name = name
        self.update()

    def set_range(self, vmin: float, vmax: float) -> None:
        self._value_min = vmin
        self._value_max = vmax
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(HISTOGRAM_BG))

        bar_w = 24
        bar_x = 8
        bar_y = 16
        bar_h = self.height() - 40

        if bar_h <= 0:
            painter.end()
            return

        colors = get_colormap_lut(self._colormap_name)

        # Шкала: сверху max, снизу min
        for i in range(bar_h):
            ratio = 1.0 - i / bar_h
            color_idx = int(ratio * 255)
            r, g, b = colors[color_idx]
            painter.setPen(QColor(int(r), int(g), int(b)))
            painter.drawLine(bar_x, bar_y + i, bar_x + bar_w, bar_y + i)

        # Рамка
        painter.setPen(QPen(QColor(HISTOGRAM_AXIS), 1))
        painter.drawRect(bar_x, bar_y, bar_w, bar_h)

        # Подписи
        font = QFont()
        font.setPointSize(7)
        painter.setFont(font)
        painter.setPen(QPen(QColor(HISTOGRAM_AXIS)))

        n_labels = 5
        for i in range(n_labels):
            ratio = 1.0 - i / (n_labels - 1)
            y = bar_y + int(i * bar_h / (n_labels - 1))
            value = self._value_min + ratio * (self._value_max - self._value_min)
            text = f"{value:.2f}"
            painter.drawText(
                bar_x + bar_w + 4, y - 7,
                self.width() - bar_w - 12, 14,
                Qt.AlignLeft | Qt.AlignVCenter,
                text,
            )

        painter.end()