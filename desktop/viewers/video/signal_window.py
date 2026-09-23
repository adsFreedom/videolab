"""Окно FFT-спектра сигнала пикселя / ROI."""
import numpy as np
import cv2
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox,
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

        # Кривые текущего пространства (пересоздаются при смене)
        self._curves: list[pg.PlotDataItem] = []
        self._legend = None

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
        self.combo_space.addItems(["RGB", "HSV", "LAB", "YUV"])
        self.combo_space.currentTextChanged.connect(self._on_space_changed)
        top_panel.addWidget(self.combo_space)

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

        # Легенда (создаём заново при смене пространства)
        self._legend = self._fft_plot.addLegend()

        # Пики
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

        # Инициализируем кривые для RGB по умолчанию
        self._rebuild_curves("RGB")

    # ==================== API ====================

    def set_signal(
        self,
        rgb_data: np.ndarray,
        fps: float,
        pixel_xy: tuple[int, int],
        video_name: str,
    ) -> None:
        """Сохраняем исходные данные RGB."""
        if rgb_data is None or len(rgb_data) < 2:
            return

        self._rgb_data = rgb_data.copy()
        self._fps = fps
        self._video_name = video_name

        self._refresh()

    def clear(self) -> None:
        self._rgb_data = None
        for c in self._curves:
            c.setData([], [])
        self._clear_peaks()
        self._info_label.setText("(нет данных)")

    # ==================== ПЕРЕСЧЁТ ====================

    def _on_space_changed(self, space: str) -> None:
        self._rebuild_curves(space)
        self._refresh()

    def _rebuild_curves(self, space: str) -> None:
        """Пересоздаёт кривые и легенду для нового пространства."""
        # Удаляем старые кривые
        for c in self._curves:
            self._fft_plot.removeItem(c)
        self._curves.clear()

        # Удаляем старую легенду и создаём новую
        if self._legend is not None:
            self._fft_plot.removeItem(self._legend)
        self._legend = self._fft_plot.addLegend()

        # Метки и цвета по пространствам
        configs = {
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
        config = configs.get(space, configs["RGB"])

        # Создаём 3 кривые
        for label, color in config:
            curve = self._fft_plot.plot(
                pen=pg.mkPen(color, width=1.2), name=label,
            )
            self._curves.append(curve)

    def _refresh(self) -> None:
        if self._rgb_data is None or len(self._rgb_data) < 2:
            return

        space = self.combo_space.currentText()

        # 1. Получаем каналы
        channels, labels = self._get_channels(self._rgb_data, space)
        if channels is None or len(channels) == 0:
            self.clear()
            return

        n = len(self._rgb_data)
        fps = self._fps

        # 2. FFT для каждого канала
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

        # 3. Обновляем кривые
        for i, curve in enumerate(self._curves):
            if i < len(spectra):
                curve.setData(freqs, spectra[i])
            else:
                curve.setData([], [])

        self._fft_plot.setTitle(f"FFT-спектр ({space})")
        self._fft_plot.autoRange()

        # 4. Пики по первому каналу
        self._clear_peaks()
        peaks = self._find_peaks(freqs, spectra[0], self.MAX_PEAKS) if spectra else []
        for freq, amp in peaks:
            label = pg.TextItem(
                text=f"{freq:.2f} Hz",
                color=HISTOGRAM_COLOR_Y,
                anchor=(0, 1),
            )
            label.setPos(freq, amp)
            self._fft_plot.addItem(label)
            self._peak_labels.append(label)

        # 5. Инфо
        duration = n / fps
        info = (
            f"Видео: {self._video_name}   Пространство: {space}   "
            f"Кадров: {n}   FPS: {fps:.2f}   Длительность: {duration:.2f} сек"
        )
        if peaks and labels:
            info += f"   |   Пик {labels[0]}: {peaks[0][0]:.2f} Гц"
        self._info_label.setText(info)

    # ==================== КОНВЕРТАЦИЯ ====================

    def _get_channels(
        self, rgb_data: np.ndarray, space: str,
    ) -> tuple[list[np.ndarray] | None, list[str]]:
        """Возвращает (список каналов, список меток)."""
        if space == "RGB":
            channels = [
                rgb_data[:, 0],
                rgb_data[:, 1],
                rgb_data[:, 2],
            ]
            return channels, ["R", "G", "B"]

        # cv2: RGB → другое пространство
        arr = rgb_data.reshape((-1, 1, 3)).astype(np.uint8)

        if space == "HSV":
            converted = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
            labels = ["H", "S", "V"]
        elif space == "LAB":
            converted = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
            labels = ["L", "a", "b"]
        elif space == "YUV":
            converted = cv2.cvtColor(arr, cv2.COLOR_RGB2YUV)
            labels = ["Y", "U", "V"]
        else:
            return None, []

        converted = converted.reshape((-1, 3))
        channels = [
            converted[:, 0],
            converted[:, 1],
            converted[:, 2],
        ]
        return channels, labels

    # ==================== ПИКИ ====================

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