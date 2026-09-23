"""Маркер выбранного пикселя на видео."""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QColor, QPen


class PixelMarkerOverlay(QWidget):
    """
    Прозрачный оверлей поверх VideoSurface.
    Рисует крестик на выбранном пикселе.
    """

    CROSS_SIZE = 8
    CROSS_COLOR = "#ffcc00"
    CROSS_WIDTH = 2

    def __init__(self, parent=None):
        super().__init__(parent)

        self._image_pos: tuple[int, int] | None = None      # координаты в изображении
        self._widget_pos: QPoint | None = None               # координаты на виджете

        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def set_pixel(self, image_pos: tuple[int, int], widget_pos: QPoint) -> None:
        """Устанавливает маркер."""
        self._image_pos = image_pos
        self._widget_pos = widget_pos
        self.update()

    def clear(self) -> None:
        self._image_pos = None
        self._widget_pos = None
        self.update()

    def update_widget_pos(self, widget_pos: QPoint) -> None:
        """Обновляет позицию на виджете (например, после zoom)."""
        if self._widget_pos is not None:
            self._widget_pos = widget_pos
            self.update()

    def get_image_pos(self) -> tuple[int, int] | None:
        return self._image_pos

    def paintEvent(self, event):
        if self._widget_pos is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        pen = QPen(QColor(self.CROSS_COLOR), self.CROSS_WIDTH)
        painter.setPen(pen)

        cx = self._widget_pos.x()
        cy = self._widget_pos.y()
        s = self.CROSS_SIZE

        # Крестик
        painter.drawLine(cx - s, cy, cx + s, cy)
        painter.drawLine(cx, cy - s, cx, cy + s)

        # Круг
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(cx, cy), s // 2, s // 2)

        painter.end()