"""Вкладка данных узла."""
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit

from core.project import ProjectManager


class DataTab(QWidget):
    """Вкладка с расшифровкой YAML-данных узла."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project: ProjectManager | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

    def set_project(self, project: ProjectManager) -> None:
        self.project = project

    def load_node(self, node_path: str, node_data: dict) -> None:
        """Заполняет вкладку данными узла."""
        lines = []

        lines.append(f"<b>Путь:</b> {node_path}")
        lines.append(f"<b>Обработчик:</b> {node_data.get('processor', '-')}")
        lines.append(f"<b>Создан:</b> {node_data.get('created', '-')}")

        input_files = node_data.get("input_files", {})
        input_snapshot = node_data.get("input_files_snapshot")
        if input_files:
            lines.append("<br><b>Входные файлы:</b>")
            for key, value in input_files.items():
                match = ""
                if input_snapshot is not None:
                    if input_snapshot.get(key) == value:
                        match = " (совпадает)"
                    else:
                        match = " ⚠ изменено"
                lines.append(f"  • {key}: {value}{match}")

        settings = node_data.get("settings", {})
        snapshot = node_data.get("settings_snapshot")
        if settings:
            lines.append("<br><b>Настройки:</b>")
            lines.append(f"  Текущие: {settings}")
            if snapshot is not None:
                lines.append(f"  Snapshot: {snapshot}")
                diffs = []
                all_keys = set(settings.keys()) | set(snapshot.keys())
                for key in sorted(all_keys):
                    old = snapshot.get(key, "(нет)")
                    new = settings.get(key, "(нет)")
                    if old != new:
                        diffs.append(f"    ⚠ {key}: было {old}, стало {new}")
                if diffs:
                    lines.append("<br><b>Различия:</b>")
                    lines.extend(diffs)
            else:
                lines.append("  <i>(snapshot отсутствует — узел не обработан)</i>")

        duration = node_data.get("last_duration_seconds")
        if duration is not None:
            lines.append(f"<br><b>Время последней обработки:</b> {duration} сек")

        last_run = node_data.get("last_run_at")
        if last_run:
            lines.append(f"<b>Последний запуск:</b> {last_run}")

        expected = node_data.get("expected_outputs")
        if expected:
            lines.append("<br><b>Ожидаемые выходы:</b>")
            for f in expected:
                exists = "OK" if (Path(node_path) / f).exists() else "MISS"
                lines.append(f"  [{exists}] {f}")

        if self.project:
            is_valid, msg = self.project.validate_node(node_path)
            status = "✅ Валидный" if is_valid else f"❌ {msg}"
            lines.append(f"<br><b>Статус:</b> {status}")

        self.text.setHtml("<br>".join(lines))

    def clear(self) -> None:
        self.text.clear()