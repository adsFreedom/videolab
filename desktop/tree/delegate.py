"""Делегат дерева: прогресс-бар справа от текста."""
import time

from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QPainter, QPen

from core.progress_registry import progress_registry
from desktop.tree.model import ROLE_PATH, ROLE_STATE


class TreeDelegate(QStyledItemDelegate):
    """Делегат: прогресс-бар справа от текста. Высота строки — 26 px."""

    # Параметры
    BAR_WIDTH = 100
    BAR_HEIGHT = 14
    BAR_MARGIN_RIGHT = 8
    TEXT_GAP = 12
    ROW_HEIGHT = 22

    # Цвета
    BAR_BG = QColor("#3c3c3c")
    BAR_FILL = QColor("#0e639c")
    BAR_WAVE = QColor("#4fc1ff")

    def sizeHint(self, option, index):
        """Задаёт высоту строки."""
        size = super().sizeHint(option, index)
        size.setHeight(self.ROW_HEIGHT)
        return size

    def paint(self, painter: QPainter, option, index) -> None:
        node_path = index.data(ROLE_PATH)
        state = index.data(ROLE_STATE)

        if state == "processing" and node_path:
            progress = progress_registry.get(node_path)
            if progress is not None:
                self._paint_with_progress(painter, option, index, progress)
                return

        super().paint(painter, option, index)

    def _paint_with_progress(
        self, painter: QPainter, option, index, progress: tuple[int, int]
    ) -> None:
        current, total = progress
        full_rect = option.rect

        if option.state & QStyle.State_Selected:
            painter.fillRect(full_rect, QColor("#094771"))

        bar_area_w = self.BAR_WIDTH + self.BAR_MARGIN_RIGHT
        text_rect = QRect(
            full_rect.left(),
            full_rect.top(),
            max(0, full_rect.width() - bar_area_w - self.TEXT_GAP),
            full_rect.height(),
        )

        text_option = option
        text_option.rect = text_rect

        if option.state & QStyle.State_Selected:
            text_option.state &= ~QStyle.State_Selected

        super().paint(painter, text_option, index)

        bar_rect = QRect(
            full_rect.right() - self.BAR_MARGIN_RIGHT - self.BAR_WIDTH,
            full_rect.top() + (full_rect.height() - self.BAR_HEIGHT) // 2,
            self.BAR_WIDTH,
            self.BAR_HEIGHT,
        )

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.BAR_BG)
        painter.drawRoundedRect(bar_rect, 3, 3)

        # Шрифт для процентов — маленький
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        if total > 0:
            ratio = max(0.0, min(1.0, current / total))
            fill_w = int(bar_rect.width() * ratio)

            if fill_w > 0:
                fill_rect = QRect(
                    bar_rect.left(), bar_rect.top(),
                    fill_w, bar_rect.height(),
                )
                painter.setBrush(self.BAR_FILL)
                painter.drawRoundedRect(fill_rect, 3, 3)

            percent = int(ratio * 100)
            painter.setPen(QPen(QColor("#ffffff")))
            painter.drawText(bar_rect, Qt.AlignCenter, f"{percent}%")
        else:
            self._paint_wave(painter, bar_rect)
            painter.setPen(QPen(QColor("#ffffff")))
            painter.drawText(bar_rect, Qt.AlignCenter, "...")

        painter.restore()

    def _paint_wave(self, painter: QPainter, bar_rect: QRect) -> None:
        bar_w = bar_rect.width()
        bar_h = bar_rect.height()
        if bar_w <= 0:
            return

        phase = (time.time() * 1.5) % 2.0
        wave_w = max(30, bar_w // 3)
        t = phase if phase < 1.0 else 2.0 - phase
        wave_x = int(-wave_w + (bar_w + wave_w) * t)

        wave_rect = QRect(
            bar_rect.left() + wave_x,
            bar_rect.top(),
            wave_w,
            bar_h,
        )
        clipped = wave_rect.intersected(bar_rect)
        if clipped.width() <= 0:
            return

        painter.save()
        painter.setClipRect(bar_rect)
        painter.setBrush(self.BAR_WAVE)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(wave_rect, 3, 3)
        painter.restore()