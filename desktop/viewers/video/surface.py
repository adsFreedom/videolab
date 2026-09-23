"""Виджет отрисовки кадра видео."""
import numpy as np
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen

from desktop.viewers.styles import VIDEO_SURFACE_STYLE


class VideoSurface(QWidget):
    """Виджет отображения кадра видео."""

    pixel_hovered = Signal(int, int, tuple)
    mouse_left = Signal()
    clicked = Signal()
    pixel_marked = Signal(int, int, QPoint)
    roi_marked = Signal(int, int, int, int, QRect)   # x, y, w, h, widget_rect

    MODE_PLAY_PAUSE = "play_pause"
    MODE_MARK_PIXEL = "mark_pixel"
    MODE_MARK_ROI = "mark_roi"

    def __init__(self, parent=None):
        super().__init__(parent)

        self._pixmap: QPixmap | None = None
        self._frame: np.ndarray | None = None
        self._last_mouse_pos: tuple[int, int] | None = None

        self._mode = self.MODE_PLAY_PAUSE

        # Выделение ROI
        self._roi_active = False
        self._roi_start: QPoint | None = None
        self._roi_current: QPoint | None = None

        self.setMouseTracking(True)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(VIDEO_SURFACE_STYLE)
        self.setCursor(Qt.CrossCursor)

    # ==================== API ====================

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self._roi_active = False
        self._roi_start = None
        self._roi_current = None
        self.update()

    def get_mode(self) -> str:
        return self._mode

    def set_frame(self, frame: np.ndarray | None) -> None:
        self._frame = frame

        if frame is None:
            self._pixmap = None
        else:
            self._pixmap = self._numpy_to_pixmap(frame)

        if self._last_mouse_pos is not None and frame is not None:
            x, y = self._last_mouse_pos
            h, w = frame.shape[:2]
            if 0 <= x < w and 0 <= y < h:
                b, g, r = frame[y, x]
                self.pixel_hovered.emit(x, y, (int(r), int(g), int(b)))

        self.update()

    def clear(self) -> None:
        self._frame = None
        self._pixmap = None
        self._last_mouse_pos = None
        self.update()

    def image_to_widget_pos(self, img_x: int, img_y: int) -> QPoint | None:
        if self._frame is None:
            return None
        rect = self._pixmap_rect()
        if rect is None:
            return None
        rx, ry, rw, rh = rect
        if rw <= 0 or rh <= 0:
            return None
        h, w = self._frame.shape[:2]
        if w <= 0 or h <= 0:
            return None
        wx = rx + int(img_x * rw / w)
        wy = ry + int(img_y * rh / h)
        return QPoint(wx, wy)

    # ==================== ВНУТРЕННИЕ ====================

    def _numpy_to_pixmap(self, frame: np.ndarray) -> QPixmap:
        rgb = frame[:, :, ::-1].copy()
        rgb = np.ascontiguousarray(rgb)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(qimg)

    def _pixmap_rect(self):
        if self._pixmap is None:
            return None
        scaled = self._pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        return (x, y, scaled.width(), scaled.height())

    def _widget_to_image(self, wx: float, wy: float):
        if self._frame is None:
            return None
        rect = self._pixmap_rect()
        if rect is None:
            return None
        rx, ry, rw, rh = rect
        if rw <= 0 or rh <= 0:
            return None
        frame_h, frame_w = self._frame.shape[:2]
        fx = int((wx - rx) * frame_w / rw)
        fy = int((wy - ry) * frame_h / rh)
        fx = max(0, min(fx, frame_w - 1))
        fy = max(0, min(fy, frame_h - 1))
        return (fx, fy)

    # ==================== СОБЫТИЯ ====================

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1a1a1a"))

        if self._pixmap is None:
            painter.end()
            return

        scaled = self._pixmap.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

        # Рисуем ROI при выделении
        if (self._mode == self.MODE_MARK_ROI and
                self._roi_start is not None and self._roi_current is not None):
            rect = QRect(self._roi_start, self._roi_current).normalized()
            pen = QPen(QColor("#ffcc00"), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

        painter.end()

    def mouseMoveEvent(self, event):
        if self._frame is None:
            return

        mx = event.position().x()
        my = event.position().y()

        # Пипетка
        pos = self._widget_to_image(mx, my)
        if pos is not None:
            fx, fy = pos
            self._last_mouse_pos = (fx, fy)
            b, g, r = self._frame[fy, fx]
            self.pixel_hovered.emit(fx, fy, (int(r), int(g), int(b)))

        # ROI в процессе выделения
        if self._roi_active and self._roi_start is not None:
            self._roi_current = QPoint(int(mx), int(my))
            self.update()

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._mode == self.MODE_MARK_PIXEL:
                self._on_mark_pixel(event.position().x(), event.position().y())
            elif self._mode == self.MODE_MARK_ROI:
                self._roi_active = True
                self._roi_start = QPoint(
                    int(event.position().x()),
                    int(event.position().y()),
                )
                self._roi_current = self._roi_start
                self.update()
            else:
                self.clicked.emit()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._roi_active:
            self._roi_active = False
            if self._roi_start is not None and self._roi_current is not None:
                self._on_roi_finished()
            self.update()
        super().mouseReleaseEvent(event)

    def _on_mark_pixel(self, wx: float, wy: float) -> None:
        if self._frame is None:
            return
        pos = self._widget_to_image(wx, wy)
        if pos is None:
            return
        fx, fy = pos
        self.pixel_marked.emit(fx, fy, QPoint(int(wx), int(wy)))

    def _on_roi_finished(self) -> None:
        """Пользователь завершил выделение ROI."""
        if self._roi_start is None or self._roi_current is None:
            return

        rect = QRect(self._roi_start, self._roi_current).normalized()

        # Минимальный размер
        if rect.width() < 4 or rect.height() < 4:
            return

        # Координаты в изображении
        tl = self._widget_to_image(rect.left(), rect.top())
        br = self._widget_to_image(rect.right(), rect.bottom())
        if tl is None or br is None:
            return

        x = tl[0]
        y = tl[1]
        w = br[0] - tl[0] + 1
        h = br[1] - tl[1] + 1

        if w < 2 or h < 2:
            return

        self.roi_marked.emit(x, y, w, h, rect)

    def leaveEvent(self, event):
        self._last_mouse_pos = None
        self.mouse_left.emit()
        super().leaveEvent(event)