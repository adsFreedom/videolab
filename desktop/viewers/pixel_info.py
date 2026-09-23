"""Панель информации о пикселе под курсором."""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

from desktop.viewers.styles import (
    PIXEL_COORD_LABEL_STYLE,
    PIXEL_RGB_LABEL_STYLE,
    PIXEL_SWATCH_EMPTY_STYLE,
    PIXEL_SWATCH_TEMPLATE,
)


class PixelInfoWidget(QWidget):
    """Показывает RGB пикселя под курсором. Общий для video и image."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        self._coord_label = QLabel("—")
        self._coord_label.setMinimumWidth(100)
        self._coord_label.setStyleSheet(PIXEL_COORD_LABEL_STYLE)
        layout.addWidget(self._coord_label)

        self._color_swatch = QLabel()
        self._color_swatch.setFixedSize(24, 16)
        self._color_swatch.setStyleSheet(PIXEL_SWATCH_EMPTY_STYLE)
        layout.addWidget(self._color_swatch)

        self._rgb_label = QLabel("R: —  G: —  B: —")
        self._rgb_label.setStyleSheet(PIXEL_RGB_LABEL_STYLE)
        layout.addWidget(self._rgb_label)

        layout.addStretch()

    def update_pixel(self, x: int, y: int, rgb: tuple[int, int, int]) -> None:
        r, g, b = rgb
        self._coord_label.setText(f"x: {x}   y: {y}")
        self._rgb_label.setText(f"R: {r:3d}  G: {g:3d}  B: {b:3d}")
        color = QColor(r, g, b)
        self._color_swatch.setStyleSheet(
            PIXEL_SWATCH_TEMPLATE.format(color=color.name())
        )

    def clear(self) -> None:
        self._coord_label.setText("—")
        self._rgb_label.setText("R: —  G: —  B: —")
        self._color_swatch.setStyleSheet(PIXEL_SWATCH_EMPTY_STYLE)