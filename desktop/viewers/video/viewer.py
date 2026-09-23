"""Просмотрщик видео — композиция кирпичей."""
import numpy as np
import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QMessageBox, QProgressDialog,
)
from PySide6.QtCore import Qt, QTimer, QPoint, QRect
from PySide6.QtGui import QKeySequence, QShortcut

from core.logger import log
from desktop.viewers.base import BaseViewer
from desktop.viewers.pixel_info import PixelInfoWidget
from desktop.viewers.styles import VIDEO_FRAME_STYLE
from desktop.viewers.video.source import VideoSource
from desktop.viewers.video.surface import VideoSurface
from desktop.viewers.video.controls import VideoControls
from desktop.viewers.video.overlay import OverlayWidget
from desktop.viewers.video.speed_slider import SpeedSlider
from desktop.viewers.video.pixel_marker import (
    PixelMarkerOverlay,
    ROIMarkerOverlay,
)
from desktop.viewers.video.signal_window import SignalWindow


class VideoViewer(BaseViewer):
    """Просмотрщик одного видеофайла."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._source = VideoSource()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer_tick)

        self._is_playing = False
        self._loop = False

        self._marked_pixel: tuple[int, int] | None = None
        self._marked_roi: tuple[int, int, int, int] | None = None

        self._signal_window: SignalWindow | None = None

        # --- Компоновка ---
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(4, 4, 4, 0)
        left_layout.setSpacing(0)

        self._surface_frame = QFrame()
        self._surface_frame.setObjectName("VideoFrame")
        self._surface_frame.setStyleSheet(VIDEO_FRAME_STYLE)

        frame_layout = QVBoxLayout(self._surface_frame)
        frame_layout.setContentsMargins(2, 2, 2, 2)
        frame_layout.setSpacing(0)

        self._surface = VideoSurface()
        self._surface.pixel_hovered.connect(self._on_pixel_hovered)
        self._surface.mouse_left.connect(self._on_mouse_left)
        self._surface.clicked.connect(self._on_surface_clicked)
        self._surface.pixel_marked.connect(self._on_pixel_marked)
        self._surface.roi_marked.connect(self._on_roi_marked)
        frame_layout.addWidget(self._surface)

        left_layout.addWidget(self._surface_frame, stretch=1)

        # Overlay
        self._overlay = OverlayWidget(self._surface)
        self._overlay.move(10, 10)
        self._overlay.hide()

        # Маркеры
        self._pixel_marker = PixelMarkerOverlay(self._surface)
        self._pixel_marker.setGeometry(self._surface.rect())
        self._pixel_marker.raise_()

        self._roi_marker = ROIMarkerOverlay(self._surface)
        self._roi_marker.setGeometry(self._surface.rect())
        self._roi_marker.raise_()

        self._pixel_info = PixelInfoWidget()
        left_layout.addWidget(self._pixel_info)

        top_layout.addLayout(left_layout, stretch=1)

        self._speed = SpeedSlider()
        self._speed.speed_changed.connect(self._on_speed_changed)
        top_layout.addWidget(self._speed)

        root.addLayout(top_layout, stretch=1)

        self._controls = VideoControls()
        self._controls.play_pause_clicked.connect(self._on_play_pause)
        self._controls.stop_clicked.connect(self._on_stop)
        self._controls.seek_requested.connect(self._on_seek)
        self._controls.loop_toggled.connect(self._on_loop_toggled)
        self._controls.mark_pixel_toggled.connect(self._on_mark_pixel_toggled)
        self._controls.mark_roi_toggled.connect(self._on_mark_roi_toggled)
        root.addWidget(self._controls)

        self._controls.set_enabled_controls(False)

        # --- Горячие клавиши ---
        QShortcut(QKeySequence("Space"), self, self._on_play_pause,
                  context=Qt.ApplicationShortcut)
        QShortcut(QKeySequence("Left"), self, self._on_step_backward,
                  context=Qt.ApplicationShortcut)
        QShortcut(QKeySequence("Right"), self, self._on_step_forward,
                  context=Qt.ApplicationShortcut)
        QShortcut(QKeySequence("Home"), self, self._on_home,
                  context=Qt.ApplicationShortcut)
        QShortcut(QKeySequence("End"), self, self._on_end,
                  context=Qt.ApplicationShortcut)

    # ==================== API ====================

    def load(self, file_path: str) -> None:
        self._timer.stop()
        self._is_playing = False

        if not self._source.open(file_path):
            log("ERROR", f"Не удалось открыть видео: {file_path}")
            return

        info = self._source.info
        log("INFO",
            f"Видео загружено: {info.frame_count} кадров, "
            f"{info.fps:.2f} fps, {info.width}x{info.height}")

        self._controls.set_total_frames(info.frame_count)
        self._controls.set_current_frame(0)
        self._controls.set_enabled_controls(True)
        self._controls.set_playing_state(False)

        self._render_frame(0)
        self._overlay.show()

    def cleanup(self) -> None:
        self._timer.stop()
        self._source.close()
        self._surface.clear()
        self._pixel_info.clear()
        self._overlay.hide()
        self._pixel_marker.clear()
        self._roi_marker.clear()
        if self._signal_window is not None:
            self._signal_window.close()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixel_marker is not None:
            self._pixel_marker.setGeometry(self._surface.rect())
        if self._roi_marker is not None:
            self._roi_marker.setGeometry(self._surface.rect())

    # ==================== УПРАВЛЕНИЕ ====================

    def _on_play_pause(self) -> None:
        if not self._source.is_open:
            return
        if self._is_playing:
            self._pause()
        else:
            if self._source.current_frame >= self._source.frame_count - 1:
                self._render_frame(0)
                self._controls.set_current_frame(0)
            self._play()

    def _on_surface_clicked(self) -> None:
        if self._surface.get_mode() != VideoSurface.MODE_PLAY_PAUSE:
            return
        if not self._source.is_open:
            return
        if self._is_playing:
            self._pause()
        else:
            if self._source.current_frame >= self._source.frame_count - 1:
                self._render_frame(0)
                self._controls.set_current_frame(0)
            self._play()

    def _play(self) -> None:
        self._is_playing = True
        self._controls.set_playing_state(True)
        self._timer.start(self._compute_interval_ms())

    def _pause(self) -> None:
        self._is_playing = False
        self._controls.set_playing_state(False)
        self._timer.stop()

    def _compute_interval_ms(self) -> int:
        fps = self._source.fps if self._source.fps > 0 else 30.0
        speed = self._speed.get_speed()
        if speed <= 0:
            speed = 1.0
        interval = int(1000.0 / (fps * speed))
        return max(1, interval)

    def _on_stop(self) -> None:
        self._pause()
        self._render_frame(0)
        self._controls.set_current_frame(0)

    def _on_seek(self, frame_index: int) -> None:
        self._render_frame(frame_index)
        self._controls.set_current_frame(frame_index)

    def _on_step_backward(self) -> None:
        self._pause()
        current = self._source.current_frame
        new_frame = max(0, current - 1)
        self._render_frame(new_frame)
        self._controls.set_current_frame(new_frame)

    def _on_step_forward(self) -> None:
        self._pause()
        current = self._source.current_frame
        new_frame = min(self._source.frame_count - 1, current + 1)
        self._render_frame(new_frame)
        self._controls.set_current_frame(new_frame)

    def _on_home(self) -> None:
        self._pause()
        self._render_frame(0)
        self._controls.set_current_frame(0)

    def _on_end(self) -> None:
        self._pause()
        last = self._source.frame_count - 1
        if last < 0:
            last = 0
        self._render_frame(last)
        self._controls.set_current_frame(last)

    def _on_speed_changed(self, speed: float) -> None:
        if self._is_playing:
            self._timer.start(self._compute_interval_ms())

    def _on_loop_toggled(self, enabled: bool) -> None:
        self._loop = enabled

    def _on_timer_tick(self) -> None:
        current = self._source.current_frame
        next_frame = current + 1
        if next_frame >= self._source.frame_count:
            if self._loop:
                next_frame = 0
            else:
                self._pause()
                return
        self._render_frame(next_frame)
        self._controls.set_current_frame(next_frame)

    # ==================== РЕНДЕР ====================

    def _render_frame(self, frame_index: int) -> None:
        frame = self._source.get_frame(frame_index)
        if frame is None:
            return
        self._surface.set_frame(frame)
        self._update_overlay(frame_index)
        self._update_markers()

    def _update_overlay(self, frame_index: int) -> None:
        info = self._source.info
        if info is None:
            return
        time_sec = frame_index / info.fps if info.fps > 0 else 0.0
        self._overlay.update_info(
            frame_index=frame_index,
            frame_count=info.frame_count,
            time_sec=time_sec,
            duration=info.duration,
            fps=info.fps,
            width=info.width,
            height=info.height,
        )

    def _update_markers(self) -> None:
        """Обновить позиции маркеров (например, при resize)."""
        if self._marked_pixel is not None:
            img_x, img_y = self._marked_pixel
            widget_pos = self._surface.image_to_widget_pos(img_x, img_y)
            if widget_pos is not None:
                self._pixel_marker.set_pixel(self._marked_pixel, widget_pos)

    # ==================== СОБЫТИЯ ====================

    def _on_pixel_hovered(self, x: int, y: int, rgb: tuple) -> None:
        self._pixel_info.update_pixel(x, y, rgb)

    def _on_mouse_left(self) -> None:
        self._pixel_info.clear()

    # ==================== МАРКЕР ПИКСЕЛЯ ====================

    def _on_mark_pixel_toggled(self, checked: bool) -> None:
        if checked:
            self._surface.set_mode(VideoSurface.MODE_MARK_PIXEL)
            log("INFO", "Режим: отметка пикселя")
        else:
            self._surface.set_mode(VideoSurface.MODE_PLAY_PAUSE)
            self._marked_pixel = None
            self._pixel_marker.clear()
            log("INFO", "Режим: воспроизведение")

    def _on_pixel_marked(self, img_x: int, img_y: int, widget_pos: QPoint) -> None:
        self._marked_pixel = (img_x, img_y)
        self._pixel_marker.set_pixel(self._marked_pixel, widget_pos)
        log("INFO", f"Пиксель отмечен: ({img_x}, {img_y})")
        self._collect_pixel_signal()

    # ==================== МАРКЕР ROI ====================

    def _on_mark_roi_toggled(self, checked: bool) -> None:
        if checked:
            self._surface.set_mode(VideoSurface.MODE_MARK_ROI)
            log("INFO", "Режим: выделение ROI")
        else:
            self._surface.set_mode(VideoSurface.MODE_PLAY_PAUSE)
            self._marked_roi = None
            self._roi_marker.clear()
            log("INFO", "Режим: воспроизведение")

    def _on_roi_marked(
        self, x: int, y: int, w: int, h: int, widget_rect: QRect,
    ) -> None:
        self._marked_roi = (x, y, w, h)
        self._roi_marker.set_rect((x, y, w, h), widget_rect)
        log("INFO", f"ROI отмечен: ({x}, {y}) {w}x{h}")
        self._collect_roi_signal()

    # ==================== СБОР СИГНАЛА ====================

    def _collect_pixel_signal(self) -> None:
        """Сбор RGB для отмеченного пикселя."""
        if self._marked_pixel is None or not self._source.is_open:
            return

        info = self._source.info
        if info is None:
            return

        img_x, img_y = self._marked_pixel
        video_path = self._source.file_path

        def picker(frame):
            h, w = frame.shape[:2]
            px = min(max(img_x, 0), w - 1)
            py = min(max(img_y, 0), h - 1)
            b, g, r = frame[py, px]
            return (int(r), int(g), int(b))

        title = f"пикселя ({img_x}, {img_y})"
        self._collect_and_show(video_path, info, picker, title)

    def _collect_roi_signal(self) -> None:
        """Сбор среднего RGB по ROI."""
        if self._marked_roi is None or not self._source.is_open:
            return

        info = self._source.info
        if info is None:
            return

        rx, ry, rw, rh = self._marked_roi
        video_path = self._source.file_path

        def picker(frame):
            h, w = frame.shape[:2]
            x1 = min(max(rx, 0), w - 1)
            y1 = min(max(ry, 0), h - 1)
            x2 = min(max(rx + rw, 0), w)
            y2 = min(max(ry + rh, 0), h)
            if x2 <= x1 or y2 <= y1:
                return (0, 0, 0)
            region = frame[y1:y2, x1:x2]
            mean_bgr = region.mean(axis=(0, 1))
            b, g, r = mean_bgr
            return (int(r), int(g), int(b))

        title = f"ROI ({rx}, {ry}) {rw}x{rh}"
        self._collect_and_show(video_path, info, picker, title)

    def _collect_and_show(self, video_path, info, picker, title: str) -> None:
        """Общий сбор данных и открытие окна сигнала."""
        progress = QProgressDialog(
            f"Сбор данных: {title}...",
            "Отмена", 0, info.frame_count, self
        )
        progress.setWindowTitle("Сбор сигнала")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(200)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            progress.close()
            QMessageBox.warning(self, "Ошибка", "Не удалось открыть видео")
            return

        values = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % 10 == 0:
                progress.setValue(frame_idx)
                if progress.wasCanceled():
                    break

            values.append(picker(frame))
            frame_idx += 1

        cap.release()
        progress.setValue(info.frame_count)
        progress.close()

        if not values:
            QMessageBox.warning(self, "Ошибка", "Не удалось собрать данные")
            return

        rgb_data = np.array(values, dtype=np.uint8)

        if self._signal_window is None:
            self._signal_window = SignalWindow(parent=self.window())
        self._signal_window.set_signal(
            rgb_data=rgb_data,
            fps=info.fps,
            pixel_xy=(0, 0),
            video_name=f"{self._source.file_name} — {title}",
        )
        self._signal_window.show()
        self._signal_window.raise_()
        self._signal_window.activateWindow()