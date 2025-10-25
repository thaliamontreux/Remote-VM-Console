import re

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLineEdit, QColorDialog


_HEX_RE = re.compile(r'^#?[0-9A-Fa-f]{6}$')


class ColorField(QWidget):
    changed = Signal(str)

    def __init__(self, value='#2f2f45', parent=None):
        super().__init__(parent)
        self._value = self._normalize(value)
        self.btn = QPushButton()
        self.btn.setFixedWidth(36)
        self.btn.clicked.connect(self._choose)
        self.edit = QLineEdit(self._value)
        self.edit.editingFinished.connect(self._edited)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.btn)
        lay.addWidget(self.edit)
        self._apply()

    def _normalize(self, s):
        if not s:
            return '#000000'
        if not s.startswith('#'):
            s = '#' + s
        return s[:7]

    def _apply(self):
        self.edit.setText(self._value)
        self.btn.setStyleSheet(f'background: {self._value}; border: 1px solid #444; border-radius: 4px;')

    def _choose(self):
        col = QColorDialog.getColor(QColor(self._value), self)
        if col.isValid():
            self._value = col.name().upper()
            self._apply()
            self.changed.emit(self._value)

    def _edited(self):
        text = self.edit.text().strip()
        if _HEX_RE.match(text or ''):
            self._value = self._normalize(text).upper()
            self._apply()
            self.changed.emit(self._value)
        else:
            self._apply()

    def value(self):
        return self._value

    def setValue(self, val):
        self._value = self._normalize(val).upper()
        self._apply()
