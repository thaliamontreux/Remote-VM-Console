import logging
import traceback
import shiboken6

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QSizePolicy, QWidgetItem


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=6, hspacing=6, vspacing=6):
        super().__init__(parent)
        self._itemList = []
        self._hspace = hspacing
        self._vspace = vspacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._itemList.append(item)
        try:
            wid = item.widget()
        except Exception:
            wid = None
        # Ensure layout list stays clean when widgets are destroyed
        if wid is not None:
            try:
                wid.destroyed.connect(lambda _=None, it=item: self._remove_item(it))
            except Exception:
                pass
    
    def addWidget(self, widget):
        self.addItem(QWidgetItem(widget))

    def count(self):
        return len(self._itemList)

    def itemAt(self, index):
        if 0 <= index < len(self._itemList):
            return self._itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._itemList):
            return self._itemList.pop(index)
        return None

    def _remove_item(self, item):
        try:
            if item in self._itemList:
                self._itemList.remove(item)
        except Exception:
            pass

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return False

    def heightForWidth(self, width):
        try:
            return self._doLayout(QRect(0, 0, width, 0), True)
        except Exception as e:
            logging.error(f"[FLOW] heightForWidth error: {e}")
            traceback.print_exc()
            return 0

    def setGeometry(self, rect):
        super().setGeometry(rect)
        try:
            self._doLayout(rect, False)
        except Exception as e:
            logging.error(f"[FLOW] setGeometry error: {e}")
            traceback.print_exc()

    def sizeHint(self):
        try:
            l, t, r, b = self.getContentsMargins()
            # Conservative non-zero size independent of child widgets
            return QSize(max(1, l + r + 1), max(1, t + b + 1))
        except Exception as e:
            logging.error(f"[FLOW] sizeHint error: {e}")
            traceback.print_exc()
            return QSize(1, 1)

    def minimumSize(self):
        try:
            l, t, r, b = self.getContentsMargins()
            return QSize(max(1, l + r + 1), max(1, t + b + 1))
        except Exception as e:
            logging.error(f"[FLOW] minimumSize error: {e}")
            traceback.print_exc()
            return QSize(1, 1)

    def _smartSpacing(self, pm):
        return self._hspace if pm == 0 else self._vspace

    def _doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        l, t, r, b = self.getContentsMargins()
        effective_rect = rect.adjusted(l, t, -r, -b)
        x = effective_rect.x()
        y = effective_rect.y()
        lineHeight = 0

        # Iterate over a copy to avoid concurrent modification issues
        for item in list(self._itemList):
            try:
                wid = None
                try:
                    wid = item.widget()
                except Exception:
                    wid = None
                if wid is None:
                    continue
                try:
                    if not shiboken6.isValid(wid):
                        # Drop invalid widgets from layout
                        self._remove_item(item)
                        continue
                except Exception:
                    # If isValid is not available, best-effort proceed
                    pass

                spaceX = self._hspace
                spaceY = self._vspace
                hint = wid.sizeHint()
                nextX = x + hint.width() + spaceX
                if nextX - spaceX > effective_rect.right() and lineHeight > 0:
                    x = effective_rect.x()
                    y = y + lineHeight + spaceY
                    hint = wid.sizeHint()
                    nextX = x + hint.width() + spaceX
                    lineHeight = 0
                    logging.debug(f"[FLOW] wrap -> new row at y={y}")
                if not testOnly:
                    wid.setGeometry(QRect(QPoint(x, y), hint))
                    logging.debug(f"[FLOW] place widget id={id(wid)} pos=({x},{y}) size=({hint.width()}x{hint.height()})")
                x = nextX
                lineHeight = max(lineHeight, hint.height())
            except Exception as e:
                logging.error(f"[FLOW] item layout error: {e}")
                traceback.print_exc()

        return y + lineHeight - rect.y() + b
