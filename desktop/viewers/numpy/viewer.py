"""Просмотрщик numpy-файлов."""
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QDoubleSpinBox, QCheckBox, QSlider, QFrame,
)
from PySide6.QtCore import Qt

from core.logger import log
from desktop.viewers.base import BaseViewer
from desktop.viewers.numpy.source import NumpySource
from desktop.viewers.numpy.canvas import NumpyCanvas, COLORMAPS


class NumpyViewer(BaseViewer):
    """Просмотрщик .npy / .npz файлов."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._source = NumpySource()

        # Для 3D: текущий индекс
        self._slice_index = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ==================== ВЕРХНЯЯ ПАНЕЛЬ ====================

        top = QHBoxLayout()
        top.setContentsMargins(8, 8, 8, 8)
        top.setSpacing(8)

        # Инфо (название файла, размер, dtype)
        self._info_label = QLabel("(нет данных)")
        self._info_label.setStyleSheet(
            "font-family: Consolas; font-size: 9pt; font-weight: bold;"
        )
        top.addWidget(self._info_label)

        top.addStretch()

        # Палитра
        top.addWidget(QLabel("Палитра:"))
        self.combo_colormap = QComboBox()
        self.combo_colormap.setFixedWidth(90)
        self.combo_colormap.addItems(list(COLORMAPS.keys()))
        self.combo_colormap.currentTextChanged.connect(self._on_colormap_changed)
        top.addWidget(self.combo_colormap)

        root.addLayout(top)

        # ==================== ГЛАВНАЯ ОБЛАСТЬ ====================

        # Слайдер для 3D (сначала скрыт)
        self._slice_row = QWidget()
        slice_layout = QHBoxLayout(self._slice_row)
        slice_layout.setContentsMargins(8, 0, 8, 0)

        self._slice_label = QLabel("Индекс: 0 / 0")
        slice_layout.addWidget(self._slice_label)

        self._slice_slider = QSlider(Qt.Horizontal)
        self._slice_slider.setRange(0, 0)
        self._slice_slider.valueChanged.connect(self._on_slice_changed)
        slice_layout.addWidget(self._slice_slider, stretch=1)

        self._slice_row.setVisible(False)
        root.addWidget(self._slice_row)

        # Canvas
        self._canvas = NumpyCanvas()
        self._canvas.clicked.connect(self._on_canvas_clicked)
        root.addWidget(self._canvas, stretch=1)

        # ==================== НИЖНЯЯ ПАНЕЛЬ ====================

        bottom = QHBoxLayout()
        bottom.setContentsMargins(8, 4, 8, 8)

        self._stats_label = QLabel("—")
        self._stats_label.setStyleSheet(
            "font-family: Consolas; font-size: 9pt;"
        )
        bottom.addWidget(self._stats_label)

        bottom.addStretch()

        # Авто-диапазон
        self.check_auto_range = QCheckBox("Авто")
        self.check_auto_range.setChecked(True)
        self.check_auto_range.stateChanged.connect(self._on_auto_range_changed)
        bottom.addWidget(self.check_auto_range)

        bottom.addWidget(QLabel("Min:"))
        self.spin_min = QDoubleSpinBox()
        self.spin_min.setRange(-1e9, 1e9)
        self.spin_min.setDecimals(4)
        self.spin_min.setFixedWidth(100)
        self.spin_min.valueChanged.connect(self._on_range_changed)
        self.spin_min.setEnabled(False)
        bottom.addWidget(self.spin_min)

        bottom.addWidget(QLabel("Max:"))
        self.spin_max = QDoubleSpinBox()
        self.spin_max.setRange(-1e9, 1e9)
        self.spin_max.setDecimals(4)
        self.spin_max.setFixedWidth(100)
        self.spin_max.valueChanged.connect(self._on_range_changed)
        self.spin_max.setEnabled(False)
        bottom.addWidget(self.spin_max)

        root.addLayout(bottom)

    # ==================== API ====================

    def load(self, file_path: str) -> None:
        if not self._source.open(file_path):
            log("ERROR", f"Не удалось открыть numpy-файл: {file_path}")
            return

        self._slice_index = 0

        info = (
            f"{self._source.file_name}   "
            f"shape={self._source.shape}   "
            f"dtype={self._source.dtype}"
        )
        self._info_label.setText(info)

        log("INFO", f"NPY загружен: shape={self._source.shape}, dtype={self._source.dtype}")

        self._refresh_display()

    def cleanup(self) -> None:
        self._source.close()
        self._canvas.clear()

    # ==================== ОТОБРАЖЕНИЕ ====================

    def _refresh_display(self) -> None:
        arr = self._source.array
        if arr is None:
            return

        # === 1D массив ===
        if arr.ndim == 1:
            # Преобразуем в 2D — строка
            data2d = arr.reshape(1, -1)
            self._slice_row.setVisible(False)
            self._set_canvas_data(data2d)
            self._update_stats(arr)

        # === 2D массив ===
        elif arr.ndim == 2:
            self._slice_row.setVisible(False)
            self._set_canvas_data(arr)
            self._update_stats(arr)

        # === 3D массив ===
        elif arr.ndim == 3:
            depth = arr.shape[0]
            self._slice_index = min(self._slice_index, depth - 1)
            self._slice_row.setVisible(True)
            self._slice_slider.blockSignals(True)
            self._slice_slider.setRange(0, depth - 1)
            self._slice_slider.setValue(self._slice_index)
            self._slice_slider.blockSignals(False)
            self._slice_label.setText(f"Индекс: {self._slice_index} / {depth - 1}")

            data2d = arr[self._slice_index]
            self._set_canvas_data(data2d)
            self._update_stats(data2d)

        # === 4D+ ===
        else:
            # Упрощение: берём первый срез до 3D
            log("WARNING", f"Массив {arr.ndim}D — поддерживаем до 3D. Показан первый срез.")
            data = arr.reshape(-1, *arr.shape[-2:])
            data2d = data[0]
            self._slice_row.setVisible(False)
            self._set_canvas_data(data2d)
            self._update_stats(data2d)

    def _set_canvas_data(self, data2d: np.ndarray) -> None:
        """Передаём данные в canvas с текущими диапазонами."""
        if self.check_auto_range.isChecked():
            self._canvas.set_data(
                data2d,
                colormap=self.combo_colormap.currentText(),
            )
            vmin, vmax = self._canvas.get_range()
            self.spin_min.blockSignals(True)
            self.spin_max.blockSignals(True)
            self.spin_min.setValue(vmin)
            self.spin_max.setValue(vmax)
            self.spin_min.blockSignals(False)
            self.spin_max.blockSignals(False)
        else:
            vmin = self.spin_min.value()
            vmax = self.spin_max.value()
            self._canvas.set_data(
                data2d,
                colormap=self.combo_colormap.currentText(),
                value_min=vmin,
                value_max=vmax,
            )

    def _update_stats(self, data: np.ndarray) -> None:
        if data.size == 0:
            self._stats_label.setText("—")
            return
        d = data.astype(np.float64)
        self._stats_label.setText(
            f"min={d.min():.4f}  max={d.max():.4f}  "
            f"mean={d.mean():.4f}  std={d.std():.4f}  size={data.size}"
        )

    # ==================== СОБЫТИЯ ====================

    def _on_colormap_changed(self, name: str) -> None:
        self._canvas.set_colormap(name)

    def _on_slice_changed(self, value: int) -> None:
        self._slice_index = value
        arr = self._source.array
        if arr is None or arr.ndim < 3:
            return
        depth = arr.shape[0]
        self._slice_label.setText(f"Индекс: {value} / {depth - 1}")
        data2d = arr[value]
        self._set_canvas_data(data2d)
        self._update_stats(data2d)

    def _on_auto_range_changed(self, state: int) -> None:
        auto = state == Qt.Checked.value
        self.spin_min.setEnabled(not auto)
        self.spin_max.setEnabled(not auto)
        self._refresh_display()

    def _on_range_changed(self, _value: float) -> None:
        if self.check_auto_range.isChecked():
            return
        vmin = self.spin_min.value()
        vmax = self.spin_max.value()
        self._canvas.set_range(vmin, vmax)

    def _on_canvas_clicked(self, x: int, y: int, value: float) -> None:
        self._stats_label.setText(
            f"({x}, {y}) = {value:.6f}   "
            f"|  {self._stats_label.text().split('|')[0].strip()}"
        )