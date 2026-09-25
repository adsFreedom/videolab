"""Утилиты для работы с проектом в контексте CSP."""
from pathlib import Path


def find_frames_source(start_dir: Path) -> Path | None:
    """
    Ищет ближайший узел вверх по дереву с meta.yaml + frames/.
    """
    current = Path(start_dir).resolve()
    while True:
        meta = current / "meta.yaml"
        frames = current / "frames"
        if meta.exists() and frames.is_dir():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent