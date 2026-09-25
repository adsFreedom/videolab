"""Окно карты мощности сигнала на частоте."""
import numpy as np
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QDoubleSpinBox, QMessageBox, QProgressDialog,
    QFileDialog,
)
from PySide6.QtCore import Qt

from desktop.viewers.styles import MEDIA_BUTTON_STYLE
from desktop.viewers.video.power_map.canvas import PowerMapCanvas
from desktop.viewers.video.power_map.colorbar import ColorbarWidget
from desktop.viewers.video.power_map.colormaps import COLORMAPS
from desktop.viewers.video.power_map.computation import compute_power_map
from utils.color_conversions import get_channel_names
import cv2


class PowerMapWindow(QMainWindow):
    """Отдельное окно: карта мощности сигнала на частоте (внутри ROI)."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Карта мощности")
        self.resize(1000, 650)

        self._video_path: str = ""
        self._fps: float = 0.0
        self._video_size: tuple[int, int] = (0, 0)
        self._first_frame: np.ndarray | None = None
        self._peak_freqs: list[float] = []
        self._roi: tuple[int, int, int, int] | None = None

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ==================== ВЕРХНЯЯ ПАНЕЛЬ ====================
        layout.addLayout(self._create_top_panel())

        # ==================== ИНФО ====================
        self._info_label = QLabel("Нажмите 'Построить' для расчёта карты")
        self._info_label.setStyleSheet(
            "padding: 4px; font-family: Consolas; font-size: 9pt;"
        )
        layout.addWidget(self._info_label)

        # ==================== КАРТА + COLORBAR ====================
        map_row = QHBoxLayout()
        map_row.setSpacing(4)

        self._canvas = PowerMapCanvas()
        map_row.addWidget(self._canvas, stretch=1)

        self._colorbar = ColorbarWidget()
        map_row.addWidget(self._colorbar)

        layout.addLayout(map_row, stretch=1)

        # ==================== КНОПКИ ====================
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
        self._colorbar.set_colormap("Turbo")

    # ==================== СОЗДАНИЕ UI ====================

    def _create_top_panel(self) -> QHBoxLayout:
        """Верхняя панель управления."""
        top = QHBoxLayout()
        top.setSpacing(8)

        top.addWidget(QLabel("Пространство:"))
        self.combo_space = QComboBox()
        self.combo_space.setFixedWidth(80)
        self.combo_space.addItems(["YIQ", "RGB", "HSV", "LAB", "YUV"])
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

        top.addWidget(QLabel("Палитра:"))
        self.combo_colormap = QComboBox()
        self.combo_colormap.setFixedWidth(90)
        self.combo_colormap.addItems(list(COLORMAPS.keys()))
        self.combo_colormap.setCurrentText("Turbo")
        self.combo_colormap.currentTextChanged.connect(self._on_colormap_changed)
        top.addWidget(self.combo_colormap)

        return top

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
        self.combo_channel.clear()
        self.combo_channel.addItems(get_channel_names(space))

    def _on_colormap_changed(self, name: str) -> None:
        self._canvas.set_colormap(name)
        self._colorbar.set_colormap(name)

    # ==================== РАСЧЁТ ====================

    def _compute_map(self) -> None:
        if not self._video_path:
            QMessageBox.warning(self, "Ошибка", "Нет пути к видео")
            return

        target_freq = self.spin_freq.value()
        freq_width = self.spin_width.value()
        space = self.combo_space.currentText()
        channel_idx = self.combo_channel.currentIndex()

        # Прогресс
        cap = cv2.VideoCapture(self._video_path)
        if not cap.isOpened():
            QMessageBox.warning(self, "Ошибка", "Не удалось открыть видео")
            return
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        progress = QProgressDialog(
            f"Расчёт карты на {target_freq:.2f} Гц...",
            "Отмена", 0, frame_count, self,
        )
        progress.setWindowTitle("Расчёт карты")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(200)

        def on_progress(current: int, total: int) -> bool:
            progress.setValue(current)
            return not progress.wasCanceled()

        result = compute_power_map(
            video_path=self._video_path,
            fps=self._fps,
            roi=self._roi,
            space=space,
            channel_idx=channel_idx,
            target_freq=target_freq,
            freq_width=freq_width,
            first_frame=self._first_frame,
            progress_callback=on_progress,
        )

        progress.setValue(frame_count)
        progress.close()

        if result is None:
            QMessageBox.warning(self, "Ошибка", "Расчёт не удался или отменён")
            return

        self._canvas.set_map(
            result["map"],
            result["background"],
            result["raw_min"],
            result["raw_max"],
        )
        self._colorbar.set_colormap(self.combo_colormap.currentText())
        self._colorbar.set_range(result["raw_min"], result["raw_max"])
        self.btn_save.setEnabled(True)

        rx, ry, rw, rh = result["roi"]
        info = (
            f"ROI: ({rx}, {ry}) {rw}x{rh}   "
            f"Частота: {target_freq:.2f} ± {freq_width:.2f} Гц   "
            f"Канал: {space} / {self.combo_channel.currentText()}   "
            f"Кадров: {result['frames_count']}   "
            f"Max: {result['raw_max']:.2f}   Min: {result['raw_min']:.2f}"
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

        pixmap = self._canvas._build_pixmap()
        if pixmap is None:
            return
        pixmap.save(path, "PNG")

    # ==================== СОБЫТИЯ ====================

    def _on_canvas_clicked(self, x: int, y: int, value: float) -> None:
        raw_min, raw_max = self._canvas.get_raw_range()
        absolute_value = raw_min + value * (raw_max - raw_min)

        if self._roi is not None:
            rx, ry, _, _ = self._roi
            abs_x = rx + x
            abs_y = ry + y
        else:
            abs_x, abs_y = x, y

        self._info_label.setText(
            f"ROI-локальные: ({x}, {y})   Абсолютные: ({abs_x}, {abs_y})   "
            f"Мощность: {absolute_value:.4f}   "
            f"Частота: {self.spin_freq.value():.2f} Гц"
        )