"""Вертикальный слайдер скорости воспроизведения."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QPushButton,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont


class TicksWidget(QWidget):
    """Виджет с рисками и подписями, синхронизированный со слайдером."""

    TICK_STEP = 5         # каждые 0.5 (при делении на 10)
    TICK_LENGTH = 6

    def __init__(self, slider: QSlider, parent=None):
        super().__init__(parent)
        self._slider = slider
        self.setFixedWidth(30)

        self._tick_color = QColor("#666666")
        self._label_color = QColor("#a0a0a0")

    def paintEvent(self, event):
        super().paintEvent(event)

        if self._slider is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        # Те же границы, что у слайдера (стандартные ~10 px отступы)
        groove_top = 10
        groove_bottom = self._slider.height() - 10
        groove_height = groove_bottom - groove_top

        if groove_height <= 0:
            painter.end()
            return

        minimum = self._slider.minimum()
        maximum = self._slider.maximum()

        font = QFont()
        font.setPointSize(7)
        painter.setFont(font)

        value = minimum
        while value <= maximum:
            ratio = (value - minimum) / (maximum - minimum)
            y = groove_bottom - int(ratio * groove_height)

            # Риска
            painter.setPen(QPen(self._tick_color, 1))
            painter.drawLine(0, y, self.TICK_LENGTH, y)

            # Подпись
            painter.setPen(QPen(self._label_color))
            label = f"{value / 10:.1f}"
            painter.drawText(
                self.TICK_LENGTH + 2, y - 7,
                self.width() - self.TICK_LENGTH - 2, 14,
                Qt.AlignLeft | Qt.AlignVCenter,
                label,
            )

            value += self.TICK_STEP

        painter.end()


class SpeedSlider(QWidget):
    """Вертикальный слайдер скорости: 0.1 — 2.0, шаг 0.1."""

    speed_changed = Signal(float)

    MIN_SPEED = 0.1
    MAX_SPEED = 2.0
    DEFAULT_SPEED = 1.0

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedWidth(96)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Метка сверху — текущее значение
        self._value_label = QLabel("1.0x")
        self._value_label.setAlignment(Qt.AlignCenter)
        self._value_label.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 9pt;"
        )
        layout.addWidget(self._value_label)

        # Слайдер + риски в одной строке
        middle = QHBoxLayout()
        middle.setContentsMargins(0, 0, 0, 0)
        middle.setSpacing(0)

        self._slider = QSlider(Qt.Vertical)
        self._slider.setMinimum(int(self.MIN_SPEED * 10))
        self._slider.setMaximum(int(self.MAX_SPEED * 10))
        self._slider.setValue(int(self.DEFAULT_SPEED * 10))
        self._slider.setSingleStep(1)
        self._slider.setPageStep(1)
        self._slider.setInvertedAppearance(False)
        self._slider.setTickPosition(QSlider.NoTicks)
        self._slider.valueChanged.connect(self._on_value_changed)
        middle.addWidget(self._slider, alignment=Qt.AlignHCenter)

        # Виджет рисок — справа от слайдера
        self._ticks = TicksWidget(self._slider)
        middle.addWidget(self._ticks, alignment=Qt.AlignVCenter)

        middle.addStretch()
        layout.addLayout(middle, stretch=1)

        # Кнопка сброса
        self._btn_reset = QPushButton("x1")
        self._btn_reset.setToolTip("Сбросить скорость на 1.0x")
        self._btn_reset.setFixedWidth(48)
        self._btn_reset.clicked.connect(self._on_reset)
        layout.addWidget(self._btn_reset, alignment=Qt.AlignHCenter)

    # ==================== API ====================

    def get_speed(self) -> float:
        return self._slider.value() / 10.0

    def set_speed(self, speed: float) -> None:
        speed = max(self.MIN_SPEED, min(self.MAX_SPEED, speed))
        self._slider.setValue(int(speed * 10))

    # ==================== ВНУТРЕННИЕ ====================

    def _on_value_changed(self, value: int) -> None:
        speed = value / 10.0
        self._value_label.setText(f"{speed:.1f}x")
        self.speed_changed.emit(speed)

    def _on_reset(self) -> None:
        self._slider.setValue(int(self.DEFAULT_SPEED * 10))