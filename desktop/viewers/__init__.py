"""Просмотрщики файлов."""
from desktop.viewers.registry import ViewerRegistry
from desktop.viewers.viewer_window import ViewerWindow


def register_default_viewers() -> None:
    """Регистрирует все встроенные просмотрщики."""
    from desktop.viewers.video import VideoViewer
    from desktop.viewers.image import ImageViewer
    from desktop.viewers.numpy import NumpyViewer

    ViewerRegistry.register(
        [".avi", ".mp4", ".mov", ".mkv", ".webm"],
        VideoViewer,
    )
    ViewerRegistry.register(
        [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif"],
        ImageViewer,
    )
    ViewerRegistry.register(
        [".npy", ".npz"],
        NumpyViewer,
    )


__all__ = ["ViewerRegistry", "ViewerWindow", "register_default_viewers"]