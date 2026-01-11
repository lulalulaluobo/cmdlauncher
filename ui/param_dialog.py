from typing import Dict, List, Optional

from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
    QPushButton,
)

from core.models import ParamDefinition


class ParamDialog(QDialog):
    def __init__(self, title: str, params: List[ParamDefinition], parent=None) -> None:
        super().__init__(parent)
        self._params = params
        self._fields: Dict[str, QLineEdit] = {}
        self._choice_values: Dict[str, str] = {}

        self.setWindowTitle(title)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        has_standard_inputs = False

        for param in params:
            if param.ui == "buttons" and param.choices:
                button_row = QWidget(self)
                button_layout = QHBoxLayout(button_row)
                button_layout.setContentsMargins(0, 0, 0, 0)
                for choice in param.choices:
                    label = choice
                    if param.choice_labels and choice in param.choice_labels:
                        label = param.choice_labels[choice]
                    button = QPushButton(label, self)
                    button.clicked.connect(
                        lambda checked=False, pid=param.param_id, val=choice: self._pick_choice(pid, val)
                    )
                    button_layout.addWidget(button)
                form.addRow(QLabel(param.label), button_row)
                continue

            has_standard_inputs = True
            field = QLineEdit(self)
            if param.kind == "int":
                min_value = param.min_value if param.min_value is not None else 0
                max_value = param.max_value if param.max_value is not None else 2_147_483_647
                field.setValidator(QIntValidator(min_value, max_value, self))
            if param.default is not None:
                field.setPlaceholderText(str(param.default))
            elif param.choices:
                field.setPlaceholderText(" / ".join(param.choices))
            form.addRow(QLabel(param.label), field)
            self._fields[param.param_id] = field

        layout.addLayout(form)

        if has_standard_inputs:
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
            buttons.accepted.connect(self._on_accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)

    def values(self) -> Dict[str, str]:
        values = {key: field.text().strip() for key, field in self._fields.items()}
        values.update(self._choice_values)
        return values

    def _on_accept(self) -> None:
        errors = self._validate()
        if errors:
            QMessageBox.warning(self, "CmdLauncher", "\n".join(errors))
            return
        self.accept()

    def _validate(self) -> List[str]:
        errors: List[str] = []
        for param in self._params:
            if param.param_id in self._fields:
                value = self._fields[param.param_id].text().strip()
            else:
                value = self._choice_values.get(param.param_id, "")
            if param.required and not value:
                errors.append(f"{param.label} is required.")
                continue
            if param.kind == "int" and value:
                try:
                    number = int(value)
                except ValueError:
                    errors.append(f"{param.label} must be an integer.")
                    continue
                if param.min_value is not None and number < param.min_value:
                    errors.append(f"{param.label} must be >= {param.min_value}.")
                if param.max_value is not None and number > param.max_value:
                    errors.append(f"{param.label} must be <= {param.max_value}.")
            if param.choices and value:
                if value not in param.choices:
                    allowed = ", ".join(param.choices)
                    errors.append(f"{param.label} must be one of: {allowed}.")
        return errors

    def _pick_choice(self, param_id: str, value: str) -> None:
        self._choice_values[param_id] = value
        self.accept()
