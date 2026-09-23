"""Просмотрщик видео — композиция кирпичей."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut

from core.logger import log
from desktop.viewers.base import BaseViewer
from desktop.viewers.video.source import VideoSource
from desktop.viewers.video.surface import VideoSurface
from desktop.viewers.video.controls import VideoControls
from desktop.viewers.video.overlay import OverlayWidget
from desktop.viewers.video.pixel_info import PixelInfoWidget
from desktop.viewers.video.speed_slider import SpeedSlider


SURFACE_FRAME_STYLE = """
QFrame#VideoFrame {
    border: 2px solid #3e4a5a;
    border-radius: 4px;
    background-color: #0d0d0d;
}
"""


class VideoViewer(BaseViewer):
    """Просмотрщик одного видеофайла."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._source = VideoSource()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer_tick)

        self._is_playing = False
        self._loop = False

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
        self._surface_frame.setStyleSheet(SURFACE_FRAME_STYLE)

        frame_layout = QVBoxLayout(self._surface_frame)
        frame_layout.setContentsMargins(2, 2, 2, 2)
        frame_layout.setSpacing(0)

        self._surface = VideoSurface()
        self._surface.pixel_hovered.connect(self._on_pixel_hovered)
        self._surface.mouse_left.connect(self._on_mouse_left)
        self._surface.clicked.connect(self._on_surface_clicked)
        frame_layout.addWidget(self._surface)

        left_layout.addWidget(self._surface_frame, stretch=1)

        self._overlay = OverlayWidget(self._surface)
        self._overlay.move(10, 10)
        self._overlay.hide()

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
        log(
            "INFO",
            f"Видео загружено: {info.frame_count} кадров, "
            f"{info.fps:.2f} fps, {info.width}x{info.height}"
        )

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
        """Клик по видео — play/pause. Если видео в конце — с начала."""
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

    # ==================== СОБЫТИЯ ====================

    def _on_pixel_hovered(self, x: int, y: int, rgb: tuple) -> None:
        self._pixel_info.update_pixel(x, y, rgb)

    def _on_mouse_left(self) -> None:
        self._pixel_info.clear()