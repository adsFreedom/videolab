"""Вертикальный слайдер скорости воспроизведения."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSlider, QLabel,
)
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush

from desktop.viewers.styles import (
    SPEED_VALUE_LABEL_STYLE,
    TICK_COLOR,
    TICK_LABEL_COLOR,
)


class SpeedSliderWidget(QSlider):
    """
    Кастомный вертикальный слайдер скорости.
    Внутренний масштаб: value = speed * 100 (0.1 → 10, 2.0 → 200).
    """

    # Геометрия
    PADDING_TOP = 16
    PADDING_BOTTOM = 16
    TRACK_WIDTH = 6
    HANDLE_RADIUS = 8
    HANDLE_RADIUS_HOVER = 10
    TICK_LENGTH = 6
    LABEL_WIDTH = 30

    # Масштаб (value = speed * SCALE)
    SCALE = 100

    # Ключевые риски (с подписями), в единицах шкалы
    KEY_TICKS = [10, 50, 100, 150, 200]  # 0.1, 0.5, 1.0, 1.5, 2.0
    # Средние риски (без подписей)
    MID_TICKS = [25, 30, 75, 125, 175]   # 0.25, 0.3, 0.75, 1.25, 1.75

    # Цвета
    TRACK_COLOR = QColor("#3a3a3d")
    FILL_COLOR = QColor("#0e639c")
    HANDLE_COLOR = QColor("#1177bb")
    HANDLE_COLOR_HOVER = QColor("#2a87cb")
    HANDLE_BORDER_COLOR = QColor("#ffffff")
    TICK_COLOR = QColor(TICK_COLOR)
    LABEL_COLOR = QColor(TICK_LABEL_COLOR)

    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)

        self._hover = False

        self.setMinimum(int(0.1 * self.SCALE))   # 10
        self.setMaximum(int(2.0 * self.SCALE))   # 200
        self.setValue(int(1.0 * self.SCALE))     # 100
        self.setSingleStep(5)                     # 0.05
        self.setPageStep(5)
        self.setInvertedAppearance(False)
        self.setTickPosition(QSlider.NoTicks)
        self.setMouseTracking(True)

        # Ширина: ручка слева + дорожка + риски + подписи
        width = (
            self.HANDLE_RADIUS_HOVER        # левый отступ для ручки
            + self.TRACK_WIDTH
            + 4
            + self.TICK_LENGTH
            + 4
            + self.LABEL_WIDTH
        )
        self.setFixedWidth(width)

    # ==================== РИСОВАНИЕ ====================

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Дорожка сдвинута вправо, чтобы ручка не обрезалась слева
        track_x = self.HANDLE_RADIUS_HOVER + self.TRACK_WIDTH // 2
        track_top = self.PADDING_TOP
        track_bottom = self.height() - self.PADDING_BOTTOM
        track_height = track_bottom - track_top

        if track_height <= 0:
            painter.end()
            return

        minimum = self.minimum()
        maximum = self.maximum()
        value = self.value()

        # --- Дорожка (фон) ---
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.TRACK_COLOR))
        track_rect = QRect(
            track_x - self.TRACK_WIDTH // 2,
            track_top,
            self.TRACK_WIDTH,
            track_height,
        )
        painter.drawRoundedRect(track_rect, 3, 3)

        # --- Позиция ручки ---
        ratio = (value - minimum) / (maximum - minimum) if maximum > minimum else 0
        handle_y = track_bottom - int(ratio * track_height)
        handle_x = track_x

        # --- Заполнение ---
        if handle_y < track_bottom:
            painter.setBrush(QBrush(self.FILL_COLOR))
            fill_rect = QRect(
                track_x - self.TRACK_WIDTH // 2,
                handle_y,
                self.TRACK_WIDTH,
                track_bottom - handle_y,
            )
            painter.drawRoundedRect(fill_rect, 3, 3)

        # --- Риски ---
        self._draw_ticks(painter, track_x, track_top, track_bottom, minimum, maximum)

        # --- Ручка ---
        radius = self.HANDLE_RADIUS_HOVER if self._hover else self.HANDLE_RADIUS
        handle_color = self.HANDLE_COLOR_HOVER if self._hover else self.HANDLE_COLOR

        painter.setPen(QPen(self.HANDLE_BORDER_COLOR, 1))
        painter.setBrush(QBrush(handle_color))
        painter.drawEllipse(QPoint(handle_x, handle_y), radius, radius)

        painter.end()

    def _draw_ticks(self, painter, track_x, track_top, track_bottom, minimum, maximum):
        track_height = track_bottom - track_top

        font = QFont()
        font.setPointSize(7)
        painter.setFont(font)

        tick_start = track_x + self.TRACK_WIDTH // 2 + 2

        # Ключевые риски (с подписями)
        for tick_value in self.KEY_TICKS:
            if tick_value < minimum or tick_value > maximum:
                continue
            ratio = (tick_value - minimum) / (maximum - minimum)
            y = track_bottom - int(ratio * track_height)

            painter.setPen(QPen(self.TICK_COLOR, 1))
            painter.drawLine(tick_start, y, tick_start + self.TICK_LENGTH, y)

            painter.setPen(QPen(self.LABEL_COLOR))
            label = f"{tick_value / self.SCALE:.1f}"
            painter.drawText(
                tick_start + self.TICK_LENGTH + 3,
                y - 7,
                self.LABEL_WIDTH,
                14,
                Qt.AlignLeft | Qt.AlignVCenter,
                label,
            )

        # Средние риски (короче, без подписей)
        painter.setPen(QPen(self.TICK_COLOR, 1))
        for tick_value in self.MID_TICKS:
            if tick_value < minimum or tick_value > maximum:
                continue
            ratio = (tick_value - minimum) / (maximum - minimum)
            y = track_bottom - int(ratio * track_height)
            painter.drawLine(
                tick_start, y,
                tick_start + self.TICK_LENGTH - 2, y,
            )

    # ==================== СОБЫТИЯ ====================

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._set_value_from_pos(event.position().y())
            self.setSliderDown(True)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isSliderDown():
            self._set_value_from_pos(event.position().y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setSliderDown(False)
        super().mouseReleaseEvent(event)

    def _set_value_from_pos(self, y_pos: float) -> None:
        track_top = self.PADDING_TOP
        track_bottom = self.height() - self.PADDING_BOTTOM
        track_height = track_bottom - track_top
        if track_height <= 0:
            return

        clamped_y = max(track_top, min(track_bottom, y_pos))
        ratio = (track_bottom - clamped_y) / track_height

        minimum = self.minimum()
        maximum = self.maximum()
        value = minimum + ratio * (maximum - minimum)

        # Округляем к ближайшему шагу (5 единиц = 0.05)
        step = self.singleStep()
        value = round(value / step) * step
        self.setValue(int(value))


class SpeedSlider(QWidget):
    """Вертикальный слайдер скорости: 0.1 — 2.0, шаг 0.05."""

    speed_changed = Signal(float)

    MIN_SPEED = 0.1
    MAX_SPEED = 2.0
    DEFAULT_SPEED = 1.0

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Метка сверху
        self._value_label = QLabel("1.00x")
        self._value_label.setAlignment(Qt.AlignCenter)
        self._value_label.setStyleSheet(
            SPEED_VALUE_LABEL_STYLE + "\nfont-size: 11pt; font-weight: bold;"
        )
        layout.addWidget(self._value_label)

        # Слайдер
        self._slider = SpeedSliderWidget()
        self._slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self._slider, stretch=1, alignment=Qt.AlignHCenter)

    # ==================== API ====================

    def get_speed(self) -> float:
        return self._slider.value() / SpeedSliderWidget.SCALE

    def set_speed(self, speed: float) -> None:
        speed = max(self.MIN_SPEED, min(self.MAX_SPEED, speed))
        self._slider.setValue(int(speed * SpeedSliderWidget.SCALE))

    # ==================== ВНУТРЕННИЕ ====================

    def _on_value_changed(self, value: int) -> None:
        speed = value / SpeedSliderWidget.SCALE
        self._value_label.setText(f"{speed:.2f}x")
        self.speed_changed.emit(speed)