import logging
import sys
import platform
import os
import faulthandler

from PySide6.QtCore import qInstallMessageHandler, QtMsgType
from PySide6.QtWidgets import QApplication
from PySide6 import __version__ as PYSIDE6_VERSION

from pvmc.ui.main_window import PentaVMControlMainWindow
from pvmc.logging_utils import attach_to_root, set_debug_enabled
from pvmc.config import ConfigManager


def setup_logging():
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(fmt)
        root.addHandler(handler)
    # Respect user setting for debug verbosity (and silence entirely when off)
    try:
        cm = ConfigManager()
        debug_on = cm.get_bool('debug_logging', True)
    except Exception:
        debug_on = True
    set_debug_enabled(bool(debug_on))

    def _qt_log_handler(mode, context, message):
        prefix = '[QT] '
        if mode == QtMsgType.QtDebugMsg:
            logging.debug(prefix + message)
        elif mode == QtMsgType.QtInfoMsg:
            logging.info(prefix + message)
        elif mode == QtMsgType.QtWarningMsg:
            logging.warning(prefix + message)
        elif mode == QtMsgType.QtCriticalMsg:
            logging.error(prefix + message)
        elif mode == QtMsgType.QtFatalMsg:
            logging.critical(prefix + message)

    qInstallMessageHandler(_qt_log_handler)

    def _excepthook(exctype, value, tb):
        import traceback
        logging.critical(f'Uncaught exception: {exctype.__name__}: {value}')
        traceback.print_tb(tb)

    sys.excepthook = _excepthook
    # Attach in-memory buffer for diagnostics bundle
    try:
        attach_to_root()
    except Exception:
        pass


def main():
    setup_logging()
    faulthandler.enable()
    logging.info(f'Starting PentaVMControl... (pid={os.getpid()})')

    app = QApplication(sys.argv)
    app.setApplicationName('PentaVMControl')
    app.setDesktopFileName('PentaVMControl')
    logging.debug(f"[ENV] Python={sys.version.split()[0]} Platform={platform.platform()}")
    logging.debug(f"[ENV] PySide6={PYSIDE6_VERSION}")
    try:
        screens = app.screens()
        logging.debug(f"[ENV] Screens detected: {len(screens)}")
        for i, s in enumerate(screens):
            g = s.geometry()
            av = s.availableGeometry()
            logging.debug(f"[ENV] Screen[{i}] name='{s.name()}' geo=({g.x()},{g.y()},{g.width()}x{g.height()}) avail=({av.x()},{av.y()},{av.width()}x{av.height()}) dpr={s.devicePixelRatio()}")
    except Exception as e:
        logging.error(f"[ENV] Screen enumeration failed: {e}")

    win = PentaVMControlMainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
