"""Источник изображения — обёртка над QImage. Без Qt-виджетов."""
from pathlib import Path
import numpy as np
from PySide6.QtGui import QImage


class ImageSource:
    """
    Источник изображения на базе QImage.

    Хранит:
    - numpy-массив (RGB или RGBA)
    - QImage для рендера
    - метаданные
    """

    def __init__(self):
        self._file_path: str = ""
        self._qimage: QImage | None = None
        self._array: np.ndarray | None = None
        self._has_alpha: bool = False

    # ==================== ЗАГРУЗКА ====================

    def open(self, file_path: str) -> bool:
        """Открывает файл изображения."""
        if not Path(file_path).exists():
            return False

        img = QImage(file_path)
        if img.isNull():
            return False

        self._file_path = file_path
        self._qimage = img
        self._array = self._qimage_to_numpy(img)
        self._has_alpha = img.hasAlphaChannel()
        return True

    def open_from_array(self, arr: np.ndarray, name: str = "crop") -> bool:
        """Открывает изображение из numpy-массива (для извлечённых областей)."""
        if arr is None or arr.size == 0:
            return False

        self._file_path = name
        self._array = arr.copy()

        # Создаём QImage для рендера
        if arr.ndim == 2:
            rgb = np.stack([arr, arr, arr], axis=-1)
        else:
            rgb = arr

        rgb = np.ascontiguousarray(rgb)
        h, w = rgb.shape[:2]

        # Формат RGB888 (3 канала). Если RGBA — обрезаем alpha.
        if rgb.shape[2] == 4:
            rgb = np.ascontiguousarray(rgb[:, :, :3])

        self._qimage = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        self._has_alpha = False
        return True

    def close(self) -> None:
        """Освобождает ресурсы."""
        self._file_path = ""
        self._qimage = None
        self._array = None
        self._has_alpha = False

    # ==================== ИНФОРМАЦИЯ ====================

    @property
    def is_open(self) -> bool:
        return self._qimage is not None and not self._qimage.isNull()

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def file_name(self) -> str:
        return Path(self._file_path).name if self._file_path else ""

    @property
    def width(self) -> int:
        return self._qimage.width() if self._qimage else 0

    @property
    def height(self) -> int:
        return self._qimage.height() if self._qimage else 0

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def format(self) -> str:
        if not self._file_path:
            return ""
        suffix = Path(self._file_path).suffix.upper().lstrip(".")
        return suffix if suffix else "RAW"

    @property
    def has_alpha(self) -> bool:
        return self._has_alpha

    @property
    def qimage(self) -> QImage | None:
        return self._qimage

    @property
    def array(self) -> np.ndarray | None:
        return self._array

    # ==================== КАНАЛЫ ====================

    def get_channel_array(self, channel: str) -> np.ndarray | None:
        """
        Возвращает numpy-массив (RGB, 3 канала) для указанного канала.
        channel: "RGB", "R", "G", "B", "A", "Y", "Gray"
        """
        if self._array is None:
            return None

        arr = self._array

        if channel == "RGB":
            if arr.ndim == 2:
                return self._gray_to_rgb(arr)
            if arr.shape[2] == 4:
                return arr[:, :, :3].copy()
            return arr.copy()

        if channel in ("R", "G", "B"):
            if arr.ndim == 2:
                return self._gray_to_rgb(arr)
            idx = {"R": 0, "G": 1, "B": 2}[channel]
            if arr.shape[2] > idx:
                return self._gray_to_rgb(arr[:, :, idx])
            return None

        if channel == "A":
            if arr.ndim == 3 and arr.shape[2] == 4:
                return self._gray_to_rgb(arr[:, :, 3])
            return None

        if channel in ("Y", "Gray"):
            if arr.ndim == 2:
                return self._gray_to_rgb(arr)
            if arr.shape[2] >= 3:
                r = arr[:, :, 0].astype(np.float32)
                g = arr[:, :, 1].astype(np.float32)
                b = arr[:, :, 2].astype(np.float32)
                y = (0.299 * r + 0.587 * g + 0.114 * b).astype(np.uint8)
                return self._gray_to_rgb(y)
            return None

        return None

    def get_rgb_at(self, x: int, y: int) -> tuple[int, int, int]:
        """Возвращает (r, g, b) в точке. Границы проверяются."""
        if self._array is None:
            return (0, 0, 0)

        h, w = self._array.shape[:2]
        if x < 0 or x >= w or y < 0 or y >= h:
            return (0, 0, 0)

        arr = self._array
        if arr.ndim == 2:
            v = int(arr[y, x])
            return (v, v, v)

        r = int(arr[y, x, 0])
        g = int(arr[y, x, 1]) if arr.shape[2] > 1 else r
        b = int(arr[y, x, 2]) if arr.shape[2] > 2 else r
        return (r, g, b)

    # ==================== ГИСТОГРАММА ====================

    def get_histogram_data(self) -> dict[str, np.ndarray]:
        """
        Возвращает данные гистограммы:
        {"R": array(256), "G": ..., "B": ..., "Y": ...}
        """
        result = {}
        if self._array is None:
            return result

        arr = self._array

        if arr.ndim == 2:
            hist = np.bincount(arr.flatten(), minlength=256)[:256]
            result["R"] = hist
            result["G"] = hist
            result["B"] = hist
            result["Y"] = hist
            return result

        r = arr[:, :, 0]
        g = arr[:, :, 1] if arr.shape[2] > 1 else r
        b = arr[:, :, 2] if arr.shape[2] > 2 else r

        result["R"] = np.bincount(r.flatten(), minlength=256)[:256]
        result["G"] = np.bincount(g.flatten(), minlength=256)[:256]
        result["B"] = np.bincount(b.flatten(), minlength=256)[:256]

        y = (0.299 * r.astype(np.float32) +
             0.587 * g.astype(np.float32) +
             0.114 * b.astype(np.float32)).astype(np.uint8)
        result["Y"] = np.bincount(y.flatten(), minlength=256)[:256]

        return result

    # ==================== ВНУТРЕННИЕ ====================

    @staticmethod
    def _qimage_to_numpy(qimg: QImage) -> np.ndarray:
        """QImage → numpy (RGB или RGBA)."""
        if qimg.format() not in (QImage.Format_RGB888, QImage.Format_RGBA8888):
            qimg = qimg.convertToFormat(QImage.Format_RGBA8888)

        width = qimg.width()
        height = qimg.height()

        if qimg.format() == QImage.Format_RGBA8888:
            ptr = qimg.constBits()
            arr = np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 4))
            if np.all(arr[:, :, 3] == 255):
                return arr[:, :, :3].copy()
            return arr.copy()

        ptr = qimg.constBits()
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 3))
        return arr.copy()

    @staticmethod
    def _gray_to_rgb(gray: np.ndarray) -> np.ndarray:
        """2D → 3D RGB."""
        return np.stack([gray, gray, gray], axis=-1)