from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtWidgets import QWidget


class MiniGauge(QWidget):
    def __init__(self, value=0.0, color='#4CAF50', track='#444444', parent=None):
        super().__init__(parent)
        self._value = float(max(0.0, min(100.0, value)))
        self._color = QColor(color)
        self._track = QColor(track)
        self._textColor = QColor('#FFFFFF')
        self.setFixedSize(30, 30)
        self.setToolTip(f"{self._value:.0f}%")

    def sizeHint(self):
        return QSize(30, 30)

    def setValue(self, v):
        self._value = float(max(0.0, min(100.0, v)))
        self.setToolTip(f"{self._value:.0f}%")
        self.update()

    def setColor(self, c):
        self._color = QColor(c)
        self.update()

    def setTrack(self, c):
        self._track = QColor(c)
        self.update()

    def setTextColor(self, c):
        self._textColor = QColor(c)
        self.update()

    def paintEvent(self, event):
        d = min(self.width(), self.height())
        r = QRectF(2, 2, d - 4, d - 4)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        # Track
        pen = QPen(self._track, 4)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(r, 0, 360 * 16)
        # Value arc
        pen = QPen(self._color, 4)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        span = int(360.0 * (self._value / 100.0) * 16)
        # Start at 90 deg (top) going clockwise
        p.drawArc(r, 90 * 16, -span)
        # Centered percentage text
        try:
            p.setPen(self._textColor)
            f = QFont(self.font())
            f.setPixelSize(9)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter, f"{int(round(self._value))}%")
        except Exception:
            pass
        p.end()
