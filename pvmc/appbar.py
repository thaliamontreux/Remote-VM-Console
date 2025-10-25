import ctypes
import platform
import logging
import traceback
from ctypes import wintypes

from PySide6.QtCore import QRect


ABM_NEW = 0
ABM_REMOVE = 1
ABM_QUERYPOS = 2
ABM_SETPOS = 3

ABE_LEFT = 0
ABE_TOP = 1
ABE_RIGHT = 2
ABE_BOTTOM = 3

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uCallbackMessage", wintypes.UINT),
        ("uEdge", wintypes.UINT),
        ("rc", RECT),
        ("lParam", wintypes.LPARAM),
    ]


class AppBarManager:
    def __init__(self):
        self.registered = False

    def _edge_to_const(self, edge):
        if edge == 'left':
            return ABE_LEFT
        if edge == 'right':
            return ABE_RIGHT
        return ABE_TOP

    def register(self, window, edge, screen_rect: QRect):
        if platform.system() != 'Windows':
            logging.debug(f'[APPBAR] Non-Windows platform; setting geometry to screen rect {screen_rect} and skipping AppBar registration')
            window.setGeometry(screen_rect)
            return
        try:
            hwnd = int(window.winId())
            w = max(1, int(window.width()))
            h = max(1, int(window.height()))
            logging.debug(f'[APPBAR] Register start: hwnd={hwnd}, edge={edge}, screen=({screen_rect.x()},{screen_rect.y()},{screen_rect.width()}x{screen_rect.height()}), windowSize=({w}x{h})')
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = wintypes.HWND(hwnd)
            abd.uCallbackMessage = 0
            abd.uEdge = self._edge_to_const(edge)
            abd.rc = RECT(screen_rect.left(), screen_rect.top(), screen_rect.right(), screen_rect.bottom())

            shapp = ctypes.windll.shell32

            if not self.registered:
                res_new = shapp.SHAppBarMessage(ABM_NEW, ctypes.byref(abd))
                logging.debug(f'[APPBAR] ABM_NEW -> {res_new}')

            # Query the system for the ideal position given our desired edge and extent
            res_q = shapp.SHAppBarMessage(ABM_QUERYPOS, ctypes.byref(abd))
            logging.debug(f'[APPBAR] ABM_QUERYPOS -> {res_q} rc=({abd.rc.left},{abd.rc.top},{abd.rc.right},{abd.rc.bottom})')

            # Adjust size on the specified edge
            if abd.uEdge == ABE_TOP:
                abd.rc.bottom = abd.rc.top + h
            elif abd.uEdge == ABE_LEFT:
                abd.rc.right = abd.rc.left + w
            elif abd.uEdge == ABE_RIGHT:
                abd.rc.left = abd.rc.right - w
            else:  # bottom
                abd.rc.top = abd.rc.bottom - h

            res_set = shapp.SHAppBarMessage(ABM_SETPOS, ctypes.byref(abd))
            logging.debug(f'[APPBAR] ABM_SETPOS -> {res_set} rc=({abd.rc.left},{abd.rc.top},{abd.rc.right},{abd.rc.bottom})')

            l = int(abd.rc.left)
            t = int(abd.rc.top)
            r = int(abd.rc.right)
            b = int(abd.rc.bottom)
            window.setGeometry(l, t, r - l, b - t)
            logging.debug(f'[APPBAR] Register done: setGeometry=({l},{t},{r-l}x{b-t}) registered={self.registered}')
            self.registered = True
        except Exception as e:
            logging.error(f'[APPBAR] Register failed: {e}')
            traceback.print_exc()
            window.setGeometry(screen_rect)

    def set_pos(self, window, edge, screen_rect: QRect):
        """Adjust an already-registered AppBar's position/size using ABM_SETPOS only.
        This avoids re-issuing ABM_NEW or ABM_QUERYPOS during dynamic resizing.
        """
        if platform.system() != 'Windows':
            window.setGeometry(screen_rect)
            return
        try:
            hwnd = int(window.winId())
            w = max(1, int(window.width()))
            h = max(1, int(window.height()))
            logging.debug(f'[APPBAR] set_pos: hwnd={hwnd} edge={edge} w={w} h={h} screen=({screen_rect.x()},{screen_rect.y()},{screen_rect.width()}x{screen_rect.height()})')
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = wintypes.HWND(hwnd)
            abd.uCallbackMessage = 0
            abd.uEdge = self._edge_to_const(edge)
            abd.rc = RECT(screen_rect.left(), screen_rect.top(), screen_rect.right(), screen_rect.bottom())
            # Directly set rc size on desired edge
            if abd.uEdge == ABE_TOP:
                abd.rc.bottom = abd.rc.top + h
            elif abd.uEdge == ABE_LEFT:
                abd.rc.right = abd.rc.left + w
            elif abd.uEdge == ABE_RIGHT:
                abd.rc.left = abd.rc.right - w
            else:
                abd.rc.top = abd.rc.bottom - h
            res_set = ctypes.windll.shell32.SHAppBarMessage(ABM_SETPOS, ctypes.byref(abd))
            logging.debug(f'[APPBAR] set_pos ABM_SETPOS -> {res_set} rc=({abd.rc.left},{abd.rc.top},{abd.rc.right},{abd.rc.bottom})')
            l = int(abd.rc.left)
            t = int(abd.rc.top)
            r = int(abd.rc.right)
            b = int(abd.rc.bottom)
            window.setGeometry(l, t, r - l, b - t)
        except Exception as e:
            logging.error(f'[APPBAR] set_pos failed: {e}')
            traceback.print_exc()
            window.setGeometry(screen_rect)

    def unregister(self, window):
        if not self.registered:
            return
        try:
            hwnd = int(window.winId())
            logging.debug(f'[APPBAR] Unregister start: hwnd={hwnd}')
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = wintypes.HWND(hwnd)
            ctypes.windll.shell32.SHAppBarMessage(ABM_REMOVE, ctypes.byref(abd))
            self.registered = False
        except Exception as e:
            logging.error(f'[APPBAR] Unregister failed: {e}')
            traceback.print_exc()
            self.registered = False
