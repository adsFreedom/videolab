"""Просмотрщики файлов."""
from desktop.viewers.registry import ViewerRegistry
from desktop.viewers.viewer_window import ViewerWindow


def register_default_viewers() -> None:
    from desktop.viewers.video import VideoViewer
    from desktop.viewers.image import ImageViewer

    ViewerRegistry.register(
        [".avi", ".mp4", ".mov", ".mkv", ".webm"],
        VideoViewer,
    )
    ViewerRegistry.register(
        [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif"],
        ImageViewer,
    )


__all__ = ["ViewerRegistry", "ViewerWindow", "register_default_viewers"]