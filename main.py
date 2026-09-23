"""Точка входа VideoLab."""
import sys

from PySide6.QtWidgets import QApplication, QStyleFactory

# Регистрация обработчиков
from processors import crop, extract_frames  # noqa: F401

# Регистрация просмотрщиков
from desktop.viewers import register_default_viewers

from desktop.window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("VideoLab")
    app.setOrganizationName("VideoLab")

    app.setStyle(QStyleFactory.create("Fusion"))

    # Регистрируем просмотрщики
    register_default_viewers()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()