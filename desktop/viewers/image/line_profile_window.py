"""Окно профиля по линии."""
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PySide6.QtCore import Qt

from desktop.viewers.styles import (
    HISTOGRAM_BG,
    HISTOGRAM_COLOR_R,
    HISTOGRAM_COLOR_G,
    HISTOGRAM_COLOR_B,
    HISTOGRAM_COLOR_Y,
    MEDIA_BUTTON_STYLE,
)


class LineProfileWindow(QMainWindow):
    """Отдельное окно с графиком профиля вдоль линии."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Профиль по линии")
        self.resize(700, 400)

        # Конфигурация pyqtgraph
        pg.setConfigOptions(antialias=True)

        # Основной виджет
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Заголовок
        self._info_label = QLabel("Проведите линию на изображении")
        self._info_label.setStyleSheet(
            "padding: 4px; font-family: Consolas; font-size: 9pt;"
        )
        layout.addWidget(self._info_label)

        # График
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground(HISTOGRAM_BG)
        self._plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self._plot_widget.setLabel("bottom", "Позиция вдоль линии")
        self._plot_widget.setLabel("left", "Значение")
        self._plot_widget.addLegend()

        # Кривые
        self._curve_r = self._plot_widget.plot(
            pen=pg.mkPen(HISTOGRAM_COLOR_R, width=1.5), name="R",
        )
        self._curve_g = self._plot_widget.plot(
            pen=pg.mkPen(HISTOGRAM_COLOR_G, width=1.5), name="G",
        )
        self._curve_b = self._plot_widget.plot(
            pen=pg.mkPen(HISTOGRAM_COLOR_B, width=1.5), name="B",
        )
        self._curve_y = self._plot_widget.plot(
            pen=pg.mkPen(HISTOGRAM_COLOR_Y, width=1.5, style=Qt.DashLine), name="Y",
        )

        layout.addWidget(self._plot_widget, stretch=1)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._btn_clear = QPushButton("Очистить")
        self._btn_clear.setStyleSheet(MEDIA_BUTTON_STYLE)
        self._btn_clear.clicked.connect(self.clear)
        btn_layout.addWidget(self._btn_clear)
        layout.addLayout(btn_layout)

        self.setCentralWidget(container)

    # ==================== API ====================

    def set_profile(
        self,
        values_r: np.ndarray,
        values_g: np.ndarray,
        values_b: np.ndarray,
        values_y: np.ndarray,
        start_xy: tuple[int, int],
        end_xy: tuple[int, int],
        length_px: float,
    ) -> None:
        """Обновляет график."""
        x = np.arange(len(values_r))

        self._curve_r.setData(x, values_r)
        self._curve_g.setData(x, values_g)
        self._curve_b.setData(x, values_b)
        self._curve_y.setData(x, values_y)

        self._info_label.setText(
            f"({start_xy[0]}, {start_xy[1]}) → ({end_xy[0]}, {end_xy[1]})   "
            f"Длина: {length_px:.1f} px   Точек: {len(values_r)}"
        )

        self._plot_widget.autoRange()

    def clear(self) -> None:
        self._curve_r.setData([], [])
        self._curve_g.setData([], [])
        self._curve_b.setData([], [])
        self._curve_y.setData([], [])
        self._info_label.setText("Проведите линию на изображении")