"""Диалоги."""
from desktop.dialogs.processor_chooser import ProcessorChooserDialog
from desktop.dialogs.error import ErrorDialog, show_current_exception

__all__ = [
    "ProcessorChooserDialog",
    "ErrorDialog",
    "show_current_exception",
]