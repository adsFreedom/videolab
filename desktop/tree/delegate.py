"""Делегат дерева: рисует полоску прогресса в колонке состояния."""
import time
import math

from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QPainter, QPen

from core.progress_registry import progress_registry
from desktop.tree.model import ROLE_PATH, ROLE_STATE


class TreeDelegate(QStyledItemDelegate):
    """
    Делегат дерева:
    - колонка 0 — стандартная отрисовка (имя, иконка, выделение);
    - колонка 1 — полоска прогресса (если узел обрабатывается),
                  иначе стандартная отрисовка (✅ / ❌).
    """

    # Настройки полоски
    BAR_MARGIN = 4          # отступ от краёв ячейки
    BAR_HEIGHT = 10         # высота полоски

    # Цвета
    BAR_BG = QColor("#3c3c3c")          # фон полоски
    BAR_FILL = QColor("#0e639c")        # заполнение
    BAR_WAVE = QColor("#4fc1ff")        # бегущая волна

    def paint(self, painter: QPainter, option, index) -> None:
        # Колонка 1 — рисуем полоску, если узел обрабатывается
        if index.column() == 1:
            node_path = index.data(ROLE_PATH)
            state = index.data(ROLE_STATE)

            if state == "processing" and node_path:
                self._paint_progress(painter, option, node_path)
                return

        # Всё остальное — стандартная отрисовка
        super().paint(painter, option, index)

    def _paint_progress(self, painter: QPainter, option, node_path: str) -> None:
        """Рисует полоску прогресса."""
        progress = progress_registry.get(node_path)
        if progress is None:
            return

        current, total = progress

        # --- Выделение (если ячейка выделена) ---
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor("#094771"))

        # --- Область полоски ---
        rect = option.rect
        bar_x = rect.left() + self.BAR_MARGIN
        bar_w = rect.width() - 2 * self.BAR_MARGIN
        bar_h = self.BAR_HEIGHT
        bar_y = rect.top() + (rect.height() - bar_h) // 2

        bar_rect = QRect(bar_x, bar_y, bar_w, bar_h)

        # --- Фон полоски ---
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.BAR_BG)
        painter.drawRoundedRect(bar_rect, 3, 3)

        if total > 0:
            # Определённый прогресс
            ratio = max(0.0, min(1.0, current / total))
            fill_w = int(bar_w * ratio)

            if fill_w > 0:
                fill_rect = QRect(bar_x, bar_y, fill_w, bar_h)
                painter.setBrush(self.BAR_FILL)
                painter.drawRoundedRect(fill_rect, 3, 3)

            # Текст процентов
            percent = int(ratio * 100)
            painter.setPen(QPen(QColor("#ffffff")))
            painter.setFont(option.font)
            painter.drawText(
                option.rect,
                Qt.AlignCenter,
                f"{percent}%",
            )
        else:
            # Неопределённый — бегущая волна
            self._paint_wave(painter, bar_rect)

            # Текст "..." в центре
            painter.setPen(QPen(QColor("#ffffff")))
            painter.setFont(option.font)
            painter.drawText(
                option.rect,
                Qt.AlignCenter,
                "...",
            )

        painter.restore()

    def _paint_wave(self, painter: QPainter, bar_rect: QRect) -> None:
        """Рисует бегущую волну внутри полоски."""
        bar_w = bar_rect.width()
        bar_h = bar_rect.height()

        if bar_w <= 0:
            return

        # Фаза волны — меняется со временем
        phase = (time.time() * 1.5) % 2.0  # 0..2

        # Ширина светлой части — треть полоски
        wave_w = max(30, bar_w // 3)

        # Позиция волны — двигается слева-направо
        # phase 0..1: слева за пределами → справа за пределами
        t = phase if phase < 1.0 else 2.0 - phase  # 0..1..0, туда-обратно
        wave_x = int(-wave_w + (bar_w + wave_w) * t)

        wave_rect = QRect(
            bar_rect.left() + wave_x,
            bar_rect.top(),
            wave_w,
            bar_h,
        )

        # Ограничиваем в пределах полоски
        clipped = wave_rect.intersected(bar_rect)
        if clipped.width() <= 0:
            return

        painter.save()
        painter.setClipRect(bar_rect)
        painter.setBrush(self.BAR_WAVE)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(wave_rect, 3, 3)
        painter.restore()