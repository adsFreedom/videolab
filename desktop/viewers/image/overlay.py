"""Оверлей с метаданными изображения."""
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt

from desktop.viewers.styles import VIDEO_OVERLAY_STYLE


class ImageOverlay(QLabel):
    """Оверлей: размер, формат, глубина, канал, zoom."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet(VIDEO_OVERLAY_STYLE)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setText("")

    def update_info(
        self,
        width: int,
        height: int,
        fmt: str,
        has_alpha: bool,
        channel: str,
        zoom: float,
    ) -> None:
        color_mode = "RGBA" if has_alpha else "RGB"
        text = (
            f"{width}x{height}   {fmt}   {color_mode}\n"
            f"Канал: {channel}    Zoom: {int(zoom * 100)}%"
        )
        self.setText(text)
        self.adjustSize()