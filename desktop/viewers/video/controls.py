"""Панель управления видео."""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSlider, QLabel,
)
from PySide6.QtCore import Qt, Signal

from desktop.viewers.styles import SYMBOL_BUTTON_STYLE, SEEK_SLIDER_STYLE


class VideoControls(QWidget):
    """Панель управления: play/pause, stop, loop, seek."""

    play_pause_clicked = Signal()
    stop_clicked = Signal()
    seek_requested = Signal(int)
    loop_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._is_playing = False
        self._total_frames = 0
        self._is_slider_dragging = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        btn_size = 36

        # Play / Pause
        self.btn_play = QPushButton("▶")
        self.btn_play.setToolTip("Play / Pause (Space)")
        self.btn_play.setFixedSize(btn_size, btn_size)
        self.btn_play.setStyleSheet(SYMBOL_BUTTON_STYLE)
        self.btn_play.clicked.connect(self.play_pause_clicked.emit)
        layout.addWidget(self.btn_play)

        # Stop
        self.btn_stop = QPushButton("■")
        self.btn_stop.setToolTip("Stop")
        self.btn_stop.setFixedSize(btn_size, btn_size)
        self.btn_stop.setStyleSheet(SYMBOL_BUTTON_STYLE)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.btn_stop)

        # Текущий кадр / всего
        self.label_frame = QLabel("0 / 0")
        self.label_frame.setStyleSheet("padding: 0 4px;")
        layout.addWidget(self.label_frame)

        # Seek
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.setFixedHeight(24)
        self.slider.setStyleSheet(SEEK_SLIDER_STYLE)
        self.slider.sliderPressed.connect(self._on_slider_pressed)
        self.slider.sliderReleased.connect(self._on_slider_released)
        self.slider.valueChanged.connect(self._on_slider_value_changed)
        layout.addWidget(self.slider, stretch=1)

        # Loop
        self.btn_loop = QPushButton("↻")
        self.btn_loop.setCheckable(True)
        self.btn_loop.setToolTip("Закольцевать воспроизведение")
        self.btn_loop.setFixedSize(btn_size, btn_size)
        self.btn_loop.setStyleSheet(SYMBOL_BUTTON_STYLE)
        self.btn_loop.toggled.connect(self.loop_toggled.emit)
        layout.addWidget(self.btn_loop)

    # ==================== API ====================

    def set_total_frames(self, total: int) -> None:
        self._total_frames = total
        self.slider.setRange(0, max(0, total - 1))
        self._update_frame_label(self.slider.value())

    def set_current_frame(self, frame_index: int) -> None:
        if self._is_slider_dragging:
            return
        self.slider.blockSignals(True)
        self.slider.setValue(frame_index)
        self.slider.blockSignals(False)
        self._update_frame_label(frame_index)

    def set_playing_state(self, is_playing: bool) -> None:
        self._is_playing = is_playing
        if is_playing:
            self.btn_play.setText("⏸")
        else:
            self.btn_play.setText("▶")

    def set_enabled_controls(self, enabled: bool) -> None:
        self.btn_play.setEnabled(enabled)
        self.btn_stop.setEnabled(enabled)
        self.btn_loop.setEnabled(enabled)
        self.slider.setEnabled(enabled)

    # ==================== ВНУТРЕННИЕ ====================

    def _update_frame_label(self, frame_index: int) -> None:
        display = frame_index + 1 if self._total_frames > 0 else 0
        self.label_frame.setText(f"{display} / {self._total_frames}")

    def _on_slider_pressed(self) -> None:
        self._is_slider_dragging = True

    def _on_slider_released(self) -> None:
        self._is_slider_dragging = False
        self.seek_requested.emit(self.slider.value())

    def _on_slider_value_changed(self, value: int) -> None:
        self._update_frame_label(value)
        if self._is_slider_dragging:
            self.seek_requested.emit(value)