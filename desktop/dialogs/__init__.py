"""Диалоги."""
from desktop.dialogs.processor_dialog import ProcessorChooserDialog
from desktop.dialogs.progress_dialog import ProgressDialog
from desktop.dialogs.error import ErrorDialog, show_current_exception

__all__ = [
    "ProcessorChooserDialog",
    "ProgressDialog",
    "ErrorDialog",
    "show_current_exception",
]