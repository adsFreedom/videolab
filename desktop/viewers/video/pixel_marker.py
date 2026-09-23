"""Маркеры выбранного пикселя и ROI на видео."""
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint, QRect
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

        self._image_pos: tuple[int, int] | None = None
        self._widget_pos: QPoint | None = None

        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def set_pixel(self, image_pos: tuple[int, int], widget_pos: QPoint) -> None:
        self._image_pos = image_pos
        self._widget_pos = widget_pos
        self.update()

    def clear(self) -> None:
        self._image_pos = None
        self._widget_pos = None
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

        painter.drawLine(cx - s, cy, cx + s, cy)
        painter.drawLine(cx, cy - s, cx, cy + s)

        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(cx, cy), s // 2, s // 2)

        painter.end()


class ROIMarkerOverlay(QWidget):
    """
    Прозрачный оверлей поверх VideoSurface.
    Рисует прямоугольник выделенного ROI.
    """

    BORDER_COLOR = "#ffcc00"
    BORDER_WIDTH = 2

    def __init__(self, parent=None):
        super().__init__(parent)

        self._widget_rect: QRect | None = None
        self._image_rect: tuple[int, int, int, int] | None = None  # x, y, w, h

        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def set_rect(
        self,
        image_rect: tuple[int, int, int, int],
        widget_rect: QRect,
    ) -> None:
        self._image_rect = image_rect
        self._widget_rect = widget_rect
        self.update()

    def clear(self) -> None:
        self._image_rect = None
        self._widget_rect = None
        self.update()

    def get_image_rect(self) -> tuple[int, int, int, int] | None:
        return self._image_rect

    def paintEvent(self, event):
        if self._widget_rect is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        pen = QPen(QColor(self.BORDER_COLOR), self.BORDER_WIDTH)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self._widget_rect)

        painter.end()