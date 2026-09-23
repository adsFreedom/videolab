"""Стили для просмотрщиков.

Все стили, специфичные для просмотрщиков, живут здесь.
Это позволяет легко выделить папку viewers/ в отдельный проект.
"""

# ==================== КНОПКИ ====================

MEDIA_BUTTON_STYLE = """
QPushButton {
    background-color: #3a3a3d;
    border: 1px solid #4a4a4d;
    border-radius: 3px;
    color: #d4d4d4;
}

QPushButton:hover {
    background-color: #4a4a4e;
    border: 1px solid #5a5a5e;
}

QPushButton:pressed {
    background-color: #2a4a6a;
    border: 1px solid #3a5a7a;
}

QPushButton:checked {
    background-color: #0e639c;
    border: 1px solid #1177bb;
    color: #ffffff;
}

QPushButton:checked:hover {
    background-color: #1177bb;
    border: 1px solid #2a87cb;
}

QPushButton:disabled {
    background-color: #2a2a2d;
    border: 1px solid #3a3a3d;
    color: #666666;
}
"""


# ==================== SEEK SLIDER (горизонтальный) ====================

SEEK_SLIDER_STYLE = """
QSlider::groove:horizontal {
    height: 6px;
    background: #3a3a3d;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #0e639c;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #1177bb;
    border: 1px solid #ffffff;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #2a87cb;
}

QSlider::handle:horizontal:pressed {
    background: #2a87cb;
}
"""


# ==================== ВИДЕО ====================

VIDEO_SURFACE_STYLE = """
QWidget {
    background-color: #1a1a1a;
}
"""


VIDEO_FRAME_STYLE = """
QFrame#VideoFrame {
    border: 2px solid #3e4a5a;
    border-radius: 4px;
    background-color: #0d0d0d;
}
"""


VIDEO_OVERLAY_STYLE = """
QLabel {
    background-color: rgba(0, 0, 0, 160);
    color: #ffffff;
    padding: 4px 8px;
    border-radius: 3px;
    font-family: Consolas, monospace;
    font-size: 9pt;
}
"""


# ==================== ИЗОБРАЖЕНИЕ ====================

IMAGE_SURFACE_STYLE = """
QWidget {
    background-color: #1a1a1a;
}
"""


IMAGE_FRAME_STYLE = """
QFrame#ImageFrame {
    border: 2px solid #3e4a5a;
    border-radius: 4px;
    background-color: #0d0d0d;
}
"""


IMAGE_SELECTION_COLOR = "#4fc1ff"
IMAGE_SELECTION_WIDTH = 2


# ==================== PIXEL INFO ====================

PIXEL_COORD_LABEL_STYLE = """
font-family: Consolas, monospace;
"""


PIXEL_RGB_LABEL_STYLE = """
font-family: Consolas, monospace;
"""


PIXEL_SWATCH_EMPTY_STYLE = """
background-color: #1a1a1a;
border: 1px solid #3e3e42;
"""


PIXEL_SWATCH_TEMPLATE = """
background-color: {color};
border: 1px solid #3e3e42;
"""


# ==================== SPEED SLIDER ====================

SPEED_VALUE_LABEL_STYLE = """
font-family: Consolas, monospace;
font-size: 9pt;
"""


TICKS_LABEL_STYLE = """
font-family: Consolas, monospace;
font-size: 8pt;
color: #808080;
"""


# ==================== ЦВЕТА РИСОК ====================

TICK_COLOR = "#666666"
TICK_LABEL_COLOR = "#a0a0a0"


# ==================== ГИСТОГРАММА ====================

HISTOGRAM_BG = "#1e1e1e"
HISTOGRAM_GRID = "#3e3e42"
HISTOGRAM_AXIS = "#808080"

HISTOGRAM_COLOR_R = "#ff5555"
HISTOGRAM_COLOR_G = "#55ff55"
HISTOGRAM_COLOR_B = "#5599ff"
HISTOGRAM_COLOR_Y = "#ffffff"
HISTOGRAM_COLOR_GRAY = "#cccccc"