"""Окно осциллограммы пикселя + FFT."""
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


class SignalWindow(QMainWindow):
    """Отдельное окно: осциллограмма + FFT."""

    MAX_PEAKS = 5

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Сигнал пикселя")
        self.resize(900, 700)

        pg.setConfigOptions(antialias=True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Заголовок
        self._info_label = QLabel("(нет данных)")
        self._info_label.setStyleSheet(
            "padding: 4px; font-family: Consolas; font-size: 9pt;"
        )
        layout.addWidget(self._info_label)

        # ==================== ОСЦИЛЛОГРАММА ====================

        self._time_plot = pg.PlotWidget()
        self._time_plot.setBackground(HISTOGRAM_BG)
        self._time_plot.showGrid(x=True, y=True, alpha=0.2)
        self._time_plot.setLabel("bottom", "Время (сек)")
        self._time_plot.setLabel("left", "Значение (0–255)")
        self._time_plot.addLegend()

        self._curve_r = self._time_plot.plot(
            pen=pg.mkPen(HISTOGRAM_COLOR_R, width=1.2), name="R",
        )
        self._curve_g = self._time_plot.plot(
            pen=pg.mkPen(HISTOGRAM_COLOR_G, width=1.2), name="G",
        )
        self._curve_b = self._time_plot.plot(
            pen=pg.mkPen(HISTOGRAM_COLOR_B, width=1.2), name="B",
        )

        layout.addWidget(self._time_plot, stretch=1)

        # ==================== FFT ====================

        self._fft_plot = pg.PlotWidget()
        self._fft_plot.setBackground(HISTOGRAM_BG)
        self._fft_plot.showGrid(x=True, y=True, alpha=0.2)
        self._fft_plot.setLabel("bottom", "Частота (Гц)")
        self._fft_plot.setLabel("left", "Амплитуда")
        self._fft_plot.addLegend()

        self._fft_r = self._fft_plot.plot(
            pen=pg.mkPen(HISTOGRAM_COLOR_R, width=1.2), name="R",
        )
        self._fft_g = self._fft_plot.plot(
            pen=pg.mkPen(HISTOGRAM_COLOR_G, width=1.2), name="G",
        )
        self._fft_b = self._fft_plot.plot(
            pen=pg.mkPen(HISTOGRAM_COLOR_B, width=1.2), name="B",
        )

        # Пики FFT (текстовые метки) для R канала
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

    # ==================== API ====================

    def set_signal(
        self,
        rgb_data: np.ndarray,   # shape (N, 3)
        fps: float,
        pixel_xy: tuple[int, int],
        video_name: str,
    ) -> None:
        """Обновляет графики."""
        if rgb_data is None or len(rgb_data) < 2:
            return

        n = len(rgb_data)
        r = rgb_data[:, 0].astype(float)
        g = rgb_data[:, 1].astype(float)
        b = rgb_data[:, 2].astype(float)

        # ==================== ВРЕМЕННОЙ РЯД ====================

        t = np.arange(n) / fps

        self._curve_r.setData(t, r)
        self._curve_g.setData(t, g)
        self._curve_b.setData(t, b)

        self._time_plot.setTitle(f"Временной ряд")
        self._time_plot.autoRange()

        # ==================== FFT ====================

        # Убираем DC (среднее)
        r_dc = r - r.mean()
        g_dc = g - g.mean()
        b_dc = b - b.mean()

        # Применяем окно Hann
        window = np.hanning(n)
        r_w = r_dc * window
        g_w = g_dc * window
        b_w = b_dc * window

        # FFT
        freqs = np.fft.rfftfreq(n, d=1.0 / fps)
        fft_r = np.abs(np.fft.rfft(r_w))
        fft_g = np.abs(np.fft.rfft(g_w))
        fft_b = np.abs(np.fft.rfft(b_w))

        # Убираем нулевую частоту (DC) из отображения
        if len(freqs) > 1:
            freqs = freqs[1:]
            fft_r = fft_r[1:]
            fft_g = fft_g[1:]
            fft_b = fft_b[1:]

        self._fft_r.setData(freqs, fft_r)
        self._fft_g.setData(freqs, fft_g)
        self._fft_b.setData(freqs, fft_b)

        self._fft_plot.setTitle("FFT-спектр")
        self._fft_plot.autoRange()

        # ==================== ПИКИ ====================

        self._clear_peaks()
        peaks = self._find_peaks(freqs, fft_r, self.MAX_PEAKS)
        for i, (freq, amp) in enumerate(peaks):
            label = pg.TextItem(
                text=f"{freq:.2f} Hz",
                color=HISTOGRAM_COLOR_Y,
                anchor=(0, 1),
            )
            label.setPos(freq, amp)
            self._fft_plot.addItem(label)
            self._peak_labels.append(label)

        # ==================== ИНФО ====================

        duration = n / fps
        info = (
            f"Видео: {video_name}   Пиксель: ({pixel_xy[0]}, {pixel_xy[1]})   "
            f"Кадров: {n}   FPS: {fps:.2f}   Длительность: {duration:.2f} сек"
        )
        if peaks:
            top = peaks[0]
            info += f"   |   Пик R: {top[0]:.2f} Гц"
        self._info_label.setText(info)

    def clear(self) -> None:
        self._curve_r.setData([], [])
        self._curve_g.setData([], [])
        self._curve_b.setData([], [])
        self._fft_r.setData([], [])
        self._fft_g.setData([], [])
        self._fft_b.setData([], [])
        self._clear_peaks()
        self._info_label.setText("(нет данных)")

    # ==================== ВНУТРЕННИЕ ====================

    def _clear_peaks(self) -> None:
        for label in self._peak_labels:
            self._fft_plot.removeItem(label)
        self._peak_labels.clear()

    def _find_peaks(
        self,
        freqs: np.ndarray,
        spectrum: np.ndarray,
        max_peaks: int,
    ) -> list[tuple[float, float]]:
        """
        Простой поиск локальных максимумов.
        Возвращает список (частота, амплитуда), отсортированный по амплитуде.
        """
        if len(spectrum) < 3:
            return []

        peaks = []
        for i in range(1, len(spectrum) - 1):
            if (spectrum[i] > spectrum[i - 1] and
                    spectrum[i] > spectrum[i + 1] and
                    spectrum[i] > spectrum.mean() * 2):  # порог — 2 средних
                peaks.append((float(freqs[i]), float(spectrum[i])))

        # Сортируем по амплитуде
        peaks.sort(key=lambda x: -x[1])
        return peaks[:max_peaks]