"""Действия над узлами дерева."""
from pathlib import Path
import subprocess
import sys

from PySide6.QtWidgets import QMessageBox

from core.logger import log
from core.project import ProjectManager
from core.processors import ProcessorRegistry
from core.utils import load_yaml
from core.execution import ExecutionContext
from core.progress_registry import progress_registry
from core.worker import ProcessingWorker, ProcessingThread
from desktop.dialogs.processor_chooser import ProcessorChooserDialog
from desktop.dialogs.error import ErrorDialog, show_current_exception


class TreeActions:
    """Набор действий над узлами."""

    def __init__(self, panel):
        self.panel = panel

    # ==================== ПЕРЕСЧЁТ ====================

    def rescan_node(self, node_path: str) -> None:
        project = self.panel.project
        if not project:
            return

        node_data = load_yaml(Path(node_path) / f"{Path(node_path).name}.yaml")
        processor_name = node_data.get("processor", "")
        try:
            processor_class = ProcessorRegistry.get(processor_name)
        except KeyError:
            log("ERROR", f"Обработчик '{processor_name}' не зарегистрирован")
            return

        log("INFO", f"Пересчёт узла: {node_path}")
        self.run_with_progress(node_path, processor_class)

    # ==================== ДОБАВЛЕНИЕ ====================

    def add_processor(self, node_path: str) -> None:
        project = self.panel.project
        if not project:
            return

        available = project.get_available_processors(node_path)

        if not available:
            QMessageBox.information(
                self.panel, "Обработчики",
                "Нет доступных обработчиков для этого узла.\n\n"
                "Возможно, отсутствуют подходящие входные файлы."
            )
            log("WARNING", f"Для узла {node_path} нет доступных обработчиков")
            return

        dialog = ProcessorChooserDialog(
            project=project,
            node_path=node_path,
            processors=available,
            parent=self.panel,
        )

        if dialog.exec() != ProcessorChooserDialog.Accepted:
            return

        processor_name = dialog.result_processor_name
        action = dialog.result_action

        log("INFO", f"Создание обработчика '{processor_name}' для узла {node_path}")

        try:
            new_node_path = project.create_processor_node(
                parent_path=node_path,
                processor_name=processor_name,
                input_files=dialog.result_input_files,
                settings=dialog.result_settings,
            )

            processor_class = ProcessorRegistry.get(processor_name)

            if action == ProcessorChooserDialog.ACTION_ADD_AND_RUN:
                self.run_with_progress(new_node_path, processor_class)
            else:
                log("SUCCESS", f"Обработчик создан (без обработки): {new_node_path}")
                self.panel.refresh()
        except Exception as e:
            error_msg = f"Ошибка обработчика '{processor_name}': {e}"
            log("ERROR", error_msg, exc_info=True)
            show_current_exception(self.panel, "Ошибка обработки", error_msg)

    # ==================== ЗАПУСК ОБРАБОТКИ ====================

    def run_with_progress(self, node_path: str, processor_class: type) -> None:
        node_name = Path(node_path).name

        context = ExecutionContext(node_path=node_path)
        progress_registry.set(node_path, 0, 0)

        # Точечное обновление только этого узла (⏳)
        if not self.panel.model.update_node_state(node_path):
            self.panel.refresh()

        self.panel.start_progress_updates()

        try:
            self.panel.main_window_ref.settings_panel.processor_tab.set_processing_state(True)
        except AttributeError:
            pass

        worker = ProcessingWorker(self.panel.project, node_path, context)
        thread = ProcessingThread(worker)

        self.panel._current_thread = thread
        self.panel._current_worker = worker
        self.panel._current_context = context

        def cleanup():
            self.panel._current_thread = None
            self.panel._current_worker = None
            self.panel._current_context = None

            try:
                self.panel.main_window_ref.settings_panel.processor_tab.set_processing_state(False)
            except AttributeError:
                pass

        def on_finished():
            # 1. Чистим registry и таймер
            progress_registry.clear(node_path)
            self.panel.stop_progress_updates()

            # 2. Обновляем узел И ВСЕХ его потомков
            #    (после обработки родителя дети каскадно краснеют)
            if not self.panel.model.update_node_and_descendants(node_path):
                self.panel.refresh()

            # 3. Сообщения
            if context.cancelled:
                log("WARNING", f"Обработка отменена: {node_path}")
                QMessageBox.information(
                    self.panel, "Отменено",
                    "Обработка была отменена пользователем."
                )
            elif context.error:
                error_msg = f"Ошибка обработки '{node_name}': {context.error}"
                tb = context.traceback or ""
                log("ERROR", f"{error_msg}\n\n{tb}")
                ErrorDialog.show_error(
                    self.panel, "Ошибка обработки",
                    f"{context.error}\n\n{tb}",
                )
            else:
                log("SUCCESS", f"Узел обработан: {node_path}")

            # 4. Обновляем панель настроек
            try:
                settings_panel = self.panel.main_window_ref.settings_panel
                settings_panel.load_node(settings_panel.current_node_path)
            except AttributeError:
                pass

            cleanup()

        thread.finished.connect(on_finished)
        thread.start()

    # ==================== ОТМЕНА ====================

    def cancel_processing(self) -> None:
        context = self.panel._current_context
        if context is None:
            return
        log("INFO", f"Запрос отмены обработки: {context.node_path}")
        context.cancel()

    # ==================== ПРОВОДНИК ====================

    def open_in_explorer(self, node_path: str) -> None:
        path = Path(node_path)
        if not path.exists():
            QMessageBox.warning(self.panel, "Ошибка", "Папка не существует")
            return
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    # ==================== УДАЛЕНИЕ ====================

    def delete_node(self, node_path: str) -> None:
        project = self.panel.project
        if not project:
            return

        descendants = project.get_descendants(node_path)

        if descendants:
            preview_lines = []
            for d in descendants[:10]:
                preview_lines.append(f"  • {Path(d).name}")
            if len(descendants) > 10:
                preview_lines.append(f"  ... и ещё {len(descendants) - 10}")

            msg = (
                f"Удалить узел «{Path(node_path).name}» и все его результаты?\n\n"
                f"Будут удалены следующие узлы:\n" + "\n".join(preview_lines)
            )
        else:
            msg = f"Удалить узел «{Path(node_path).name}»?"

        reply = QMessageBox.question(
            self.panel, "Удаление узла", msg,
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            project.delete_node(node_path)
            self.panel.tree_view.clearSelection()
            self.panel.refresh()
            self.panel.node_selected.emit("")
            log("INFO", f"Узел удален: {node_path}")
        except Exception as e:
            log("ERROR", f"Ошибка удаления узла: {e}", exc_info=True)
            show_current_exception(self.panel, "Ошибка удаления", str(e))