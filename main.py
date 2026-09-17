"""Точка входа VideoLab."""
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Регистрация обработчиков
from processors import crop, extract_frames  # noqa: F401

from desktop.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VideoLab")
    app.setOrganizationName("VideoLab")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()