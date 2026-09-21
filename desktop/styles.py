"""Стили для приложения VideoLab."""

DARK_THEME = """
QMainWindow {
    background-color: #1e1e1e;
    color: #d4d4d4;
}

QWidget {
    background-color: #252526;
    color: #d4d4d4;
    font-family: "Segoe UI", "Ubuntu", sans-serif;
    font-size: 10pt;
}

QToolBar {
    background-color: #2d2d30;
    border: none;
    padding: 4px;
    spacing: 4px;
}

QToolButton {
    background-color: transparent;
    color: #d4d4d4;
    padding: 6px 12px;
    border: 1px solid transparent;
    border-radius: 3px;
}

QToolButton:hover {
    background-color: #3e3e42;
}

QToolButton:pressed {
    background-color: #007acc;
}

QTreeView, QListView {
    background-color: #1e1e1e;
    border: 1px solid #3e3e42;
    color: #d4d4d4;
    outline: none;
}

QTreeView::item:selected, QListView::item:selected {
    background-color: #094771;
    color: #ffffff;
}

QTreeView::item:hover, QListView::item:hover {
    background-color: #2a2d2e;
}

QTabWidget::pane {
    border: 1px solid #3e3e42;
    background-color: #252526;
}

QTabBar::tab {
    background-color: #2d2d30;
    color: #999999;
    padding: 6px 12px;
    border: 1px solid #3e3e42;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: #3e3e42;
    color: #ffffff;
    border-bottom: 1px solid #3e3e42;
}

QTabBar::tab:hover:!selected {
    background-color: #252526;
}

QSplitter::handle {
    background-color: #3e3e42;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

QStatusBar {
    background-color: #007acc;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #2d2d30;
    color: #d4d4d4;
    padding: 4px;
    border: none;
    border-right: 1px solid #3e3e42;
}

QPushButton {
    background-color: #0e639c;
    color: #ffffff;
    border: none;
    padding: 6px 16px;
    border-radius: 3px;
}

QPushButton:hover {
    background-color: #1177bb;
}

QPushButton:pressed {
    background-color: #0d5a8f;
}

QPushButton:disabled {
    background-color: #3e3e42;
    color: #666666;
}

QLabel {
    color: #d4d4d4;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #3c3c3c;
    color: #d4d4d4;
    border: 1px solid #3e3e42;
    padding: 4px;
    border-radius: 3px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #007acc;
}

QCheckBox {
    color: #d4d4d4;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
}

QProgressBar {
    background-color: #3c3c3c;
    border: 1px solid #3e3e42;
    border-radius: 3px;
    text-align: center;
    color: #d4d4d4;
}

QProgressBar::chunk {
    background-color: #0e639c;
}

QMenu {
    background-color: #2d2d30;
    color: #d4d4d4;
    border: 1px solid #3e3e42;
    padding: 4px 0px;
}

QMenu::item {
    background-color: transparent;
    padding: 6px 24px 6px 24px;
    border: none;
}

QMenu::item:selected {
    background-color: #094771;
    color: #ffffff;
}

QMenu::item:disabled {
    color: #666666;
}

QMenu::separator {
    height: 1px;
    background-color: #3e3e42;
    margin: 4px 8px;
}
"""


LIGHT_THEME = """
/* Заглушка для светлой темы. Позже заполним. */
"""