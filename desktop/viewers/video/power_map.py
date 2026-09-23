"""Карта мощности сигнала на выбранной частоте (внутри ROI)."""
import numpy as np
import cv2
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QDoubleSpinBox, QMessageBox, QProgressDialog,
    QFileDialog,
)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QImage, QPixmap, QColor, QPainter, QPen, QFont

from desktop.viewers.styles import (
    HISTOGRAM_BG,
    HISTOGRAM_AXIS,
    MEDIA_BUTTON_STYLE,
)


class PowerMapCanvas(QWidget):
    """Виджет отрисовки карты мощности."""

    PADDING = 8

    def __init__(self, parent=None):
        super().__init__(parent)

        self._map: np.ndarray | None = None
        self._background: np.ndarray | None = None
        self._alpha: float = 0.7
        self._marker_xy: tuple[int, int] | None = None

        self.setMinimumSize(480, 360)
        self.setStyleSheet(f"background-color: {HISTOGRAM_BG};")
        self.setMouseTracking(True)

    def set_map(self, map_data: np.ndarray, background: np.ndarray | None) -> None:
        self._map = map_data
        self._background = background
        self._marker_xy = None
        self.update()

    def clear(self) -> None:
        self._map = None
        self._background = None
        self._marker_xy = None
        self.update()

    def get_map(self) -> np.ndarray | None:
        return self._map

    # ==================== ГЕОМЕТРИЯ ====================

    def _display_rect(self) -> QRect | None:
        if self._map is None:
            return None

        h, w = self._map.shape
        if w <= 0 or h <= 0:
            return None

        avail_w = self.width() - 2 * self.PADDING
        avail_h = self.height() - 2 * self.PADDING

        scale = min(avail_w / w, avail_h / h)
        draw_w = max(1, int(w * scale))
        draw_h = max(1, int(h * scale))

        x = (self.width() - draw_w) // 2
        y = (self.height() - draw_h) // 2

        return QRect(x, y, draw_w, draw_h)

    def _widget_to_map(self, wx: float, wy: float) -> tuple[int, int] | None:
        if self._map is None:
            return None
        rect = self._display_rect()
        if rect is None:
            return None

        if (wx < rect.left() or wx >= rect.right() or
                wy < rect.top() or wy >= rect.bottom()):
            return None

        h, w = self._map.shape
        mx = int((wx - rect.left()) * w / rect.width())
        my = int((wy - rect.top()) * h / rect.height())
        mx = max(0, min(mx, w - 1))
        my = max(0, min(my, h - 1))
        return (mx, my)

    # ==================== РИСОВАНИЕ ====================

    def _build_display_pixmap(self) -> QPixmap | None:
        if self._map is None:
            return None

        h, w = self._map.shape

        try:
            colormap = pg.colormap.get("viridis")
        except Exception:
            colormap = pg.colormap.get("viridis", source="matplotlib")

        colors = colormap.getLookupTable(nPts=256, alpha=False)

        m = self._map
        m_min = float(m.min())
        m_max = float(m.max())
        if m_max > m_min:
            norm = (m - m_min) / (m_max - m_min)
        else:
            norm = np.zeros_like(m)
        indices = (norm * 255).astype(np.uint8)

        colored = colors[indices]

        if self._background is not None and self._background.shape[:2] == (h, w):
            bg = self._background.astype(np.float32)
            if bg.ndim == 2:
                bg = np.stack([bg, bg, bg], axis=-1)
            fg = colored.astype(np.float32)
            a = self._alpha
            blended = (fg * a + bg * (1 - a)).astype(np.uint8)
        else:
            blended = colored

        blended = np.ascontiguousarray(blended)
        qimg = QImage(blended.data, w, h, 3 * w, QImage.Format_RGB888)
        return QPixmap.fromImage(qimg)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(HISTOGRAM_BG))

        pixmap = self._build_display_pixmap()
        if pixmap is None:
            painter.setPen(QPen(QColor(HISTOGRAM_AXIS)))
            font = QFont()
            font.setItalic(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "Нет данных")
            painter.end()
            return

        rect = self._display_rect()
        if rect is None:
            painter.end()
            return

        scaled = pixmap.scaled(
            rect.size(),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
        painter.drawPixmap(rect.left(), rect.top(), scaled)

        if self._marker_xy is not None:
            h, w = self._map.shape
            rx = rect.left() + int(self._marker_xy[0] * rect.width() / w)
            ry = rect.top() + int(self._marker_xy[1] * rect.height() / h)
            pen = QPen(QColor("#ffffff"), 2)
            painter.setPen(pen)
            painter.drawLine(rx - 8, ry, rx + 8, ry)
            painter.drawLine(rx, ry - 8, rx, ry + 8)

        painter.end()

    # ==================== СОБЫТИЯ ====================

    def mousePressEvent(self, event):
        if self._map is None:
            return

        pos = self._widget_to_map(event.position().x(), event.position().y())
        if pos is None:
            return

        self._marker_xy = pos
        self.update()

        value = float(self._map[pos[1], pos[0]])

        parent = self.window()
        if hasattr(parent, "_on_canvas_clicked"):
            parent._on_canvas_clicked(pos[0], pos[1], value)


class PowerMapWindow(QMainWindow):
    """Отдельное окно: карта мощности сигнала на частоте (внутри ROI)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Карта мощности")
        self.resize(900, 650)

        self._video_path: str = ""
        self._fps: float = 0.0
        self._video_size: tuple[int, int] = (0, 0)
        self._first_frame: np.ndarray | None = None
        self._peak_freqs: list[float] = []

        # ROI (x, y, w, h) или None (всё изображение)
        self._roi: tuple[int, int, int, int] | None = None

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ==================== ВЕРХНЯЯ ПАНЕЛЬ ====================

        top = QHBoxLayout()
        top.setSpacing(8)

        top.addWidget(QLabel("Пространство:"))
        self.combo_space = QComboBox()
        self.combo_space.setFixedWidth(80)
        self.combo_space.addItems(["RGB", "HSV", "LAB", "YUV"])
        self.combo_space.currentTextChanged.connect(lambda _: self._update_labels())
        top.addWidget(self.combo_space)

        top.addSpacing(8)

        top.addWidget(QLabel("Канал:"))
        self.combo_channel = QComboBox()
        self.combo_channel.setFixedWidth(60)
        top.addWidget(self.combo_channel)

        top.addSpacing(8)

        top.addWidget(QLabel("Частота (Гц):"))
        self.spin_freq = QDoubleSpinBox()
        self.spin_freq.setRange(0.01, 10000.0)
        self.spin_freq.setDecimals(2)
        self.spin_freq.setSingleStep(0.1)
        self.spin_freq.setValue(2.0)
        self.spin_freq.setFixedWidth(100)
        top.addWidget(self.spin_freq)

        top.addWidget(QLabel("±"))
        self.spin_width = QDoubleSpinBox()
        self.spin_width.setRange(0.0, 100.0)
        self.spin_width.setDecimals(2)
        self.spin_width.setSingleStep(0.05)
        self.spin_width.setValue(0.1)
        self.spin_width.setFixedWidth(80)
        top.addWidget(self.spin_width)

        self.btn_compute = QPushButton("Построить")
        self.btn_compute.setStyleSheet(MEDIA_BUTTON_STYLE)
        self.btn_compute.clicked.connect(self._compute_map)
        top.addWidget(self.btn_compute)

        top.addStretch()
        layout.addLayout(top)

        # ==================== ИНФО ====================

        self._info_label = QLabel("Нажмите 'Построить' для расчёта карты")
        self._info_label.setStyleSheet(
            "padding: 4px; font-family: Consolas; font-size: 9pt;"
        )
        layout.addWidget(self._info_label)

        # ==================== КАРТА ====================

        self._canvas = PowerMapCanvas()
        layout.addWidget(self._canvas, stretch=1)

        # ==================== КНОПКИ СНИЗУ ====================

        bottom = QHBoxLayout()
        bottom.addStretch()

        self.btn_save = QPushButton("Сохранить PNG")
        self.btn_save.setStyleSheet(MEDIA_BUTTON_STYLE)
        self.btn_save.clicked.connect(self._save_png)
        self.btn_save.setEnabled(False)
        bottom.addWidget(self.btn_save)

        layout.addLayout(bottom)

        self.setCentralWidget(container)

        self._update_labels()

    # ==================== API ====================

    def set_source(
        self,
        video_path: str,
        fps: float,
        video_size: tuple[int, int],
        first_frame: np.ndarray | None,
        peak_freqs: list[float],
        roi: tuple[int, int, int, int] | None = None,
    ) -> None:
        self._video_path = video_path
        self._fps = fps
        self._video_size = video_size
        self._first_frame = first_frame
        self._peak_freqs = peak_freqs
        self._roi = roi
        self._canvas.clear()
        self.btn_save.setEnabled(False)

        if roi is not None:
            x, y, w, h = roi
            roi_text = f"ROI: ({x}, {y}) {w}x{h}"
        else:
            roi_text = "ROI: всё изображение"

        if peak_freqs:
            self.spin_freq.setValue(peak_freqs[0])
            self._info_label.setText(
                f"{roi_text}   |   Пики: "
                f"{', '.join(f'{f:.2f}' for f in peak_freqs[:5])} Гц"
            )
        else:
            self._info_label.setText(
                f"{roi_text}   |   Пики не найдены, выберите частоту вручную"
            )

    # ==================== UI ====================

    def _update_labels(self) -> None:
        space = self.combo_space.currentText()
        maps = {
            "RGB": ["R", "G", "B"],
            "HSV": ["H", "S", "V"],
            "LAB": ["L", "a", "b"],
            "YUV": ["Y", "U", "V"],
        }
        self.combo_channel.clear()
        self.combo_channel.addItems(maps.get(space, ["R", "G", "B"]))

    # ==================== РАСЧЁТ ====================

    def _compute_map(self) -> None:
        if not self._video_path:
            QMessageBox.warning(self, "Ошибка", "Нет пути к видео")
            return

        target_freq = self.spin_freq.value()
        freq_width = self.spin_width.value()
        space = self.combo_space.currentText()
        channel_idx = self.combo_channel.currentIndex()

        cap = cv2.VideoCapture(self._video_path)
        if not cap.isOpened():
            QMessageBox.warning(self, "Ошибка", "Не удалось открыть видео")
            return

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self._fps if self._fps > 0 else cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0

        # Определяем ROI (или всё изображение)
        vid_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        vid_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if self._roi is not None:
            rx, ry, rw, rh = self._roi
        else:
            rx, ry, rw, rh = 0, 0, vid_w, vid_h

        # Клампим к границам
        rx = max(0, min(rx, vid_w - 1))
        ry = max(0, min(ry, vid_h - 1))
        rw = min(rw, vid_w - rx)
        rh = min(rh, vid_h - ry)

        if rw < 2 or rh < 2:
            QMessageBox.warning(self, "Ошибка", "Слишком маленькая область")
            cap.release()
            return

        progress = QProgressDialog(
            f"Расчёт карты на {target_freq:.2f} Гц (ROI {rw}x{rh})...",
            "Отмена", 0, frame_count, self,
        )
        progress.setWindowTitle("Расчёт карты")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(200)

        frames = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % 20 == 0:
                progress.setValue(frame_idx)
                if progress.wasCanceled():
                    cap.release()
                    progress.close()
                    return

            # Обрезаем кадр по ROI
            frame_crop = frame[ry:ry + rh, rx:rx + rw]

            # BGR → RGB
            frame_rgb = cv2.cvtColor(frame_crop, cv2.COLOR_BGR2RGB)

            # Выбираем канал
            if space == "RGB":
                ch = frame_rgb[:, :, channel_idx]
            else:
                if space == "HSV":
                    conv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV)
                elif space == "LAB":
                    conv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2LAB)
                elif space == "YUV":
                    conv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2YUV)
                else:
                    conv = frame_rgb
                ch = conv[:, :, channel_idx]

            frames.append(ch)
            frame_idx += 1

        cap.release()
        progress.setValue(frame_count)
        progress.close()

        if len(frames) < 4:
            QMessageBox.warning(self, "Ошибка", "Слишком мало кадров")
            return

        # Стек: (N, H_roi, W_roi)
        data = np.stack(frames, axis=0).astype(np.float32)
        n = data.shape[0]

        # Убираем DC
        data = data - data.mean(axis=0, keepdims=True)

        # Hann по времени
        window = np.hanning(n).astype(np.float32)
        data = data * window[:, None, None]

        # FFT по времени
        spectrum = np.fft.rfft(data, axis=0)
        magnitude = np.abs(spectrum)

        freqs = np.fft.rfftfreq(n, d=1.0 / fps)

        # Диапазон частот
        if freq_width > 0:
            mask = (freqs >= target_freq - freq_width) & (freqs <= target_freq + freq_width)
        else:
            step = freqs[1] - freqs[0] if len(freqs) > 1 else 1e-3
            mask = np.isclose(freqs, target_freq, atol=step)

        if not mask.any():
            idx = int(np.argmin(np.abs(freqs - target_freq)))
            magnitude_at_freq = magnitude[idx]
        else:
            magnitude_at_freq = magnitude[mask].mean(axis=0)

        # Нормализация
        mag_min = float(magnitude_at_freq.min())
        mag_max = float(magnitude_at_freq.max())
        if mag_max > mag_min:
            normalized = (magnitude_at_freq - mag_min) / (mag_max - mag_min)
        else:
            normalized = magnitude_at_freq * 0.0

        # Фон — обрезанный первый кадр
        background = None
        if self._first_frame is not None:
            fh, fw = self._first_frame.shape[:2]
            if fh >= ry + rh and fw >= rx + rw:
                background = self._first_frame[ry:ry + rh, rx:rx + rw]
            else:
                background = self._first_frame

        if background is None:
            cap2 = cv2.VideoCapture(self._video_path)
            ret, frame = cap2.read()
            cap2.release()
            if ret:
                frame_crop = frame[ry:ry + rh, rx:rx + rw]
                background = cv2.cvtColor(frame_crop, cv2.COLOR_BGR2RGB)

        self._canvas.set_map(normalized, background)
        self.btn_save.setEnabled(True)

        info = (
            f"ROI: ({rx}, {ry}) {rw}x{rh}   "
            f"Частота: {target_freq:.2f} ± {freq_width:.2f} Гц   "
            f"Канал: {space} / {self.combo_channel.currentText()}   "
            f"Кадров: {n}   Max: {mag_max:.2f}"
        )
        self._info_label.setText(info)

    # ==================== СОХРАНЕНИЕ ====================

    def _save_png(self) -> None:
        if self._canvas.get_map() is None:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить карту", "power_map.png", "PNG (*.png)"
        )
        if not path:
            return

        pixmap = self._canvas._build_display_pixmap()
        if pixmap is None:
            return
        pixmap.save(path, "PNG")

    def _on_canvas_clicked(self, x: int, y: int, value: float) -> None:
        # x, y — координаты внутри ROI
        if self._roi is not None:
            rx, ry, _, _ = self._roi
            abs_x = rx + x
            abs_y = ry + y
        else:
            abs_x, abs_y = x, y

        self._info_label.setText(
            f"ROI-локальные: ({x}, {y})   Абсолютные: ({abs_x}, {abs_y})   "
            f"Значение: {value:.4f}   "
            f"Частота: {self.spin_freq.value():.2f} Гц"
        )