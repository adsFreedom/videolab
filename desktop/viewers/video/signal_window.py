"""Окно FFT-спектра сигнала пикселя / ROI."""
import numpy as np
import cv2
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox,
)
from PySide6.QtCore import Qt

from utils.color_conversions import rgb_to_yiq, convert_rgb, get_channel_names
from desktop.viewers.styles import (
    HISTOGRAM_BG,
    HISTOGRAM_COLOR_R,
    HISTOGRAM_COLOR_G,
    HISTOGRAM_COLOR_B,
    HISTOGRAM_COLOR_Y,
    MEDIA_BUTTON_STYLE,
)


class SignalWindow(QMainWindow):
    """Отдельное окно: FFT-спектр сигнала."""

    MAX_PEAKS = 5

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("FFT сигнала")
        self.resize(900, 500)

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
        # YIQ добавлен первым — это ключевое пространство для амплификации
        self.combo_space.addItems(["YIQ", "RGB", "HSV", "LAB", "YUV"])
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

        self._legend = self._fft_plot.addLegend()
        self._peak_labels: list[pg.TextItem] = []

        layout.addWidget(self._fft_plot, stretch=1)

        # ==================== КНОПКИ ====================

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._btn_clear = QPushButton("Очистить")
        self._btn_clear.setStyleSheet(MEDIA_BUTTON_STYLE)
        self._btn_clear.clicked.connect(self.clear)
        btn_layout.addWidget(self._btn_clear)

        layout.addLayout(btn_layout)

        self.setCentralWidget(container)

        # Инициализация кривых — YIQ по умолчанию
        self._rebuild_curves("YIQ")

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
        self._current_peaks = []

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

        configs = {
            "YIQ": [
                ("Y", HISTOGRAM_COLOR_Y),
                ("I", "#ff55ff"),
                ("Q", "#55ffff"),
            ],
            "RGB": [
                ("R", HISTOGRAM_COLOR_R),
                ("G", HISTOGRAM_COLOR_G),
                ("B", HISTOGRAM_COLOR_B),
            ],
            "HSV": [
                ("H", "#ff55ff"),
                ("S", "#ffaa55"),
                ("V", HISTOGRAM_COLOR_Y),
            ],
            "LAB": [
                ("L", HISTOGRAM_COLOR_Y),
                ("a", HISTOGRAM_COLOR_R),
                ("b", HISTOGRAM_COLOR_B),
            ],
            "YUV": [
                ("Y", HISTOGRAM_COLOR_Y),
                ("U", "#5555ff"),
                ("V", "#ff5555"),
            ],
        }
        config = configs.get(space, configs["YIQ"])

        for label, color in config:
            curve = self._fft_plot.plot(pen=pg.mkPen(color, width=1.2), name=label)
            self._curves.append(curve)

    def _refresh(self) -> None:
        if self._rgb_data is None or len(self._rgb_data) < 2:
            return

        space = self.combo_space.currentText()
        channels, labels = self._get_channels(self._rgb_data, space)
        if channels is None or len(channels) == 0:
            self.clear()
            return

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

        duration = n / fps
        info = (
            f"Видео: {self._video_name}   Пространство: {space}   "
            f"Кадров: {n}   FPS: {fps:.2f}   Длительность: {duration:.2f} сек"
        )
        if peaks and labels:
            info += f"   |   Пик {labels[0]}: {peaks[0][0]:.2f} Гц"
        self._info_label.setText(info)

    # ==================== КОНВЕРТАЦИЯ ====================

    def _get_channels(self, rgb_data: np.ndarray, space: str):
        """Возвращает (channels, labels) для пространства."""
        arr = convert_rgb(rgb_data, space)
        if arr is None:
            return None, []

        # Для одиночных каналов — разбить на 3 канала
        return [arr[:, 0], arr[:, 1], arr[:, 2]], get_channel_names(space)

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