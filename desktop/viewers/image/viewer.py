"""Просмотрщик изображения — композиция кирпичей."""
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QKeySequence, QShortcut, QPixmap, QImage

from core.logger import log
from desktop.viewers.base import BaseViewer
from desktop.viewers.pixel_info import PixelInfoWidget
from desktop.viewers.styles import IMAGE_FRAME_STYLE
from desktop.viewers.image.source import ImageSource
from desktop.viewers.image.surface import ImageSurface
from desktop.viewers.image.controls import ImageControls
from desktop.viewers.image.overlay import ImageOverlay
from desktop.viewers.image.histogram_window import HistogramWindow
from desktop.viewers.image.line_profile_window import LineProfileWindow


class ImageViewer(BaseViewer):
    """Просмотрщик одного изображения."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._source = ImageSource()
        self._histogram_window: HistogramWindow | None = None
        self._line_profile_window: LineProfileWindow | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._controls = ImageControls()
        self._controls.fit_clicked.connect(self._on_fit)
        self._controls.reset_clicked.connect(self._on_reset)
        self._controls.space_changed.connect(self._on_space_changed)
        self._controls.channel_changed.connect(self._on_channel_changed)
        self._controls.extract_clicked.connect(self._on_extract_selection)
        self._controls.histogram_clicked.connect(self.show_histogram)
        self._controls.line_profile_clicked.connect(self._on_line_profile_toggled)
        root.addWidget(self._controls)

        self._surface_frame = QFrame()
        self._surface_frame.setObjectName("ImageFrame")
        self._surface_frame.setStyleSheet(IMAGE_FRAME_STYLE)

        frame_layout = QVBoxLayout(self._surface_frame)
        frame_layout.setContentsMargins(2, 2, 2, 2)
        frame_layout.setSpacing(0)

        self._surface = ImageSurface()
        self._surface.pixel_hovered.connect(self._on_pixel_hovered)
        self._surface.mouse_left.connect(self._on_mouse_left)
        self._surface.selection_changed.connect(self._on_selection_changed)
        self._surface.zoom_changed.connect(self._on_zoom_changed)
        self._surface.line_drawn.connect(self._on_line_drawn)
        frame_layout.addWidget(self._surface)

        root.addWidget(self._surface_frame, stretch=1)

        self._overlay = ImageOverlay(self._surface)
        self._overlay.move(10, 10)
        self._overlay.hide()

        self._pixel_info = PixelInfoWidget()
        root.addWidget(self._pixel_info)

        QShortcut(QKeySequence("Ctrl++"), self, self._on_zoom_in,
                  context=Qt.ApplicationShortcut)
        QShortcut(QKeySequence("Ctrl+="), self, self._on_zoom_in,
                  context=Qt.ApplicationShortcut)
        QShortcut(QKeySequence("Ctrl+-"), self, self._on_zoom_out,
                  context=Qt.ApplicationShortcut)
        QShortcut(QKeySequence("Ctrl+0"), self, self._on_reset,
                  context=Qt.ApplicationShortcut)
        QShortcut(QKeySequence("Ctrl+1"), self, self._on_fit,
                  context=Qt.ApplicationShortcut)
        QShortcut(QKeySequence("Ctrl+E"), self, self._on_extract_selection,
                  context=Qt.ApplicationShortcut)

        self._controls.set_enabled_controls(False)

    # ==================== API ====================

    def load(self, file_path: str) -> None:
        if not self._source.open(file_path):
            log("ERROR", f"Не удалось открыть изображение: {file_path}")
            return
        log("INFO",
            f"Изображение загружено: {self._source.width}x{self._source.height}, "
            f"{self._source.format}")
        self._finish_load()

    def load_from_array(self, arr: np.ndarray, name: str = "crop") -> None:
        if not self._source.open_from_array(arr, name):
            log("ERROR", "Не удалось загрузить изображение из массива")
            return
        log("INFO", f"Изображение (crop): {self._source.width}x{self._source.height}")
        self._finish_load()

    def _finish_load(self) -> None:
        self._controls.set_enabled_controls(True)
        space = self._controls.get_space()
        channels = self._source.get_available_channels(space)
        self._controls.set_channels(channels)
        self._refresh_display()
        self._surface.reset_view()
        self._update_histogram()
        self._overlay.show()
        self._update_overlay()

    def cleanup(self) -> None:
        self._source.close()
        self._surface.clear()
        self._pixel_info.clear()
        self._overlay.hide()
        if self._histogram_window is not None:
            self._histogram_window.close()
        if self._line_profile_window is not None:
            self._line_profile_window.close()

    # ==================== ОТОБРАЖЕНИЕ ====================

    def _refresh_display(self) -> None:
        if not self._source.is_open:
            return
        space = self._controls.get_space()
        channel = self._controls.get_channel()
        arr = self._source.get_channel_array(channel, space)
        if arr is None:
            return
        if arr.ndim == 2:
            rgb = np.stack([arr, arr, arr], axis=-1)
        else:
            rgb = arr
        rgb = np.ascontiguousarray(rgb)
        h, w = rgb.shape[:2]
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        self._surface.set_image(pixmap, source_array=arr)

    def _update_overlay(self) -> None:
        self._overlay.update_info(
            width=self._source.width,
            height=self._source.height,
            fmt=self._source.format,
            has_alpha=self._source.has_alpha,
            channel=f"{self._controls.get_space()} / {self._controls.get_channel()}",
            zoom=self._surface.get_zoom(),
        )

    # ==================== УПРАВЛЕНИЕ ====================

    def _on_zoom_in(self) -> None:
        self._surface.zoom_in()

    def _on_zoom_out(self) -> None:
        self._surface.zoom_out()

    def _on_fit(self) -> None:
        self._surface.fit_to_window()

    def _on_reset(self) -> None:
        self._surface.reset_view()

    def _on_space_changed(self, space: str) -> None:
        if not self._source.is_open:
            return
        channels = self._source.get_available_channels(space)
        self._controls.set_channels(channels)
        old_zoom = self._surface.get_zoom()
        self._refresh_display()
        self._surface.set_zoom(old_zoom)
        self._update_overlay()
        self._update_histogram()

    def _on_channel_changed(self, channel: str) -> None:
        if not self._source.is_open:
            return
        old_zoom = self._surface.get_zoom()
        self._refresh_display()
        self._surface.set_zoom(old_zoom)
        self._update_overlay()
        self._update_histogram()

    def _on_zoom_changed(self, zoom: float) -> None:
        self._controls.set_zoom_label(zoom)
        self._update_overlay()

    def _on_selection_changed(self, rect: QRect | None) -> None:
        has_selection = rect is not None and rect.width() > 0 and rect.height() > 0
        self._controls.set_extract_enabled(has_selection)

    # ==================== СОБЫТИЯ ====================

    def _on_pixel_hovered(self, x: int, y: int, rgb: tuple) -> None:
        self._pixel_info.update_pixel(x, y, rgb)

    def _on_mouse_left(self) -> None:
        self._pixel_info.clear()

    # ==================== ИЗВЛЕЧЕНИЕ ОБЛАСТИ ====================

    def _on_extract_selection(self) -> None:
        rect = self._surface.get_selection_rect()
        if rect is None or rect.width() < 2 or rect.height() < 2:
            return
        arr = self._source.array
        if arr is None:
            return

        x, y, w, h = rect.left(), rect.top(), rect.width(), rect.height()
        crop = arr[y:y + h, x:x + w].copy()
        crop_name = f"{self._source.file_name}_crop_{x}_{y}_{w}_{h}"

        crop_window = _CropViewerWindow(crop, crop_name, parent=self.window())
        crop_window.show()
        log("INFO", f"Извлечена область: {x},{y} {w}x{h}")
        self._surface.clear_selection()

    # ==================== LINE PROFILE ====================

    def _on_line_profile_toggled(self) -> None:
        """Пользователь нажал кнопку Line Profile."""
        if self._controls.btn_line.isChecked():
            self._surface.set_mode(ImageSurface.MODE_LINE)
            self._surface.setCursor(Qt.CrossCursor)
            log("INFO", "Режим: линия для Line Profile")
        else:
            self._surface.set_mode(ImageSurface.MODE_SELECTION)
            log("INFO", "Режим: выделение области")

    def _on_line_drawn(self, start: QPoint, end: QPoint) -> None:
        """Пользователь провёл линию — считаем профиль."""
        if not self._source.is_open:
            return

        arr = self._source.array
        if arr is None:
            return

        # Профиль считаем по **оригинальному** RGB-массиву (не по каналу)
        r, g, b, y = self._compute_profile(arr, start, end)

        if r is None:
            return

        length = float(np.hypot(end.x() - start.x(), end.y() - start.y()))

        if self._line_profile_window is None:
            self._line_profile_window = LineProfileWindow(parent=self.window())
        self._line_profile_window.set_profile(
            r, g, b, y,
            (start.x(), start.y()),
            (end.x(), end.y()),
            length,
        )
        self._line_profile_window.show()
        self._line_profile_window.raise_()
        self._line_profile_window.activateWindow()

    def _compute_profile(self, arr: np.ndarray, start: QPoint, end: QPoint):
        """
        Считает значения R, G, B, Y вдоль линии.
        Использует алгоритм Брезенхэма для выборки пикселей.
        """
        x0, y0 = start.x(), start.y()
        x1, y1 = end.x(), end.y()

        num_samples = max(abs(x1 - x0), abs(y1 - y0)) + 1
        if num_samples < 2:
            return None, None, None, None

        xs = np.linspace(x0, x1, num_samples).astype(int)
        ys = np.linspace(y0, y1, num_samples).astype(int)

        h, w = arr.shape[:2]
        xs = np.clip(xs, 0, w - 1)
        ys = np.clip(ys, 0, h - 1)

        # RGB или grayscale
        if arr.ndim == 2:
            vals = arr[ys, xs]
            r = vals.astype(float)
            g = vals.astype(float)
            b = vals.astype(float)
            y = vals.astype(float)
        else:
            r = arr[ys, xs, 0].astype(float)
            g = arr[ys, xs, 1].astype(float) if arr.shape[2] > 1 else r
            b = arr[ys, xs, 2].astype(float) if arr.shape[2] > 2 else r
            y = 0.299 * r + 0.587 * g + 0.114 * b

        return r, g, b, y

    # ==================== ГИСТОГРАММА ====================

    def _update_histogram(self) -> None:
        if not self._source.is_open:
            return
        if self._histogram_window is None:
            return
        space = self._controls.get_space()
        data = self._source.get_histogram_data(space)
        self._histogram_window.set_data(data, space)
        self._histogram_window.set_title_file(self._source.file_name)

    def show_histogram(self) -> None:
        if self._histogram_window is None:
            self._histogram_window = HistogramWindow(parent=self.window())
        self._update_histogram()
        self._histogram_window.show()
        self._histogram_window.raise_()
        self._histogram_window.activateWindow()


class _CropViewerWindow(QWidget):
    """Отдельное окно с полноценным ImageViewer для вырезанной области."""

    def __init__(self, arr: np.ndarray, name: str, parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle(f"Область: {name}")
        self.resize(900, 700)

        self._viewer = ImageViewer()
        self._viewer.load_from_array(arr, name)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._viewer)

    def closeEvent(self, event):
        try:
            self._viewer.cleanup()
        except Exception:
            pass
        super().closeEvent(event)