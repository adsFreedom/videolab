"""Просмотрщики файлов."""
from desktop.viewers.registry import ViewerRegistry
from desktop.viewers.viewer_window import ViewerWindow


def register_default_viewers() -> None:
    """Регистрирует все встроенные просмотрщики."""
    from desktop.viewers.video import VideoViewer

    ViewerRegistry.register(
        [".avi", ".mp4", ".mov", ".mkv", ".webm"],
        VideoViewer,
    )


__all__ = ["ViewerRegistry", "ViewerWindow", "register_default_viewers"]