"""Окно FFT-спектра сигнала пикселя / ROI."""
import numpy as np
import cv2
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QApplication,
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
from utils.color_conversions import convert_rgb, get_channel_names


# Цвет кривых по пространствам
_CURVE_COLORS = {
    "RGB": [HISTOGRAM_COLOR_R, HISTOGRAM_COLOR_G, HISTOGRAM_COLOR_B],
    "YIQ": [HISTOGRAM_COLOR_Y, "#ff55ff", "#55ffff"],
    "HSV": ["#ff55ff", "#ffaa55", HISTOGRAM_COLOR_Y],
    "LAB": [HISTOGRAM_COLOR_Y, HISTOGRAM_COLOR_R, HISTOGRAM_COLOR_B],
    "YUV": [HISTOGRAM_COLOR_Y, "#5555ff", "#ff5555"],
}


class SignalWindow(QMainWindow):
    """Отдельное окно: FFT-спектр сигнала + выделение диапазона."""

    MAX_PEAKS = 5

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("FFT сигнала")
        self.resize(900, 600)

        pg.setConfigOptions(antialias=True)

        self._rgb_data: np.ndarray | None = None
        self._fps: float = 0.0
        self._video_name: str = ""
        self._video_path: str = ""
        self._video_size: tuple[int, int] = (0, 0)
        self._first_frame: np.ndarray | None = None
        self._roi: tuple[int, int, int, int] | None = None

        self._curves: list[pg.PlotDataItem] = []
        self._legend = None
        self._current_peaks: list[float] = []
        self._current_freqs: np.ndarray | None = None
        self._current_spectrum: np.ndarray | None = None

        self._power_map_window = None

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ==================== ВЕРХНЯЯ ПАНЕЛЬ ====================

        top_panel = QHBoxLayout()
        top_panel.setSpacing(8)

        top_panel.addWidget(QLabel("Пространство:"))
        self.combo_space = QComboBox()
        self.combo_space.setFixedWidth(80)
        self.combo_space.addItems(["RGB", "YIQ", "HSV", "LAB", "YUV"])
        self.combo_space.currentTextChanged.connect(self._on_space_changed)
        top_panel.addWidget(self.combo_space)

        top_panel.addSpacing(16)

        self.btn_power_map = QPushButton("Карта на частоте")
        self.btn_power_map.setStyleSheet(MEDIA_BUTTON_STYLE)
        self.btn_power_map.setToolTip(
            "Показать, где в выделенной области сигнал на этой частоте максимален"
        )
        self.btn_power_map.clicked.connect(self._show_power_map)
        top_panel.addWidget(self.btn_power_map)

        top_panel.addStretch()
        layout.addLayout(top_panel)

        # ==================== ИНФО ====================

        self._info_label = QLabel("(нет данных)")
        self._info_label.setStyleSheet(
            "padding: 4px; font-family: Consolas; font-size: 9pt;"
        )
        layout.addWidget(self._info_label)

        # ==================== FFT ГРАФИК ====================

        self._fft_plot = pg.PlotWidget()
        self._fft_plot.setBackground(HISTOGRAM_BG)
        self._fft_plot.showGrid(x=True, y=True, alpha=0.2)
        self._fft_plot.setLabel("bottom", "Частота (Гц)")
        self._fft_plot.setLabel("left", "Амплитуда")

        # Отключаем стандартное меню pyqtgraph
        self._fft_plot.setMenuEnabled(False)
        self._fft_plot.setContextMenuPolicy(Qt.CustomContextMenu)
        self._fft_plot.customContextMenuRequested.connect(self._on_plot_context_menu)

        self._legend = self._fft_plot.addLegend()
        self._peak_labels: list[pg.TextItem] = []

        # Регион выделения
        self._region = pg.LinearRegionItem(
            values=(0.0, 1.0),
            brush=pg.mkBrush(79, 193, 255, 40),
            pen=pg.mkPen("#4fc1ff", width=1),
            movable=True,
        )
        self._region.setZValue(-10)
        self._region.sigRegionChanged.connect(self._on_region_changed)
        self._fft_plot.addItem(self._region)

        layout.addWidget(self._fft_plot, stretch=1)

        # ==================== СТРОКА ДИАПАЗОНА ====================

        range_row = QHBoxLayout()
        range_row.setSpacing(8)

        self._range_label = QLabel("Диапазон: —")
        self._range_label.setStyleSheet(
            "padding: 4px; font-family: Consolas; font-size: 10pt; font-weight: bold;"
        )
        range_row.addWidget(self._range_label)

        range_row.addStretch()

        self._btn_copy_range = QPushButton("Скопировать диапазон")
        self._btn_copy_range.setStyleSheet(MEDIA_BUTTON_STYLE)
        self._btn_copy_range.setToolTip("Скопировать в буфер: fmin,fmax")
        self._btn_copy_range.clicked.connect(self._copy_range)
        range_row.addWidget(self._btn_copy_range)

        layout.addLayout(range_row)

        # ==================== КНОПКИ ====================

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._btn_clear = QPushButton("Очистить")
        self._btn_clear.setStyleSheet(MEDIA_BUTTON_STYLE)
        self._btn_clear.clicked.connect(self.clear)
        btn_layout.addWidget(self._btn_clear)

        layout.addLayout(btn_layout)

        self.setCentralWidget(container)

        self._rebuild_curves("RGB")

    # ==================== API ====================

    def set_signal(
        self,
        rgb_data: np.ndarray,
        fps: float,
        pixel_xy: tuple[int, int],
        video_name: str,
        video_path: str = "",
        video_size: tuple[int, int] = (0, 0),
        first_frame: np.ndarray | None = None,
        roi: tuple[int, int, int, int] | None = None,
    ) -> None:
        if rgb_data is None or len(rgb_data) < 2:
            return

        self._rgb_data = rgb_data.copy()
        self._fps = fps
        self._video_name = video_name
        self._video_path = video_path
        self._video_size = video_size
        self._first_frame = first_frame
        self._roi = roi

        self._refresh()

    def clear(self) -> None:
        self._rgb_data = None
        for c in self._curves:
            c.setData([], [])
        self._clear_peaks()
        self._info_label.setText("(нет данных)")
        self._range_label.setText("Диапазон: —")
        self._current_peaks = []
        self._current_freqs = None
        self._current_spectrum = None

    # ==================== ПЕРЕСЧЁТ ====================

    def _on_space_changed(self, space: str) -> None:
        self._rebuild_curves(space)
        self._refresh()

    def _rebuild_curves(self, space: str) -> None:
        for c in self._curves:
            self._fft_plot.removeItem(c)
        self._curves.clear()

        if self._legend is not None:
            self._fft_plot.removeItem(self._legend)
        self._legend = self._fft_plot.addLegend()

        names = get_channel_names(space)
        colors = _CURVE_COLORS.get(space, _CURVE_COLORS["RGB"])

        for i, name in enumerate(names):
            color = colors[i] if i < len(colors) else "#ffffff"
            curve = self._fft_plot.plot(pen=pg.mkPen(color, width=1.2), name=name)
            self._curves.append(curve)

    def _refresh(self) -> None:
        if self._rgb_data is None or len(self._rgb_data) < 2:
            return

        space = self.combo_space.currentText()
        arr = convert_rgb(self._rgb_data, space)
        if arr is None:
            self.clear()
            return

        channels = [arr[:, 0], arr[:, 1], arr[:, 2]]
        labels = get_channel_names(space)

        n = len(self._rgb_data)
        fps = self._fps

        window = np.hanning(n)
        freqs = np.fft.rfftfreq(n, d=1.0 / fps)

        spectra = []
        for ch in channels:
            ch = ch.astype(float)
            ch_dc = ch - ch.mean()
            ch_w = ch_dc * window
            spectrum = np.abs(np.fft.rfft(ch_w))
            spectra.append(spectrum)

        if len(freqs) > 1:
            freqs = freqs[1:]
            spectra = [s[1:] for s in spectra]

        for i, curve in enumerate(self._curves):
            if i < len(spectra):
                curve.setData(freqs, spectra[i])
            else:
                curve.setData([], [])

        self._fft_plot.setTitle(f"FFT-спектр ({space})")
        self._fft_plot.autoRange()

        # Запоминаем для ПКМ
        self._current_freqs = freqs
        self._current_spectrum = spectra[0] if spectra else None

        # Пики
        self._clear_peaks()
        peaks = self._find_peaks(freqs, spectra[0], self.MAX_PEAKS) if spectra else []
        self._current_peaks = [p[0] for p in peaks]

        for freq, amp in peaks:
            label = pg.TextItem(
                text=f"{freq:.2f} Hz",
                color=HISTOGRAM_COLOR_Y,
                anchor=(0, 1),
            )
            label.setPos(freq, amp)
            self._fft_plot.addItem(label)
            self._peak_labels.append(label)

        # Автоматическое выделение вокруг первого пика
        if self._current_peaks:
            self._set_region_around_peak(self._current_peaks[0])

        # Инфо
        duration = n / fps
        info = (
            f"Видео: {self._video_name}   Пространство: {space}   "
            f"Кадров: {n}   FPS: {fps:.2f}   Длительность: {duration:.2f} сек"
        )
        if peaks and labels:
            info += f"   |   Пик {labels[0]}: {peaks[0][0]:.2f} Гц"
        self._info_label.setText(info)

    # ==================== ПИКИ ====================

    def _clear_peaks(self) -> None:
        for label in self._peak_labels:
            self._fft_plot.removeItem(label)
        self._peak_labels.clear()

    def _find_peaks(self, freqs, spectrum, max_peaks):
        if len(spectrum) < 3:
            return []
        peaks = []
        for i in range(1, len(spectrum) - 1):
            if (spectrum[i] > spectrum[i - 1] and
                    spectrum[i] > spectrum[i + 1] and
                    spectrum[i] > spectrum.mean() * 2):
                peaks.append((float(freqs[i]), float(spectrum[i])))
        peaks.sort(key=lambda x: -x[1])
        return peaks[:max_peaks]

    # ==================== РЕГИОН ====================

    def _set_region_around_peak(self, peak_freq: float) -> None:
        """Автоматически ставит регион вокруг пика ±20%."""
        width = peak_freq * 0.2
        if width < 0.05:
            width = 0.05

        fmin = max(0.0, peak_freq - width)
        fmax = peak_freq + width

        self._region.blockSignals(True)
        self._region.setRegion((fmin, fmax))
        self._region.blockSignals(False)

        self._update_range_label(fmin, fmax)

    def _on_region_changed(self) -> None:
        fmin, fmax = self._region.getRegion()
        self._update_range_label(fmin, fmax)

    def _update_range_label(self, fmin: float, fmax: float) -> None:
        width = fmax - fmin
        self._range_label.setText(
            f"Диапазон: {fmin:.3f} – {fmax:.3f} Гц   (ширина {width:.3f})"
        )

    def _copy_range(self) -> None:
        """Копирует диапазон в буфер как 'fmin,fmax'."""
        fmin, fmax = self._region.getRegion()
        text = f"{fmin:.3f},{fmax:.3f}"
        QApplication.clipboard().setText(text)
        self._info_label.setText(f"Скопировано: {text}")

    # ==================== ПКМ-МЕНЮ ====================

    def _on_plot_context_menu(self, pos) -> None:
        """Своё контекстное меню на графике."""
        # Позиция в координатах графика
        view_box = self._fft_plot.getPlotItem().getViewBox()
        scene_pos = self._fft_plot.mapToScene(pos)
        view_pos = view_box.mapSceneToView(scene_pos)
        freq_under_cursor = float(view_pos.x())

        menu = pg.QtWidgets.QMenu(self)

        act_copy_freq = menu.addAction(
            f"Скопировать частоту: {freq_under_cursor:.3f} Гц"
        )
        act_copy_freq.triggered.connect(
            lambda: self._copy_value(f"{freq_under_cursor:.3f}")
        )

        menu.addSeparator()

        fmin, fmax = self._region.getRegion()

        act_copy_fmin = menu.addAction(f"Скопировать fmin: {fmin:.3f}")
        act_copy_fmin.triggered.connect(lambda: self._copy_value(f"{fmin:.3f}"))

        act_copy_fmax = menu.addAction(f"Скопировать fmax: {fmax:.3f}")
        act_copy_fmax.triggered.connect(lambda: self._copy_value(f"{fmax:.3f}"))

        act_copy_range = menu.addAction(
            f"Скопировать диапазон: {fmin:.3f},{fmax:.3f}"
        )
        act_copy_range.triggered.connect(self._copy_range)

        menu.exec(self._fft_plot.mapToGlobal(pos))

    def _copy_value(self, text: str) -> None:
        QApplication.clipboard().setText(text)
        self._info_label.setText(f"Скопировано: {text}")

    # ==================== КАРТА МОЩНОСТИ ====================

    def _show_power_map(self) -> None:
        if not self._video_path:
            self._info_label.setText("Нет пути к видео — карта недоступна")
            return

        from desktop.viewers.video.power_map import PowerMapWindow

        if self._power_map_window is None:
            self._power_map_window = PowerMapWindow(parent=self.window())

        self._power_map_window.set_source(
            video_path=self._video_path,
            fps=self._fps,
            video_size=self._video_size,
            first_frame=self._first_frame,
            peak_freqs=self._current_peaks,
            roi=self._roi,
        )
        self._power_map_window.show()
        self._power_map_window.raise_()
        self._power_map_window.activateWindow()