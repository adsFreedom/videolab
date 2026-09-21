"""Построение контекстного меню дерева."""
from pathlib import Path

from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction

from core.utils import load_yaml
from desktop.tree.model import ROLE_PATH


def build_context_menu(panel, pos) -> None:
    """
    Строит и показывает контекстное меню.
    Если есть активная обработка — показываем ЕДИНОЕ меню отмены.
    """
    # --- Если есть активная обработка — единое меню отмены ---
    if panel._current_context is not None:
        _build_cancel_menu(panel, pos)
        return

    # --- Обычное меню ---
    _build_normal_menu(panel, pos)


def _build_cancel_menu(panel, pos) -> None:
    """Единое меню отмены обработки. Показывается для любого узла."""
    context = panel._current_context

    # Название обработчика — из YAML обрабатываемого узла
    node_path = context.node_path
    node_name = Path(node_path).name
    title_text = f"Отменить обработку: {node_name}"

    try:
        node_data = load_yaml(
            Path(node_path) / f"{Path(node_path).name}.yaml"
        )
        processor_name = node_data.get("processor", "")
        # Иконка и display_name — из процессора, если можем
        from core.processors import ProcessorRegistry
        try:
            proc_cls = ProcessorRegistry.get(processor_name)
            icon = proc_cls.icon
            display_name = proc_cls.display_name
            title_text = f"Отменить: {icon} {display_name}"
        except KeyError:
            pass
    except Exception:
        pass

    menu = QMenu(panel)

    cancel_action = QAction(f"❌ {title_text}", panel)
    cancel_action.triggered.connect(panel.actions.cancel_processing)
    menu.addAction(cancel_action)

    menu.exec(panel.tree_view.mapToGlobal(pos))


def _build_normal_menu(panel, pos) -> None:
    """Обычное контекстное меню для узла."""
    tree_view = panel.tree_view
    index = tree_view.indexAt(pos)
    if not index.isValid():
        return

    # Приводим к нулевой колонке
    index = panel.model.index(index.row(), 0, index.parent())

    item = panel.model.itemFromIndex(index)
    if not item:
        return
    node_path = item.data(ROLE_PATH) or ""
    if not node_path:
        return

    node_path_obj = Path(node_path)
    yaml_path = node_path_obj / f"{node_path_obj.name}.yaml"
    node_data = load_yaml(yaml_path)
    processor_type = node_data.get("processor", "")

    menu = QMenu(panel)

    if processor_type != "source":
        rescan_action = QAction("🔄 Пересчитать", panel)
        rescan_action.triggered.connect(
            lambda: panel.actions.rescan_node(node_path)
        )
        menu.addAction(rescan_action)

    add_processor_action = QAction("➕ Добавить обработчик", panel)
    add_processor_action.triggered.connect(
        lambda: panel.actions.add_processor(node_path)
    )
    menu.addAction(add_processor_action)

    menu.addSeparator()

    open_folder_action = QAction("📂 Открыть в проводнике", panel)
    open_folder_action.triggered.connect(
        lambda: panel.actions.open_in_explorer(node_path)
    )
    menu.addAction(open_folder_action)

    if processor_type != "source":
        delete_action = QAction("❌ Удалить узел", panel)
        delete_action.triggered.connect(
            lambda: panel.actions.delete_node(node_path)
        )
        menu.addAction(delete_action)

    menu.exec(tree_view.mapToGlobal(pos))