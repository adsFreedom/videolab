"""Виджет отрисовки изображения с zoom, выделением и линией."""
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen

from desktop.viewers.styles import (
    IMAGE_SURFACE_STYLE,
    IMAGE_SELECTION_COLOR,
    IMAGE_SELECTION_WIDTH,
)


class ImageSurface(QWidget):
    """
    Виджет отображения изображения.

    Режимы:
    - SELECTION: ЛКМ + drag → прямоугольник (для извлечения области).
    - LINE: ЛКМ + drag → линия (для Line Profile).
    """

    MODE_SELECTION = "selection"
    MODE_LINE = "line"

    pixel_hovered = Signal(int, int, tuple)
    mouse_left = Signal()
    selection_changed = Signal(object)         # QRect | None
    zoom_changed = Signal(float)
    line_drawn = Signal(object, object)        # (QPoint, QPoint) в координатах изображения

    MIN_ZOOM = 0.05
    MAX_ZOOM = 32.0

    def __init__(self, parent=None):
        super().__init__(parent)

        self._pixmap: QPixmap | None = None
        self._source_array = None

        self._zoom = 1.0
        self._offset = QPoint(0, 0)

        self._last_mouse_pos: tuple[int, int] | None = None

        # Режим
        self._mode = self.MODE_SELECTION

        # Выделение
        self._selection_start: QPoint | None = None
        self._selection_current: QPoint | None = None
        self._selection_active = False

        # Линия
        self._line_start: QPoint | None = None
        self._line_current: QPoint | None = None
        self._line_active = False

        self.setMouseTracking(True)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(IMAGE_SURFACE_STYLE)
        self.setCursor(Qt.CrossCursor)
        self.setFocusPolicy(Qt.StrongFocus)

    # ==================== API ====================

    def set_mode(self, mode: str) -> None:
        """Переключение режима работы мыши."""
        self._mode = mode
        # Сбрасываем активные выделения при смене режима
        self.clear_selection()
        self.clear_line()

    def get_mode(self) -> str:
        return self._mode

    def set_image(self, pixmap: QPixmap | None, source_array=None) -> None:
        self._pixmap = pixmap
        self._source_array = source_array
        self._zoom = 1.0
        self._offset = QPoint(0, 0)
        self.clear_selection()
        self.clear_line()
        self.zoom_changed.emit(self._zoom)
        self.update()

    def clear(self) -> None:
        self._pixmap = None
        self._source_array = None
        self._zoom = 1.0
        self._offset = QPoint(0, 0)
        self.clear_selection()
        self.clear_line()
        self.update()

    def fit_to_window(self) -> None:
        if self._pixmap is None:
            return
        w_ratio = self.width() / self._pixmap.width()
        h_ratio = self.height() / self._pixmap.height()
        self._zoom = min(w_ratio, h_ratio) * 0.98
        self._offset = QPoint(0, 0)
        self.zoom_changed.emit(self._zoom)
        self.update()

    def reset_view(self) -> None:
        self._zoom = 1.0
        self._offset = QPoint(0, 0)
        self.zoom_changed.emit(self._zoom)
        self.update()

    def zoom_in(self) -> None:
        self._apply_zoom(1.25, self.rect().center())

    def zoom_out(self) -> None:
        self._apply_zoom(1 / 1.25, self.rect().center())

    def set_zoom(self, zoom: float) -> None:
        zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom))
        self._zoom = zoom
        self.zoom_changed.emit(self._zoom)
        self.update()

    def get_zoom(self) -> float:
        return self._zoom

    # ==================== ВЫДЕЛЕНИЕ ====================

    def get_selection_rect(self) -> QRect | None:
        if self._selection_start is None or self._selection_current is None:
            return None
        r = QRect(self._selection_start, self._selection_current).normalized()
        if r.width() < 2 or r.height() < 2:
            return None

        img_rect = self._pixmap_draw_rect()
        if img_rect is None:
            return None

        rx, ry, rw, rh = img_rect
        if rw <= 0 or rh <= 0:
            return None

        sx = self._pixmap.width() / rw
        sy = self._pixmap.height() / rh

        ix = int((r.left() - rx) * sx)
        iy = int((r.top() - ry) * sy)
        iw = int(r.width() * sx)
        ih = int(r.height() * sy)

        ix = max(0, min(ix, self._pixmap.width() - 1))
        iy = max(0, min(iy, self._pixmap.height() - 1))
        iw = min(iw, self._pixmap.width() - ix)
        ih = min(ih, self._pixmap.height() - iy)

        return QRect(ix, iy, iw, ih)

    def clear_selection(self) -> None:
        self._selection_start = None
        self._selection_current = None
        self._selection_active = False
        self.selection_changed.emit(None)
        self.update()

    # ==================== ЛИНИЯ ====================

    def clear_line(self) -> None:
        self._line_start = None
        self._line_current = None
        self._line_active = False
        self.update()

    # ==================== ГЕОМЕТРИЯ ====================

    def _pixmap_draw_rect(self) -> tuple[int, int, int, int] | None:
        if self._pixmap is None:
            return None
        scaled_w = int(self._pixmap.width() * self._zoom)
        scaled_h = int(self._pixmap.height() * self._zoom)
        cx = self.width() // 2 + self._offset.x()
        cy = self.height() // 2 + self._offset.y()
        x = cx - scaled_w // 2
        y = cy - scaled_h // 2
        return (x, y, scaled_w, scaled_h)

    def _widget_to_image_pos(self, wx: float, wy: float) -> tuple[int, int] | None:
        if self._pixmap is None:
            return None
        rect = self._pixmap_draw_rect()
        if rect is None:
            return None
        rx, ry, rw, rh = rect
        if rw <= 0 or rh <= 0:
            return None
        if wx < rx or wx >= rx + rw or wy < ry or wy >= ry + rh:
            return None
        fx = int((wx - rx) * self._pixmap.width() / rw)
        fy = int((wy - ry) * self._pixmap.height() / rh)
        fx = max(0, min(fx, self._pixmap.width() - 1))
        fy = max(0, min(fy, self._pixmap.height() - 1))
        return (fx, fy)

    def _widget_to_image_point_clamped(self, wx: float, wy: float) -> QPoint | None:
        """Как _widget_to_image_pos, но без проверки границ — клампит."""
        if self._pixmap is None:
            return None
        rect = self._pixmap_draw_rect()
        if rect is None:
            return None
        rx, ry, rw, rh = rect
        if rw <= 0 or rh <= 0:
            return None
        fx = int((wx - rx) * self._pixmap.width() / rw)
        fy = int((wy - ry) * self._pixmap.height() / rh)
        fx = max(0, min(fx, self._pixmap.width() - 1))
        fy = max(0, min(fy, self._pixmap.height() - 1))
        return QPoint(fx, fy)

    def _image_point_to_widget(self, ix: int, iy: int) -> QPoint | None:
        """Координаты изображения → координаты виджета."""
        if self._pixmap is None:
            return None
        rect = self._pixmap_draw_rect()
        if rect is None:
            return None
        rx, ry, rw, rh = rect
        if self._pixmap.width() <= 0 or self._pixmap.height() <= 0:
            return None
        wx = rx + int(ix * rw / self._pixmap.width())
        wy = ry + int(iy * rh / self._pixmap.height())
        return QPoint(wx, wy)

    # ==================== РИСОВАНИЕ ====================

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1a1a1a"))

        if self._pixmap is None:
            painter.end()
            return

        rect = self._pixmap_draw_rect()
        if rect is None:
            painter.end()
            return

        rx, ry, rw, rh = rect
        scaled = self._pixmap.scaled(
            rw, rh,
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
        painter.drawPixmap(rx, ry, scaled)

        # Рамка выделения
        if self._selection_start is not None and self._selection_current is not None:
            sel_rect = QRect(self._selection_start, self._selection_current).normalized()
            pen = QPen(QColor(IMAGE_SELECTION_COLOR), IMAGE_SELECTION_WIDTH)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(sel_rect)

        # Линия
        if self._line_start is not None and self._line_current is not None:
            pen = QPen(QColor("#4fc1ff"), 2)
            painter.setPen(pen)
            painter.drawLine(self._line_start, self._line_current)

            # Точки на концах
            painter.setBrush(QColor("#4fc1ff"))
            painter.drawEllipse(self._line_start, 3, 3)
            painter.drawEllipse(self._line_current, 3, 3)

        painter.end()

    # ==================== СОБЫТИЯ ====================

    def mouseMoveEvent(self, event):
        mx = event.position().x()
        my = event.position().y()

        # Пипетка
        pos = self._widget_to_image_pos(mx, my)
        if pos is not None and self._source_array is not None:
            fx, fy = pos
            self._last_mouse_pos = (fx, fy)
            arr = self._source_array
            if arr.ndim == 2:
                v = int(arr[fy, fx])
                rgb = (v, v, v)
            else:
                r = int(arr[fy, fx, 0])
                g = int(arr[fy, fx, 1]) if arr.shape[2] > 1 else r
                b = int(arr[fy, fx, 2]) if arr.shape[2] > 2 else r
                rgb = (r, g, b)
            self.pixel_hovered.emit(fx, fy, rgb)

        # Активные операции
        if self._selection_active and self._selection_start is not None:
            self._selection_current = QPoint(int(mx), int(my))
            self.update()
            self.selection_changed.emit(self.get_selection_rect())

        if self._line_active and self._line_start is not None:
            self._line_current = self._widget_to_image_point_clamped(mx, my)
            if self._line_current is not None:
                self._line_current = self._image_point_to_widget(
                    self._line_current.x(), self._line_current.y()
                )
            self.update()

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._mode == self.MODE_SELECTION:
                self._selection_active = True
                self._selection_start = QPoint(
                    int(event.position().x()),
                    int(event.position().y()),
                )
                self._selection_current = self._selection_start
            elif self._mode == self.MODE_LINE:
                self._line_active = True
                self._line_start = QPoint(
                    int(event.position().x()),
                    int(event.position().y()),
                )
                self._line_current = self._line_start
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._mode == self.MODE_SELECTION and self._selection_active:
                self._selection_active = False
                self.update()
                self.selection_changed.emit(self.get_selection_rect())

            elif self._mode == self.MODE_LINE and self._line_active:
                self._line_active = False
                self.update()
                self._emit_line_profile()

        super().mouseReleaseEvent(event)

    def _emit_line_profile(self) -> None:
        """Собрать начальную и конечную точки линии и эмитить сигнал."""
        if self._line_start is None or self._line_current is None:
            return

        start_img = self._widget_to_image_point_clamped(
            self._line_start.x(), self._line_start.y()
        )
        end_img = self._widget_to_image_point_clamped(
            self._line_current.x(), self._line_current.y()
        )
        if start_img is None or end_img is None:
            return

        # Отбрасываем, если линия слишком короткая
        dx = end_img.x() - start_img.x()
        dy = end_img.y() - start_img.y()
        if dx * dx + dy * dy < 4:
            return

        self.line_drawn.emit(start_img, end_img)

    def wheelEvent(self, event):
        if self._pixmap is None:
            return
        delta = event.angleDelta().y()
        if delta == 0:
            return
        factor = 1.15 if delta > 0 else 1 / 1.15
        cursor_pos = event.position().toPoint()
        self._apply_zoom(factor, cursor_pos)
        event.accept()

    def leaveEvent(self, event):
        self._last_mouse_pos = None
        self.mouse_left.emit()
        super().leaveEvent(event)

    # ==================== ZOOM ====================

    def _apply_zoom(self, factor: float, anchor_widget_pos: QPoint) -> None:
        old_zoom = self._zoom
        new_zoom = old_zoom * factor
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, new_zoom))
        if abs(new_zoom - old_zoom) < 1e-6:
            return

        rect = self._pixmap_draw_rect()
        if rect is None:
            return
        rx, ry, rw, rh = rect
        if rw <= 0 or rh <= 0:
            return

        anchor_img_x = (anchor_widget_pos.x() - rx) / rw * self._pixmap.width()
        anchor_img_y = (anchor_widget_pos.y() - ry) / rh * self._pixmap.height()

        self._zoom = new_zoom

        scaled_w = int(self._pixmap.width() * self._zoom)
        scaled_h = int(self._pixmap.height() * self._zoom)

        target_x = anchor_widget_pos.x() - anchor_img_x * self._zoom
        target_y = anchor_widget_pos.y() - anchor_img_y * self._zoom

        new_center_x = target_x + scaled_w // 2
        new_center_y = target_y + scaled_h // 2

        self._offset = QPoint(
            new_center_x - self.width() // 2,
            new_center_y - self.height() // 2,
        )

        self.zoom_changed.emit(self._zoom)
        self.update()