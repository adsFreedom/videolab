"""Утилиты для работы с файлами в UI."""
from pathlib import Path

# Расширения → (иконка, категория)
FILE_TYPES = {
    # Видео
    ".avi": ("🎬", "video"),
    ".mp4": ("🎬", "video"),
    ".mov": ("🎬", "video"),
    ".mkv": ("🎬", "video"),
    ".webm": ("🎬", "video"),

    # Изображения
    ".png": ("🖼️", "image"),
    ".jpg": ("🖼️", "image"),
    ".jpeg": ("🖼️", "image"),
    ".bmp": ("🖼️", "image"),
    ".tiff": ("🖼️", "image"),
    ".gif": ("🖼️", "image"),

    # Numpy
    ".npy": ("📊", "numpy"),
    ".npz": ("📊", "numpy"),

    # Текст
    ".yaml": ("📄", "text"),
    ".yml": ("📄", "text"),
    ".json": ("📄", "text"),
    ".txt": ("📄", "text"),
    ".log": ("📄", "text"),
    ".csv": ("📄", "text"),
    ".md": ("📄", "text"),
}


def get_file_icon(filename: str) -> str:
    """Возвращает эмодзи-иконку для файла."""
    ext = Path(filename).suffix.lower()
    return FILE_TYPES.get(ext, ("📎", "unknown"))[0]


def get_file_category(filename: str) -> str:
    """Возвращает категорию файла (video, image, numpy, text, unknown)."""
    ext = Path(filename).suffix.lower()
    return FILE_TYPES.get(ext, ("📎", "unknown"))[1]


def format_size(size_bytes: int) -> str:
    """Форматирует размер файла в читаемый вид."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"