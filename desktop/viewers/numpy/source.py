"""Источник numpy-данных."""
from pathlib import Path
import numpy as np


class NumpySource:
    """Загрузка и хранение numpy-массива."""

    def __init__(self):
        self._file_path: str = ""
        self._array: np.ndarray | None = None

    def open(self, file_path: str) -> bool:
        """Загружает .npy файл."""
        path = Path(file_path)
        if not path.exists():
            return False

        try:
            if path.suffix.lower() == ".npz":
                data = np.load(str(path))
                # Берём первый массив из npz
                keys = list(data.keys())
                if not keys:
                    return False
                self._array = data[keys[0]]
            else:
                self._array = np.load(str(path))
        except Exception:
            return False

        self._file_path = file_path
        return True

    def close(self) -> None:
        self._file_path = ""
        self._array = None

    @property
    def is_open(self) -> bool:
        return self._array is not None

    @property
    def file_path(self) -> str:
        return self._file_path

    @property
    def file_name(self) -> str:
        return Path(self._file_path).name if self._file_path else ""

    @property
    def array(self) -> np.ndarray | None:
        return self._array

    @property
    def shape(self) -> tuple:
        return self._array.shape if self._array is not None else ()

    @property
    def dtype(self) -> str:
        return str(self._array.dtype) if self._array is not None else ""

    @property
    def ndim(self) -> int:
        return self._array.ndim if self._array is not None else 0

    @property
    def size(self) -> int:
        return int(self._array.size) if self._array is not None else 0

    def get_stats(self) -> dict:
        """Статистика массива."""
        if self._array is None:
            return {}
        arr = self._array.astype(np.float64)
        return {
            "min": float(arr.min()),
            "max": float(arr.max()),
            "mean": float(arr.mean()),
            "std": float(arr.std()),
        }