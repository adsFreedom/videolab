"""Оверлей с информацией о видео."""
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt

from desktop.viewers.styles import VIDEO_OVERLAY_STYLE


class OverlayWidget(QLabel):
    """Оверлей: время, кадр, fps."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet(VIDEO_OVERLAY_STYLE)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setText("")

    def update_info(
        self,
        frame_index: int,
        frame_count: int,
        time_sec: float,
        duration: float,
        fps: float,
        width: int,
        height: int,
    ) -> None:
        time_str = self._format_time(time_sec)
        dur_str = self._format_time(duration)

        display_frame = frame_index + 1

        text = (
            f"{time_str} / {dur_str}\n"
            f"кадр: {display_frame} / {frame_count}\n"
            f"fps: {fps:.2f}   {width}x{height}"
        )
        self.setText(text)
        self.adjustSize()

    @staticmethod
    def _format_time(seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:06.3f}"
        return f"{m:02d}:{s:06.3f}"