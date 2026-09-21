"""Рабочий поток для обработки узла."""
import time
import traceback
from pathlib import Path

from PySide6.QtCore import QThread

from core.execution import ExecutionContext, CancelledError
from core.utils import save_yaml, timestamp


class ProcessingWorker:
    """
    Выполняет обработку узла. Не QObject — просто класс с методом run().
    Запускается из ProcessingThread.
    """

    def __init__(self, project, node_path: str, context: ExecutionContext):
        self.project = project
        self.node_path = node_path
        self.context = context

    def run(self) -> None:
        start_time = time.time()

        try:
            node_data = self.project.get_node_info(self.node_path)
            processor = self.project.get_node_processor(self.node_path)

            result = processor.run(
                input_files=node_data.get("input_files", {}),
                settings=node_data.get("settings", {}),
                output_dir=self.node_path,
                context=self.context,
            )

            duration = time.time() - start_time

            node_path_obj = Path(self.node_path)
            yaml_file = node_path_obj / f"{node_path_obj.name}.yaml"

            if result.get("output_files"):
                node_data["expected_outputs"] = result["output_files"]

            node_data["settings_snapshot"] = dict(node_data.get("settings", {}))
            node_data["input_files_snapshot"] = dict(node_data.get("input_files", {}))
            node_data["last_run_at"] = timestamp()
            node_data["last_duration_seconds"] = round(duration, 3)

            save_yaml(yaml_file, node_data)

            self.context.result = result
            self.context.done = True

        except CancelledError:
            self.context.cancelled = True
            self.context.done = True

        except Exception as e:
            self.context.error = str(e)
            self.context.traceback = traceback.format_exc()
            self.context.done = True


class ProcessingThread(QThread):
    """
    Поток, который просто выполняет worker.run() и завершается.

    Никакого moveToThread и event loop — мы не используем сигналы Qt
    между потоками. Когда worker.run() вернёт управление, поток завершится,
    и QThread.finished эмитится автоматически (Qt сам это делает).
    """

    def __init__(self, worker: ProcessingWorker, parent=None):
        super().__init__(parent)
        self.worker = worker

    def run(self) -> None:
        """Выполняется в новом потоке."""
        try:
            self.worker.run()
        except Exception as e:
            # На всякий случай — не даём потоку упасть молча
            print(f"ProcessingThread.run error: {e}", flush=True)