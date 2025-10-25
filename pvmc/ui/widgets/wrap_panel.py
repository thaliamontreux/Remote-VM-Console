import logging
import traceback

from PySide6.QtCore import QRect, QPoint, QSize
from PySide6.QtWidgets import QWidget


class WrapPanel(QWidget):
    def __init__(self, parent=None, margin=8, hspacing=8, vspacing=8):
        super().__init__(parent)
        self.margin = margin
        self.hspacing = hspacing
        self.vspacing = vspacing
        self.setContentsMargins(margin, margin, margin, margin)
        self._children = []

    def addWidget(self, w):
        try:
            w.setParent(self)
            w.show()
            self._children.append(w)
            self._layout_children()
            self.update()
        except Exception as e:
            logging.error(f"[WRAP] addWidget error: {type(e).__name__}: {e}")
            traceback.print_exc()

    def clear(self):
        try:
            for w in self._children:
                try:
                    w.setParent(None)
                    w.deleteLater()
                except Exception:
                    pass
            self._children.clear()
            self._layout_children()
            self.update()
        except Exception as e:
            logging.error(f"[WRAP] clear error: {type(e).__name__}: {e}")
            traceback.print_exc()

    def count(self):
        return len(self._children)

    def _children_iter(self):
        for w in self._children:
            if w is None:
                continue
            if not w.isVisible():
                continue
            yield w

    def _layout_children(self):
        try:
            m = self.contentsMargins()
            l, t, r, b = m.left(), m.top(), m.right(), m.bottom()
            area = self.rect().adjusted(l, t, -r, -b)
            x = area.x()
            y = area.y()
            line_h = 0
            right = area.right()
            for w in self._children_iter():
                try:
                    sz = w.size()
                    if sz.width() <= 0 or sz.height() <= 0:
                        hint = w.sizeHint()
                        w_w = max(1, hint.width())
                        w_h = max(1, hint.height())
                    else:
                        w_w = sz.width()
                        w_h = sz.height()
                    next_x = x + w_w + self.hspacing
                    if next_x - self.hspacing > right and line_h > 0:
                        x = area.x()
                        y = y + line_h + self.vspacing
                        next_x = x + w_w + self.hspacing
                        line_h = 0
                        logging.debug(f"[WRAP] wrap -> new row at y={y}")
                    w.setGeometry(QRect(QPoint(x, y), QSize(w_w, w_h)))
                    logging.debug(f"[WRAP] place widget id={id(w)} pos=({x},{y}) size=({w_w}x{w_h})")
                    x = next_x
                    line_h = max(line_h, w_h)
                except Exception as e:
                    logging.error(f"[WRAP] item layout error: {type(e).__name__}: {e}")
                    traceback.print_exc()
        except Exception as e:
            logging.error(f"[WRAP] layout error: {type(e).__name__}: {e}")
            traceback.print_exc()

    def resizeEvent(self, event):
        self._layout_children()
        super().resizeEvent(event)

    def showEvent(self, event):
        self._layout_children()
        super().showEvent(event)

    def sizeHint(self):
        try:
            m = self.contentsMargins()
            l, t, r, b = m.left(), m.top(), m.right(), m.bottom()
            return QSize(max(1, l + r + 1), max(1, t + b + 1))
        except Exception:
            return QSize(1, 1)

    def minimumSizeHint(self):
        return self.sizeHint()
