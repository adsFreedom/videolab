"""Источник изображения — обёртка над QImage. Без Qt-виджетов."""
from pathlib import Path
import numpy as np
import cv2
from PySide6.QtGui import QImage


class ImageSource:
    """
    Источник изображения на базе QImage.

    Хранит:
    - numpy-массив (RGB или RGBA) — в исходном виде
    - QImage для рендера
    - метаданные
    """

    def __init__(self):
        self._file_path: str = ""
        self._qimage: QImage | None = None
        self._array_rgb: np.ndarray | None = None  # всегда RGB или RGBA
        self._has_alpha: bool = False

    # ==================== ЗАГРУЗКА ====================

    def open(self, file_path: str) -> bool:
        if not Path(file_path).exists():
            return False

        img = QImage(file_path)
        if img.isNull():
            return False

        self._file_path = file_path
        self._qimage = img
        self._array_rgb = self._qimage_to_numpy(img)
        self._has_alpha = img.hasAlphaChannel()
        return True

    def open_from_array(self, arr: np.ndarray, name: str = "crop") -> bool:
        if arr is None or arr.size == 0:
            return False

        self._file_path = name

        # Приводим к RGB
        if arr.ndim == 2:
            self._array_rgb = np.stack([arr, arr, arr], axis=-1)
        else:
            self._array_rgb = arr.copy()

        rgb = self._array_rgb
        if rgb.shape[2] == 4:
            rgb = np.ascontiguousarray(rgb[:, :, :3])
        else:
            rgb = np.ascontiguousarray(rgb)

        h, w = rgb.shape[:2]
        self._qimage = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        self._has_alpha = False
        return True

    def close(self) -> None:
        self._file_path = ""
        self._qimage = None
        self._array_rgb = None
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
        return self._array_rgb

    # ==================== ЦВЕТОВЫЕ ПРОСТРАНСТВА ====================

    def _get_array_in_space(self, space: str) -> np.ndarray | None:
        """
        Возвращает массив в заданном пространстве.
        space: "RGB" | "HSV" | "LAB" | "YUV"
        """
        if self._array_rgb is None:
            return None

        arr = self._array_rgb

        # Grayscale — оставляем как есть
        if arr.ndim == 2:
            arr = np.stack([arr, arr, arr], axis=-1)

        # RGBA → RGB для конвертации
        if arr.shape[2] == 4:
            arr = arr[:, :, :3]

        if space == "RGB":
            return arr.copy()

        # cv2 требует uint8 для конвертации
        if arr.dtype != np.uint8:
            arr = arr.astype(np.uint8)

        if space == "HSV":
            return cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
        if space == "LAB":
            return cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
        if space == "YUV":
            # cv2.COLOR_RGB2YUV возвращает YUV с диапазоном 0-255
            return cv2.cvtColor(arr, cv2.COLOR_RGB2YUV)

        return arr.copy()

    def _space_to_rgb_for_display(self, arr: np.ndarray, space: str) -> np.ndarray:
        """
        Конвертирует массив обратно в RGB для отображения.
        Для HSV / LAB / YUV — чтобы видеть «эффект пространства».
        """
        if space == "RGB":
            return arr

        arr = arr.astype(np.uint8)
        if space == "HSV":
            return cv2.cvtColor(arr, cv2.COLOR_HSV2RGB)
        if space == "LAB":
            return cv2.cvtColor(arr, cv2.COLOR_LAB2RGB)
        if space == "YUV":
            return cv2.cvtColor(arr, cv2.COLOR_YUV2RGB)
        return arr

    def get_channel_array(self, channel: str, space: str = "RGB") -> np.ndarray | None:
        """
        Возвращает numpy-массив (RGB, 3 канала) для отображения.

        channel:
            - "RGB" / "HSV" / "LAB" / "YUV" — полное (в пространстве space)
            - одиночные каналы: R, G, B, A, H, S, V, L, a, b, Y, U, V, Gray
        space: "RGB" | "HSV" | "LAB" | "YUV"
        """
        arr = self._get_array_in_space(space)
        if arr is None:
            return None

        # Полное пространство — конвертируем обратно для отображения
        if channel == space:
            rgb_display = self._space_to_rgb_for_display(arr, space)
            return rgb_display

        # Одиночные каналы
        if arr.ndim == 2:
            return self._gray_to_rgb(arr)

        # Определяем индекс канала в текущем пространстве
        channel_maps = {
            "RGB": {"R": 0, "G": 1, "B": 2},
            "HSV": {"H": 0, "S": 1, "V": 2},
            "LAB": {"L": 0, "a": 1, "b": 2},
            "YUV": {"Y": 0, "U": 1, "V": 2},
        }

        idx = channel_maps.get(space, {}).get(channel)
        if idx is None:
            return None

        if arr.shape[2] <= idx:
            return None

        gray = arr[:, :, idx]
        return self._gray_to_rgb(gray)

    def get_available_channels(self, space: str) -> list[str]:
        """Список доступных каналов для пространства."""
        if space == "RGB":
            channels = ["RGB"]
            if self._has_alpha:
                channels.append("A")
            channels.extend(["R", "G", "B", "Y", "Gray"])
            return channels

        if space == "HSV":
            return ["HSV", "H", "S", "V"]

        if space == "LAB":
            return ["LAB", "L", "a", "b"]

        if space == "YUV":
            return ["YUV", "Y", "U", "V"]

        return ["RGB"]

    # ==================== ПИПЕТКА ====================

    def get_rgb_at(self, x: int, y: int) -> tuple[int, int, int]:
        """Возвращает (r, g, b) в точке."""
        if self._array_rgb is None:
            return (0, 0, 0)

        h, w = self._array_rgb.shape[:2]
        if x < 0 or x >= w or y < 0 or y >= h:
            return (0, 0, 0)

        arr = self._array_rgb
        if arr.ndim == 2:
            v = int(arr[y, x])
            return (v, v, v)

        r = int(arr[y, x, 0])
        g = int(arr[y, x, 1]) if arr.shape[2] > 1 else r
        b = int(arr[y, x, 2]) if arr.shape[2] > 2 else r
        return (r, g, b)

    # ==================== ГИСТОГРАММА ====================

    def get_histogram_data(self, space: str = "RGB") -> dict[str, np.ndarray]:
        """
        Возвращает данные гистограммы в указанном пространстве.
        Для RGB — R, G, B, Y.
        Для HSV — H, S, V.
        И т.д.
        """
        result = {}

        if space == "RGB":
            arr = self._array_rgb
            if arr is None:
                return result
            if arr.ndim == 2:
                hist = np.bincount(arr.flatten(), minlength=256)[:256]
                return {"R": hist, "G": hist, "B": hist, "Y": hist}

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

        # Для других пространств
        arr = self._get_array_in_space(space)
        if arr is None:
            return result

        if arr.ndim == 2:
            hist = np.bincount(arr.flatten(), minlength=256)[:256]
            return {"R": hist, "G": hist, "B": hist, "Y": hist}

        keys = {
            "HSV": ["H", "S", "V"],
            "LAB": ["L", "a", "b"],
            "YUV": ["Y", "U", "V"],
        }.get(space, ["R", "G", "B"])

        for i, key in enumerate(keys):
            if arr.shape[2] > i:
                result[key] = np.bincount(arr[:, :, i].flatten(), minlength=256)[:256]

        return result

    # ==================== ВНУТРЕННИЕ ====================

    @staticmethod
    def _qimage_to_numpy(qimg: QImage) -> np.ndarray:
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
        return np.stack([gray, gray, gray], axis=-1)