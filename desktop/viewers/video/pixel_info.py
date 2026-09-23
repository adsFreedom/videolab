"""Панель информации о пикселе под курсором."""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt


class PixelInfoWidget(QWidget):
    """Показывает RGB пикселя под курсором."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        self._coord_label = QLabel("—")
        self._coord_label.setMinimumWidth(100)
        self._coord_label.setStyleSheet("font-family: Consolas, monospace;")
        layout.addWidget(self._coord_label)

        self._color_swatch = QLabel()
        self._color_swatch.setFixedSize(24, 16)
        self._color_swatch.setStyleSheet(
            "background-color: #1a1a1a; border: 1px solid #3e3e42;"
        )
        layout.addWidget(self._color_swatch)

        self._rgb_label = QLabel("R: —  G: —  B: —")
        self._rgb_label.setStyleSheet("font-family: Consolas, monospace;")
        layout.addWidget(self._rgb_label)

        layout.addStretch()

    def update_pixel(self, x: int, y: int, rgb: tuple[int, int, int]) -> None:
        """Обновляет данные о пикселе."""
        r, g, b = rgb
        self._coord_label.setText(f"x: {x}   y: {y}")
        self._rgb_label.setText(f"R: {r:3d}  G: {g:3d}  B: {b:3d}")
        color = QColor(r, g, b)
        self._color_swatch.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #3e3e42;"
        )

    def clear(self) -> None:
        """Очищает данные."""
        self._coord_label.setText("—")
        self._rgb_label.setText("R: —  G: —  B: —")
        self._color_swatch.setStyleSheet(
            "background-color: #1a1a1a; border: 1px solid #3e3e42;"
        )