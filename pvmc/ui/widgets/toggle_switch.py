from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox


class ToggleSwitch(QCheckBox):
    def __init__(self, parent=None):
        super().__init__('', parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setChecked(False)
        self.toggled.connect(self._apply)
        self._apply()

    def sizeHint(self):
        sh = super().sizeHint()
        return sh.expandedTo(sh)

    def _apply(self):
        on = self.isChecked()
        bg = '#2ECC71' if on else '#E74C3C'  # green/red
        # Simple pill style switch using checkbox base
        self.setStyleSheet(
            f"QCheckBox {{ background-color: {bg}; border-radius: 12px; padding: 0px; min-width: 46px; min-height: 24px; }}\n"
            "QCheckBox::indicator { width: 0; height: 0; }\n"
        )

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        self._apply()
