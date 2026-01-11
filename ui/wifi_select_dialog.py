from typing import List, Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class WifiSelectDialog(QDialog):
    def __init__(self, wifi_names: List[str], parent=None) -> None:
        super().__init__(parent)
        self._selected: Optional[str] = None

        self.setWindowTitle("选择 WiFi")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("请选择要查看的 WiFi：", self))

        for name in wifi_names:
            button = QPushButton(name, self)
            button.clicked.connect(lambda checked=False, value=name: self._pick(value))
            layout.addWidget(button)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel, parent=self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected(self) -> Optional[str]:
        return self._selected

    def _pick(self, value: str) -> None:
        self._selected = value
        self.accept()
