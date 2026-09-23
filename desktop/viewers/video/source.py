"""Источник видео — обёртка над OpenCV. Без Qt."""
from dataclasses import dataclass
from pathlib import Path
import cv2
import numpy as np


@dataclass
class VideoInfo:
    """Метаданные видео."""
    path: str
    frame_count: int
    fps: float
    width: int
    height: int
    duration: float


class VideoSource:
    """Источник видео на базе cv2.VideoCapture."""

    def __init__(self):
        self._cap: cv2.VideoCapture | None = None
        self._info: VideoInfo | None = None
        self._current_frame: int = 0

    # ==================== ЗАГРУЗКА ====================

    def open(self, file_path: str) -> bool:
        """Открывает видеофайл. Возвращает True при успехе."""
        self.close()

        if not Path(file_path).exists():
            return False

        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return False

        self._cap = cap

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        duration = frame_count / fps if fps > 0 else 0.0

        self._info = VideoInfo(
            path=file_path,
            frame_count=frame_count,
            fps=fps,
            width=width,
            height=height,
            duration=duration,
        )
        self._current_frame = 0
        return True

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._info = None
        self._current_frame = 0

    # ==================== ИНФОРМАЦИЯ ====================

    @property
    def info(self) -> VideoInfo | None:
        return self._info

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def file_path(self) -> str:
        return self._info.path if self._info else ""

    @property
    def file_name(self) -> str:
        return Path(self._info.path).name if self._info else ""

    @property
    def frame_count(self) -> int:
        return self._info.frame_count if self._info else 0

    @property
    def fps(self) -> float:
        return self._info.fps if self._info else 0.0

    @property
    def width(self) -> int:
        return self._info.width if self._info else 0

    @property
    def height(self) -> int:
        return self._info.height if self._info else 0

    @property
    def duration(self) -> float:
        return self._info.duration if self._info else 0.0

    @property
    def current_frame(self) -> int:
        return self._current_frame

    # ==================== ДОСТУП К КАДРАМ ====================

    def get_frame(self, frame_index: int) -> np.ndarray | None:
        """Возвращает кадр по индексу (BGR)."""
        if not self.is_open:
            return None

        frame_index = max(0, min(frame_index, self.frame_count - 1))

        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = self._cap.read()

        if not ret:
            return None

        self._current_frame = frame_index
        return frame

    def get_pixel(self, frame: np.ndarray, x: int, y: int) -> tuple[int, int, int]:
        """Возвращает (r, g, b) пикселя в кадре."""
        if frame is None:
            return (0, 0, 0)

        h, w = frame.shape[:2]
        if x < 0 or x >= w or y < 0 or y >= h:
            return (0, 0, 0)

        b, g, r = frame[y, x]
        return (int(r), int(g), int(b))