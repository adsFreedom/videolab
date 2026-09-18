"""Построение контекстного меню дерева."""
from pathlib import Path

from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction

from core.utils import load_yaml
from desktop.tree.model import ROLE_PATH


def build_context_menu(panel, pos) -> None:
    """
    Строит и показывает контекстное меню в позиции pos.
    panel — TreePanel, откуда берем tree_view и project.
    """
    tree_view = panel.tree_view
    index = tree_view.indexAt(pos)
    if not index.isValid():
        return

    item = panel.model.itemFromIndex(index)
    node_path = item.data(ROLE_PATH) or ""
    if not node_path:
        return

    node_path_obj = Path(node_path)
    yaml_path = node_path_obj / f"{node_path_obj.name}.yaml"
    node_data = load_yaml(yaml_path)
    processor_type = node_data.get("processor", "")

    menu = QMenu(panel)

    if processor_type != "source":
        rescan_action = QAction("Пересчитать", panel)
        rescan_action.triggered.connect(
            lambda: panel.actions.rescan_node(node_path)
        )
        menu.addAction(rescan_action)

    add_processor_action = QAction("Добавить обработчик", panel)
    add_processor_action.triggered.connect(
        lambda: panel.actions.add_processor(node_path)
    )
    menu.addAction(add_processor_action)

    menu.addSeparator()

    open_folder_action = QAction("Открыть в проводнике", panel)
    open_folder_action.triggered.connect(
        lambda: panel.actions.open_in_explorer(node_path)
    )
    menu.addAction(open_folder_action)

    if processor_type != "source":
        delete_action = QAction("Удалить узел", panel)
        delete_action.triggered.connect(
            lambda: panel.actions.delete_node(node_path)
        )
        menu.addAction(delete_action)

    menu.exec(tree_view.mapToGlobal(pos))