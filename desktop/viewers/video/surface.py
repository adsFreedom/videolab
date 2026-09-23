"""Виджет отрисовки кадра видео."""
import numpy as np
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor

from desktop.viewers.styles import VIDEO_SURFACE_STYLE


class VideoSurface(QWidget):
    """Виджет для отображения кадра видео."""

    pixel_hovered = Signal(int, int, tuple)
    mouse_left = Signal()
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._pixmap: QPixmap | None = None
        self._frame: np.ndarray | None = None
        self._last_mouse_pos: tuple[int, int] | None = None

        self.setMouseTracking(True)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(VIDEO_SURFACE_STYLE)
        self.setCursor(Qt.CrossCursor)

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
        painter.end()

    def mouseMoveEvent(self, event):
        if self._frame is None:
            return

        rect = self._pixmap_rect()
        if rect is None:
            return

        rx, ry, rw, rh = rect
        mx = event.position().x()
        my = event.position().y()

        if mx < rx or mx >= rx + rw or my < ry or my >= ry + rh:
            return

        frame_w = self._frame.shape[1]
        frame_h = self._frame.shape[0]

        fx = int((mx - rx) * frame_w / rw)
        fy = int((my - ry) * frame_h / rh)

        fx = max(0, min(fx, frame_w - 1))
        fy = max(0, min(fy, frame_h - 1))

        self._last_mouse_pos = (fx, fy)

        b, g, r = self._frame[fy, fx]
        self.pixel_hovered.emit(fx, fy, (int(r), int(g), int(b)))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def leaveEvent(self, event):
        self._last_mouse_pos = None
        self.mouse_left.emit()