"""Окно гистограммы изображения."""
import numpy as np
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPolygon

from desktop.viewers.styles import (
    HISTOGRAM_BG,
    HISTOGRAM_GRID,
    HISTOGRAM_AXIS,
    HISTOGRAM_COLOR_R,
    HISTOGRAM_COLOR_G,
    HISTOGRAM_COLOR_B,
    HISTOGRAM_COLOR_Y,
)


class HistogramCanvas(QWidget):
    """Виджет отрисовки гистограммы с осями."""

    PADDING_LEFT = 56
    PADDING_RIGHT = 16
    PADDING_TOP = 16
    PADDING_BOTTOM = 40

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: dict[str, np.ndarray] = {}
        self._space: str = "RGB"

        self.setMinimumSize(460, 300)
        self.setStyleSheet(f"background-color: {HISTOGRAM_BG};")

    def set_data(self, data: dict[str, np.ndarray], space: str = "RGB") -> None:
        self._data = data
        self._space = space
        self.update()

    def clear(self) -> None:
        self._data = {}
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        painter.fillRect(self.rect(), QColor(HISTOGRAM_BG))

        plot_x = self.PADDING_LEFT
        plot_y = self.PADDING_TOP
        plot_w = self.width() - self.PADDING_LEFT - self.PADDING_RIGHT
        plot_h = self.height() - self.PADDING_TOP - self.PADDING_BOTTOM

        if plot_w <= 0 or plot_h <= 0:
            painter.end()
            return

        max_val = 0
        for hist in self._data.values():
            if len(hist) > 0:
                max_val = max(max_val, int(hist.max()))

        self._draw_grid_and_y_labels(painter, plot_x, plot_y, plot_w, plot_h, max_val)

        if self._data and max_val > 0:
            self._draw_curves(painter, plot_x, plot_y, plot_w, plot_h, max_val)

        self._draw_x_labels(painter, plot_x, plot_y, plot_w, plot_h)
        self._draw_axis_titles(painter, plot_x, plot_y, plot_w, plot_h)

        painter.end()

    # ==================== СЕТКА ====================

    def _draw_grid_and_y_labels(self, painter, x, y, w, h, max_val):
        font = QFont()
        font.setPointSize(7)
        painter.setFont(font)

        for i in range(5):
            gy = y + int(h * i / 4)
            value = int(max_val * (4 - i) / 4)

            painter.setPen(QPen(QColor(HISTOGRAM_GRID), 1, Qt.DotLine))
            painter.drawLine(x, gy, x + w, gy)

            painter.setPen(QPen(QColor(HISTOGRAM_AXIS)))
            painter.drawText(
                2, gy - 7,
                self.PADDING_LEFT - 8, 14,
                Qt.AlignRight | Qt.AlignVCenter,
                self._format_count(value),
            )

        for i in range(0, 256, 64):
            gx = x + int(w * i / 255)
            painter.setPen(QPen(QColor(HISTOGRAM_GRID), 1, Qt.DotLine))
            painter.drawLine(gx, y, gx, y + h)

        painter.setPen(QPen(QColor(HISTOGRAM_AXIS), 1))
        painter.drawRect(x, y, w, h)

    # ==================== КРИВЫЕ ====================

    def _draw_curves(self, painter, x, y, w, h, max_val):
        color_maps = {
            "RGB": {
                "R": HISTOGRAM_COLOR_R,
                "G": HISTOGRAM_COLOR_G,
                "B": HISTOGRAM_COLOR_B,
                "Y": HISTOGRAM_COLOR_Y,
                "Gray": HISTOGRAM_COLOR_Y,
            },
            "HSV": {
                "H": "#ff55ff",
                "S": "#ffaa55",
                "V": HISTOGRAM_COLOR_Y,
            },
            "LAB": {
                "L": HISTOGRAM_COLOR_Y,
                "a": HISTOGRAM_COLOR_R,
                "b": HISTOGRAM_COLOR_B,
            },
            "YUV": {
                "Y": HISTOGRAM_COLOR_Y,
                "U": "#55ff55",
                "V": "#5555ff",
            },
        }
        color_map = color_maps.get(self._space, color_maps["RGB"])

        # Порядок отрисовки: сначала «фоновые», потом акцентные
        order_map = {
            "RGB": ["Y", "B", "G", "R", "Gray"],
            "HSV": ["V", "S", "H"],
            "LAB": ["L", "b", "a"],
            "YUV": ["Y", "V", "U"],
        }
        order = order_map.get(self._space, list(color_map.keys()))

        for key in order:
            if key not in self._data:
                continue
            hist = self._data[key]
            if len(hist) != 256:
                continue

            color = QColor(color_map.get(key, "#ffffff"))
            painter.setPen(QPen(color, 1))

            points = []
            for i in range(256):
                v = int(hist[i])
                px = x + int(w * i / 255)
                py = y + h - int(h * v / max_val) if max_val > 0 else y + h
                points.append(QPoint(px, py))

            polygon = QPolygon(points)
            painter.drawPolyline(polygon)

    # ==================== ПОДПИСИ ====================

    def _draw_x_labels(self, painter, x, y, w, h):
        font = QFont()
        font.setPointSize(7)
        painter.setFont(font)
        painter.setPen(QPen(QColor(HISTOGRAM_AXIS)))

        for value in [0, 64, 128, 192, 255]:
            gx = x + int(w * value / 255)
            painter.drawText(
                gx - 20, y + h + 4,
                40, 16,
                Qt.AlignCenter,
                str(value),
            )

    def _draw_axis_titles(self, painter, x, y, w, h):
        font = QFont()
        font.setPointSize(8)
        font.setItalic(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor(HISTOGRAM_AXIS)))

        painter.drawText(
            x, y + h + 20,
            w, 16,
            Qt.AlignCenter,
            "Значение (0–255)",
        )

        painter.save()
        painter.translate(12, y + h // 2)
        painter.rotate(-90)
        painter.drawText(
            -60, -8,
            120, 16,
            Qt.AlignCenter,
            "Пиксели",
        )
        painter.restore()

    # ==================== УТИЛИТЫ ====================

    @staticmethod
    def _format_count(value: int) -> str:
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M"
        if value >= 1_000:
            return f"{value / 1_000:.1f}K"
        return str(value)


class LegendWidget(QWidget):
    """Легенда с цветами каналов. Зависит от пространства."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self._space = "RGB"

    def set_space(self, space: str) -> None:
        self._space = space
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        legends = {
            "RGB": [
                ("R", HISTOGRAM_COLOR_R),
                ("G", HISTOGRAM_COLOR_G),
                ("B", HISTOGRAM_COLOR_B),
                ("Y (яркость)", HISTOGRAM_COLOR_Y),
            ],
            "HSV": [
                ("H (тон)", "#ff55ff"),
                ("S (насыщенность)", "#ffaa55"),
                ("V (значение)", HISTOGRAM_COLOR_Y),
            ],
            "LAB": [
                ("L (светлота)", HISTOGRAM_COLOR_Y),
                ("a (зелёный–красный)", HISTOGRAM_COLOR_R),
                ("b (синий–жёлтый)", HISTOGRAM_COLOR_B),
            ],
            "YUV": [
                ("Y (яркость)", HISTOGRAM_COLOR_Y),
                ("U (синий)", "#5555ff"),
                ("V (красный)", "#ff5555"),
            ],
        }
        items = legends.get(self._space, legends["RGB"])

        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)

        x = 12
        y = self.height() // 2

        for label, color in items:
            painter.setPen(QPen(QColor(HISTOGRAM_AXIS), 1))
            painter.setBrush(QColor(color))
            painter.drawRect(x, y - 5, 12, 10)
            x += 16

            painter.setPen(QPen(QColor(HISTOGRAM_AXIS)))
            painter.drawText(
                x, y - 8,
                180, 16,
                Qt.AlignLeft | Qt.AlignVCenter,
                label,
            )
            x += 180

        painter.end()


class HistogramWindow(QMainWindow):
    """Отдельное окно с гистограммой."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Гистограмма")
        self.resize(620, 400)

        self._canvas = HistogramCanvas()
        self._legend = LegendWidget()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._canvas, stretch=1)
        layout.addWidget(self._legend)

        self.setCentralWidget(container)

    def set_data(self, data: dict[str, np.ndarray], space: str = "RGB") -> None:
        self._canvas.set_data(data, space)
        self._legend.set_space(space)

    def set_title_file(self, file_name: str) -> None:
        self.setWindowTitle(f"Гистограмма — {file_name}")

    def clear(self) -> None:
        self._canvas.clear()