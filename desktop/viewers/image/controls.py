"""Панель управления изображением."""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QComboBox,
)
from PySide6.QtCore import Qt, Signal

from desktop.viewers.styles import MEDIA_BUTTON_STYLE, SYMBOL_BUTTON_STYLE


class ImageControls(QWidget):
    """Панель управления: fit, reset, пространство, каналы, снимок, гистограмма, FFT."""

    fit_clicked = Signal()
    reset_clicked = Signal()
    space_changed = Signal(str)
    channel_changed = Signal(str)
    extract_clicked = Signal()
    histogram_clicked = Signal()
    fft_clicked = Signal()
    line_profile_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        btn_size = 36

        # Fit
        self.btn_fit = QPushButton("Fit")
        self.btn_fit.setToolTip("Вписать в окно (Ctrl+1)")
        self.btn_fit.setFixedSize(52, btn_size)
        self.btn_fit.setStyleSheet(MEDIA_BUTTON_STYLE)
        self.btn_fit.clicked.connect(self.fit_clicked.emit)
        layout.addWidget(self.btn_fit)

        # Reset 100%
        self.btn_reset = QPushButton("100%")
        self.btn_reset.setToolTip("Оригинальный размер (Ctrl+0)")
        self.btn_reset.setFixedSize(64, btn_size)
        self.btn_reset.setStyleSheet(MEDIA_BUTTON_STYLE)
        self.btn_reset.clicked.connect(self.reset_clicked.emit)
        layout.addWidget(self.btn_reset)

        # Zoom label
        self.label_zoom = QLabel("100%")
        self.label_zoom.setFixedWidth(60)
        self.label_zoom.setAlignment(Qt.AlignCenter)
        self.label_zoom.setStyleSheet("font-family: Consolas; font-size: 9pt;")
        layout.addWidget(self.label_zoom)

        layout.addStretch()

        # Пространство
        layout.addWidget(QLabel("Пространство:"))
        self.combo_space = QComboBox()
        self.combo_space.setFixedWidth(80)
        self.combo_space.addItems(["RGB", "HSV", "LAB", "YUV"])
        self.combo_space.currentTextChanged.connect(self.space_changed.emit)
        layout.addWidget(self.combo_space)

        layout.addSpacing(8)

        # Каналы
        layout.addWidget(QLabel("Канал:"))
        self.combo_channel = QComboBox()
        self.combo_channel.setFixedWidth(90)
        self.combo_channel.currentTextChanged.connect(self.channel_changed.emit)
        layout.addWidget(self.combo_channel)

        layout.addSpacing(8)

        # Line Profile
        self.btn_line = QPushButton("↗")
        self.btn_line.setToolTip("Профиль по линии")
        self.btn_line.setCheckable(True)
        self.btn_line.setFixedSize(btn_size, btn_size)
        self.btn_line.setStyleSheet(SYMBOL_BUTTON_STYLE)
        self.btn_line.clicked.connect(self.line_profile_clicked.emit)
        layout.addWidget(self.btn_line)

        # FFT
        self.btn_fft = QPushButton("FFT")
        self.btn_fft.setToolTip("Спектр Фурье изображения")
        self.btn_fft.setFixedSize(52, btn_size)
        self.btn_fft.setStyleSheet(MEDIA_BUTTON_STYLE)
        self.btn_fft.clicked.connect(self.fft_clicked.emit)
        layout.addWidget(self.btn_fft)

        # Гистограмма
        self.btn_histogram = QPushButton("📊")
        self.btn_histogram.setToolTip("Показать гистограмму")
        self.btn_histogram.setFixedSize(btn_size, btn_size)
        self.btn_histogram.setStyleSheet(SYMBOL_BUTTON_STYLE)
        self.btn_histogram.clicked.connect(self.histogram_clicked.emit)
        layout.addWidget(self.btn_histogram)

        # Извлечь область
        self.btn_extract = QPushButton("Извлечь")
        self.btn_extract.setToolTip("Открыть выделенную область в новом окне (Ctrl+E)")
        self.btn_extract.setFixedHeight(btn_size)
        self.btn_extract.setStyleSheet(MEDIA_BUTTON_STYLE)
        self.btn_extract.clicked.connect(self.extract_clicked.emit)
        self.btn_extract.setEnabled(False)
        layout.addWidget(self.btn_extract)

    # ==================== API ====================

    def set_zoom_label(self, zoom: float) -> None:
        self.label_zoom.setText(f"{int(zoom * 100)}%")

    def set_channels(self, channels: list[str]) -> None:
        self.combo_channel.blockSignals(True)
        current = self.combo_channel.currentText()
        self.combo_channel.clear()
        self.combo_channel.addItems(channels)
        if current in channels:
            self.combo_channel.setCurrentText(current)
        self.combo_channel.blockSignals(False)

    def get_channel(self) -> str:
        return self.combo_channel.currentText()

    def get_space(self) -> str:
        return self.combo_space.currentText()

    def set_extract_enabled(self, enabled: bool) -> None:
        self.btn_extract.setEnabled(enabled)

    def set_enabled_controls(self, enabled: bool) -> None:
        self.btn_fit.setEnabled(enabled)
        self.btn_reset.setEnabled(enabled)
        self.combo_space.setEnabled(enabled)
        self.combo_channel.setEnabled(enabled)
        self.btn_histogram.setEnabled(enabled)
        self.btn_fft.setEnabled(enabled)
        self.btn_line.setEnabled(enabled)