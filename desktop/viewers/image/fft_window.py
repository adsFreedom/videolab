"""Окно FFT-анализа изображения."""
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont

from desktop.viewers.styles import (
    HISTOGRAM_BG,
    HISTOGRAM_GRID,
    HISTOGRAM_AXIS,
    HISTOGRAM_COLOR_R,
    HISTOGRAM_COLOR_G,
    HISTOGRAM_COLOR_B,
    HISTOGRAM_COLOR_Y,
    MEDIA_BUTTON_STYLE,
)


class SpectrumCanvas(QWidget):
    """Виджет отрисовки 2D-спектра (magnitude или phase)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._pixmap: QPixmap | None = None
        self._info_text: str = ""

        self.setMinimumSize(320, 320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(f"background-color: {HISTOGRAM_BG};")

    def set_pixmap(self, pixmap: QPixmap | None, info: str = "") -> None:
        self._pixmap = pixmap
        self._info_text = info
        self.update()

    def clear(self) -> None:
        self._pixmap = None
        self._info_text = ""
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(HISTOGRAM_BG))

        if self._pixmap is None:
            painter.setPen(QPen(QColor(HISTOGRAM_AXIS)))
            font = QFont()
            font.setItalic(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            painter.end()
            return

        # Масштабируем с сохранением пропорций
        scaled = self._pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

        # Подпись внизу
        if self._info_text:
            painter.setPen(QPen(QColor(HISTOGRAM_AXIS)))
            font = QFont()
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(
                4, self.height() - 6,
                self.width() - 8, 16,
                Qt.AlignLeft | Qt.AlignVCenter,
                self._info_text,
            )

        painter.end()


class FFTWindow(QMainWindow):
    """Отдельное окно с FFT-анализом изображения."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("FFT")
        self.resize(1000, 520)

        self._array_rgb: np.ndarray | None = None

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ==================== ВЕРХНЯЯ ПАНЕЛЬ ====================

        top_panel = QHBoxLayout()
        top_panel.setSpacing(8)

        # Каналы
        top_panel.addWidget(QLabel("Каналы:"))
        self.cb_r = QCheckBox("R")
        self.cb_r.setChecked(True)
        self.cb_r.stateChanged.connect(self._refresh)
        top_panel.addWidget(self.cb_r)

        self.cb_g = QCheckBox("G")
        self.cb_g.setChecked(True)
        self.cb_g.stateChanged.connect(self._refresh)
        top_panel.addWidget(self.cb_g)

        self.cb_b = QCheckBox("B")
        self.cb_b.setChecked(True)
        self.cb_b.stateChanged.connect(self._refresh)
        top_panel.addWidget(self.cb_b)

        self.cb_gray = QCheckBox("Gray")
        self.cb_gray.stateChanged.connect(self._refresh)
        top_panel.addWidget(self.cb_gray)

        top_panel.addSpacing(16)

        # Опции
        self.cb_log = QCheckBox("Log")
        self.cb_log.setChecked(True)
        self.cb_log.stateChanged.connect(self._refresh)
        top_panel.addWidget(self.cb_log)

        self.cb_hann = QCheckBox("Hann")
        self.cb_hann.setChecked(True)
        self.cb_hann.stateChanged.connect(self._refresh)
        top_panel.addWidget(self.cb_hann)

        self.cb_phase = QCheckBox("Фаза")
        self.cb_phase.stateChanged.connect(self._refresh)
        top_panel.addWidget(self.cb_phase)

        top_panel.addStretch()
        layout.addLayout(top_panel)

        # ==================== ОСНОВНАЯ ЧАСТЬ ====================

        main_layout = QHBoxLayout()
        main_layout.setSpacing(8)

        # 2D-спектр
        self._spectrum_canvas = SpectrumCanvas()
        main_layout.addWidget(self._spectrum_canvas, stretch=1)

        # Радиальный профиль (pyqtgraph)
        pg.setConfigOptions(antialias=True)
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground(HISTOGRAM_BG)
        self._plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self._plot_widget.setLabel("bottom", "Частота (цикл/пиксель)")
        self._plot_widget.setLabel("left", "Амплитуда")
        self._plot_widget.addLegend()

        self._curve_r = self._plot_widget.plot(
            pen=pg.mkPen(HISTOGRAM_COLOR_R, width=1.5), name="R",
        )
        self._curve_g = self._plot_widget.plot(
            pen=pg.mkPen(HISTOGRAM_COLOR_G, width=1.5), name="G",
        )
        self._curve_b = self._plot_widget.plot(
            pen=pg.mkPen(HISTOGRAM_COLOR_B, width=1.5), name="B",
        )
        self._curve_gray = self._plot_widget.plot(
            pen=pg.mkPen(HISTOGRAM_COLOR_Y, width=1.5, style=Qt.DashLine), name="Gray",
        )

        main_layout.addWidget(self._plot_widget, stretch=1)

        layout.addLayout(main_layout, stretch=1)

        self.setCentralWidget(container)

    # ==================== API ====================

    def set_image_array(self, arr: np.ndarray) -> None:
        """
        arr: RGB или grayscale numpy.
        RGB — ожидаем shape (h, w, 3).
        Grayscale — (h, w).
        """
        if arr is None:
            return

        # Нормализуем: всегда держим RGB (3 канала)
        if arr.ndim == 2:
            self._array_rgb = np.stack([arr, arr, arr], axis=-1)
        elif arr.ndim == 3 and arr.shape[2] >= 3:
            self._array_rgb = arr[:, :, :3]
        else:
            self._array_rgb = np.stack([arr, arr, arr], axis=-1)

        if self._array_rgb.dtype != np.uint8:
            self._array_rgb = self._array_rgb.astype(np.uint8)

        self._refresh()

    def clear(self) -> None:
        self._array_rgb = None
        self._spectrum_canvas.clear()
        self._curve_r.setData([], [])
        self._curve_g.setData([], [])
        self._curve_b.setData([], [])
        self._curve_gray.setData([], [])

    # ==================== РАСЧЁТ ====================

    def _refresh(self) -> None:
        if self._array_rgb is None:
            return

        arr = self._array_rgb
        h, w = arr.shape[:2]

        # Какие каналы выбраны
        use_r = self.cb_r.isChecked()
        use_g = self.cb_g.isChecked()
        use_b = self.cb_b.isChecked()
        use_gray = self.cb_gray.isChecked()

        if not (use_r or use_g or use_b or use_gray):
            self._spectrum_canvas.clear()
            return

        # Окно Hann
        if self.cb_hann.isChecked():
            wy = np.hanning(h).astype(np.float32)
            wx = np.hanning(w).astype(np.float32)
            window = np.outer(wy, wx)
        else:
            window = None

        log_scale = self.cb_log.isChecked()
        show_phase = self.cb_phase.isChecked()

        # Контейнеры для нормализованных спектров (для 2D)
        spectra_norm = {}
        radial_data = {}
        max_radial = None

        # Список каналов для расчёта
        channels = []
        if use_r:
            channels.append(("R", arr[:, :, 0], HISTOGRAM_COLOR_R))
        if use_g:
            channels.append(("G", arr[:, :, 1], HISTOGRAM_COLOR_G))
        if use_b:
            channels.append(("B", arr[:, :, 2], HISTOGRAM_COLOR_B))
        if use_gray:
            gray = (0.299 * arr[:, :, 0].astype(np.float32) +
                    0.587 * arr[:, :, 1].astype(np.float32) +
                    0.114 * arr[:, :, 2].astype(np.float32)).astype(np.uint8)
            channels.append(("Gray", gray, HISTOGRAM_COLOR_Y))

        # Расчёт для каждого канала
        for name, ch_arr, _color in channels:
            ch = ch_arr.astype(np.float32)
            if window is not None:
                ch = ch * window

            f = np.fft.fft2(ch)
            fshift = np.fft.fftshift(f)

            if show_phase:
                # Фазовый спектр: нормализуем в 0..1
                phase = np.angle(fshift)
                # phase: -pi..pi → 0..1
                data = (phase + np.pi) / (2 * np.pi)
                # Для отображения используем magnitude для нормировки?
                # Просто показываем фазу как grayscale.
                # Но чтобы не был шумом — маскируем по magnitude.
                mag = np.abs(fshift)
                if mag.max() > 0:
                    mask = mag < (mag.max() * 0.01)
                    data[mask] = 0.5  # серая середина
                spectra_norm[name] = data
            else:
                magnitude = np.abs(fshift)
                if log_scale:
                    magnitude = np.log1p(magnitude)
                spectra_norm[name] = magnitude

            # Радиальный профиль (всегда по magnitude)
            if not show_phase:
                magnitude_for_radial = np.abs(fshift)
            else:
                magnitude_for_radial = np.abs(fshift)  # даже для фазы — magnitude

            radial = self._compute_radial_profile(magnitude_for_radial)
            radial_data[name] = radial
            if max_radial is None:
                max_radial = len(radial)

        # === Отрисовка 2D-спектра ===
        if not show_phase:
            self._render_magnitude_2d(spectra_norm, channels, h, w)
            info = f"{w}x{h}   Log={log_scale}   Hann={self.cb_hann.isChecked()}"
        else:
            self._render_phase_2d(spectra_norm, channels, h, w)
            info = f"{w}x{h}   Phase   Hann={self.cb_hann.isChecked()}"

        self._spectrum_canvas.set_pixmap(self._spectrum_canvas._pixmap, info)

        # === Радиальный профиль ===
        self._update_radial_plot(radial_data)

    def _compute_radial_profile(self, magnitude: np.ndarray) -> np.ndarray:
        """Средняя magnitude по радиусам."""
        h, w = magnitude.shape
        cy, cx = h // 2, w // 2

        y, x = np.ogrid[:h, :w]
        r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2).astype(int)

        max_r = min(cy, cx)
        radial = np.zeros(max_r + 1)
        counts = np.zeros(max_r + 1)

        # Более эффективная реализация через bincount
        r_flat = r.flatten()
        mag_flat = magnitude.flatten()

        # Ограничиваем r до max_r
        mask = r_flat <= max_r
        r_flat = r_flat[mask]
        mag_flat = mag_flat[mask]

        sums = np.bincount(r_flat, weights=mag_flat, minlength=max_r + 1)
        counts = np.bincount(r_flat, minlength=max_r + 1)

        with np.errstate(divide='ignore', invalid='ignore'):
            radial = sums / counts
        radial = np.nan_to_num(radial, nan=0.0)

        return radial

    def _render_magnitude_2d(
        self, spectra_norm: dict, channels: list, h: int, w: int,
    ) -> None:
        """2D-спектр с наложением каналов в цвете."""
        # Сначала нормализуем каждый канал отдельно
        normalized = {}
        for name, data, _color in channels:
            if name not in spectra_norm:
                continue
            d = spectra_norm[name]
            mx = d.max()
            if mx > 0:
                normalized[name] = d / mx
            else:
                normalized[name] = d

        # Собираем RGB-картинку
        rgb = np.zeros((h, w, 3), dtype=np.float32)

        color_map = {
            "R": (1.0, 0.0, 0.0),
            "G": (0.0, 1.0, 0.0),
            "B": (0.0, 0.0, 1.0),
            "Gray": (1.0, 1.0, 1.0),
        }

        for name, _data, _color in channels:
            if name not in normalized:
                continue
            weight = normalized[name]
            cr, cg, cb = color_map.get(name, (1.0, 1.0, 1.0))
            rgb[:, :, 0] = np.maximum(rgb[:, :, 0], weight * cr)
            rgb[:, :, 1] = np.maximum(rgb[:, :, 1], weight * cg)
            rgb[:, :, 2] = np.maximum(rgb[:, :, 2], weight * cb)

        rgb = (rgb * 255).clip(0, 255).astype(np.uint8)
        rgb = np.ascontiguousarray(rgb)

        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        self._spectrum_canvas._pixmap = pixmap
        self._spectrum_canvas.update()

    def _render_phase_2d(
        self, spectra_norm: dict, channels: list, h: int, w: int,
    ) -> None:
        """Фазовый спектр — grayscale, средний по выбранным каналам."""
        # Берём первый выбранный канал (или усредняем)
        if not channels:
            return

        # Усредняем фазы по всем выбранным каналам
        acc = np.zeros((h, w), dtype=np.float32)
        count = 0
        for name, _data, _color in channels:
            if name not in spectra_norm:
                continue
            acc += spectra_norm[name]
            count += 1

        if count == 0:
            return

        acc /= count
        gray = (acc * 255).clip(0, 255).astype(np.uint8)
        rgb = np.stack([gray, gray, gray], axis=-1)
        rgb = np.ascontiguousarray(rgb)

        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        self._spectrum_canvas._pixmap = pixmap
        self._spectrum_canvas.update()

    def _update_radial_plot(self, radial_data: dict) -> None:
        """Обновляет график радиального профиля."""
        if not radial_data:
            self._curve_r.setData([], [])
            self._curve_g.setData([], [])
            self._curve_b.setData([], [])
            self._curve_gray.setData([], [])
            return

        # Максимальная длина
        max_len = max(len(v) for v in radial_data.values())
        if max_len < 2:
            return

        # X-ось: нормализованная частота (0..0.5 цикл/пиксель)
        # radius r соответствует частоте r / N (где N = размер изображения)
        # Но для простоты используем r / (2 * max_r)
        x = np.arange(max_len) / (2 * max_len)

        def set_curve(curve, name):
            if name in radial_data:
                data = radial_data[name]
                curve.setData(x[:len(data)], data)
            else:
                curve.setData([], [])

        set_curve(self._curve_r, "R")
        set_curve(self._curve_g, "G")
        set_curve(self._curve_b, "B")
        set_curve(self._curve_gray, "Gray")

        self._plot_widget.autoRange()