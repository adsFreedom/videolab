"""Виджет для генерации формы из settings_schema."""
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QSpinBox, QDoubleSpinBox, QCheckBox,
    QLineEdit, QComboBox, QLabel,
)
from PySide6.QtCore import Signal


class SchemaForm(QWidget):
    """
    Динамическая форма, генерируемая из settings_schema.

    settings_schema = {
        "start_frame": {
            "type": "spinbox",
            "label": "Начальный кадр",
            "default": 0,
            "min": 0,
            "max": 1000,
            "step": 1,
            "tooltip": "..."
        },
        ...
    }
    """

    value_changed = Signal()

    def __init__(self, schema: dict, parent=None):
        super().__init__(parent)
        self.schema = schema
        self.widgets: dict[str, QWidget] = {}

        layout = QFormLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        for key, param in schema.items():
            widget = self._create_widget(key, param)
            if widget is None:
                continue

            self.widgets[key] = widget

            label_text = param.get("label", key)
            label = QLabel(label_text)

            tooltip = param.get("tooltip", "")
            if tooltip:
                label.setToolTip(tooltip)
                widget.setToolTip(tooltip)

            layout.addRow(label, widget)

    def _create_widget(self, key: str, param: dict) -> QWidget | None:
        """Создает виджет по типу из схемы."""
        ptype = param.get("type", "lineedit")
        default = param.get("default")

        if ptype == "spinbox":
            w = QSpinBox()
            w.setMinimum(param.get("min", -2_147_483_648))
            w.setMaximum(param.get("max", 2_147_483_647))
            w.setSingleStep(param.get("step", 1))
            if default is not None:
                w.setValue(int(default))
            # Лямбда игнорирует аргумент int, который передает Qt
            w.valueChanged.connect(lambda _: self.value_changed.emit())
            return w

        elif ptype == "double_spinbox":
            w = QDoubleSpinBox()
            w.setMinimum(param.get("min", -1e9))
            w.setMaximum(param.get("max", 1e9))
            w.setSingleStep(param.get("step", 0.1))
            w.setDecimals(param.get("decimals", 3))
            if default is not None:
                w.setValue(float(default))
            w.valueChanged.connect(lambda _: self.value_changed.emit())
            return w

        elif ptype == "checkbox":
            w = QCheckBox()
            if default is not None:
                w.setChecked(bool(default))
            # stateChanged передает int
            w.stateChanged.connect(lambda _: self.value_changed.emit())
            return w

        elif ptype == "lineedit":
            w = QLineEdit()
            if default is not None:
                w.setText(str(default))
            # textChanged передает str
            w.textChanged.connect(lambda _: self.value_changed.emit())
            return w

        elif ptype == "combobox":
            w = QComboBox()
            options = param.get("options", [])
            w.addItems([str(o) for o in options])
            if default is not None and default in options:
                w.setCurrentText(str(default))
            # currentTextChanged передает str
            w.currentTextChanged.connect(lambda _: self.value_changed.emit())
            return w

        return None

    def get_values(self) -> dict:
        """Возвращает текущие значения формы."""
        values = {}
        for key, widget in self.widgets.items():
            if isinstance(widget, QSpinBox):
                values[key] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                values[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                values[key] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                values[key] = widget.text()
            elif isinstance(widget, QComboBox):
                values[key] = widget.currentText()
        return values

    def set_values(self, values: dict) -> None:
        """Устанавливает значения формы."""
        for key, value in values.items():
            if key not in self.widgets:
                continue
            widget = self.widgets[key]
            if isinstance(widget, QSpinBox):
                widget.setValue(int(value))
            elif isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(value))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))
            elif isinstance(widget, QComboBox):
                widget.setCurrentText(str(value))

    def validate(self) -> tuple[bool, str]:
        """Проверяет валидность значений формы."""
        return True, ""